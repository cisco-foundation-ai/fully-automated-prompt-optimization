# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Dependency fingerprints must invalidate every generation-visible input."""

from __future__ import annotations

from copy import deepcopy

import pytest

from src.hephaestus.evaluation_assets.dependencies import (
    build_stage_seven_dependency,
    build_stage_six_dependency,
    dependency_matches,
)


def _stage_six_inputs() -> dict:
    return {
        "cluster": {
            "cluster_id": "c1",
            "route": "route-a",
            "record_ids": ["u1"],
            "representative_ids": ["u1"],
            "top_terms": ["request"],
        },
        "match": {
            "cluster_id": "c1",
            "status": "matched_trusted_intent",
            "matched_intent_id": "g1",
            "score": 0.9,
            "trusted_example_count": 1,
            "trusted_group_count": 1,
        },
        "guideline": {
            "guideline_id": "g1",
            "source_record_ids": ["f1"],
            "criteria": [{"kind": "required", "statement": "answer"}],
            "support": {"examples": 1, "groups": 1},
        },
        "source_members": [
            {"identity": "f1", "content_sha256": "a" * 64},
            {"identity": "u1", "content_sha256": "b" * 64},
        ],
        "provider": {
            "provider": "fake",
            "model": "rubric-v1",
            "settings": {"batch_size": 8, "temperature": 0},
        },
        "prompt": {"revision": "label-inference-v1", "sha256": "c" * 64},
        "algorithm_revision": "stage-six-dependency-v1",
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["cluster"]["record_ids"].append("u2"),
        lambda value: value["match"].update(score=0.8),
        lambda value: value["guideline"]["criteria"][0].update(statement="changed"),
        lambda value: value["guideline"]["support"].update(groups=2),
        lambda value: value["source_members"][0].update(content_sha256="d" * 64),
        lambda value: value["provider"].update(model="rubric-v2"),
        lambda value: value["provider"]["settings"].update(batch_size=4),
        lambda value: value["prompt"].update(revision="label-inference-v2"),
        lambda value: value.update(algorithm_revision="stage-six-dependency-v2"),
    ],
)
def test_stage_six_dependency_binds_every_declared_input(mutate) -> None:
    """Stable IDs cannot conceal any Stage 6 semantic dependency change."""
    baseline_inputs = _stage_six_inputs()
    baseline = build_stage_six_dependency(**baseline_inputs)
    changed_inputs = deepcopy(baseline_inputs)
    mutate(changed_inputs)
    changed = build_stage_six_dependency(**changed_inputs)

    assert changed["dependency_sha256"] != baseline["dependency_sha256"]
    assert dependency_matches(baseline, baseline)
    assert not dependency_matches(baseline, changed)


def _stage_seven_inputs() -> dict:
    stage_six = build_stage_six_dependency(**_stage_six_inputs())
    return {
        "cluster": _stage_six_inputs()["cluster"],
        "rubric": {
            "cluster_id": "c1",
            "must": ["answer"],
            "must_not": [],
            "deterministic_checks": [],
        },
        "stage_six_dependency": stage_six,
        "comparison_members": [
            {"identity": "feedback-f1", "content_sha256": "e" * 64}
        ],
        "provider": _stage_six_inputs()["provider"],
        "prompt": {"revision": "synthetic-v1", "sha256": "f" * 64},
        "settings": {
            "candidate_count": 2,
            "literal_leakage_min_length": 24,
            "token_overlap_threshold": 0.95,
        },
        "algorithm_revision": "stage-seven-dependency-v1",
    }


def _replace_stage_six_dependency(value: dict) -> None:
    changed_inputs = _stage_six_inputs()
    changed_inputs["match"]["score"] = 0.7
    value["stage_six_dependency"] = build_stage_six_dependency(**changed_inputs)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["rubric"]["must"].append("cite"),
        _replace_stage_six_dependency,
        lambda value: value["comparison_members"][0].update(
            content_sha256="1" * 64
        ),
        lambda value: value["provider"].update(model="rubric-v2"),
        lambda value: value["prompt"].update(revision="synthetic-v2"),
        lambda value: value["settings"].update(candidate_count=3),
        lambda value: value["settings"].update(token_overlap_threshold=0.9),
        lambda value: value.update(algorithm_revision="stage-seven-dependency-v2"),
    ],
)
def test_stage_seven_dependency_binds_every_declared_input(mutate) -> None:
    """Synthetic reuse changes whenever generation or filter evidence changes."""
    baseline_inputs = _stage_seven_inputs()
    baseline = build_stage_seven_dependency(**baseline_inputs)
    changed_inputs = deepcopy(baseline_inputs)
    mutate(changed_inputs)
    changed = build_stage_seven_dependency(**changed_inputs)

    assert changed["dependency_sha256"] != baseline["dependency_sha256"]


@pytest.mark.parametrize(
    "persisted",
    [
        {},
        {"schema_version": "unknown"},
        {
            "schema_version": "fapo-stage-six-dependency-v1",
            "dependency_sha256": "0" * 64,
            "descriptor": {},
        },
    ],
)
def test_malformed_or_missing_dependency_fails_closed(persisted: dict) -> None:
    """An extension regenerates rather than trusting incomplete evidence."""
    current = build_stage_six_dependency(**_stage_six_inputs())

    assert not dependency_matches(persisted, current)
