# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for pure evaluation-asset review and exact-family contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

import pytest


def _case(case_id: str = "inferred-u1") -> dict[str, Any]:
    return {
        "case_id": case_id,
        "task_type": "support",
        "context": {
            "messages_json": '[{"role":"user","content":"Hello"}]',
            "tool_context_json": '[{"name":"lookup","arguments":{"id":1}}]',
            "runtime_json": '{"locale":"en-US"}',
            "verbatim": "  Exact text  ",
        },
        "expected": {
            "rubric": {"must": ["Answer accurately"]},
            "reference_output": "A",
        },
        "metadata": {
            "source": "unlabeled_trace",
            "group_id": "group-u1",
            "request_id": "request-u1",
            "trust_tier": "inferred_from_trusted_feedback",
        },
    }


def _dependency() -> dict[str, Any]:
    return {
        "schema_version": "fapo-stage6-dependency-v1",
        "trusted_split_plan_sha256": "sha256:" + "a" * 64,
        "cluster": {
            "cluster_id": "route-001",
            "route": "support",
            "record_ids": ["u1"],
            "representative_ids": ["u1"],
            "top_terms": ["hello"],
        },
        "match": {
            "status": "matched_trusted_intent",
            "matched_intent_id": "guideline-1",
            "score": 0.9,
            "reason": "exact route",
        },
        "guideline": {
            "guideline_id": "guideline-1",
            "support": {"record_count": 2, "group_count": 2},
            "criteria": [{"statement": "Answer accurately"}],
        },
        "source_members": [
            {
                "record_id": "u1",
                "prepared_record_sha256": "sha256:" + "b" * 64,
                "raw_record_sha256": "sha256:" + "c" * 64,
            }
        ],
        "provider": {
            "provider": "openai",
            "model": "rubric-model",
            "request_settings": {"temperature": 0},
        },
        "prompt": {
            "name": "label-inference-v1",
            "sha256": "sha256:" + "d" * 64,
        },
        "pipeline_settings": {"batch_size": 3, "contract_revision": "v1"},
    }


def _source_provenance() -> dict[str, Any]:
    return {
        "source_record_ids": ["u1"],
        "source_record_sha256s": ["sha256:" + "e" * 64],
        "source_cluster": "route-001",
        "matched_intent_id": "guideline-1",
    }


def _review_item(
    *,
    dependency: dict[str, Any] | None = None,
    timestamp: str = "2026-08-21T12:00:00Z",
) -> dict[str, Any]:
    from src.hephaestus.evaluation_assets.review import build_review_item

    return build_review_item(
        case=_case(),
        dependency=dependency or _dependency(),
        source_provenance=_source_provenance(),
        reviewer="fapo_pipeline",
        timestamp=timestamp,
    )


def _review_item_for(case_id: str) -> dict[str, Any]:
    from src.hephaestus.evaluation_assets.review import build_review_item

    case = _case(case_id)
    case["metadata"]["group_id"] = f"group-{case_id}"
    case["metadata"]["request_id"] = f"request-{case_id}"
    source = _source_provenance()
    source["source_record_ids"] = [case_id]
    return build_review_item(
        case=case,
        dependency={**_dependency(), "case_id": case_id},
        source_provenance=source,
        reviewer="fapo_pipeline",
        timestamp="2026-08-21T12:00:00Z",
    )


def _family_case(
    case_id: str,
    text: str,
    group_id: str,
    *,
    trust_tier: str = "trusted_feedback",
    split_group_id: str | None = None,
    trusted_split: str | None = None,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = {
        "case_id": case_id,
        "task_type": "support",
        "context": {
            "messages_json": json.dumps(
                [{"role": "user", "content": text}],
                separators=(",", ":"),
            ),
            "tool_context_json": "[]",
            "runtime_json": "{}",
        },
        "expected": expected or {"reference_output": "answer"},
        "metadata": {"group_id": group_id, "trust_tier": trust_tier},
    }
    if split_group_id is not None:
        case["metadata"]["split_group_id"] = split_group_id
    if trusted_split is not None:
        case["metadata"]["trusted_split"] = trusted_split
    return case


def test_canonical_json_is_order_stable_and_value_exact() -> None:
    """Catch lossy normalization or acceptance of non-JSON fingerprint inputs."""
    from src.hephaestus.evaluation_assets.review import canonical_json_bytes

    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert canonical_json_bytes({"items": [1, 2]}) != canonical_json_bytes({"items": [2, 1]})
    assert canonical_json_bytes({"text": "a b"}) != canonical_json_bytes({"text": "ab"})
    assert canonical_json_bytes({"text": "\u00e9"}) != canonical_json_bytes({"text": "e\u0301"})
    assert canonical_json_bytes({"number": 1}) != canonical_json_bytes({"number": 1.0})
    with pytest.raises(ValueError, match="finite"):
        canonical_json_bytes({"number": math.nan})
    with pytest.raises(TypeError, match="JSON"):
        canonical_json_bytes({"items": (1, 2)})
    with pytest.raises(TypeError, match="string"):
        canonical_json_bytes({1: "value"})


def test_context_fingerprint_parses_declared_json_fields_only() -> None:
    """Catch raw JSON formatting hashes and accidental truth/metadata inclusion."""
    from src.hephaestus.evaluation_assets.review import (
        model_visible_context_fingerprint,
    )

    first = _case()
    reformatted = copy.deepcopy(first)
    reformatted["context"]["messages_json"] = '[ { "content" : "Hello", "role" : "user" } ]'
    reformatted["context"]["tool_context_json"] = '[ { "arguments" : { "id" : 1 }, "name" : "lookup" } ]'
    reformatted["context"]["runtime_json"] = '{ "locale" : "en-US" }'
    reformatted["case_id"] = "changed"
    reformatted["task_type"] = "changed"
    reformatted["expected"] = {"reference_output": "changed"}
    reformatted["metadata"] = {"changed": True}
    assert model_visible_context_fingerprint(first) == (model_visible_context_fingerprint(reformatted))

    for path, value in (
        (("context", "messages_json"), '[{"role":"assistant","content":"Hello"}]'),
        (("context", "tool_context_json"), "[]"),
        (("context", "runtime_json"), '{"locale":"fr-FR"}'),
        (("context", "verbatim"), " Exact text "),
    ):
        changed = copy.deepcopy(first)
        changed[path[0]][path[1]] = value
        assert model_visible_context_fingerprint(changed) != (model_visible_context_fingerprint(first))

    malformed = copy.deepcopy(first)
    malformed["context"]["messages_json"] = "not-json"
    with pytest.raises(ValueError, match="messages_json"):
        model_visible_context_fingerprint(malformed)


def test_review_fingerprint_changes_for_complete_case_dependency_and_source() -> None:
    """Catch any partial projection that leaves approved semantic content unbound."""
    from src.hephaestus.evaluation_assets.review import build_review_item

    base = build_review_item(
        case=_case(),
        dependency=_dependency(),
        source_provenance=_source_provenance(),
        reviewer="fapo_pipeline",
        timestamp="2026-08-21T12:00:00Z",
    )
    case_mutations = {
        "case_id": "changed-id",
        "task_type": "changed-task",
        "context": {"messages_json": "[]"},
        "expected": {"reference_output": "changed"},
        "metadata": {
            "source": "changed",
            "trust_tier": "inferred_from_trusted_feedback",
        },
    }
    for field, value in case_mutations.items():
        changed_case = copy.deepcopy(_case())
        changed_case[field] = value
        changed = build_review_item(
            case=changed_case,
            dependency=_dependency(),
            source_provenance=_source_provenance(),
            reviewer="fapo_pipeline",
            timestamp="2026-08-21T12:00:00Z",
        )
        assert changed["fingerprint"] != base["fingerprint"], field

    changed_dependency = copy.deepcopy(_dependency())
    changed_dependency["guideline"]["criteria"][0]["statement"] = "Changed"
    assert (
        build_review_item(
            case=_case(),
            dependency=changed_dependency,
            source_provenance=_source_provenance(),
            reviewer="fapo_pipeline",
            timestamp="2026-08-21T12:00:00Z",
        )["fingerprint"]
        != base["fingerprint"]
    )

    changed_source = copy.deepcopy(_source_provenance())
    changed_source["source_record_sha256s"] = ["sha256:" + "f" * 64]
    assert (
        build_review_item(
            case=_case(),
            dependency=_dependency(),
            source_provenance=changed_source,
            reviewer="fapo_pipeline",
            timestamp="2026-08-21T12:00:00Z",
        )["fingerprint"]
        != base["fingerprint"]
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("trusted_split_plan_sha256",), "sha256:" + "f" * 64),
        (("cluster", "record_ids"), ["u1", "u2"]),
        (("cluster", "representative_ids"), ["u2"]),
        (("cluster", "route"), "billing"),
        (("cluster", "top_terms"), ["billing"]),
        (("match", "score"), 0.8),
        (("match", "status"), "needs_more_feedback"),
        (("match", "reason"), "changed"),
        (("guideline", "criteria"), [{"statement": "Changed"}]),
        (("guideline", "support"), {"record_count": 3, "group_count": 2}),
        (
            ("source_members",),
            [
                {
                    "record_id": "u2",
                    "prepared_record_sha256": "sha256:" + "2" * 64,
                    "raw_record_sha256": "sha256:" + "3" * 64,
                }
            ],
        ),
        (("provider", "provider"), "custom"),
        (("provider", "model"), "other-model"),
        (("provider", "request_settings"), {"temperature": 0.1}),
        (("prompt", "sha256"), "sha256:" + "1" * 64),
        (("pipeline_settings", "batch_size"), 4),
        (("pipeline_settings", "contract_revision"), "v2"),
    ],
)
def test_dependency_fingerprint_binds_every_descriptor_field(path: tuple[str, ...], value: Any) -> None:
    """Catch stable-ID reuse when any complete dependency input changes."""
    from src.hephaestus.evaluation_assets.review import dependency_fingerprint

    base = _dependency()
    changed = copy.deepcopy(base)
    target: dict[str, Any] = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert dependency_fingerprint(changed) != dependency_fingerprint(base)


def test_review_item_scoreability_hook_fails_closed() -> None:
    """Catch eligible review items that an integrated scorer cannot score."""
    from src.hephaestus.evaluation_assets.review import build_review_item

    seen: list[dict[str, Any]] = []

    def scoreable(expected: dict[str, Any]) -> bool:
        seen.append(expected)
        return bool(expected.get("reference_output"))

    item = build_review_item(
        case=_case(),
        dependency=_dependency(),
        source_provenance=_source_provenance(),
        reviewer="fapo_pipeline",
        timestamp="2026-08-21T12:00:00Z",
        scoreability=scoreable,
    )
    assert item["initial_decision"]["status"] == "pending"
    assert seen == [_case()["expected"]]

    with pytest.raises(ValueError, match="scoreable"):
        build_review_item(
            case=_case(),
            dependency=_dependency(),
            source_provenance=_source_provenance(),
            reviewer="fapo_pipeline",
            timestamp="2026-08-21T12:00:00Z",
            scoreability=lambda _expected: False,
        )


def test_review_item_rejects_incomplete_dependency_or_source_provenance() -> None:
    """Catch review authority built over placeholders instead of full provenance."""
    from src.hephaestus.evaluation_assets.review import build_review_item

    with pytest.raises(ValueError, match="dependency"):
        build_review_item(
            case=_case(),
            dependency={"x": 1},
            source_provenance=_source_provenance(),
            reviewer="fapo_pipeline",
            timestamp="2026-08-21T12:00:00Z",
        )
    with pytest.raises(ValueError, match="source_provenance"):
        build_review_item(
            case=_case(),
            dependency=_dependency(),
            source_provenance={"x": 1},
            reviewer="fapo_pipeline",
            timestamp="2026-08-21T12:00:00Z",
        )


def test_authentic_dependency_still_requires_complete_generation_provenance() -> None:
    """Catch byte-authentic rows whose nested generation authority is empty."""
    from src.hephaestus.evaluation_assets.dependencies import (
        build_stage_seven_dependency,
        build_stage_six_dependency,
        dependency_matches,
    )
    from src.hephaestus.evaluation_assets.review import dependency_fingerprint

    stage_six_inputs = {
        "cluster": {"cluster_id": "route-001"},
        "match": {"status": "matched_trusted_intent"},
        "guideline": {"guideline_id": "guideline-1"},
        "source_members": [
            {"identity": "u1", "content_sha256": "a" * 64},
        ],
        "provider": {
            "provider": "fake",
            "model": "rubric-model",
            "settings": {"temperature": 0},
        },
        "prompt": {"revision": "label-inference-v1", "sha256": "b" * 64},
        "algorithm_revision": "stage-six-v1",
    }
    stage_six = build_stage_six_dependency(**stage_six_inputs)
    dependency_fingerprint(stage_six)

    incomplete_stage_six = []
    for field in ("provider", "prompt"):
        changed = copy.deepcopy(stage_six_inputs)
        changed[field] = {}
        incomplete_stage_six.append(build_stage_six_dependency(**changed))
    changed = copy.deepcopy(stage_six_inputs)
    changed["provider"]["settings"] = {}
    incomplete_stage_six.append(build_stage_six_dependency(**changed))

    stage_seven_inputs = {
        "cluster": {"cluster_id": "route-001"},
        "rubric": {"must": ["Answer accurately"]},
        "stage_six_dependency": stage_six,
        "comparison_members": [
            {"identity": "u1", "content_sha256": "c" * 64},
        ],
        "provider": stage_six_inputs["provider"],
        "prompt": {"revision": "synthetic-v1", "sha256": "d" * 64},
        "settings": {"candidate_count": 2},
        "algorithm_revision": "stage-seven-v1",
    }
    stage_seven = build_stage_seven_dependency(**stage_seven_inputs)
    dependency_fingerprint(stage_seven)
    changed = copy.deepcopy(stage_seven_inputs)
    changed["settings"] = {}
    incomplete_stage_seven = build_stage_seven_dependency(**changed)

    for incomplete in [*incomplete_stage_six, incomplete_stage_seven]:
        assert dependency_matches(incomplete, incomplete)
        with pytest.raises(ValueError, match="dependency"):
            dependency_fingerprint(incomplete)


def test_self_authenticated_dependency_rejects_malformed_member_provenance() -> None:
    """Catch a valid outer digest concealing arbitrary nested member objects."""
    from src.hephaestus.evaluation_assets.dependencies import (
        build_stage_seven_dependency,
        build_stage_six_dependency,
        dependency_matches,
    )
    from src.hephaestus.evaluation_assets.review import dependency_fingerprint

    stage_six = build_stage_six_dependency(
        cluster={"cluster_id": "route-001"},
        match={"status": "matched_trusted_intent"},
        guideline={"guideline_id": "guideline-1"},
        source_members=[{"identity": "u1", "content_sha256": "a" * 64}],
        provider={
            "provider": "fake",
            "model": "rubric-model",
            "settings": {"temperature": 0},
        },
        prompt={"revision": "label-inference-v1", "sha256": "b" * 64},
        algorithm_revision="stage-six-v1",
    )
    stage_seven = build_stage_seven_dependency(
        cluster={"cluster_id": "route-001"},
        rubric={"must": ["Answer accurately"]},
        stage_six_dependency=stage_six,
        comparison_members=[{"identity": "u1", "content_sha256": "c" * 64}],
        provider=stage_six["descriptor"]["provider"],
        prompt={"revision": "synthetic-v1", "sha256": "d" * 64},
        settings={"candidate_count": 2},
        algorithm_revision="stage-seven-v1",
    )

    for dependency, member_field in (
        (stage_six, "source_members"),
        (stage_seven, "comparison_members"),
    ):
        malformed = copy.deepcopy(dependency)
        malformed["descriptor"][member_field] = [{"arbitrary": True}]
        digest_payload = {
            "schema_version": malformed["schema_version"],
            "descriptor": malformed["descriptor"],
        }
        malformed["dependency_sha256"] = hashlib.sha256(
            json.dumps(
                digest_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        assert dependency_matches(malformed, malformed)
        with pytest.raises(ValueError, match="member"):
            dependency_fingerprint(malformed)


def test_missing_stale_or_malformed_terminal_decision_resolves_pending() -> None:
    """Catch stale or corrupt authority accidentally approving a current item."""
    from src.hephaestus.evaluation_assets.review import (
        record_review_decision,
        resolve_review_decision,
    )

    item = _review_item()
    pending = resolve_review_decision(item, [])
    assert pending == {
        "case_id": "inferred-u1",
        "fingerprint": item["fingerprint"],
        "status": "pending",
        "decision_id": None,
        "reviewer": "fapo_pipeline",
        "timestamp": "2026-08-21T12:00:00Z",
        "note": None,
        "inherited_from": None,
    }

    stale_item = _review_item(dependency={**_dependency(), "revision": 2})
    stale, appended = record_review_decision(
        stale_item,
        [],
        status="approved",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
    )
    assert appended is True
    assert resolve_review_decision(item, [stale])["status"] == "pending"

    malformed = {
        **stale,
        "case_id": item["case_id"],
        "fingerprint": item["fingerprint"],
        "decision_id": "sha256:" + "0" * 64,
    }
    assert resolve_review_decision(item, [malformed])["status"] == "pending"
    assert resolve_review_decision(item, [malformed, malformed])["status"] == ("pending")

    approved, _ = record_review_decision(
        item,
        [],
        status="approved",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
    )
    changed_dependency = {**_dependency(), "revision": 2}
    assert (
        resolve_review_decision(
            item,
            [approved],
            dependency=changed_dependency,
        )["status"]
        == "pending"
    )

    tampered_item = copy.deepcopy(item)
    tampered_item["case"]["expected"] = {"reference_output": "tampered"}
    assert resolve_review_decision(tampered_item, [stale])["status"] == "pending"


def test_terminal_decision_is_immutable_and_replay_idempotent() -> None:
    """Catch duplicate appends or reversal of a terminal human decision."""
    from src.hephaestus.evaluation_assets.review import (
        ReviewDecisionConflictError,
        record_review_decision,
        resolve_review_decision,
        validate_review_decision,
    )

    item = _review_item()
    approved, appended = record_review_decision(
        item,
        [],
        status="approved",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
        note="Verified expected outcome",
    )
    assert appended is True
    assert approved["case_id"] == item["case_id"]
    assert approved["fingerprint"] == item["fingerprint"]
    assert approved["status"] == "approved"
    assert validate_review_decision(approved) == approved
    assert resolve_review_decision(item, [approved])["status"] == "approved"

    replay, appended = record_review_decision(
        item,
        [approved],
        status="approved",
        reviewer="another-request-reviewer",
        timestamp="2026-08-21T14:00:00Z",
    )
    assert replay == approved
    assert appended is False

    with pytest.raises(ReviewDecisionConflictError, match="immutable"):
        record_review_decision(
            item,
            [approved],
            status="rejected",
            reviewer="reviewer-b",
            timestamp="2026-08-21T14:00:00Z",
        )

    extra = {**approved, "unexpected": True}
    with pytest.raises(ValueError, match="schema"):
        validate_review_decision(extra)


def test_duplicate_terminal_rows_fail_closed_and_block_new_mutation() -> None:
    """Catch latest-write-wins behavior when an authority log is duplicated."""
    from src.hephaestus.evaluation_assets.review import (
        ReviewIntegrityError,
        record_review_decision,
        resolve_review_decision,
    )

    item = _review_item()
    approved, _ = record_review_decision(
        item,
        [],
        status="approved",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
    )
    assert resolve_review_decision(item, [approved, approved])["status"] == "pending"
    with pytest.raises(ReviewIntegrityError, match="multiple"):
        record_review_decision(
            item,
            [approved, approved],
            status="approved",
            reviewer="reviewer-a",
            timestamp="2026-08-21T13:00:00Z",
        )


def test_any_malformed_decision_log_row_invalidates_authority() -> None:
    """Catch approval despite corruption elsewhere in the append-only log."""
    from src.hephaestus.evaluation_assets.review import (
        ReviewIntegrityError,
        record_review_decision,
        resolve_review_decision,
    )

    item = _review_item()
    approved, _ = record_review_decision(
        item,
        [],
        status="approved",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
    )
    assert resolve_review_decision(item, [approved, "garbage"])["status"] == ("pending")
    with pytest.raises(ReviewIntegrityError, match="malformed"):
        record_review_decision(
            item,
            [{"case_id": item["case_id"]}],
            status="approved",
            reviewer="reviewer-a",
            timestamp="2026-08-21T13:00:00Z",
        )


def test_missing_decision_authority_fails_closed() -> None:
    """Catch raw iteration errors when the decision authority is absent."""
    from src.hephaestus.evaluation_assets.review import (
        ReviewIntegrityError,
        record_review_decision,
        resolve_review_decision,
    )

    item = _review_item()
    assert resolve_review_decision(item, None)["status"] == "pending"
    with pytest.raises(ReviewIntegrityError, match="malformed"):
        record_review_decision(
            item,
            None,
            status="approved",
            reviewer="reviewer-a",
            timestamp="2026-08-21T13:00:00Z",
        )


def test_child_inherits_only_an_identical_fingerprint_and_case() -> None:
    """Catch approval inheritance by stable case ID instead of exact content."""
    from src.hephaestus.evaluation_assets.review import (
        inherit_review_decision,
        record_review_decision,
        validate_review_decision,
    )

    parent_item = _review_item()
    parent_decision, _ = record_review_decision(
        parent_item,
        [],
        status="rejected",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
        note="Unsupported answer",
    )
    identical_child = _review_item(timestamp="2026-08-22T12:00:00Z")
    inherited = inherit_review_decision(
        parent_item=parent_item,
        child_item=identical_child,
        parent_decisions=[parent_decision],
        parent_asset_id="v1",
        reviewer="fapo_pipeline",
        timestamp="2026-08-22T13:00:00Z",
    )
    assert inherited is not None
    assert inherited["status"] == "rejected"
    assert inherited["original_reviewer"] == "reviewer-a"
    assert inherited["original_timestamp"] == "2026-08-21T13:00:00Z"
    assert inherited["inherited_from"] == {
        "parent_asset_id": "v1",
        "parent_decision_id": parent_decision["decision_id"],
        "parent_fingerprint": parent_item["fingerprint"],
    }
    assert validate_review_decision(inherited) == inherited

    changed_child = _review_item(dependency={**_dependency(), "revision": 2})
    assert (
        inherit_review_decision(
            parent_item=parent_item,
            child_item=changed_child,
            parent_decisions=[parent_decision],
            parent_asset_id="v1",
            reviewer="fapo_pipeline",
            timestamp="2026-08-22T13:00:00Z",
        )
        is None
    )


def test_decision_set_fingerprint_binds_the_exact_resolved_authority() -> None:
    """Catch finalization guards that ignore terminal decision changes."""
    from src.hephaestus.evaluation_assets.review import (
        decision_set_fingerprint,
        record_review_decision,
        review_set_fingerprint,
    )

    item = _review_item()
    dependency = _dependency()
    review_set = review_set_fingerprint(
        stage7_receipt_sha256="sha256:" + "7" * 64,
        review_items=[item],
        held_cases=[],
        dependencies={item["case_id"]: dependency},
    )
    pending = decision_set_fingerprint(
        review_set_fingerprint=review_set,
        review_items=[item],
        dependencies={item["case_id"]: dependency},
        decisions=[],
    )
    approved, _ = record_review_decision(
        item,
        [],
        status="approved",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
    )
    terminal = decision_set_fingerprint(
        review_set_fingerprint=review_set,
        review_items=[item],
        dependencies={item["case_id"]: dependency},
        decisions=[approved],
    )

    assert pending.startswith("sha256:")
    assert terminal.startswith("sha256:")
    assert pending != terminal
    assert terminal == decision_set_fingerprint(
        review_set_fingerprint=review_set,
        review_items=[item],
        dependencies={item["case_id"]: dependency},
        decisions=[approved],
    )


def test_finalization_freezes_exact_current_items_holds_and_decisions() -> None:
    """Catch finalization snapshots that can drift from the reviewed set."""
    from src.hephaestus.evaluation_assets.review import (
        build_review_finalization,
        record_review_decision,
        validate_review_finalization,
    )

    approved_item = _review_item_for("inferred-u1")
    pending_item = _review_item_for("synthetic-s1")
    approved, _ = record_review_decision(
        approved_item,
        [],
        status="approved",
        reviewer="reviewer-a",
        timestamp="2026-08-21T13:00:00Z",
    )
    held = [
        {
            "case_id": "trusted-conflict",
            "fingerprint": "sha256:" + "9" * 64,
            "reason": "conflicting_expected_truth",
            "audit_detail": {"context": "sha256:" + "8" * 64},
        }
    ]
    receipt = "sha256:" + "7" * 64
    finalization = build_review_finalization(
        review_items=[pending_item, approved_item],
        dependencies={
            "inferred-u1": {**_dependency(), "case_id": "inferred-u1"},
            "synthetic-s1": {**_dependency(), "case_id": "synthetic-s1"},
        },
        decisions=[approved],
        held_cases=held,
        stage7_receipt_sha256=receipt,
        trusted_count=4,
        reviewer="release-reviewer",
        timestamp="2026-08-21T14:00:00Z",
        note="Release the approved subset",
    )
    assert finalization["items"] == [
        {
            "case_id": "inferred-u1",
            "fingerprint": approved_item["fingerprint"],
            "status": "approved",
            "decision_id": approved["decision_id"],
        },
        {
            "case_id": "synthetic-s1",
            "fingerprint": pending_item["fingerprint"],
            "status": "pending",
            "decision_id": None,
        },
    ]
    assert finalization["held"] == [
        {
            "case_id": "trusted-conflict",
            "fingerprint": "sha256:" + "9" * 64,
            "reason": "conflicting_expected_truth",
        }
    ]
    assert finalization["counts"] == {
        "trusted": 4,
        "approved": 1,
        "pending": 1,
        "rejected": 0,
        "held": 1,
    }
    assert (
        validate_review_finalization(
            finalization,
            review_items=[approved_item, pending_item],
            dependencies={
                "inferred-u1": {**_dependency(), "case_id": "inferred-u1"},
                "synthetic-s1": {**_dependency(), "case_id": "synthetic-s1"},
            },
            decisions=[approved],
            held_cases=held,
            stage7_receipt_sha256=receipt,
        )
        == finalization
    )

    other_audit = build_review_finalization(
        review_items=[approved_item, pending_item],
        dependencies={
            "inferred-u1": {**_dependency(), "case_id": "inferred-u1"},
            "synthetic-s1": {**_dependency(), "case_id": "synthetic-s1"},
        },
        decisions=[approved],
        held_cases=held,
        stage7_receipt_sha256=receipt,
        trusted_count=4,
        reviewer="different-finalizer",
        timestamp="2026-08-21T15:00:00Z",
    )
    assert other_audit["finalization_id"] == finalization["finalization_id"]


def test_finalization_validator_rejects_stale_or_malformed_snapshot() -> None:
    """Catch release authorization with a changed queue, hold set, or counts."""
    from src.hephaestus.evaluation_assets.review import (
        build_review_finalization,
        validate_review_finalization,
    )

    item = _review_item()
    receipt = "sha256:" + "7" * 64
    finalization = build_review_finalization(
        review_items=[item],
        dependencies={item["case_id"]: _dependency()},
        decisions=[],
        held_cases=[],
        stage7_receipt_sha256=receipt,
        trusted_count=2,
        reviewer="release-reviewer",
        timestamp="2026-08-21T14:00:00Z",
    )
    with pytest.raises(ValueError, match="schema"):
        validate_review_finalization({**finalization, "extra": True})
    with pytest.raises(ValueError, match="review set"):
        validate_review_finalization(
            finalization,
            review_items=[_review_item_for("changed")],
            dependencies={"changed": {**_dependency(), "case_id": "changed"}},
            decisions=[],
            held_cases=[],
            stage7_receipt_sha256=receipt,
        )
    with pytest.raises(ValueError, match="receipt"):
        validate_review_finalization(
            finalization,
            review_items=[item],
            dependencies={item["case_id"]: _dependency()},
            decisions=[],
            held_cases=[],
            stage7_receipt_sha256="sha256:" + "6" * 64,
        )
    with pytest.raises(ValueError, match="dependency"):
        validate_review_finalization(
            finalization,
            review_items=[item],
            dependencies={item["case_id"]: {**_dependency(), "revision": "changed"}},
            decisions=[],
            held_cases=[],
            stage7_receipt_sha256=receipt,
        )

    bad_counts = copy.deepcopy(finalization)
    bad_counts["counts"]["approved"] = 1
    with pytest.raises(ValueError, match="counts"):
        validate_review_finalization(bad_counts)


def test_finalization_rejects_missing_or_malformed_decision_authority() -> None:
    """Catch a finalization mutation that silently converts corruption to pending."""
    from src.hephaestus.evaluation_assets.review import (
        ReviewIntegrityError,
        build_review_finalization,
    )

    item = _review_item()
    arguments = {
        "review_items": [item],
        "dependencies": {item["case_id"]: _dependency()},
        "held_cases": [],
        "stage7_receipt_sha256": "sha256:" + "7" * 64,
        "trusted_count": 1,
        "reviewer": "release-reviewer",
        "timestamp": "2026-08-21T14:00:00Z",
    }
    with pytest.raises(ReviewIntegrityError, match="decision authority"):
        build_review_finalization(decisions=None, **arguments)
    with pytest.raises(ReviewIntegrityError, match="decision authority"):
        build_review_finalization(decisions=[{"case_id": item["case_id"]}], **arguments)


def test_structural_finalization_parse_cannot_authorize_false_approval() -> None:
    """Catch a self-rehashed snapshot bypassing live decision authority."""
    from src.hephaestus.evaluation_assets.review import (
        REVIEW_FINALIZATION_IDENTITY_SCHEMA_VERSION,
        ReviewIntegrityError,
        build_review_finalization,
        fingerprint_json,
        parse_review_finalization,
        validate_review_finalization,
    )

    item = _review_item()
    receipt = "sha256:" + "7" * 64
    finalization = build_review_finalization(
        review_items=[item],
        dependencies={item["case_id"]: _dependency()},
        decisions=[],
        held_cases=[],
        stage7_receipt_sha256=receipt,
        trusted_count=1,
        reviewer="release-reviewer",
        timestamp="2026-08-21T14:00:00Z",
    )
    tampered = copy.deepcopy(finalization)
    tampered["items"][0]["status"] = "approved"
    tampered["items"][0]["decision_id"] = "sha256:" + "5" * 64
    tampered["counts"]["pending"] = 0
    tampered["counts"]["approved"] = 1
    identity = {
        key: tampered[key]
        for key in (
            "review_set_fingerprint",
            "stage7_receipt_sha256",
            "items",
            "held",
            "counts",
        )
    }
    tampered["finalization_id"] = fingerprint_json(
        {
            "schema_version": REVIEW_FINALIZATION_IDENTITY_SCHEMA_VERSION,
            "snapshot": identity,
        }
    )
    assert parse_review_finalization(tampered) == tampered
    with pytest.raises(ReviewIntegrityError, match="live review authority"):
        validate_review_finalization(tampered)
    with pytest.raises(ValueError, match="decisions"):
        validate_review_finalization(
            tampered,
            review_items=[item],
            dependencies={item["case_id"]: _dependency()},
            decisions=[],
            held_cases=[],
            stage7_receipt_sha256=receipt,
        )


def test_exact_context_family_is_transitive_across_sources_and_groups() -> None:
    """Catch pairwise-only grouping that leaks a graph chain across splits."""
    from src.hephaestus.evaluation_assets.review import build_duplicate_families

    cases = [
        _family_case(
            "trusted-a",
            "Context A",
            "group-a",
            split_group_id="split-group-a",
            trusted_split="train",
        ),
        _family_case(
            "inferred-b",
            "Context A",
            "group-b",
            trust_tier="inferred_from_trusted_feedback",
        ),
        _family_case(
            "synthetic-c",
            "Context C",
            "group-b",
            trust_tier="synthetic_from_trusted_rubric",
        ),
        _family_case(
            "synthetic-d",
            "Context C",
            "group-d",
            trust_tier="synthetic_from_trusted_rubric",
        ),
    ]
    families = build_duplicate_families(cases)
    assert len(families) == 1
    family = families[0]
    assert [member["case_id"] for member in family["members"]] == [
        "inferred-b",
        "synthetic-c",
        "synthetic-d",
        "trusted-a",
    ]
    assert family["group_ids"] == ["group-a", "group-b", "group-d"]
    assert family["split_group_id"] == "split-group-a"
    assert family["assigned_early_split"] == "train"
    assert family["hold_reasons"] == []


def test_supplied_split_group_is_an_exact_transitive_union_edge() -> None:
    """Catch separation of cases already assigned to one Task 5 component."""
    from src.hephaestus.evaluation_assets.review import build_duplicate_families

    families = build_duplicate_families(
        [
            _family_case(
                "trusted-a",
                "Different A",
                "group-a",
                split_group_id="split-shared",
                trusted_split="validation",
            ),
            _family_case(
                "trusted-b",
                "Different B",
                "group-b",
                split_group_id="split-shared",
                trusted_split="validation",
            ),
        ]
    )
    assert len(families) == 1
    assert families[0]["split_group_id"] == "split-shared"
    assert families[0]["assigned_early_split"] == "validation"


def test_exact_family_does_not_fold_whitespace_case_or_paraphrase() -> None:
    """Catch prohibited semantic, case, or whitespace duplicate grouping."""
    from src.hephaestus.evaluation_assets.review import build_duplicate_families

    families = build_duplicate_families(
        [
            _family_case("a", "Reset password", "group-a"),
            _family_case("b", "reset password", "group-b"),
            _family_case("c", "Reset password ", "group-c"),
            _family_case("d", "Help me change my password", "group-d"),
        ]
    )
    assert len(families) == 4
    assert {tuple(member["case_id"] for member in row["members"]) for row in families} == {
        ("a",),
        ("b",),
        ("c",),
        ("d",),
    }


def test_identical_context_and_truth_share_one_unheld_split_group() -> None:
    """Catch accidental deduplication or conflict classification of exact replicas."""
    from src.hephaestus.evaluation_assets.review import (
        build_duplicate_families,
        validate_duplicate_family,
    )

    families = build_duplicate_families(
        [
            _family_case("a", "Same", "group-a"),
            _family_case(
                "b",
                "Same",
                "group-b",
                trust_tier="inferred_from_trusted_feedback",
            ),
        ]
    )
    assert len(families) == 1
    family = families[0]
    assert len(family["members"]) == 2
    assert len(family["truth_fingerprints"]) == 1
    assert family["split_group_id"].startswith("splitgrp-")
    assert family["hold_reasons"] == []
    assert validate_duplicate_family(family) == family
    with pytest.raises(ValueError, match="schema"):
        validate_duplicate_family({**family, "extra": True})


def test_provenance_only_expected_fields_do_not_create_a_truth_conflict() -> None:
    """Duplicate truth compares scoreable fields, not label provenance."""
    from src.hephaestus.evaluation_assets.review import build_duplicate_families

    trusted_expected = {
        "reference_output": "answer",
        "label_source": "evaluation_guideline_from_trusted_feedback",
        "confidence": 0.9,
        "feedback_polarity": "positive",
        "evaluation_guideline_ids": ["guideline-1"],
        "evaluation_guidelines": [{"guideline_id": "guideline-1"}],
    }
    inferred_expected = {
        "reference_output": "answer",
        "label_source": "inferred_from_trusted_feedback",
        "confidence": 0.7,
    }

    families = build_duplicate_families(
        [
            _family_case(
                "trusted-a",
                "Same",
                "group-a",
                expected=trusted_expected,
            ),
            _family_case(
                "inferred-b",
                "Same",
                "group-b",
                trust_tier="inferred_from_trusted_feedback",
                expected=inferred_expected,
            ),
        ]
    )

    assert len(families) == 1
    assert len(families[0]["truth_fingerprints"]) == 1
    assert families[0]["hold_reasons"] == []


def test_conflicting_truth_holds_every_member_of_the_connected_component() -> None:
    """Catch preference by trust tier when exact context has conflicting truth."""
    from src.hephaestus.evaluation_assets.review import build_duplicate_families

    families = build_duplicate_families(
        [
            _family_case(
                "trusted-a",
                "Same",
                "group-a",
                expected={"reference_output": "A"},
            ),
            _family_case(
                "inferred-b",
                "Same",
                "group-b",
                trust_tier="inferred_from_trusted_feedback",
                expected={"reference_output": "B"},
            ),
            _family_case(
                "synthetic-c",
                "Other",
                "group-b",
                trust_tier="synthetic_from_trusted_rubric",
            ),
        ]
    )
    assert len(families) == 1
    assert families[0]["hold_reasons"] == ["conflicting_expected_truth"]
    assert {member["case_id"] for member in families[0]["members"]} == {
        "trusted-a",
        "inferred-b",
        "synthetic-c",
    }


def test_derived_bridge_across_early_splits_is_held_without_reassignment() -> None:
    """Catch reshuffling of protected assignments after a derived bridge appears."""
    from src.hephaestus.evaluation_assets.review import build_duplicate_families

    families = build_duplicate_families(
        [
            _family_case(
                "trusted-train",
                "Train context",
                "group-train",
                split_group_id="split-train",
                trusted_split="train",
            ),
            _family_case(
                "trusted-test",
                "Test context",
                "group-test",
                split_group_id="split-test",
                trusted_split="test",
            ),
            _family_case(
                "derived-bridge",
                "Train context",
                "group-test",
                trust_tier="inferred_from_trusted_feedback",
            ),
        ]
    )
    assert len(families) == 1
    family = families[0]
    assert family["assigned_early_split"] is None
    assert family["split_group_id"] == "split-test"
    assert family["split_group_aliases"] == ["split-train"]
    assert family["hold_reasons"] == ["early_split_component_conflict"]
    anchors = {member["case_id"]: member["early_split"] for member in family["members"]}
    assert anchors == {
        "derived-bridge": None,
        "trusted-test": "test",
        "trusted-train": "train",
    }


def test_duplicate_family_validator_rejects_disconnected_self_signed_members() -> None:
    """Catch a structurally rehashed row that is not one connected component."""
    from src.hephaestus.evaluation_assets.review import (
        DUPLICATE_FAMILY_IDENTITY_SCHEMA_VERSION,
        DUPLICATE_FAMILY_SCHEMA_VERSION,
        SPLIT_GROUP_IDENTITY_SCHEMA_VERSION,
        build_duplicate_families,
        fingerprint_json,
        validate_duplicate_family,
    )

    singletons = build_duplicate_families(
        [
            _family_case("a", "Context A", "group-a"),
            _family_case("b", "Context B", "group-b"),
        ]
    )
    members = sorted(
        [member for family in singletons for member in family["members"]],
        key=lambda row: row["case_id"],
    )
    context_fingerprints = sorted({member["context_fingerprint"] for member in members})
    group_ids = sorted({member["group_id"] for member in members})
    split_identity = fingerprint_json(
        {
            "schema_version": SPLIT_GROUP_IDENTITY_SCHEMA_VERSION,
            "group_ids": group_ids,
            "context_fingerprints": context_fingerprints,
        }
    )
    family_identity = fingerprint_json(
        {
            "schema_version": DUPLICATE_FAMILY_IDENTITY_SCHEMA_VERSION,
            "members": members,
        }
    )
    disconnected = {
        "schema_version": DUPLICATE_FAMILY_SCHEMA_VERSION,
        "family_id": "family-" + family_identity.removeprefix("sha256:")[:24],
        "context_fingerprints": context_fingerprints,
        "group_ids": group_ids,
        "split_group_id": "splitgrp-" + split_identity.removeprefix("sha256:")[:24],
        "split_group_aliases": [],
        "members": members,
        "truth_fingerprints": sorted({member["truth_fingerprint"] for member in members}),
        "assigned_early_split": None,
        "hold_reasons": [],
    }
    with pytest.raises(ValueError, match="connected"):
        validate_duplicate_family(disconnected)
