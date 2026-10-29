# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from data_pipeline_fakes import ScriptedModel, make_record, write_jsonl
from filelock import FileLock

from src.hephaestus import cli
from src.hephaestus.data_pipeline import build as build_module
from src.hephaestus.data_pipeline.build import AssetExistsError, build_asset
from src.hephaestus.data_pipeline.config import AssetConfig
from src.hephaestus.data_pipeline.prepare import prepare_records
from src.hephaestus.data_pipeline.prompts import OBSERVE_PROMPT, RUBRIC_PROMPT, SYNTHESIZE_PROMPT
from src.hephaestus.datasets.jsonl_loader import load_cases_with_identity

FEEDBACK = [make_record(f"f{i:02d}", labeled=True) for i in range(15)]
UNLABELED = [make_record(f"u{i:02d}", labeled=False) for i in range(10)]


def _write_inputs(root: Path, feedback: List[Dict[str, Any]] = FEEDBACK) -> None:
    write_jsonl(root / "feedback.jsonl", feedback)
    write_jsonl(root / "unlabeled.jsonl", UNLABELED)


def _config(**overrides: Any) -> AssetConfig:
    raw = {
        "tenant_id": "demo",
        "asset_id": "v1",
        "feedback": "feedback.jsonl",
        "unlabeled": "unlabeled.jsonl",
        **overrides,
    }
    return AssetConfig.from_dict(raw)


def _build(root: Path, model: Optional[ScriptedModel] = None, **overrides: Any) -> Dict[str, Any]:
    model = model or ScriptedModel()
    return build_asset(_config(**overrides), repository_root=root, provider_factory=lambda: model)


def _cases(asset: Path) -> List[Dict[str, Any]]:
    """Return the cases in the main split files, not the trust-tier views."""
    return [
        json.loads(line)
        for split in ("train", "validation", "test", "regression")
        if (asset / "datasets" / f"{split}.jsonl").is_file()
        for line in (asset / "datasets" / f"{split}.jsonl").read_text().splitlines()
    ]


class TestBuildAsset:
    def test_builds_complete_asset(self, tmp_path: Path) -> None:
        """A build writes datasets, the catalog, the review report, and a manifest last."""
        _write_inputs(tmp_path)

        manifest = _build(tmp_path)

        asset = tmp_path / "tenants/demo/evaluation_assets/v1"
        assert set(manifest["datasets"]) == {"train", "validation", "test"}
        assert sum(d["trusted"] + d["inferred"] for d in manifest["datasets"].values()) == 25
        assert "review.md" in manifest["files"] and "catalog.json" in manifest["files"]
        assert not any(name.startswith("cache/") for name in manifest["files"])
        assert (asset / "inputs/feedback.jsonl").read_bytes() == (tmp_path / "feedback.jsonl").read_bytes()
        review = (asset / "review.md").read_text()
        assert "## Guideline catalog" in review and "G001" in review

    def test_cases_load_and_carry_criteria(self, tmp_path: Path) -> None:
        """Every case loads with the eval runner's loader and has scoreable criteria."""
        _write_inputs(tmp_path)
        _build(tmp_path)

        for path in (tmp_path / "tenants/demo/evaluation_assets/v1/datasets").glob("*.jsonl"):
            for case in load_cases_with_identity(path).cases:
                criteria = [c for group in case.expected["evaluation_guidelines"] for c in group["criteria"]]
                assert criteria and all(c["criterion_id"] for c in criteria)
                assert case.metadata["trust_tier"] in {"trusted_feedback", "inferred_from_trusted_feedback"}

    def test_regression_split_when_enabled(self, tmp_path: Path) -> None:
        """The regression split holds only trusted cases."""
        _write_inputs(tmp_path)

        manifest = _build(tmp_path, regression_split=True)

        assert manifest["datasets"]["regression"]["trusted"] > 0
        assert manifest["datasets"]["regression"]["inferred"] == 0

    def test_heldout_feedback_never_reaches_catalog(self, tmp_path: Path) -> None:
        """A phrase planted in each held-out split's feedback appears only in that record's own case."""
        records, _ = prepare_records(FEEDBACK, UNLABELED, seed=0, regression_split=True, redact=True)
        heldout = {
            split: next(r.record_id for r in records if r.labeled and r.split == split)
            for split in ("validation", "test", "regression")
        }
        canaries = {record_id: f"CANARY_{split.upper()}_7F3A" for split, record_id in heldout.items()}
        feedback = [
            make_record(row["record_id"], labeled=True, rationale=f"Missed {canaries[row['record_id']]}.")
            if row["record_id"] in canaries
            else row
            for row in FEEDBACK
        ]
        _write_inputs(tmp_path, feedback)

        _build(tmp_path, regression_split=True)

        asset = tmp_path / "tenants/demo/evaluation_assets/v1"
        for record_id, canary in canaries.items():
            for name in ("lessons.jsonl", "catalog.json"):
                assert canary not in (asset / name).read_text()
            carriers = [case["case_id"] for case in _cases(asset) if canary in json.dumps(case["expected"])]
            assert carriers == [f"feedback-{record_id}"]

    def test_trust_tier_views(self, tmp_path: Path) -> None:
        """With unlabeled input, each split also gets trusted-only and inferred-only views."""
        _write_inputs(tmp_path)
        _build(tmp_path)

        datasets = tmp_path / "tenants/demo/evaluation_assets/v1/datasets"
        for split in ("train", "validation", "test"):
            trusted = [
                json.loads(line) for line in (datasets / f"{split}_trusted.jsonl").read_text().splitlines()
            ]
            inferred = [
                json.loads(line) for line in (datasets / f"{split}_inferred.jsonl").read_text().splitlines()
            ]
            assert {case["metadata"]["trust_tier"] for case in trusted} <= {"trusted_feedback"}
            assert {case["metadata"]["trust_tier"] for case in inferred} <= {"inferred_from_trusted_feedback"}
            assert len(trusted) + len(inferred) == len((datasets / f"{split}.jsonl").read_text().splitlines())

    def test_unscoreable_records_are_excluded_and_reported(self, tmp_path: Path) -> None:
        """A record whose rubric has no criteria is left out of the datasets and listed in the review."""
        _write_inputs(tmp_path)
        model = ScriptedModel()
        model.empty_rubrics_for = {"u03"}

        _build(tmp_path, model)

        asset = tmp_path / "tenants/demo/evaluation_assets/v1"
        assert "inferred-u03" not in {case["case_id"] for case in _cases(asset)}
        review = json.loads((asset / "review.json").read_text())
        assert {"record_id": "u03", "reason": "no_checkable_criteria"} in review["records"]["excluded"]

    def test_resume_reuses_completed_calls(self, tmp_path: Path) -> None:
        """After a failed build, a rerun only makes the calls that did not finish."""
        _write_inputs(tmp_path)
        failing = ScriptedModel()
        failing.fail_rubrics_for = {"u05"}
        with pytest.raises(ConnectionError):
            _build(tmp_path, failing)

        resumed = ScriptedModel()
        _build(tmp_path, resumed)

        assert [r["payload"]["episode"]["record_id"] for r in resumed.requests] == ["u05"]
        assert resumed.count(OBSERVE_PROMPT) == resumed.count(SYNTHESIZE_PROMPT) == 0
        assert failing.count(RUBRIC_PROMPT) == 25

    def test_finished_asset_is_never_rewritten(self, tmp_path: Path) -> None:
        """Building an asset that has a manifest fails."""
        _write_inputs(tmp_path)
        _build(tmp_path)

        with pytest.raises(AssetExistsError, match="already built"):
            _build(tmp_path)

    def test_resume_requires_same_settings_and_inputs(self, tmp_path: Path) -> None:
        """A started build cannot resume with different settings or inputs."""
        _write_inputs(tmp_path)
        failing = ScriptedModel()
        failing.fail_rubrics_for = {"u05"}
        with pytest.raises(ConnectionError):
            _build(tmp_path, failing)

        with pytest.raises(ValueError, match="different settings or inputs"):
            _build(tmp_path, split_seed=7)
        write_jsonl(tmp_path / "unlabeled.jsonl", UNLABELED[:3])
        with pytest.raises(ValueError, match="different settings or inputs"):
            _build(tmp_path)

    def test_invalid_input_does_not_freeze_the_asset(self, tmp_path: Path) -> None:
        """A build rejected for invalid input can rerun with the corrected input."""
        broken = [dict(FEEDBACK[0], schema_version="v0"), *FEEDBACK[1:]]
        _write_inputs(tmp_path, broken)
        with pytest.raises(ValueError, match="schema_version"):
            _build(tmp_path)
        _write_inputs(tmp_path, [*FEEDBACK, make_record("u00", labeled=True)])
        with pytest.raises(ValueError, match="appears in both"):
            _build(tmp_path)

        _write_inputs(tmp_path)

        assert _build(tmp_path)["asset_id"] == "v1"

    def test_rejects_empty_feedback(self, tmp_path: Path) -> None:
        """Feedback is required; an empty feedback file fails the build."""
        _write_inputs(tmp_path, [])

        with pytest.raises(ValueError, match="feedback input has no records"):
            _build(tmp_path)

    def test_usage_covers_every_run(self, tmp_path: Path) -> None:
        """After a resume, the review counts model calls from every run."""
        _write_inputs(tmp_path)
        failing = ScriptedModel()
        failing.fail_rubrics_for = {"u05"}
        with pytest.raises(ConnectionError):
            _build(tmp_path, failing)

        _build(tmp_path)

        review = json.loads((tmp_path / "tenants/demo/evaluation_assets/v1/review.json").read_text())
        assert review["calls"]["rubric"]["calls"] == 25
        assert review["calls"]["rubric"]["cached"] == 24

    def test_manifest_lists_files_when_asset_is_named_cache(self, tmp_path: Path) -> None:
        """Only the cache directory, not an asset named cache, is left out of the manifest."""
        _write_inputs(tmp_path)

        manifest = _build(tmp_path, asset_id="cache")

        assert {"build.json", "catalog.json", "review.md"} <= set(manifest["files"])

    def test_workers_can_change_on_resume(self, tmp_path: Path) -> None:
        """Concurrency is not part of an asset's identity."""
        _write_inputs(tmp_path)
        failing = ScriptedModel()
        failing.fail_rubrics_for = {"u05"}
        with pytest.raises(ConnectionError):
            _build(tmp_path, failing, workers=2)

        assert _build(tmp_path, workers=1)["asset_id"] == "v1"

    def test_refuses_previous_pipeline_layout(self, tmp_path: Path) -> None:
        """An asset directory from the previous pipeline is never overwritten."""
        _write_inputs(tmp_path)
        (tmp_path / "tenants/demo/evaluation_assets/v1/stages").mkdir(parents=True)

        with pytest.raises(ValueError, match="previous pipeline"):
            _build(tmp_path)

    def test_concurrent_build_is_refused(self, tmp_path: Path) -> None:
        """A second build of the same asset fails while the first holds the lock."""
        _write_inputs(tmp_path)
        asset = tmp_path / "tenants/demo/evaluation_assets/v1"
        asset.mkdir(parents=True)

        with FileLock(str(asset / ".build.lock")):
            with pytest.raises(RuntimeError, match="another build"):
                _build(tmp_path)


class TestAssetsBuildCli:
    def test_cli_builds_from_config(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """`assets build --config` builds the asset and prints the review path."""
        _write_inputs(tmp_path)
        (tmp_path / "asset.json").write_text(json.dumps(_config().to_dict()), encoding="utf-8")
        model = ScriptedModel()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(build_module, "_openai_factory", lambda name: lambda: model)
        monkeypatch.setattr(
            sys, "argv", ["hephaestus", "assets", "build", "--config", "asset.json", "--workers", "1"]
        )

        cli.main()

        output = capsys.readouterr().out
        assert '"train"' in output
        assert "tenants/demo/evaluation_assets/v1/review.md" in output
        assert model.count(RUBRIC_PROMPT) == 25
