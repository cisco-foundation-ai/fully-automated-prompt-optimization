# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from src.hephaestus.datasets.evaluation_assets import (
    RubricOracle,
    assemble_dataset_bundle,
    filter_synthetic_cases,
    load_fapo_cases,
    split_cases_by_group,
    write_coverage_report,
)
from src.hephaestus.datasets.intent_assets import IntentCluster, IntentMatch


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
