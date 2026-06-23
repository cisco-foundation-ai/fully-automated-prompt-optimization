# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from src.hephaestus.scoring.runtime import (
    extract_score_diagnostics,
    load_tenant_scorer,
    validate_score_payload,
)


def test_load_tenant_scorer_requires_scorer_object():
    with pytest.raises(ValueError, match=r"scoring_profile\.scorer"):
        load_tenant_scorer({})


def test_load_tenant_scorer_loads_class_default_name(tmp_path: Path):
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 42.0, 'score_breakdown': {'a': 42.0}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})

    assert callable(scorer.score_case)
    assert callable(scorer.validate_case)


def test_load_tenant_scorer_loads_class_override_name(tmp_path: Path):
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class IncidentScorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 41.0, 'score_breakdown': {'a': 41.0}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path), "class_name": "IncidentScorer"}})
    payload = scorer.score_case(None, "", {})
    assert payload["composite_score"] == 41.0


def test_load_tenant_scorer_supports_relative_imports(tmp_path: Path):
    scorer_dir = tmp_path / "scorers"
    scorer_dir.mkdir()
    (scorer_dir / "__init__.py").write_text("", encoding="utf-8")
    (scorer_dir / "helpers.py").write_text(
        """\
def score_value():
    return 55.0
""",
        encoding="utf-8",
    )
    module_path = scorer_dir / "scorer.py"
    module_path.write_text(
        """\
from .helpers import score_value
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        value = score_value()
        return {'composite_score': value, 'score_breakdown': {'a': value}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})
    payload = scorer.score_case(None, "", {})
    assert payload["composite_score"] == 55.0


def test_load_tenant_scorer_isolates_same_named_packages_across_tenants(tmp_path: Path):
    tenant_one_dir = tmp_path / "tenant_one" / "scorers"
    tenant_one_dir.mkdir(parents=True)
    (tenant_one_dir / "__init__.py").write_text("", encoding="utf-8")
    (tenant_one_dir / "helpers.py").write_text(
        """\
def score_value():
    return 10.0
""",
        encoding="utf-8",
    )
    tenant_one_module_path = tenant_one_dir / "scorer.py"
    tenant_one_module_path.write_text(
        """\
from .helpers import score_value
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        value = score_value()
        return {'composite_score': value, 'score_breakdown': {'a': value}}
""",
        encoding="utf-8",
    )

    tenant_two_dir = tmp_path / "tenant_two" / "scorers"
    tenant_two_dir.mkdir(parents=True)
    (tenant_two_dir / "__init__.py").write_text("", encoding="utf-8")
    (tenant_two_dir / "helpers.py").write_text(
        """\
def score_value():
    return 90.0
""",
        encoding="utf-8",
    )
    tenant_two_module_path = tenant_two_dir / "scorer.py"
    tenant_two_module_path.write_text(
        """\
from .helpers import score_value
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        value = score_value()
        return {'composite_score': value, 'score_breakdown': {'a': value}}
""",
        encoding="utf-8",
    )

    scorer_one = load_tenant_scorer({"scorer": {"module_path": str(tenant_one_module_path)}})
    scorer_two = load_tenant_scorer({"scorer": {"module_path": str(tenant_two_module_path)}})

    payload_one = scorer_one.score_case(None, "", {})
    payload_two = scorer_two.score_case(None, "", {})
    assert payload_one["composite_score"] == 10.0
    assert payload_two["composite_score"] == 90.0


def test_load_tenant_scorer_executes_package_init_for_relative_imports(tmp_path: Path):
    scorer_dir = tmp_path / "scorers"
    scorer_dir.mkdir()
    (scorer_dir / "__init__.py").write_text("VALUE = 77.0\n", encoding="utf-8")
    (scorer_dir / "helpers.py").write_text(
        """\
from . import VALUE

def score_value():
    return VALUE
""",
        encoding="utf-8",
    )
    module_path = scorer_dir / "scorer.py"
    module_path.write_text(
        """\
from .helpers import score_value
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        value = score_value()
        return {'composite_score': value, 'score_breakdown': {'a': value}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})
    payload = scorer.score_case(None, "", {})
    assert payload["composite_score"] == 77.0


def test_load_tenant_scorer_package_init_module_executes_once(tmp_path: Path):
    scorer_dir = tmp_path / "scorers"
    scorer_dir.mkdir()
    module_path = scorer_dir / "__init__.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

COUNT = globals().get('COUNT', 0) + 1

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': float(COUNT), 'score_breakdown': {'count': float(COUNT)}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})
    payload = scorer.score_case(None, "", {})
    assert payload["composite_score"] == 1.0


def test_load_tenant_scorer_rejects_legacy_function_keys(tmp_path: Path):
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 42.0, 'score_breakdown': {'a': 42.0}}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Legacy scorer keys"):
        load_tenant_scorer({
            "scorer": {
                "module_path": str(module_path),
                "score_fn": "score_case",
                "validate_fn": "validate_case",
            }
        })


def test_load_tenant_scorer_requires_class_symbol(tmp_path: Path):
    module_path = tmp_path / "scorer.py"
    module_path.write_text("class SomethingElse:\n    pass\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"class_name 'Scorer' was not found"):
        load_tenant_scorer({"scorer": {"module_path": str(module_path)}})


def test_load_tenant_scorer_requires_class_symbol_to_be_class(tmp_path: Path):
    module_path = tmp_path / "scorer.py"
    module_path.write_text("Scorer = 123\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"must refer to a class"):
        load_tenant_scorer({"scorer": {"module_path": str(module_path)}})


def test_load_tenant_scorer_requires_subclass_contract(tmp_path: Path):
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
class Scorer:
    def validate_case(self, case, scoring_profile):
        return None
    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 42.0, 'score_breakdown': {'a': 42.0}}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"must subclass"):
        load_tenant_scorer({"scorer": {"module_path": str(module_path)}})


def test_scorer_pipeline_fallback_uses_last_output(tmp_path: Path):
    """Default score_pipeline_case calls score_case with the last step output."""
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        length = float(len(output_text))
        return {'composite_score': length, 'score_breakdown': {'len': length}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})
    step_outputs = {"step_1": "first output", "step_2": "final answer"}
    result = scorer.score_pipeline_case(None, step_outputs, {})

    # Default implementation should use the last value in step_outputs
    assert result["composite_score"] == float(len("final answer"))
    assert result["score_breakdown"] == {"len": float(len("final answer"))}


def test_scorer_pipeline_output_text_takes_priority(tmp_path: Path):
    """output_text param takes priority over dict-order fallback in score_pipeline_case."""
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        length = float(len(output_text))
        return {'composite_score': length, 'score_breakdown': {'len': length}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})
    step_outputs = {"step_1": "first output", "step_2": "dict last value"}
    result = scorer.score_pipeline_case(None, step_outputs, {}, output_text="explicit text")

    # Should use "explicit text" (len=13), not "dict last value" (len=15)
    assert result["composite_score"] == float(len("explicit text"))


def test_scorer_pipeline_empty_output_text_not_treated_as_missing(tmp_path: Path):
    """Empty string output_text is valid and should not fall back to step_outputs."""
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        length = float(len(output_text))
        return {'composite_score': length, 'score_breakdown': {'len': length}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})
    step_outputs = {"step_1": "non-empty step output"}
    result = scorer.score_pipeline_case(None, step_outputs, {}, output_text="")

    # Empty string is valid output_text (len=0), should NOT fall back to step_outputs
    assert result["composite_score"] == 0.0


def test_scorer_pipeline_empty_raises(tmp_path: Path):
    """score_pipeline_case raises ValueError when step_outputs is empty and no output_text."""
    module_path = tmp_path / "scorer.py"
    module_path.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 42.0, 'score_breakdown': {'a': 42.0}}
""",
        encoding="utf-8",
    )

    scorer = load_tenant_scorer({"scorer": {"module_path": str(module_path)}})
    with pytest.raises(ValueError, match="empty step_outputs"):
        scorer.score_pipeline_case(None, {}, {})


def test_validate_score_payload_enforces_required_fields():
    with pytest.raises(ValueError, match="composite_score"):
        validate_score_payload({"score_breakdown": {"x": 100.0}})
    with pytest.raises(ValueError, match="score_breakdown"):
        validate_score_payload({"composite_score": 100.0})


def test_validate_score_payload_enforces_range():
    with pytest.raises(ValueError, match="between 0 and 100"):
        validate_score_payload({"composite_score": 101.0, "score_breakdown": {}})
    with pytest.raises(ValueError, match="non-negative"):
        validate_score_payload({"composite_score": 50.0, "score_breakdown": {"x": -1}})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_validate_score_payload_rejects_non_finite_composite_score(value: float):
    with pytest.raises(ValueError, match=r"composite_score.*finite"):
        validate_score_payload({"composite_score": value, "score_breakdown": {}})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_validate_score_payload_rejects_non_finite_breakdown_score(value: float):
    with pytest.raises(ValueError, match=r"score_breakdown\.x.*finite"):
        validate_score_payload({"composite_score": 50.0, "score_breakdown": {"x": value}})


def test_validate_score_payload_rejects_boolean_scores():
    with pytest.raises(ValueError, match=r"composite_score.*numeric"):
        validate_score_payload({"composite_score": True, "score_breakdown": {}})
    with pytest.raises(ValueError, match=r"score_breakdown\.x.*numeric"):
        validate_score_payload({"composite_score": 50.0, "score_breakdown": {"x": False}})


def test_validate_score_payload_returns_normalized_values():
    composite_score, score_breakdown = validate_score_payload(
        {"composite_score": 87, "score_breakdown": {"format": 75, "accuracy": 99.5}}
    )

    assert composite_score == 87.0
    assert score_breakdown == {"format": 75.0, "accuracy": 99.5}


def test_validate_score_payload_allows_breakdown_above_100():
    """Breakdown values can exceed 100 (e.g. raw point totals)."""
    composite_score, score_breakdown = validate_score_payload(
        {"composite_score": 95.0, "score_breakdown": {"points_earned": 190, "points_possible": 200}}
    )
    assert score_breakdown == {"points_earned": 190.0, "points_possible": 200.0}


def test_extract_score_diagnostics_absent_returns_empty():
    assert extract_score_diagnostics({"composite_score": 100.0, "score_breakdown": {}}) == []


def test_extract_score_diagnostics_wraps_string():
    assert extract_score_diagnostics({"diagnostics": "judge[100]: correct"}) == [
        "judge[100]: correct"
    ]


def test_extract_score_diagnostics_coerces_list_items():
    assert extract_score_diagnostics({"diagnostics": ["a", 2]}) == ["a", "2"]


def test_extract_score_diagnostics_rejects_non_sequence():
    with pytest.raises(ValueError, match="diagnostics"):
        extract_score_diagnostics({"diagnostics": {"reason": "x"}})
