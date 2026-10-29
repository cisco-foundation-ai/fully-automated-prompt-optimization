# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
from data_pipeline_fakes import CRITERION, ScriptedModel, make_record

from src.hephaestus.data_pipeline import steps
from src.hephaestus.data_pipeline.config import AssetConfig
from src.hephaestus.data_pipeline.llm import JsonCalls
from src.hephaestus.data_pipeline.prepare import PreparedRecord
from src.hephaestus.data_pipeline.prompts import OBSERVE_PROMPT, SYNTHESIZE_PROMPT

PAYLOAD = {
    "transcript": [{"role": "user", "content": "Please change my   shipping address."}],
    "runtime": {"status": "pending"},
    "feedback": {"polarity": "negative", "rationale": "It never confirmed the new address."},
}


def _lesson(**overrides: Any) -> Dict[str, Any]:
    lesson = {
        "type": "failure",
        "lesson": "Confirm a new address before saving it.",
        "evidence": [{"source": "feedback", "text": "never confirmed the new address"}],
        "signal": "explicit",
        "knowable": True,
        "confidence": 0.9,
    }
    lesson.update(overrides)
    return lesson


def _config(**overrides: Any) -> AssetConfig:
    return AssetConfig.from_dict({"tenant_id": "demo", "asset_id": "v1", "feedback": "f.jsonl", **overrides})


def _calls(tmp_path: Path, model: ScriptedModel) -> JsonCalls:
    return JsonCalls(
        lambda: model, model="m", cache_dir=tmp_path / "cache", calls_path=tmp_path / "calls.jsonl"
    )


def _record(record_id: str, split: str, labeled: bool = True) -> PreparedRecord:
    return PreparedRecord(
        row=make_record(record_id, labeled=labeled), labeled=labeled, split=split, group=record_id
    )


class TestCheckLesson:
    def test_keeps_verified_lesson(self) -> None:
        """A well-formed lesson with a verbatim quote is kept."""
        lesson, reason = steps.check_lesson(_lesson(), PAYLOAD, 0.3)

        assert reason is None
        assert lesson["signal"] == "explicit"

    def test_quote_match_ignores_case_whitespace_and_elisions(self) -> None:
        """Quotes match regardless of case and spacing, and ellipses mark elisions."""
        quote = {"source": "trace", "text": '"change my shipping ... ADDRESS"'}

        lesson, _ = steps.check_lesson(_lesson(evidence=[quote], signal="clear"), PAYLOAD, 0.3)

        assert lesson is not None

    @pytest.mark.parametrize(
        "overrides, reason",
        [
            ({"evidence": [{"source": "feedback", "text": "an invented quote"}]}, "unverified_evidence"),
            (
                {"evidence": [{"source": "trace", "text": "never confirmed the new address"}]},
                "unverified_evidence",
            ),
            ({"evidence": [{"source": "feedback", "text": "the"}]}, "unverified_evidence"),
            ({"knowable": False}, "needs_hindsight"),
            ({"confidence": 0.1}, "low_confidence"),
            ({"type": "opinion"}, "malformed"),
            ({"evidence": "never confirmed"}, "malformed"),
        ],
    )
    def test_drops_with_reason(self, overrides: Dict[str, Any], reason: str) -> None:
        """Unverified, hindsight, low-confidence, and malformed lessons are dropped."""
        assert steps.check_lesson(_lesson(**overrides), PAYLOAD, 0.3) == (None, reason)

    @pytest.mark.parametrize(
        "quote",
        [
            {"source": "trace", "text": "content"},
            {"source": "trace", "text": "result_returned"},
            {"source": "feedback", "text": "polarity negative"},
            {"source": "feedback", "text": "null"},
            {"source": "trace", "text": "shipping ... change my"},
        ],
    )
    def test_structure_and_reordered_fragments_are_not_evidence(self, quote: Dict[str, str]) -> None:
        """Keys, structural tokens, polarity, and out-of-order fragments do not verify."""
        payload = {
            **PAYLOAD,
            "transcript": [*PAYLOAD["transcript"], {"tool": "t", "outcome": "result_returned"}],
        }

        assert steps.check_lesson(_lesson(evidence=[quote]), payload, 0.3) == (None, "unverified_evidence")

    def test_unlabeled_episode_has_no_feedback_evidence(self) -> None:
        """Without feedback, no feedback quote can verify."""
        payload = {key: value for key, value in PAYLOAD.items() if key != "feedback"}
        quote = {"source": "feedback", "text": "never confirmed the new address"}

        assert steps.check_lesson(_lesson(evidence=[quote]), payload, 0.3) == (None, "unverified_evidence")

    def test_explicit_needs_feedback_quote(self) -> None:
        """An explicit signal backed only by trace quotes is lowered to clear."""
        quote = {"source": "trace", "text": "shipping address"}

        lesson, _ = steps.check_lesson(_lesson(evidence=[quote]), PAYLOAD, 0.3)

        assert lesson["signal"] == "clear"


class TestParseObservations:
    def test_requires_every_record(self) -> None:
        """A missing record ID is a validation error."""
        with pytest.raises(ValueError, match="missing record_ids: b"):
            steps.parse_observations({"episodes": [{"record_id": "a", "lessons": []}]}, record_ids=["a", "b"])

    def test_rejects_unknown_record(self) -> None:
        """An unrequested record ID is a validation error."""
        with pytest.raises(ValueError, match="unexpected or repeated record_id 'z'"):
            steps.parse_observations({"episodes": [{"record_id": "z", "lessons": []}]}, record_ids=["a"])


class TestObserve:
    def test_observes_train_feedback_only_by_default(self, tmp_path: Path) -> None:
        """Held-out records and unlabeled traces are not observed by default."""
        model = ScriptedModel()
        records = [
            _record("a", "train"),
            _record("b", "validation"),
            _record("c", "test"),
            _record("u", "train", labeled=False),
        ]

        lessons, dropped = steps.observe(_calls(tmp_path, model), records, _config())

        assert [(lesson["lesson_id"], lesson["record_id"]) for lesson in lessons] == [("L0001", "a")]
        assert lessons[0]["source"] == "feedback"
        assert dropped == []

    def test_observe_traces_adds_unlabeled_train_records(self, tmp_path: Path) -> None:
        """With observe_traces, unlabeled train records are observed too."""
        model = ScriptedModel()
        records = [
            _record("a", "train"),
            _record("u", "train", labeled=False),
            _record("v", "test", labeled=False),
        ]

        lessons, _ = steps.observe(_calls(tmp_path, model), records, _config(observe_traces=True))

        assert [(lesson["record_id"], lesson["source"]) for lesson in lessons] == [
            ("a", "feedback"),
            ("u", "trace"),
        ]

    def test_batches_episodes(self, tmp_path: Path) -> None:
        """Episodes are sent in batches of batch_size."""
        model = ScriptedModel()
        records = [_record(f"r{i}", "train") for i in range(7)]

        steps.observe(_calls(tmp_path, model), records, _config(batch_size=3, workers=1))

        assert [len(r["payload"]["episodes"]) for r in model.requests] == [3, 3, 1]


def _lessons(count: int, route: str = "support", signal: str = "explicit") -> List[Dict[str, Any]]:
    return [
        {
            "lesson_id": f"L{i:04d}",
            "record_id": f"r{i}",
            "route": route,
            "source": "feedback",
            "type": "failure",
            "lesson": f"lesson {i}",
            "evidence": [],
            "signal": signal,
            "confidence": 0.9,
        }
        for i in range(1, count + 1)
    ]


class TestParseSynthesis:
    def _raw(self, lesson_ids: List[str], **extra: Any) -> Dict[str, Any]:
        guideline = {"title": "t", "dividing_line": "d", "criteria": [CRITERION], "lesson_ids": lesson_ids}
        return {"guidelines": [guideline], **extra}

    def test_rejects_unknown_lesson_ids(self) -> None:
        """A guideline citing an invented lesson ID is a validation error."""
        with pytest.raises(ValueError, match="unknown lesson IDs: L9"):
            steps.parse_synthesis(self._raw(["L1", "L9"]), lesson_ids={"L1"})

    def test_sets_aside_unaccounted_lessons(self) -> None:
        """Lessons the model left out are set aside with a reason."""
        result = steps.parse_synthesis(self._raw(["L1"]), lesson_ids={"L1", "L2"})

        assert result["set_aside"] == [{"lesson_ids": ["L2"], "reason": "not addressed by the model"}]

    def test_rejects_guideline_without_criteria(self) -> None:
        """Every guideline needs at least one criterion."""
        raw = self._raw(["L1"])
        raw["guidelines"][0]["criteria"] = []

        with pytest.raises(ValueError, match="criteria must not be empty"):
            steps.parse_synthesis(raw, lesson_ids={"L1"})


class TestSynthesize:
    def test_assigns_ids_and_support(self, tmp_path: Path) -> None:
        """Code assigns guideline and criterion IDs and computes support and strength."""
        lessons = [*_lessons(3), *_lessons(1, route="billing")]
        lessons[3]["lesson_id"], lessons[3]["record_id"] = "L0004", "r4"

        catalog = steps.synthesize(
            _calls(tmp_path, ScriptedModel()), lessons, _config(min_guideline_support=2)
        )

        billing, support = catalog["guidelines"]
        assert (billing["guideline_id"], billing["route"], billing["strength"], billing["included"]) == (
            "G001",
            "billing",
            "emerging",
            False,
        )
        assert (support["guideline_id"], support["support"], support["strength"], support["included"]) == (
            "G002",
            3,
            "strong",
            True,
        )
        assert support["criteria"][0]["criterion_id"] == "G002.c1"
        assert support["signals"] == {"explicit": 3}

    def test_large_routes_are_chunked(self, tmp_path: Path) -> None:
        """A route with more than SYNTHESIS_CHUNK lessons is built incrementally."""
        model = ScriptedModel()

        catalog = steps.synthesize(_calls(tmp_path, model), _lessons(steps.SYNTHESIS_CHUNK + 5), _config())

        requests = [r for r in model.requests if r["system_prompt"] == SYNTHESIZE_PROMPT]
        assert len(requests) == 2
        assert requests[0]["payload"]["current"] is None
        assert requests[1]["payload"]["current"]["guidelines"]
        assert len(catalog["guidelines"][0]["lesson_ids"]) == steps.SYNTHESIS_CHUNK + 5


class TestRubrics:
    GUIDELINES = {
        "G001": {
            "guideline_id": "G001",
            "title": "Confirm",
            "criteria": [{"criterion_id": "G001.c1", **CRITERION}],
        }
    }

    def test_parse_rejects_unknown_guideline(self) -> None:
        """A rubric may only choose guidelines from the catalog."""
        raw = {"applicable_guideline_ids": ["G404"], "case_criteria": [], "confidence": 0.5}

        with pytest.raises(ValueError, match="unknown guideline IDs: G404"):
            steps.parse_rubric(raw, guideline_ids={"G001"})

    def test_parse_maps_criterion_ids_to_their_guideline(self) -> None:
        """A criterion ID in the guideline list is read as its guideline."""
        raw = {"applicable_guideline_ids": ["G001.c1", "G001"], "case_criteria": [], "confidence": 0.5}

        assert steps.parse_rubric(raw, guideline_ids={"G001"})["applicable_guideline_ids"] == ["G001"]

    def test_assemble_copies_catalog_criteria_verbatim(self) -> None:
        """Chosen guideline criteria are copied verbatim, then case criteria get case IDs."""
        parsed = steps.parse_rubric(
            {"applicable_guideline_ids": ["G001"], "case_criteria": [CRITERION], "confidence": 0.7},
            guideline_ids={"G001"},
        )

        rubric = steps.assemble_rubric("r1", parsed, self.GUIDELINES)

        assert rubric["provenance"] == "guideline_grounded"
        assert [group["guideline_id"] for group in rubric["evaluation_guidelines"]] == ["G001", "case"]
        assert rubric["evaluation_guidelines"][0]["criteria"] == self.GUIDELINES["G001"]["criteria"]
        assert rubric["evaluation_guidelines"][1]["criteria"][0]["criterion_id"] == "case.c1"

    def test_no_guideline_means_trace_inferred(self) -> None:
        """A rubric with only case criteria is trace-inferred."""
        parsed = steps.parse_rubric(
            {"applicable_guideline_ids": [], "case_criteria": [CRITERION], "confidence": 0.7},
            guideline_ids=set(),
        )

        assert steps.assemble_rubric("r1", parsed, {})["provenance"] == "trace_inferred"

    def test_feedback_only_reaches_own_rubric(self, tmp_path: Path) -> None:
        """Each rubric call carries only its own record's feedback, and only included guidelines."""
        model = ScriptedModel()
        catalog = {"guidelines": [{**self.GUIDELINES["G001"], "route": "support", "included": False}]}
        records = [
            PreparedRecord(make_record(name, labeled=True, rationale=f"about {name}"), True, split, name)
            for name, split in (("a", "train"), ("b", "test"))
        ]
        records.append(_record("u", "test", labeled=False))

        steps.write_rubrics(_calls(tmp_path, model), records, catalog, _config())

        payloads = {r["payload"]["episode"]["record_id"]: r["payload"] for r in model.requests}
        assert payloads["a"]["trusted_feedback"]["rationale"] == "about a"
        assert payloads["b"]["trusted_feedback"]["rationale"] == "about b"
        assert payloads["u"]["trusted_feedback"] is None
        assert all(payload["catalog"] == [] for payload in payloads.values())
        assert model.count(OBSERVE_PROMPT) == 0
