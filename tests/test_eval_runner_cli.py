# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

import pytest
from helpers import TrackingProvider, write_dataset, write_scorer

import src.hephaestus.runs.eval_runner as eval_runner
from src.hephaestus.runs.eval_runner import _validate_eval_paths, load_eval_config, run_evaluation


def test_eval_runner_uses_tenant_scorer_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"case_id":"c1","task_type":"security","context":{"inputs.Name":"x"},"expected":{},"metadata":{}}\n',
        encoding="utf-8",
    )

    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 75.0, 'score_breakdown': {'signal_a': 100.0, 'signal_b': 50.0}}
""",
        encoding="utf-8",
    )

    chain_file = _write_single_node_chain(tmp_path, template)
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset
    )
    loaded = load_eval_config(config_path)

    class StubClient:
        def generate(self, _messages):
            return "Any model response text."

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _provider, _settings: StubClient(),
    )

    results = run_evaluation(loaded)
    assert len(results) == 1
    assert results[0]["composite_score"] == 75.0
    assert results[0]["score_breakdown"]["signal_a"] == 100.0
    assert "output_text" in results[0]


def test_eval_runner_validates_all_cases_before_provider_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        (
            '{"case_id":"c1","task_type":"security",'
            '"context":{"inputs.Name":"x"},"expected":{},"metadata":{}}\n'
            '{"case_id":"c2","task_type":"security",'
            '"context":{"inputs.Name":"y"},"expected":{},"metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        if case.case_id == 'c2':
            raise ValueError('bad case')
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 75.0, 'score_breakdown': {'signal_a': 100.0, 'signal_b': 50.0}}
""",
        encoding="utf-8",
    )

    chain_file = _write_single_node_chain(tmp_path, template)
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset
    )
    loaded = load_eval_config(config_path)

    class StubClient:
        def generate(self, _messages):
            raise AssertionError("provider.generate should not be called")

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _provider, _settings: StubClient(),
    )

    with pytest.raises(ValueError, match="bad case"):
        run_evaluation(loaded)


def test_eval_runner_accepts_sagemaker_provider(tmp_path: Path):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"case_id":"c1","task_type":"security","context":{"inputs.Name":"x"},"expected":{},"metadata":{}}\n',
        encoding="utf-8",
    )

    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 100.0, 'score_breakdown': {'format': 100.0}}
""",
        encoding="utf-8",
    )

    chain_file = _write_single_node_chain(tmp_path, template)
    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "sagemaker",
        "provider_settings": {"api_url": "https://example.execute-api.us-west-2.amazonaws.com/prod/invoke"},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {"prompt_paths": {"classify": str(template)}},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.provider == "sagemaker"


def _write_base_config(tmp_path: Path) -> dict:
    """Helper to create common config fixtures (dataset, scorer, etc.)."""
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"case_id":"c1","task_type":"security","context":{"inputs.Name":"x"},"expected":{},"metadata":{}}\n',
        encoding="utf-8",
    )
    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 100.0, 'score_breakdown': {'format': 100.0}}
""",
        encoding="utf-8",
    )
    return {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }


def test_load_chain_config(tmp_path: Path) -> None:
    """Valid chain config loads correctly with chain field populated."""
    base = _write_base_config(tmp_path)
    base["chain"] = {
        "path": "tenants/demo/chains/classify.py",
        "fn": "build_chain",
        "config": {"prompt_paths": {"classify": "tenants/demo/prompts/v1.md"}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.chain is not None
    assert loaded.chain.path == "tenants/demo/chains/classify.py"
    assert loaded.chain.fn == "build_chain"
    assert loaded.chain.config == {"prompt_paths": {"classify": "tenants/demo/prompts/v1.md"}}


def test_load_chain_config_with_chain_config(tmp_path: Path) -> None:
    """chain.config dict is passed through correctly."""
    base = _write_base_config(tmp_path)
    chain_cfg = {"key1": "value1", "key2": {"nested": True}}
    base["chain"] = {
        "path": "chains/my_chain.py",
        "fn": "build_chain",
        "config": chain_cfg,
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.chain is not None
    assert loaded.chain.config == chain_cfg


def test_load_config_defaults_only_present_textual_variant_dimensions(
    tmp_path: Path,
) -> None:
    base = _write_base_config(tmp_path)
    base["chain"] = {
        "path": "chains/my_chain.py",
        "config": {
            "prompt_paths": {"answer": "prompts/answer.md"},
            "skill_paths": ["skills/research.md"],
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)

    assert loaded.comparison_variant_dimensions == ["prompts", "skills"]


def test_load_config_accepts_explicit_non_textual_variant_dimensions(
    tmp_path: Path,
) -> None:
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py", "config": {}}
    base["comparison"] = {
        "variant_dimensions": ["chain_structure", "sampling"],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)

    assert loaded.comparison_variant_dimensions == ["chain_structure", "sampling"]


@pytest.mark.parametrize(
    "dimensions",
    [
        ["dataset"],
        ["prompts", "prompts"],
        "prompts",
    ],
)
def test_load_config_rejects_invalid_variant_dimensions(
    tmp_path: Path,
    dimensions: object,
) -> None:
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py", "config": {}}
    base["comparison"] = {"variant_dimensions": dimensions}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    with pytest.raises(ValueError, match="comparison.variant_dimensions"):
        load_eval_config(config_path)


def test_load_config_requires_chain(tmp_path: Path) -> None:
    """Config without 'chain' key raises ValueError."""
    base = _write_base_config(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    with pytest.raises(ValueError, match="must specify 'chain'"):
        load_eval_config(config_path)


def test_load_chain_config_default_fn(tmp_path: Path) -> None:
    """fn defaults to 'build_chain' when not specified."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py"}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.chain is not None
    assert loaded.chain.fn == "build_chain"
    assert loaded.chain.config == {}


def test_load_chain_rejects_empty_path(tmp_path: Path) -> None:
    """chain.path must be non-empty."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": ""}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    with pytest.raises(ValueError, match="chain.path"):
        load_eval_config(config_path)


# ---------------------------------------------------------------------------
# Helpers for chain-config tests
# ---------------------------------------------------------------------------


def _write_single_node_chain(tmp_path: Path, template_path: Path) -> Path:
    """Create a 1-node chain .py file that wraps a single prompt template."""
    chain_file = tmp_path / "chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.nodes import make_llm_node
from pathlib import Path

def build_chain(provider, config):
    prompt_path = Path(config['prompt_paths']['classify'])
    graph = StateGraph(dict)
    graph.add_node('classify', make_llm_node(provider, prompt_path))
    graph.set_entry_point('classify')
    graph.add_edge('classify', END)
    return graph.compile()
""",
        encoding="utf-8",
    )
    return chain_file


def _write_chain_config(
    tmp_path: Path,
    chain_file: Path,
    prompt_paths: dict,
    scorer_path: Path,
    dataset_path: Path,
    *,
    max_workers: int | None = None,
    output_dir: Path | None = None,
    config_name: str = "config.json",
) -> Path:
    """Write a chain-based eval config JSON file."""
    config_path = tmp_path / config_name
    config: dict = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset_path)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {"prompt_paths": prompt_paths},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer_path)}},
        "output_dir": str(output_dir or tmp_path / "out"),
    }
    if max_workers is not None:
        config["max_workers"] = max_workers
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


# ---------------------------------------------------------------------------
# Chain-config versions of eval runner tests
# ---------------------------------------------------------------------------


def test_eval_runner_uses_tenant_scorer_output_with_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chain config: scorer output flows through to results."""
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"case_id":"c1","task_type":"security","context":{"inputs.Name":"x"},"expected":{},"metadata":{}}\n',
        encoding="utf-8",
    )

    variant = tmp_path / "variant.md"
    variant.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 75.0, 'score_breakdown': {'signal_a': 100.0, 'signal_b': 50.0}}
""",
        encoding="utf-8",
    )

    chain_file = _write_single_node_chain(tmp_path, variant)
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(variant)}, scorer, dataset
    )
    loaded = load_eval_config(config_path)

    class StubClient:
        def generate(self, _messages):
            return "Any model response text."

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _provider, _settings: StubClient(),
    )

    results = run_evaluation(loaded)
    assert len(results) == 1
    assert results[0]["composite_score"] == 75.0
    assert results[0]["score_breakdown"]["signal_a"] == 100.0
    assert "output_text" in results[0]


def test_eval_runner_validates_all_cases_before_chain_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chain config: validation runs for all cases before any chain.invoke call."""
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        (
            '{"case_id":"c1","task_type":"security",'
            '"context":{"inputs.Name":"x"},"expected":{},"metadata":{}}\n'
            '{"case_id":"c2","task_type":"security",'
            '"context":{"inputs.Name":"y"},"expected":{},"metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    variant = tmp_path / "variant.md"
    variant.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        if case.case_id == 'c2':
            raise ValueError('bad case')
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 75.0, 'score_breakdown': {'signal_a': 100.0, 'signal_b': 50.0}}
""",
        encoding="utf-8",
    )

    chain_file = _write_single_node_chain(tmp_path, variant)
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(variant)}, scorer, dataset
    )
    loaded = load_eval_config(config_path)

    class StubClient:
        def generate(self, _messages):
            raise AssertionError("provider.generate should not be called")

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _provider, _settings: StubClient(),
    )

    with pytest.raises(ValueError, match="bad case"):
        run_evaluation(loaded)


def test_eval_runner_chain_config_with_step_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multi-step chain config: step_outputs included in results."""
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"case_id":"c1","task_type":"security","context":{"inputs.Name":"x"},"expected":{},"metadata":{}}\n',
        encoding="utf-8",
    )

    template1 = tmp_path / "step1.md"
    template1.write_text("User: analyze ${inputs.Name}", encoding="utf-8")
    template2 = tmp_path / "step2.md"
    template2.write_text("User: summarize ${steps.step1.output}", encoding="utf-8")

    chain_file = tmp_path / "multi_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.nodes import make_llm_node
from pathlib import Path

def build_chain(provider, config):
    p1 = Path(config['prompt_paths']['step1'])
    p2 = Path(config['prompt_paths']['step2'])
    graph = StateGraph(dict)
    graph.add_node('step1', make_llm_node(provider, p1, output_key='step1'))
    graph.add_node('step2', make_llm_node(provider, p2, output_key='step2'))
    graph.set_entry_point('step1')
    graph.add_edge('step1', 'step2')
    graph.add_edge('step2', END)
    return graph.compile()
""",
        encoding="utf-8",
    )

    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 100.0, 'score_breakdown': {'format': 100.0}}
""",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {
                "prompt_paths": {
                    "step1": str(template1),
                    "step2": str(template2),
                },
            },
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    tracking = TrackingProvider(responses=["step1 result", "step2 result"])
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: tracking,
    )

    loaded = load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 1
    assert "step_outputs" in results[0]
    assert results[0]["step_outputs"]["step1"] == "step1 result"
    assert results[0]["step_outputs"]["step2"] == "step2 result"
    assert results[0]["output_text"] == "step2 result"
    assert len(tracking.calls) == 2


# ---------------------------------------------------------------------------
# Preflight path validation tests
# ---------------------------------------------------------------------------


def test_validate_eval_paths_missing_dataset(tmp_path: Path) -> None:
    chain_file = tmp_path / "chain.py"
    chain_file.write_text("def build_chain(p, c): pass", encoding="utf-8")

    config = _make_eval_config(
        tmp_path,
        dataset_path=str(tmp_path / "nonexistent.jsonl"),
        chain_path=str(chain_file),
    )
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        _validate_eval_paths(config)


def test_validate_eval_paths_missing_chain(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("{}\n", encoding="utf-8")

    config = _make_eval_config(
        tmp_path,
        dataset_path=str(dataset),
        chain_path=str(tmp_path / "nonexistent_chain.py"),
    )
    with pytest.raises(FileNotFoundError, match="Chain module not found"):
        _validate_eval_paths(config)


def test_validate_eval_paths_missing_prompt(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("{}\n", encoding="utf-8")
    chain_file = tmp_path / "chain.py"
    chain_file.write_text("def build_chain(p, c): pass", encoding="utf-8")

    config = _make_eval_config(
        tmp_path,
        dataset_path=str(dataset),
        chain_path=str(chain_file),
        prompt_paths={"classify": str(tmp_path / "missing_prompt.md")},
    )
    with pytest.raises(FileNotFoundError, match="Prompt file not found for step 'classify'"):
        _validate_eval_paths(config)


# ---------------------------------------------------------------------------
# max_workers config parsing tests
# ---------------------------------------------------------------------------


def test_load_eval_config_max_workers_default(tmp_path: Path) -> None:
    """No max_workers key in JSON -> EvalConfig.max_workers is None."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py"}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.max_workers is None


def test_load_eval_config_max_workers_set(tmp_path: Path) -> None:
    """max_workers: 4 in JSON -> EvalConfig.max_workers == 4."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py"}
    base["max_workers"] = 4
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.max_workers == 4


@pytest.mark.parametrize("bad_value", [0, -1, -10, "4", 1.5, True])
def test_load_eval_config_max_workers_invalid(tmp_path: Path, bad_value: object) -> None:
    """max_workers of 0, negative, non-int -> ValueError."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py"}
    base["max_workers"] = bad_value
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    with pytest.raises(ValueError, match="max_workers"):
        load_eval_config(config_path)


# ---------------------------------------------------------------------------
# Concurrent execution tests
# ---------------------------------------------------------------------------


def test_eval_runner_concurrent_produces_correct_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """max_workers=2 with 3 cases: all results returned in input order."""
    dataset = write_dataset(tmp_path, cases=3)
    scorer = write_scorer(tmp_path)
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")

    chain_file = _write_single_node_chain(tmp_path, template)
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset,
        max_workers=2,
    )

    tracking = TrackingProvider(responses=["response"])
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: tracking,
    )

    results = run_evaluation(load_eval_config(config_path))

    assert len(results) == 3
    assert [r["case_id"] for r in results] == ["c1", "c2", "c3"]
    for r in results:
        assert r["composite_score"] == 100.0
        assert "output_text" in r


def test_eval_runner_max_workers_one_is_sequential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """max_workers=1 produces the same results as max_workers=None (sequential)."""
    dataset = write_dataset(tmp_path)
    scorer = write_scorer(tmp_path, composite_score=88.0, breakdown_key="accuracy")
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    chain_file = _write_single_node_chain(tmp_path, template)
    prompts = {"classify": str(template)}

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: TrackingProvider(responses=["sequential response"]),
    )

    config_w1 = _write_chain_config(
        tmp_path, chain_file, prompts, scorer, dataset,
        max_workers=1, output_dir=tmp_path / "out_w1", config_name="config_w1.json",
    )
    config_none = _write_chain_config(
        tmp_path, chain_file, prompts, scorer, dataset,
        output_dir=tmp_path / "out_none", config_name="config_none.json",
    )

    results_w1 = run_evaluation(load_eval_config(config_w1))
    results_none = run_evaluation(load_eval_config(config_none))

    assert len(results_w1) == len(results_none) == 1
    assert results_w1[0]["case_id"] == results_none[0]["case_id"]
    assert results_w1[0]["composite_score"] == results_none[0]["composite_score"]
    assert results_w1[0]["output_text"] == results_none[0]["output_text"]


# ---------------------------------------------------------------------------
# Progress tracking integration tests
# ---------------------------------------------------------------------------


def test_sequential_eval_writes_progress_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sequential eval writes progress.json with status=completed and correct count."""
    dataset = write_dataset(tmp_path, cases=2)
    scorer = write_scorer(tmp_path)
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    chain_file = _write_single_node_chain(tmp_path, template)
    out_dir = tmp_path / "out"
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset,
        output_dir=out_dir,
    )

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: TrackingProvider(responses=["resp"]),
    )

    run_evaluation(load_eval_config(config_path))

    from src.hephaestus.runs.progress import read_progress

    progress = read_progress(out_dir)
    assert progress is not None
    assert progress.status == "completed"
    assert progress.completed_cases == 2
    assert progress.total_cases == 2
    assert progress.avg_composite_score is not None


def test_concurrent_eval_writes_progress_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Concurrent eval (max_workers=2) writes correct progress.json."""
    dataset = write_dataset(tmp_path, cases=3)
    scorer = write_scorer(tmp_path)
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    chain_file = _write_single_node_chain(tmp_path, template)
    out_dir = tmp_path / "out"
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset,
        max_workers=2, output_dir=out_dir,
    )

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: TrackingProvider(responses=["resp"]),
    )

    run_evaluation(load_eval_config(config_path))

    from src.hephaestus.runs.progress import read_progress

    progress = read_progress(out_dir)
    assert progress is not None
    assert progress.status == "completed"
    assert progress.completed_cases == 3
    assert progress.total_cases == 3


def test_cli_eval_progress_subcommand(tmp_path: Path) -> None:
    """CLI eval-progress subcommand outputs correct info."""

    from src.hephaestus.runs.progress import ProgressTracker

    out_dir = tmp_path / "out"
    tracker = ProgressTracker(out_dir, total_cases=5)

    from src.hephaestus.types import EvalCaseResult

    tracker.record_result(
        EvalCaseResult(
            case_id="c1",
            task_type="security",
            diagnostics=[],
            score_breakdown={"quality": 80.0},
            composite_score=80.0,
            output_text="output",
            step_outputs={},
        )
    )
    tracker.mark_completed()

    from src.hephaestus.cli import build_parser

    parser = build_parser()

    # Test human-readable output
    args = parser.parse_args(["eval-progress", "--output-dir", str(out_dir)])
    assert args.command == "eval-progress"
    assert args.output_dir == str(out_dir)
    assert args.json_output is False

    # Test JSON flag
    args = parser.parse_args(["eval-progress", "--output-dir", str(out_dir), "--json"])
    assert args.json_output is True


def test_cli_eval_progress_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """CLI eval-progress handles missing progress file gracefully."""
    import sys

    from src.hephaestus.cli import main

    sys.argv = ["hephaestus", "eval-progress", "--output-dir", str(tmp_path / "nonexistent")]
    main()
    captured = capsys.readouterr()
    assert "No progress file found" in captured.out


def test_eval_marks_failed_on_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per-case provider failures remain distinct from successful zero scores."""
    dataset = write_dataset(tmp_path, cases=2)
    scorer = write_scorer(tmp_path)
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    chain_file = _write_single_node_chain(tmp_path, template)
    out_dir = tmp_path / "out"
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset,
        output_dir=out_dir,
    )

    # Inject a provider that raises an exception
    def failing_provider(_p, _s):
        class FailingProvider:
            def generate(self, messages, **kwargs):
                raise RuntimeError("Simulated failure")
        return FailingProvider()

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        failing_provider,
    )

    config = load_eval_config(config_path)
    results = run_evaluation(config)

    assert len(results) == 2
    for r in results:
        assert r["output_text"] == ""
        assert r["execution_status"] == "failed"
        assert r["execution_error"] == {
            "phase": "chain",
            "category": "runtime",
            "summary": "Chain execution failed.",
        }
        assert "Simulated failure" not in json.dumps(r)

    from src.hephaestus.runs.progress import read_progress

    progress = read_progress(out_dir)
    assert progress is not None
    assert progress.status == "failed"
    assert progress.successful_case_ids == []
    assert progress.failed_case_ids == ["c1", "c2"]


def test_eval_marks_failed_when_bundle_publication_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-manifest publication failure leaves progress failed."""
    dataset = write_dataset(tmp_path, cases=1)
    scorer = write_scorer(tmp_path)
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    chain_file = _write_single_node_chain(tmp_path, template)
    out_dir = tmp_path / "out"
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset,
        output_dir=out_dir,
    )

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: TrackingProvider(responses=["resp"]),
    )

    class SuccessfulChain:
        def stream(self, _state):
            yield {"classify": {"output_text": "resp", "step_outputs": {}}}

    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: SuccessfulChain(),
    )

    def failing_publish(*args, **kwargs):
        raise IOError("Simulated write failure")

    monkeypatch.setattr(eval_runner.RunBundleWriter, "publish", failing_publish)

    config = load_eval_config(config_path)
    with pytest.raises(IOError):
        run_evaluation(config)

    from src.hephaestus.runs.progress import read_progress

    progress = read_progress(out_dir)
    assert progress is not None
    assert progress.status == "failed"
    assert progress.completed_cases == 1  # Case was evaluated
    assert not (out_dir / "run_manifest.json").exists()


def test_eval_marks_failed_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eval marks progress as failed when interrupted with Ctrl+C."""
    dataset = write_dataset(tmp_path, cases=2)
    scorer = write_scorer(tmp_path)
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    chain_file = _write_single_node_chain(tmp_path, template)
    out_dir = tmp_path / "out"
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset,
        output_dir=out_dir,
    )

    # Inject a provider that raises KeyboardInterrupt
    def interrupting_provider(_p, _s):
        class InterruptingProvider:
            def generate(self, messages, **kwargs):
                raise KeyboardInterrupt("Simulated Ctrl+C")
        return InterruptingProvider()

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        interrupting_provider,
    )

    config = load_eval_config(config_path)
    with pytest.raises(KeyboardInterrupt):
        run_evaluation(config)

    from src.hephaestus.runs.progress import read_progress

    progress = read_progress(out_dir)
    assert progress is not None
    assert progress.status == "failed"


# ---------------------------------------------------------------------------
# run_id config parsing tests
# ---------------------------------------------------------------------------


def test_load_eval_config_with_run_id(tmp_path: Path) -> None:
    """run_id in JSON is parsed and stored on EvalConfig."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py"}
    base["run_id"] = "hephaestus-demo-m5kx7r"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.run_id == "hephaestus-demo-m5kx7r"


def test_load_eval_config_without_run_id(tmp_path: Path) -> None:
    """No run_id key in JSON -> EvalConfig.run_id is None."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py"}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    loaded = load_eval_config(config_path)
    assert loaded.run_id is None


def test_load_eval_config_invalid_run_id(tmp_path: Path) -> None:
    """Invalid run_id raises ValueError."""
    base = _write_base_config(tmp_path)
    base["chain"] = {"path": "chains/my_chain.py"}
    base["run_id"] = "bad-format"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid run_id"):
        load_eval_config(config_path)


def test_run_evaluation_writes_run_id_to_run_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_config.json includes run_id after run_evaluation()."""
    dataset = write_dataset(tmp_path, cases=1)
    scorer = write_scorer(tmp_path)
    template = tmp_path / "template.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    chain_file = _write_single_node_chain(tmp_path, template)
    out_dir = tmp_path / "out"
    config_path = _write_chain_config(
        tmp_path, chain_file, {"classify": str(template)}, scorer, dataset,
        output_dir=out_dir,
    )

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: TrackingProvider(responses=["resp"]),
    )

    run_evaluation(load_eval_config(config_path))

    run_config = json.loads((out_dir / "run_config.json").read_text(encoding="utf-8"))
    assert "run_id" in run_config
    assert run_config["run_id"].startswith("hephaestus-demo-")


def _make_eval_config(
    tmp_path: Path,
    dataset_path: str,
    chain_path: str,
    prompt_paths: dict | None = None,
) -> "EvalConfig":  # noqa: F821
    from src.hephaestus.types import ChainConfig, EvalConfig

    return EvalConfig(
        tenant_id="demo",
        provider="baseten",
        provider_settings={},
        dataset_path=dataset_path,
        scoring_profile={},
        output_dir=str(tmp_path / "out"),
        chain=ChainConfig(
            path=chain_path,
            fn="build_chain",
            config={"prompt_paths": prompt_paths} if prompt_paths else {},
        ),
    )
