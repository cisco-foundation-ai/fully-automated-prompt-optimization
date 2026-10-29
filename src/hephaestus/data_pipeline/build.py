# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Build one evaluation asset end to end.

Layout under ``tenants/<tenant_id>/evaluation_assets/<asset_id>/``::

    build.json          frozen settings and input hashes
    inputs/             copies of the feedback and unlabeled inputs
    splits.jsonl        split and connected group for every kept record
    lessons.jsonl       lessons from train episodes
    dropped_lessons.jsonl
    catalog.json        guidelines, facts, cannot-fix and set-aside lessons
    rubrics.jsonl       one rubric per kept record
    datasets/<split>.jsonl, <split>_trusted.jsonl, <split>_inferred.jsonl
    review.md           the human review report (review.json is the same data)
    calls.jsonl         one row per model call across all runs, with token usage
    cache/              cached model responses
    manifest.json       written last; its presence marks a finished asset
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

from filelock import FileLock, Timeout

from src.hephaestus.artifact_io import (
    atomic_copy_file,
    atomic_write_json,
    atomic_write_jsonl,
    atomic_write_text,
)
from src.hephaestus.data_pipeline.config import AssetConfig
from src.hephaestus.data_pipeline.llm import JsonCalls, JsonGenerator
from src.hephaestus.data_pipeline.prepare import SPLITS, PreparedRecord, load_input, prepare_records
from src.hephaestus.data_pipeline.publish import build_cases, render_review, review_summary
from src.hephaestus.data_pipeline.steps import observe, synthesize, write_rubrics
from src.hephaestus.datasets.trust_tiers import INFERRED_FROM_TRUSTED_FEEDBACK, TRUSTED_FEEDBACK

MANIFEST_VERSION = "fafo-evaluation-asset-v2"
MAX_OUTPUT_TOKENS = 16384


class AssetExistsError(RuntimeError):
    """The asset is already built; finished assets are never rewritten."""


def build_asset(
    config: AssetConfig,
    *,
    repository_root: Path,
    provider_factory: Optional[Callable[[], JsonGenerator]] = None,
) -> Dict[str, Any]:
    """Build or resume one asset and return its manifest.

    A rerun with the same settings and inputs resumes from the response cache.
    Different settings or inputs need a new ``asset_id``.

    Raises:
        AssetExistsError: If the asset already has a manifest.
        ValueError: If the settings or inputs differ from the started build.
        RuntimeError: If another build of the same asset holds the lock.
    """
    root = config.asset_root(repository_root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(root / ".build.lock"), timeout=0):
            return _build(config, root, repository_root, provider_factory or _openai_factory(config.model))
    except Timeout as exc:
        raise RuntimeError(f"another build of {root} is running") from exc


def _build(
    config: AssetConfig,
    root: Path,
    repository_root: Path,
    provider_factory: Callable[[], JsonGenerator],
) -> Dict[str, Any]:
    if (root / "manifest.json").exists():
        raise AssetExistsError(f"{root} is already built; use a new asset_id")
    if (root / "stages").exists() or (root / "state.json").exists():
        raise ValueError(f"{root} holds an asset from the previous pipeline; use a new asset_id")
    sources = {"feedback": config.feedback, "unlabeled": config.unlabeled}
    paths = {name: _resolve(path, repository_root) for name, path in sources.items() if path}
    feedback = load_input(paths["feedback"], labeled=True)
    if not feedback:
        raise ValueError(f"feedback input has no records: {config.feedback}")
    unlabeled = load_input(paths["unlabeled"], labeled=False) if "unlabeled" in paths else []
    records, excluded = prepare_records(
        feedback,
        unlabeled,
        seed=config.split_seed,
        regression_split=config.regression_split,
        redact=config.redact,
    )
    _check_splits(records)
    input_hashes = _freeze(config, root, paths)
    atomic_write_jsonl(
        root / "splits.jsonl",
        (
            {"record_id": r.record_id, "split": r.split, "labeled": r.labeled, "group": r.group}
            for r in records
        ),
    )

    calls = JsonCalls(
        provider_factory,
        model=config.model,
        cache_dir=root / "cache",
        calls_path=root / "calls.jsonl",
    )
    lessons, dropped = observe(calls, records, config)
    _check_lessons(records, lessons)
    atomic_write_jsonl(root / "lessons.jsonl", lessons)
    atomic_write_jsonl(root / "dropped_lessons.jsonl", dropped)
    catalog = synthesize(calls, lessons, config)
    atomic_write_json(root / "catalog.json", catalog)
    rubrics = write_rubrics(calls, records, catalog, config)
    atomic_write_jsonl(root / "rubrics.jsonl", rubrics)

    cases, unscoreable = build_cases(records, rubrics, config.asset_id)
    splits = [split for split in SPLITS if split != "regression" or config.regression_split]
    for split in splits:
        in_split = [case for case in cases if case["metadata"]["split"] == split]
        atomic_write_jsonl(root / "datasets" / f"{split}.jsonl", in_split)
        if unlabeled and split != "regression":
            for tier, name in ((TRUSTED_FEEDBACK, "trusted"), (INFERRED_FROM_TRUSTED_FEEDBACK, "inferred")):
                view = [case for case in in_split if case["metadata"]["trust_tier"] == tier]
                atomic_write_jsonl(root / "datasets" / f"{split}_{name}.jsonl", view)
    summary = review_summary(
        config=config,
        records=records,
        excluded=[*excluded, *unscoreable],
        lessons=lessons,
        dropped=dropped,
        catalog=catalog,
        cases=cases,
        call_stats=_usage(root / "calls.jsonl", calls.stats),
    )
    atomic_write_json(root / "review.json", summary)
    atomic_write_text(root / "review.md", render_review(summary, catalog, lessons, dropped))

    manifest = {
        "version": MANIFEST_VERSION,
        "tenant_id": config.tenant_id,
        "asset_id": config.asset_id,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": config.content_settings(),
        "inputs": input_hashes,
        "datasets": {
            split: {"path": f"datasets/{split}.jsonl", **summary["datasets"][split]} for split in splits
        },
        "files": {
            path.relative_to(root).as_posix(): _sha256(path)
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.relative_to(root).parts[0] != "cache" and not path.name.startswith(".")
        },
    }
    atomic_write_json(root / "manifest.json", manifest)
    return manifest


def _freeze(config: AssetConfig, root: Path, paths: Dict[str, Path]) -> Dict[str, str]:
    """Copy validated inputs on the first run; on a rerun, require identical settings and inputs."""
    hashes = {name: _sha256(path) for name, path in paths.items()}
    frozen = {"settings": config.content_settings(), "inputs": hashes}
    stored = root / "build.json"
    if stored.is_file():
        if json.loads(stored.read_text(encoding="utf-8")) != frozen:
            raise ValueError(f"{root} was started with different settings or inputs; use a new asset_id")
        return hashes
    for name, path in paths.items():
        atomic_copy_file(path, root / "inputs" / f"{name}.jsonl")
    atomic_write_json(stored, frozen)
    return hashes


def _check_splits(records: Sequence[PreparedRecord]) -> None:
    """Fail the build if an input ``group_id`` spans two splits."""
    split_by_group: Dict[str, str] = {}
    for record in records:
        group_id = str(record.row["group_id"])
        if split_by_group.setdefault(group_id, record.split) != record.split:
            raise RuntimeError(f"group_id {group_id} spans two splits")


def _check_lessons(records: Sequence[PreparedRecord], lessons: Sequence[Dict[str, Any]]) -> None:
    """Fail the build before synthesis if a lesson came from a held-out episode."""
    split_by_record = {record.record_id: record.split for record in records}
    if any(split_by_record[lesson["record_id"]] != "train" for lesson in lessons):
        raise RuntimeError("a lesson came from a held-out episode")


def _usage(calls_path: Path, run_stats: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    """Total model calls and tokens across every run; ``cached`` counts this run only."""
    usage: Dict[str, Dict[str, int]] = {}
    lines = calls_path.read_text(encoding="utf-8").splitlines() if calls_path.is_file() else []
    for row in (json.loads(line) for line in lines if line.strip()):
        totals = usage.setdefault(
            row["step"], {"calls": 0, "cached": 0, "input_tokens": 0, "output_tokens": 0}
        )
        totals["calls"] += 1
        totals["input_tokens"] += row["input_tokens"]
        totals["output_tokens"] += row["output_tokens"]
    for step, stats in run_stats.items():
        usage.setdefault(step, {"calls": 0, "cached": 0, "input_tokens": 0, "output_tokens": 0})
        usage[step]["cached"] = stats["cached"]
    return usage


def _openai_factory(model: str) -> Callable[[], JsonGenerator]:
    def factory() -> JsonGenerator:
        from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider

        return OpenAIRubricProvider(model=model, max_output_tokens=MAX_OUTPUT_TOKENS)

    return factory


def _resolve(path: str, repository_root: Path) -> Path:
    candidate = Path(path)
    resolved = candidate if candidate.is_absolute() else repository_root / candidate
    if not resolved.is_file():
        raise FileNotFoundError(f"input not found: {path}")
    return resolved


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
