# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""End-to-end tests for the headless optimization coordinator.

Each test runs the real eval runner against a throwaway tenant with a stub task
model and scripted role responses, so the loop, eval wiring, ledger, and split
discipline are all exercised without network access.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

import src.hephaestus.optimization.coordinator as coordinator
import src.hephaestus.runs.eval_runner as eval_runner
from src.hephaestus import cli
from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider
from src.hephaestus.optimization.policy import load_policy
from src.hephaestus.optimization.roles import ANALYST_SYSTEM_PROMPT

LICENSE_HEADER = """\
<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

"""
VERBOSE_PROMPT = "User: ${question}"
STRICT_PROMPT = """\
System: Respond with exactly one word: yes or no.

User: ${question}"""
HEAT_PROMPT = """\
System: Mind the heat.

User: ${question}"""
WORSE_PROMPT = """\
System: Explain your reasoning in full sentences.

User: ${question}"""

TRAIN = {"Is fire hot?": "yes", "Is ice hot?": "no", "Is the sun bright?": "yes", "Is coal white?": "no"}
VAL = {"Is snow cold?": "yes", "Is lava cold?": "no", "Is honey sweet?": "yes"}
TEST = {"Is salt sweet?": "no", "Is sugar sweet?": "yes"}
ALL_ANSWERS = {**TRAIN, **VAL, **TEST}


class StubModel:
    """Answers correctly, but verbosely unless told to use one word; truncates to max_tokens chars.

    A prompt that mentions heat also gets one-word answers, but only for questions about heat.
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        self.max_tokens = int(settings["max_tokens"])

    def generate(self, messages: List[Dict[str, str]]) -> str:
        text = "\n".join(message["content"] for message in messages)
        answer = next(value for question, value in ALL_ANSWERS.items() if question in text)
        concise = "exactly one word" in text or ("heat" in text and " hot?" in text)
        reply = answer if concise else f"Well, I think the answer is {answer}."
        return reply[: self.max_tokens]


class ScriptedGenerator:
    """Role generator returning scripted responses per role; the last response repeats."""

    def __init__(self, script: Dict[str, List[Any]]) -> None:
        self.script = {role: list(responses) for role, responses in script.items()}
        self.calls: List[Dict[str, Any]] = []
        self.system_prompts: List[str] = []

    def generate_json(self, system_prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append(copy.deepcopy(dict(payload)))
        self.system_prompts.append(system_prompt)
        queue = self.script[payload["role"]]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        return item(payload) if callable(item) else copy.deepcopy(item)

    def calls_for(self, role: str) -> List[Dict[str, Any]]:
        return [call for call in self.calls if call["role"] == role]


def _prompt_plan(technique: str = "output-format constraint") -> Dict[str, Any]:
    return {
        "clusters": [{"label": "verbose answers", "count": 2, "case_ids": ["train-0"], "level": "prompt"}],
        "plan": {
            "level": "prompt",
            "module": "answer",
            "technique": technique,
            "hypothesis": "Constraining the output to one word fixes exact-match failures.",
            "target_case_ids": [],
        },
    }


def _parameter_plan(max_tokens: int) -> Dict[str, Any]:
    return {
        "clusters": [],
        "plan": {
            "level": "parameter",
            "parameter_changes": {"provider_settings.max_tokens": max_tokens},
            "technique": "raise output budget",
            "hypothesis": "Truncated answers fail exact match.",
        },
    }


PASS_REVIEW = {"verdict": "pass", "issues": []}


def _proposal_script(prompt: str) -> Dict[str, List[Any]]:
    """Script one prompt plan whose proposal is ``prompt`` and passes LLM review."""
    return {"analyst": [_prompt_plan()], "prompt_proposer": [{"prompt": prompt}], "reviewer": [PASS_REVIEW]}


@pytest.fixture
def tenant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., Path]:
    """Return a factory that writes a throwaway tenant and its policy, returning the policy path."""
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda _provider, settings: StubModel(settings))

    def make(
        prompt: str = VERBOSE_PROMPT,
        max_tokens: int = 64,
        **policy_overrides: Any,
    ) -> Path:
        root = tmp_path / "tenant"
        prompt_dir = root / "prompts" / "answer"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "variant-001.md").write_text(LICENSE_HEADER + prompt + "\n", encoding="utf-8")
        (root / "chain.py").write_text(
            """\
from pathlib import Path

from langgraph.graph import END, StateGraph

from src.hephaestus.chains.nodes import make_llm_node


def build_chain(provider, config):
    graph = StateGraph(dict)
    graph.add_node("answer", make_llm_node(provider, Path(config["prompt_paths"]["answer"])))
    graph.set_entry_point("answer")
    graph.add_edge("answer", END)
    return graph.compile()
""",
            encoding="utf-8",
        )
        (root / "scorer.py").write_text(
            """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer


class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        match = 100.0 if output_text.strip().lower() == case.expected["answer"] else 0.0
        return {"composite_score": match, "score_breakdown": {"exact_match": match}}
""",
            encoding="utf-8",
        )
        for split, answers in (("train", TRAIN), ("val", VAL), ("test", TEST)):
            rows = [
                {
                    "case_id": f"{split}-{index}",
                    "task_type": "qa",
                    "context": {"question": question},
                    "expected": {"answer": answer},
                    "metadata": {"source": f"{split}-source"},
                }
                for index, (question, answer) in enumerate(answers.items())
            ]
            (root / f"{split}.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
        base_config = {
            "tenant_id": "demo",
            "provider": "baseten",
            "provider_settings": {"temperature": 0.0, "max_tokens": max_tokens},
            "dataset": {"path": str(root / "train.jsonl")},
            "chain": {
                "path": str(root / "chain.py"),
                "config": {"prompt_paths": {"answer": str(prompt_dir / "variant-001.md")}},
            },
            "scoring_profile": {"scorer": {"module_path": str(root / "scorer.py")}},
            "output_dir": str(root / "unused"),
        }
        (root / "base-config.json").write_text(json.dumps(base_config), encoding="utf-8")
        policy = {
            "base_config": str(root / "base-config.json"),
            "datasets": {
                "train": str(root / "train.jsonl"),
                "val": str(root / "val.jsonl"),
                "test": str(root / "test.jsonl"),
            },
            "levels": ["prompt"],
            "acceptance": {"min_val_delta": 1.0},
            "budget": {"max_iterations": 5, "plateau_patience": 3},
        }
        policy.update(policy_overrides)
        policy_path = root / "policy.json"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        return policy_path

    return make


def _run(policy_path: Path, generator: ScriptedGenerator, **kwargs: Any) -> coordinator.OptimizationResult:
    workspace = policy_path.parent / "workspace"
    return coordinator.run_optimization(load_policy(policy_path), workspace, generator=generator, **kwargs)


def _ledger(result: coordinator.OptimizationResult) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in result.ledger_path.read_text(encoding="utf-8").splitlines()]


def _eval_dirs(policy_path: Path) -> List[str]:
    evals = policy_path.parent / "workspace" / "evals"
    return sorted(path.name for path in evals.iterdir())


class TestPromptLevel:
    def test_improvement_is_accepted_as_new_variant_file(self, tenant: Callable[..., Path]) -> None:
        """A better prompt is written to a new variant file, evaluated, and accepted."""
        policy_path = tenant()
        generator = ScriptedGenerator(_proposal_script(STRICT_PROMPT))

        result = _run(policy_path, generator)

        assert result.stop_reason == "no_train_failures"
        assert (result.baseline.train.score, result.baseline.val.score) == (0.0, 0.0)
        assert result.best.candidate_id == "c001"
        assert (result.best.train.score, result.best.val.score) == (100.0, 100.0)
        prompt_dir = policy_path.parent / "prompts" / "answer"
        parent_text = (prompt_dir / "variant-001.md").read_text(encoding="utf-8")
        assert parent_text == LICENSE_HEADER + VERBOSE_PROMPT + "\n"
        variant_text = (prompt_dir / "variant-002.md").read_text(encoding="utf-8")
        assert variant_text == LICENSE_HEADER + STRICT_PROMPT + "\n"
        best_config = json.loads(result.best_config_path.read_text(encoding="utf-8"))
        assert best_config["chain"]["config"]["prompt_paths"]["answer"] == str(prompt_dir / "variant-002.md")
        assert best_config["dataset"]["path"] == str(policy_path.parent / "val.jsonl")
        assert [record["type"] for record in _ledger(result)] == ["baseline", "iteration", "final"]
        assert generator.system_prompts[0] == ANALYST_SYSTEM_PROMPT

    def test_proposer_sees_prompt_body_without_license_header(self, tenant: Callable[..., Path]) -> None:
        """The license header is preserved on disk but never shown to or rewritten by the proposer."""
        policy_path = tenant()
        generator = ScriptedGenerator(_proposal_script(STRICT_PROMPT))

        _run(policy_path, generator)

        proposal_payload = generator.calls_for("prompt_proposer")[0]
        assert proposal_payload["current_prompt"] == VERBOSE_PROMPT + "\n"
        assert proposal_payload["placeholders"] == ["question"]
        assert generator.calls_for("analyst")[0]["modules"] == {"answer": VERBOSE_PROMPT + "\n"}

    def test_static_review_failure_gets_one_revision(self, tenant: Callable[..., Path]) -> None:
        """A blocked proposal is sent back once with its issues, and the revision is evaluated."""
        policy_path = tenant()
        dropped_placeholder = "System: Respond with exactly one word.\n\nUser: the question"
        generator = ScriptedGenerator(
            {
                "analyst": [_prompt_plan()],
                "prompt_proposer": [{"prompt": dropped_placeholder}, {"prompt": STRICT_PROMPT}],
                "reviewer": [PASS_REVIEW],
            }
        )

        result = _run(policy_path, generator)

        proposals = generator.calls_for("prompt_proposer")
        assert len(proposals) == 2
        assert proposals[1]["previous_attempt"] == dropped_placeholder
        assert [issue["check"] for issue in proposals[1]["review_issues"]] == ["placeholder_integrity"]
        assert len(generator.calls_for("reviewer")) == 1
        assert result.best.candidate_id == "c001"

    def test_named_heldout_input_is_sent_back_without_naming_it(self, tenant: Callable[..., Path]) -> None:
        """A proposal that names a val input is blocked; the issue returned to the proposer is generic."""
        policy_path = tenant()
        names_val_case = STRICT_PROMPT + "\nFor example, the question Is snow cold? gets one word."
        generator = ScriptedGenerator(
            {
                "analyst": [_prompt_plan()],
                "prompt_proposer": [{"prompt": names_val_case}, {"prompt": STRICT_PROMPT}],
                "reviewer": [PASS_REVIEW],
            }
        )

        result = _run(policy_path, generator)

        issues = generator.calls_for("prompt_proposer")[1]["review_issues"]
        assert [issue["check"] for issue in issues] == ["specific_input_reference"]
        assert "snow" not in json.dumps(issues)
        assert result.best.candidate_id == "c001"

    def test_failed_revision_rejects_candidate_without_eval(self, tenant: Callable[..., Path]) -> None:
        """When the revision is still blocked, no variant is written and no eval runs."""
        policy_path = tenant(budget={"max_iterations": 1})
        leaky = "System: Respond with exactly one word.\n\nUser: ${question} (case train-1)"
        generator = ScriptedGenerator(
            {"analyst": [_prompt_plan()], "prompt_proposer": [{"prompt": leaky}], "reviewer": [PASS_REVIEW]}
        )

        result = _run(policy_path, generator)

        iteration = _ledger(result)[1]
        assert iteration["reason"] == "review_failed"
        assert iteration["review"][-1][0]["check"] == "case_id_reference"
        assert _eval_dirs(policy_path) == ["c000-train", "c000-val"]
        assert not (policy_path.parent / "prompts" / "answer" / "variant-002.md").exists()

    def test_llm_review_block_rejects_candidate(self, tenant: Callable[..., Path]) -> None:
        """A blocking LLM-review issue counts as a failed review."""
        policy_path = tenant(budget={"max_iterations": 1})
        generator = ScriptedGenerator(
            {
                "analyst": [_prompt_plan()],
                "prompt_proposer": [{"prompt": STRICT_PROMPT}],
                "reviewer": [
                    {"verdict": "fail", "issues": [{"check": "train_leakage", "severity": "block"}]}
                ],
            }
        )

        result = _run(policy_path, generator)

        assert _ledger(result)[1]["reason"] == "review_failed"
        assert len(generator.calls_for("prompt_proposer")) == 2

    def test_train_regression_skips_val_eval(self, tenant: Callable[..., Path]) -> None:
        """A candidate that regresses on train is rejected before any val eval."""
        policy_path = tenant(prompt=STRICT_PROMPT, max_tokens=2, budget={"max_iterations": 1})
        generator = ScriptedGenerator(_proposal_script(WORSE_PROMPT))

        result = _run(policy_path, generator)

        iteration = _ledger(result)[1]
        assert iteration["reason"] == "train_screen"
        assert iteration["train_delta"] == -50.0
        assert _eval_dirs(policy_path) == ["c000-train", "c000-val", "c001-train"]
        assert result.best.candidate_id == "c000"


class TestTrainingContext:
    def test_roles_see_every_training_case_with_metadata(self, tenant: Callable[..., Path]) -> None:
        """The analyst and proposer get a full training overview, including passing cases."""
        policy_path = tenant(prompt=STRICT_PROMPT, max_tokens=2, budget={"max_iterations": 1})
        generator = ScriptedGenerator(_proposal_script(WORSE_PROMPT))

        _run(policy_path, generator)

        overview = generator.calls_for("analyst")[0]["training_overview"]
        assert [(row["case_id"], row["passed"]) for row in overview] == [
            ("train-0", False),
            ("train-1", True),
            ("train-2", False),
            ("train-3", True),
        ]
        assert overview[0] == {
            "case_id": "train-0",
            "context": {"question": "Is fire hot?"},
            "expected": {"answer": "yes"},
            "metadata": {"source": "train-source"},
            "passed": False,
        }
        proposer = generator.calls_for("prompt_proposer")[0]
        assert proposer["training_overview"] == overview
        assert proposer["clusters"][0]["label"] == "verbose answers"
        assert generator.calls_for("analyst")[0]["failing_cases"][0]["metadata"] == {"source": "train-source"}

    def test_overview_is_omitted_above_the_size_limit(self, tenant: Callable[..., Path]) -> None:
        """Large training splits fall back to sampled failing cases only."""
        policy_path = tenant(
            prompt=STRICT_PROMPT, max_tokens=2, budget={"max_iterations": 1}, train_overview_limit=3
        )
        generator = ScriptedGenerator(_proposal_script(WORSE_PROMPT))

        _run(policy_path, generator)

        assert "training_overview" not in generator.calls_for("analyst")[0]
        assert "training_overview" not in generator.calls_for("prompt_proposer")[0]


class TestTrainTiebreak:
    def _script(self) -> Dict[str, List[Any]]:
        rewrite = _prompt_plan("comprehensive category definitions")
        rewrite["plan"]["scope"] = "rewrite"
        return {
            "analyst": [rewrite, _prompt_plan("role framing")],
            "prompt_proposer": [{"prompt": HEAT_PROMPT}, {"prompt": WORSE_PROMPT}],
            "reviewer": [PASS_REVIEW],
        }

    def test_val_tie_with_train_gain_is_accepted(self, tenant: Callable[..., Path]) -> None:
        """A candidate that ties on val but improves train becomes the new best."""
        policy_path = tenant(budget={"max_iterations": 2})
        generator = ScriptedGenerator(self._script())

        result = _run(policy_path, generator)

        first = _ledger(result)[1]
        assert first["reason"] == "accepted_train_tiebreak"
        assert (first["train_delta"], first["val_delta"]) == (50.0, 0.0)
        assert first["improved_case_ids"] == ["train-0", "train-1"]
        assert result.best.candidate_id == "c001"
        assert generator.calls_for("prompt_proposer")[0]["plan"]["scope"] == "rewrite"
        assert generator.calls_for("reviewer")[0]["scope"] == "rewrite"
        history = generator.calls_for("analyst")[1]["history"]
        assert history[0]["improved_case_ids"] == ["train-0", "train-1"]
        assert history[0]["scope"] == "rewrite"

    def test_tiebreak_can_be_disabled(self, tenant: Callable[..., Path]) -> None:
        """With train_tiebreak off, a val tie is rejected even when train improves."""
        policy_path = tenant(
            budget={"max_iterations": 1}, acceptance={"min_val_delta": 1.0, "train_tiebreak": False}
        )
        generator = ScriptedGenerator(self._script())

        result = _run(policy_path, generator)

        assert _ledger(result)[1]["reason"] == "selection_below_threshold"
        assert result.best.candidate_id == "c000"


class TestParameterLevel:
    def test_parameter_change_within_space_is_accepted(self, tenant: Callable[..., Path]) -> None:
        """A parameter plan is applied to the candidate config and accepted on val."""
        policy_path = tenant(
            prompt=STRICT_PROMPT,
            max_tokens=2,
            levels=["parameter"],
            parameter_space={"provider_settings.max_tokens": {"type": "int", "min": 1, "max": 64}},
        )
        generator = ScriptedGenerator({"analyst": [_parameter_plan(16)]})

        result = _run(policy_path, generator)

        assert result.best.candidate_id == "c001"
        assert result.best.config["provider_settings"]["max_tokens"] == 16
        assert result.baseline.config["provider_settings"]["max_tokens"] == 2
        analyst_payload = generator.calls_for("analyst")[0]
        assert analyst_payload["current_values"] == {"provider_settings.max_tokens": 2}
        assert analyst_payload["parameter_space"] == {
            "provider_settings.max_tokens": {"type": "int", "min": 1, "max": 64}
        }

    def test_already_evaluated_values_are_sent_back_without_eval(self, tenant: Callable[..., Path]) -> None:
        """Re-proposing rejected parameter values is refused at plan time, before any eval."""
        policy_path = tenant(
            prompt=STRICT_PROMPT,
            max_tokens=2,
            levels=["parameter"],
            parameter_space={"provider_settings.max_tokens": {"type": "int", "min": 1, "max": 64}},
        )
        plans = [_parameter_plan(1), _parameter_plan(1), _parameter_plan(16)]
        generator = ScriptedGenerator({"analyst": plans})

        result = _run(policy_path, generator)

        analyst_calls = generator.calls_for("analyst")
        assert "already evaluated" in analyst_calls[2]["previous_errors"][0]
        assert result.best.candidate_id == "c002"
        assert _eval_dirs(policy_path) == ["c000-train", "c000-val", "c001-train", "c002-train", "c002-val"]

    def test_out_of_space_plan_is_retried_then_recorded(self, tenant: Callable[..., Path]) -> None:
        """An out-of-bounds parameter plan is retried with its errors, then recorded as a role error."""
        policy_path = tenant(
            prompt=STRICT_PROMPT,
            max_tokens=2,
            levels=["parameter"],
            parameter_space={"provider_settings.max_tokens": {"type": "int", "min": 1, "max": 64}},
            budget={"max_iterations": 1},
        )
        generator = ScriptedGenerator({"analyst": [_parameter_plan(999)]})

        result = _run(policy_path, generator)

        analyst_calls = generator.calls_for("analyst")
        assert len(analyst_calls) == 2
        assert "must be <= 64" in analyst_calls[1]["previous_errors"][0]
        assert _ledger(result)[1]["reason"] == "role_error"
        assert _eval_dirs(policy_path) == ["c000-train", "c000-val"]


class TestLoopControl:
    def test_plateau_exhausts_level_and_stops(self, tenant: Callable[..., Path]) -> None:
        """Consecutive rejections exhaust a level, and techniques tried are fed back to the analyst."""
        policy_path = tenant(
            prompt=STRICT_PROMPT, max_tokens=2, budget={"max_iterations": 10, "plateau_patience": 2}
        )
        generator = ScriptedGenerator(
            {
                "analyst": [_prompt_plan("role framing"), _prompt_plan("negative examples")],
                "prompt_proposer": [{"prompt": WORSE_PROMPT}],
                "reviewer": [PASS_REVIEW],
            }
        )

        result = _run(policy_path, generator)

        assert result.stop_reason == "levels_exhausted"
        assert result.iterations == 2
        analyst_calls = generator.calls_for("analyst")
        assert analyst_calls[1]["techniques_tried_since_improvement"] == {"prompt": ["role framing"]}
        assert analyst_calls[1]["history"][0]["reason"] == "train_screen"

    def test_target_score_stops_before_iterating(self, tenant: Callable[..., Path]) -> None:
        """A baseline already at the target score stops without calling any role."""
        policy_path = tenant(prompt=STRICT_PROMPT, max_tokens=2, budget={"target_score": 30.0})
        generator = ScriptedGenerator({})

        result = _run(policy_path, generator)

        assert result.stop_reason == "target_reached"
        assert generator.calls == []

    def test_resume_continues_ledger_without_reevaluating_baseline(self, tenant: Callable[..., Path]) -> None:
        """A resumed run picks up iteration numbering and the best candidate from the ledger."""
        policy_path = tenant(prompt=STRICT_PROMPT, max_tokens=2, budget={"max_iterations": 1})
        _run(policy_path, ScriptedGenerator(_proposal_script(WORSE_PROMPT)))

        with pytest.raises(ValueError, match="already exists"):
            _run(policy_path, ScriptedGenerator(_proposal_script(WORSE_PROMPT)))

        policy = load_policy(policy_path)
        policy.budget.max_iterations = 2
        resumed = coordinator.run_optimization(
            policy,
            policy_path.parent / "workspace",
            generator=ScriptedGenerator(_proposal_script(WORSE_PROMPT)),
            resume=True,
        )

        assert resumed.iterations == 2
        iterations = [record["iteration"] for record in _ledger(resumed) if record["type"] == "iteration"]
        assert iterations == [1, 2]
        assert _eval_dirs(policy_path) == ["c000-train", "c000-val", "c001-train", "c002-train"]
        assert resumed.best.train_results[0]["case_id"] == "train-0"


class TestSplitDiscipline:
    def test_role_payloads_contain_no_val_or_test_cases(self, tenant: Callable[..., Path]) -> None:
        """Only training cases ever reach a role; val and test stay aggregate-only."""
        policy_path = tenant()
        generator = ScriptedGenerator(_proposal_script(STRICT_PROMPT))

        result = _run(policy_path, generator, final_test=True)

        dumped = json.dumps(generator.calls)
        for question in (*VAL, *TEST):
            assert question not in dumped
        assert "val-" not in dumped and "test-" not in dumped
        assert "Is fire hot?" in dumped and "train-source" in dumped
        assert result.test == {
            "baseline": _ledger(result)[-1]["test"]["baseline"],
            "best": _ledger(result)[-1]["test"]["best"],
        }
        assert (result.test["baseline"]["score"], result.test["best"]["score"]) == (0.0, 100.0)

    def test_test_split_cannot_be_reused_after_final_test(self, tenant: Callable[..., Path]) -> None:
        """Once a workspace has a test result, it can no longer be resumed."""
        policy_path = tenant(budget={"max_iterations": 0})
        _run(policy_path, ScriptedGenerator({}), final_test=True)

        with pytest.raises(ValueError, match="test split was already evaluated"):
            _run(policy_path, ScriptedGenerator({}), resume=True)


class TestOpenAIGenerator:
    def test_loop_runs_through_openai_json_provider(self, tenant: Callable[..., Path]) -> None:
        """Real role payloads serialize through the OpenAI JSON provider, and token usage is recorded."""
        script = _proposal_script(STRICT_PROMPT)

        class Completions:
            def create(self, **kwargs: Any) -> SimpleNamespace:
                role = json.loads(kwargs["messages"][1]["content"])["role"]
                content = json.dumps(script[role][0])
                return SimpleNamespace(
                    id="response-1",
                    model="role-model",
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                    usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120),
                )

        client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
        policy_path = tenant()

        result = _run(policy_path, OpenAIRubricProvider(model="role-model", client=client))

        assert result.best.candidate_id == "c001"
        assert _ledger(result)[1]["usage"] == {
            role: {"calls": 1, "input_tokens": 100, "output_tokens": 20}
            for role in ("analyst", "prompt_proposer", "reviewer")
        }


class TestCli:
    def test_optimize_command_prints_summary(
        self,
        tenant: Callable[..., Path],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`optimize` loads the policy, applies overrides, and prints a JSON summary."""
        policy_path = tenant()
        generator = ScriptedGenerator(_proposal_script(STRICT_PROMPT))
        models: List[str] = []

        def fake_provider(model: str, max_output_tokens: int) -> ScriptedGenerator:
            models.append(model)
            return generator

        monkeypatch.setattr(coordinator, "OpenAIRubricProvider", fake_provider)
        workspace = policy_path.parent / "cli-workspace"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "hephaestus",
                "optimize",
                "--policy",
                str(policy_path),
                "--workspace",
                str(workspace),
                "--role-model",
                "role-model-x",
                "--max-iterations",
                "3",
            ],
        )

        cli.main()

        summary = json.loads(capsys.readouterr().out)
        assert models == ["role-model-x"]
        assert summary["stop_reason"] == "no_train_failures"
        assert summary["best"] == {"candidate_id": "c001", "train": 100.0, "val": 100.0}
        assert summary["ledger"] == str(workspace / "ledger.jsonl")
