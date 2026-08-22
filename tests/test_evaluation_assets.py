# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.hephaestus import local_authority_io
from src.hephaestus.datasets.evaluation_assets import (
    RubricOracle,
    assemble_dataset_bundle,
    filter_synthetic_cases,
    load_fapo_cases,
    split_cases_by_group,
    write_coverage_report,
)
from src.hephaestus.datasets.intent_assets import IntentCluster, IntentMatch
from src.hephaestus.evaluation_assets import workspace as workspace_module
from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig, PipelineState
from src.hephaestus.evaluation_assets.pipeline import _write_missing_report
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


def test_rubric_oracle_serializes_expected_payload():
    oracle = RubricOracle(
        label_source="human_feedback",
        confidence=0.8,
        must=["satisfy requirement alpha"],
        must_not=["introduce unsupported values"],
        tool_expectations={"required_tool": "tool_a"},
    )

    expected = oracle.to_expected()

    assert expected["label_source"] == "human_feedback"
    assert expected["rubric"]["must"] == ["satisfy requirement alpha"]
    assert expected["tool_expectations"]["required_tool"] == "tool_a"


def test_split_cases_by_group_keeps_threads_together():
    cases = [
        _case("c1", thread="t1"),
        _case("c2", thread="t1"),
        _case("c3", thread="t2"),
        _case("c4", thread="t3"),
        _case("c5", thread="t4"),
    ]

    splits = split_cases_by_group(cases, seed=7)

    location_by_case = {
        case["case_id"]: split_name
        for split_name, split_cases in splits.items()
        for case in split_cases
    }
    assert location_by_case["c1"] == location_by_case["c2"]
    assert sorted(location_by_case) == ["c1", "c2", "c3", "c4", "c5"]


def test_filter_synthetic_cases_rejects_unscoreable_leaky_and_duplicate_cases():
    existing = [_case("trusted-1", message="category alpha request")]
    candidates = [
        _case(
            "good-1",
            message="category beta request",
            expected={"rubric": {"must": ["satisfy criterion beta"]}},
        ),
        _case("bad-score", expected={}),
        _case("bad-empty-rubric", expected={"rubric": {"must": []}}),
        _case(
            "bad-leak",
            message="The user said this was wrong because criterion alpha was missing.",
            expected={
                "rubric": {"must": ["satisfy criterion alpha"]},
                "feedback_rationale": (
                    "The user said this was wrong because criterion alpha was missing."
                ),
            },
        ),
        _case("bad-dupe", message="category alpha request"),
    ]

    result = filter_synthetic_cases(candidates, existing_cases=existing)

    assert [case["case_id"] for case in result.accepted] == ["good-1"]
    assert {issue.code for issue in result.issues} == {
        "label_leakage",
        "near_duplicate",
        "not_scoreable",
    }


def test_assemble_dataset_bundle_writes_manifest_and_split_files(tmp_path: Path):
    trusted = [_case("trusted-1", thread="t1"), _case("trusted-2", thread="t2")]
    synthetic = [_case("synth-1", thread="s1"), _case("synth-2", thread="s2")]
    regression = [_case("reg-1", thread="r1")]

    manifest = assemble_dataset_bundle(
        output_dir=tmp_path,
        dataset_version="v1",
        trusted_cases=trusted,
        synthetic_cases=synthetic,
        regression_cases=regression,
        seed=3,
    )

    manifest_path = tmp_path / "dataset_manifest.json"
    loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    train_cases = load_fapo_cases(tmp_path / "train.jsonl")
    regression_cases = load_fapo_cases(tmp_path / "regression_trusted.jsonl")

    assert manifest.dataset_version == "v1"
    assert loaded_manifest["dataset_version"] == "v1"
    assert manifest.split_counts["train"] == len(train_cases)
    assert [case["case_id"] for case in regression_cases] == ["reg-1"]


def test_write_coverage_report_includes_missing_label_requests(tmp_path: Path):
    report = tmp_path / "coverage_report.md"
    clusters = [
        IntentCluster(
            cluster_id="route-001",
            route="route",
            record_ids=["r1", "r2"],
            representative_ids=["r1"],
            top_terms=["category", "alpha"],
        )
    ]
    matches = [IntentMatch(cluster_id="route-001", status="missing_or_weak_labels", score=0.2)]

    write_coverage_report(report, clusters, matches)

    text = report.read_text(encoding="utf-8")
    assert "Missing or weak labels: 1" in text
    assert "route representative examples" in text


def test_atomic_jsonl_preserves_existing_bytes_and_cleans_temp_on_generator_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rows.jsonl"
    original = b'{"original":true}\n'
    path.write_bytes(original)

    def failing_rows():
        yield {"replacement": 1}
        raise RuntimeError("producer failed")

    with pytest.raises(RuntimeError, match="producer failed"):
        workspace_module.atomic_write_jsonl(path, failing_rows())

    assert path.read_bytes() == original
    assert list(tmp_path.glob(".rows.jsonl.*.tmp")) == []


def test_atomic_text_preserves_existing_bytes_and_cleans_temp_on_generator_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "report.md"
    original = b"original report\n"
    path.write_bytes(original)

    def failing_chunks():
        yield "replacement"
        raise RuntimeError("text producer failed")

    with pytest.raises(RuntimeError, match="text producer failed"):
        workspace_module.atomic_write_text(path, failing_chunks())

    assert path.read_bytes() == original
    assert list(tmp_path.glob(".report.md.*.tmp")) == []


def test_atomic_json_and_append_cleanup_after_serialization_failure(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "state.json"
    jsonl_path = tmp_path / "events.jsonl"
    original_json = b'{"status":"original"}\n'
    original_jsonl = b'{"event":"original"}\n'
    json_path.write_bytes(original_json)
    jsonl_path.write_bytes(original_jsonl)

    with pytest.raises(TypeError):
        workspace_module.atomic_write_json(json_path, {"invalid": object()})
    with pytest.raises(TypeError):
        workspace_module.atomic_append_jsonl(jsonl_path, {"invalid": object()})

    assert json_path.read_bytes() == original_json
    assert jsonl_path.read_bytes() == original_jsonl
    assert list(tmp_path.glob(".state.json.*.tmp")) == []
    assert list(tmp_path.glob(".events.jsonl.*.tmp")) == []


@pytest.mark.parametrize("artifact", ["state", "events", "history"])
def test_layout_writers_preserve_previous_artifact_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
) -> None:
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    layout.ensure()
    state = PipelineState.new(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        "2026-08-19T00:00:00+00:00",
    )
    path = {
        "state": layout.state_path,
        "events": layout.events_path,
        "history": layout.config_history_path,
    }[artifact]
    original = b'{"original":true}\n'
    path.write_bytes(original)

    def fail_exchange(
        directory_descriptor: int,
        source: str,
        destination: str,
        **kwargs: object,
    ) -> local_authority_io.OwnedNode:
        del directory_descriptor, source, destination, kwargs
        raise OSError("replace failed")

    monkeypatch.setattr(local_authority_io, "replace_with_backup", fail_exchange)
    with pytest.raises(OSError, match="replace failed"):
        if artifact == "state":
            layout.save_state(state)
        elif artifact == "events":
            layout.append_event("new_event")
        else:
            layout._append_config_revision({"event": "new_revision"})

    assert path.read_bytes() == original
    retained = list(path.parent.glob(f".{path.name}.*.tmp"))
    assert retained == []


@pytest.mark.parametrize("report_kind", ["coverage", "missing"])
def test_markdown_reports_preserve_previous_artifact_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    report_kind: str,
) -> None:
    path = tmp_path / f"{report_kind}.md"
    original = b"original report\n"
    path.write_bytes(original)

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        if report_kind == "coverage":
            write_coverage_report(path, [], [])
        else:
            _write_missing_report(path, [])

    assert path.read_bytes() == original
    assert list(tmp_path.glob(f".{path.name}.*.tmp")) == []


def test_copy_writer_preserves_previous_artifact_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.jsonl"
    destination = tmp_path / "destination.jsonl"
    source.write_bytes(b'{"new":true}\n')
    original = b'{"original":true}\n'
    destination.write_bytes(original)

    def fail_replace(source_path, destination_path, *args, **kwargs):
        del source_path, destination_path, args, kwargs
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        workspace_module._copy_jsonl(source, destination)

    assert destination.read_bytes() == original
    assert list(tmp_path.glob(".destination.jsonl.*.tmp")) == []


def _case(
    case_id: str,
    message: str = "process this request",
    thread: str = "thread-1",
    expected: dict | None = None,
) -> dict:
    return {
        "case_id": case_id,
        "task_type": "generic_task",
        "context": {"messages_json": json.dumps([{"role": "user", "content": message}])},
        "expected": expected if expected is not None else {"rubric": {"must": ["answer the request"]}},
        "metadata": {"group_id": thread},
    }
