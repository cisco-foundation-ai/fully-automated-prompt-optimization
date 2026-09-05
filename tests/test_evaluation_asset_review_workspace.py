# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Workspace authority tests for evaluation-asset human review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.hephaestus.evaluation_assets import workspace as workspace_module
from src.hephaestus.evaluation_assets.dependencies import (
    build_stage_six_dependency,
)
from src.hephaestus.evaluation_assets.durability import (
    EvaluationAssetIntegrityError,
)
from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig, PipelineStage
from src.hephaestus.evaluation_assets.review import (
    ReviewDecisionConflictError,
    build_review_finalization,
    build_review_item,
    case_content_fingerprint,
)
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


def _input_row(record_id: str, *, labeled: bool) -> dict:
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": f"group-{record_id}",
        "task_type": "answer",
        "route": "support",
        "user_input": f"Request {record_id}",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }
    if labeled:
        row.update(
            {
                "assistant_output": "Previous response",
                "feedback": {
                    "polarity": "positive",
                    "rationale": "The response satisfied the request.",
                },
            }
        )
    return row


def _initialized_layout(tmp_path: Path) -> EvaluationAssetLayout:
    tenants_root = tmp_path / "tenants"
    source_root = tenants_root / "tenant_a" / "source_artifacts"
    source_root.mkdir(parents=True)
    feedback = source_root / "feedback.jsonl"
    unlabeled = source_root / "unlabeled.jsonl"
    feedback.write_text(
        json.dumps(_input_row("f1", labeled=True)) + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        json.dumps(_input_row("u1", labeled=False)) + "\n",
        encoding="utf-8",
    )
    layout = EvaluationAssetLayout(
        tenants_root,
        "tenant_a",
        "v1",
        repository_base=tmp_path,
    )
    layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a", asset_id="v1"),
        feedback,
        unlabeled,
    )
    return layout


def test_initialization_creates_empty_review_authority_logs(tmp_path: Path) -> None:
    """Catch assets whose later review append has no explicit empty authority."""
    layout = _initialized_layout(tmp_path)

    assert layout.reviews_root.is_dir()
    assert layout.review_decisions_path.read_bytes() == b""
    assert layout.review_finalizations_path.read_bytes() == b""


def test_journal_commit_preserves_the_prepared_schema_version(tmp_path: Path) -> None:
    """Catch v3 commits that make an outstanding historical v2 WAL unrecoverable."""
    layout = EvaluationAssetLayout(
        tmp_path / "tenants",
        "tenant_a",
        "v1",
        repository_base=tmp_path,
    )
    layout.ensure()

    layout._commit_journal_operation(
        {
            "schema_version": "fapo-recovery-journal-v2",
            "operation_id": "a" * 32,
            "kind": "configuration_revision",
        }
    )

    committed = json.loads(layout.recovery_journal_path.read_text(encoding="utf-8"))
    assert committed["schema_version"] == "fapo-recovery-journal-v2"


def _case(case_id: str, trust_tier: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "task_type": "answer",
        "context": {
            "messages_json": '[{"role":"user","content":"Question"}]',
            "tool_context_json": "[]",
            "runtime_json": "{}",
        },
        "expected": {"rubric": {"must": ["Answer accurately"]}},
        "metadata": {
            "source": "unlabeled_trace",
            "source_cluster": "cluster-1",
            "matched_intent_id": "guideline-1",
            "group_id": f"group-{case_id}",
            "request_id": f"request-{case_id}",
            "trust_tier": trust_tier,
        },
    }


def _dependency() -> dict[str, Any]:
    return build_stage_six_dependency(
        cluster={
            "cluster_id": "cluster-1",
            "route": "support",
            "record_ids": ["u1"],
            "representative_ids": ["u1"],
        },
        match={
            "cluster_id": "cluster-1",
            "status": "matched_trusted_intent",
            "matched_intent_id": "guideline-1",
            "score": 0.9,
        },
        guideline={
            "guideline_id": "guideline-1",
            "criteria": [{"statement": "Answer accurately"}],
            "support": {"record_count": 1, "group_count": 1},
        },
        source_members=[
            {
                "identity": "unlabeled:u1",
                "content_sha256": "1" * 64,
            }
        ],
        provider={
            "provider": "test",
            "model": "rubric-model",
            "request_settings": {"temperature": 0},
        },
        prompt={"revision": "label-inference-v1", "sha256": "2" * 64},
        algorithm_revision="stage-six-dependency-v1",
    )


def _prepare_review_layout(
    tmp_path: Path,
) -> tuple[EvaluationAssetLayout, dict[str, Any], dict[str, Any]]:
    layout = _initialized_layout(tmp_path)
    dependency = _dependency()
    item = build_review_item(
        case=_case("inferred-u1", "inferred_from_trusted_feedback"),
        dependency=dependency,
        source_provenance={
            "source_record_ids": ["u1"],
            "source_record_sha256s": ["sha256:" + "3" * 64],
            "source_cluster": "cluster-1",
            "matched_intent_id": "guideline-1",
        },
        reviewer="fapo_pipeline",
        timestamp="2026-08-21T12:00:00Z",
    )
    held_case = _case("trusted-held", "trusted_feedback")
    held_fingerprint = case_content_fingerprint(held_case)
    layout._write_authority_jsonl(
        layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "case_dependencies.jsonl",
        ),
        [
            {
                "case_id": "inferred-u1",
                "record_id": "u1",
                "dependency": dependency,
            }
        ],
    )
    layout._write_authority_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_dependencies.jsonl",
        ),
        [],
    )
    layout._write_authority_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "derived_review_items.jsonl",
        ),
        [item],
    )
    layout._write_authority_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "held_derived_cases.jsonl",
        ),
        [
            {
                "case_id": held_case["case_id"],
                "fingerprint": held_fingerprint,
                "reason": "conflicting_expected_truth",
                "family_id": "family-held",
                "trust_tier": "trusted_feedback",
                "case_content_sha256": held_fingerprint,
                "case": held_case,
            }
        ],
    )
    layout._write_authority_jsonl(
        layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "trusted_cases.jsonl",
        ),
        [_case("trusted-visible", "trusted_feedback"), held_case],
    )
    state = layout.load_state()
    state.status = "awaiting_review"
    for stage_state in state.stages[:7]:
        stage_state.status = "completed"
        stage_state.started_at = "2026-08-21T11:00:00+00:00"
        stage_state.completed_at = "2026-08-21T11:01:00+00:00"
        stage_state.receipt_sha256 = "7" * 64
    layout.save_state(state)
    return layout, item, dependency


def _accept_stage_seven_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def verify_stage_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append({"args": args, "kwargs": kwargs})
        return {"schema_version": "fapo-evaluation-stage-receipt-v3"}

    monkeypatch.setattr(
        workspace_module,
        "verify_stage_receipt",
        verify_stage_receipt,
        raising=False,
    )
    return calls


def test_list_review_items_verifies_and_resolves_the_exact_current_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch unverified queue reads or review counts that include held trusted cases."""
    layout, item, _ = _prepare_review_layout(tmp_path)
    receipt_calls = _accept_stage_seven_receipt(monkeypatch)

    page = layout.list_review_items(offset=0, limit=10)

    assert len(receipt_calls) == 1
    assert receipt_calls[0]["args"][2] is PipelineStage.SYNTHETIC_COVERAGE
    assert receipt_calls[0]["kwargs"] == {
        "prompt_values": {},
        "provider_identity": None,
        "compare_current_dependencies": False,
    }
    assert page["review_set_fingerprint"].startswith("sha256:")
    assert page["decision_set_fingerprint"].startswith("sha256:")
    assert page["review_authority_revision"].startswith("sha256:")
    assert page["finalization"] is None
    assert page["stage7_receipt_sha256"] == "sha256:" + "7" * 64
    assert page["items"][0]["case_id"] == item["case_id"]
    assert page["items"][0]["status"] == "pending"
    assert page["items"][0]["case"] == item["case"]
    assert page["held"][0]["case_id"] == "trusted-held"
    assert page["held"][0]["status"] == "held"
    assert page["held"][0]["hold_reason"] == "conflicting_expected_truth"
    assert page["counts"] == {
        "trusted": 1,
        "approved": 0,
        "pending": 1,
        "rejected": 0,
        "held": 1,
        "total": 3,
    }
    assert (page["offset"], page["limit"], page["total"]) == (0, 10, 2)

    approved = layout.list_review_items(status="approved", offset=0, limit=10)
    assert approved["items"] == []
    assert approved["total"] == 0
    assert approved["counts"] == page["counts"]


def test_review_pagination_bounds_the_combined_eligible_and_held_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch held rows bypassing the page limit or being impossible to filter."""
    layout, _, _ = _prepare_review_layout(tmp_path)
    _accept_stage_seven_receipt(monkeypatch)

    first = layout.list_review_items(offset=0, limit=1)
    second = layout.list_review_items(offset=1, limit=1)
    held = layout.list_review_items(status="held", offset=0, limit=1)

    assert len(first["items"]) + len(first["held"]) == 1
    assert len(second["items"]) + len(second["held"]) == 1
    assert {
        *(row["case_id"] for row in first["items"] + first["held"]),
        *(row["case_id"] for row in second["items"] + second["held"]),
    } == {"inferred-u1", "trusted-held"}
    assert held["items"] == []
    assert [row["case_id"] for row in held["held"]] == ["trusted-held"]
    assert held["total"] == 1


def test_review_revision_tracks_decisions_and_safe_current_finalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch polling revisions that miss external review-authority mutations."""
    layout, item, dependency = _prepare_review_layout(tmp_path)
    _accept_stage_seven_receipt(monkeypatch)
    pending = layout.list_review_items()
    pending_summary = layout.artifact_summary()

    layout.decide_review(
        item["case_id"],
        item["fingerprint"],
        "approved",
        reviewer="reviewer-a",
        expected_review_set_fingerprint=pending["review_set_fingerprint"],
    )
    approved = layout.list_review_items()
    approved_summary = layout.artifact_summary()
    decisions = [
        json.loads(line)
        for line in layout.review_decisions_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    held_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "held_derived_cases.jsonl",
        ).read_text(encoding="utf-8").splitlines()
        if line
    ]
    finalization = build_review_finalization(
        review_items=[item],
        dependencies={item["case_id"]: dependency},
        decisions=decisions,
        held_cases=held_cases,
        stage7_receipt_sha256=approved["stage7_receipt_sha256"],
        trusted_count=1,
        reviewer="release-reviewer",
        timestamp="2026-08-21T14:00:00Z",
        note="private finalization note",
    )
    layout._append_control_row(layout.review_finalizations_path, finalization)
    finalized = layout.list_review_items()
    finalized_summary = layout.artifact_summary()

    assert pending["review_set_fingerprint"] == approved["review_set_fingerprint"]
    assert pending["decision_set_fingerprint"] != approved["decision_set_fingerprint"]
    assert pending["review_authority_revision"] != approved["review_authority_revision"]
    assert pending_summary["review_authority_revision"] == pending["review_authority_revision"]
    assert approved_summary["review_authority_revision"] == approved["review_authority_revision"]
    assert finalized["decision_set_fingerprint"] == approved["decision_set_fingerprint"]
    assert finalized["review_authority_revision"] != approved["review_authority_revision"]
    assert finalized_summary["review_authority_revision"] == finalized["review_authority_revision"]
    assert finalized["finalization"] == {
        "finalization_id": finalization["finalization_id"],
        "review_set_fingerprint": finalization["review_set_fingerprint"],
        "counts": finalization["counts"],
    }
    assert "reviewer" not in finalized["finalization"]
    assert "note" not in finalized["finalization"]
    assert "items" not in finalized["finalization"]


def test_decide_review_appends_once_and_binds_case_fingerprint_and_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch duplicate appends or mutation by case ID, fingerprint, or set alone."""
    layout, item, _ = _prepare_review_layout(tmp_path)
    _accept_stage_seven_receipt(monkeypatch)
    review_set = layout.list_review_items()["review_set_fingerprint"]

    approved = layout.decide_review(
        item["case_id"],
        item["fingerprint"],
        "approved",
        reviewer="reviewer-a",
        note="Checked exact case",
        expected_review_set_fingerprint=review_set,
    )
    replay = layout.decide_review(
        item["case_id"],
        item["fingerprint"],
        "approved",
        reviewer="reviewer-b",
        expected_review_set_fingerprint=review_set,
    )

    rows = [
        json.loads(line)
        for line in layout.review_decisions_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line
    ]
    assert len(rows) == 1
    assert approved == {**rows[0], "review_set_fingerprint": review_set}
    assert replay == approved
    assert layout.list_review_items()["items"][0]["status"] == "approved"

    with pytest.raises(ReviewDecisionConflictError, match="immutable"):
        layout.decide_review(
            item["case_id"],
            item["fingerprint"],
            "rejected",
            reviewer="reviewer-b",
            expected_review_set_fingerprint=review_set,
        )
    assert layout.review_decisions_path.read_text(encoding="utf-8").count("\n") == 1


def test_decide_review_rejects_a_stale_set_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch optimistic-concurrency checks performed after decision persistence."""
    layout, item, _ = _prepare_review_layout(tmp_path)
    _accept_stage_seven_receipt(monkeypatch)
    before = layout.review_decisions_path.read_bytes()

    with pytest.raises(ValueError, match="review set"):
        layout.decide_review(
            item["case_id"],
            item["fingerprint"],
            "approved",
            reviewer="reviewer-a",
            expected_review_set_fingerprint="sha256:" + "0" * 64,
        )

    assert layout.review_decisions_path.read_bytes() == before


def test_review_workspace_rejects_tampered_dependency_before_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch approval resolution against a stale or unauthentic dependency row."""
    layout, _, dependency = _prepare_review_layout(tmp_path)
    _accept_stage_seven_receipt(monkeypatch)
    dependency["descriptor"]["provider"]["model"] = "tampered-model"
    layout._write_authority_jsonl(
        layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "case_dependencies.jsonl",
        ),
        [
            {
                "case_id": "inferred-u1",
                "record_id": "u1",
                "dependency": dependency,
            }
        ],
    )

    with pytest.raises(EvaluationAssetIntegrityError, match="dependency"):
        layout.list_review_items()


def test_review_workspace_requires_the_dependency_stage_for_each_trust_tier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch a synthetic item incorrectly authorized by a Stage 6 descriptor."""
    layout, _, dependency = _prepare_review_layout(tmp_path)
    _accept_stage_seven_receipt(monkeypatch)
    mismatched = build_review_item(
        case=_case("synthetic-u1", "synthetic_from_trusted_rubric"),
        dependency=dependency,
        source_provenance={
            "source_record_ids": ["u1"],
            "source_record_sha256s": ["sha256:" + "3" * 64],
            "source_cluster": "cluster-1",
            "matched_intent_id": "guideline-1",
        },
        reviewer="fapo_pipeline",
        timestamp="2026-08-21T12:00:00Z",
    )
    layout._write_authority_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "derived_review_items.jsonl",
        ),
        [mismatched],
    )

    with pytest.raises(EvaluationAssetIntegrityError, match="dependency"):
        layout.list_review_items()


def test_review_workspace_rejects_an_unknown_held_trust_tier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch held review counts built from an unsupported provenance tier."""
    layout, _, _ = _prepare_review_layout(tmp_path)
    _accept_stage_seven_receipt(monkeypatch)
    held_path = layout.artifact_path(
        PipelineStage.SYNTHETIC_COVERAGE,
        "held_derived_cases.jsonl",
    )
    held = json.loads(held_path.read_text(encoding="utf-8"))
    held["trust_tier"] = "legacy_synthetic"
    layout._write_authority_jsonl(held_path, [held])

    with pytest.raises(EvaluationAssetIntegrityError, match="review authority"):
        layout.list_review_items()


def test_review_workspace_propagates_receipt_failure_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch review reads or decisions that continue after Stage 7 verification fails."""
    layout, item, _ = _prepare_review_layout(tmp_path)

    def reject_receipt(*_args: Any, **_kwargs: Any) -> None:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "Stage 7 receipt changed",
        )

    monkeypatch.setattr(
        workspace_module,
        "verify_stage_receipt",
        reject_receipt,
        raising=False,
    )
    before = layout.review_decisions_path.read_bytes()

    with pytest.raises(EvaluationAssetIntegrityError, match="receipt"):
        layout.list_review_items()
    with pytest.raises(EvaluationAssetIntegrityError, match="receipt"):
        layout.decide_review(
            item["case_id"],
            item["fingerprint"],
            "approved",
            reviewer="reviewer-a",
            expected_review_set_fingerprint="sha256:" + "0" * 64,
        )

    assert layout.review_decisions_path.read_bytes() == before
