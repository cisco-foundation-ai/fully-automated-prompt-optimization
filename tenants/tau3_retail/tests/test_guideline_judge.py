# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for deterministic aggregation of case-specific rubric verdicts."""

from __future__ import annotations

from tenants.tau3_retail.code.scorers.guideline_judge import GuidelineJudgeScorer


def test_aggregate_weights_severity_and_flags_critical_partial() -> None:
    criteria = [
        {"criterion_id": "critical", "severity": "critical"},
        {"criterion_id": "major", "severity": "major"},
        {"criterion_id": "minor", "severity": "minor"},
        {"criterion_id": "unused", "severity": "major"},
    ]
    verdict = {
        "criteria": [
            {"criterion_id": "critical", "status": "partial", "evidence": "x"},
            {"criterion_id": "major", "status": "satisfied", "evidence": "y"},
            {"criterion_id": "minor", "status": "violated", "evidence": "z"},
            {"criterion_id": "unused", "status": "not_applicable", "evidence": ""},
        ]
    }

    score, critical, applicable, details = GuidelineJudgeScorer._aggregate(
        criteria, verdict
    )

    assert score == 58.3333
    assert critical == 1
    assert applicable == 3
    assert len(details) == 4


def test_missing_verdict_defaults_to_violation() -> None:
    score, critical, applicable, details = GuidelineJudgeScorer._aggregate(
        [{"criterion_id": "must", "severity": "critical"}],
        {"criteria": []},
    )

    assert score == 0.0
    assert critical == 1
    assert applicable == 1
    assert details[0]["status"] == "violated"
