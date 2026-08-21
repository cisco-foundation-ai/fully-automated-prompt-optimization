# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Read-only filesystem layer for the web UI.

Walks ``tenants/<tenant_id>/`` and surfaces the artifacts a user wants to
navigate: eval runs (``evals/<run>/``), iteration history
(``docs/iteration-memory.jsonl``), prompt and skill variants
(``prompts/**/*.md`` and ``skills/**/*.md``), and per-case eval outputs
(``results.jsonl``).

Nothing here mutates tenant data. Paths are resolved relative to the tenants
root and validated to stay inside it, so the HTTP layer cannot read arbitrary
files on disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.hephaestus.evaluation_assets.models import STAGE_LABELS, PipelineStage
from src.hephaestus.evaluation_assets.publication import (
    resolve_evaluation_asset_release,
    validate_historical_generation,
)
from src.hephaestus.evaluation_assets.workspace import (
    EvaluationAssetLayout,
    list_asset_layouts,
)


def _path_is_within(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


@dataclass(frozen=True)
class _FileSnapshot:
    path: Path
    display_path: str
    device: int
    inode: int
    size: int
    expected_sha256: str | None = None


@dataclass(frozen=True)
class _DeferredDatasetSnapshot:
    tenant_dir: Path
    dataset_rel: str


@dataclass(frozen=True)
class _DatasetListingSnapshot:
    tenant_dir: Path
    ordinary: tuple[_FileSnapshot, ...]
    studio_catalogs: tuple[Path, ...]


@dataclass(frozen=True)
class _CaseSnapshot:
    results: _FileSnapshot
    dataset: _FileSnapshot | _DeferredDatasetSnapshot | None
    dataset_rel: str | None
    index: int


def _capture_file_snapshot(
    path: Path,
    display_path: str,
    *,
    expected_sha256: str | None = None,
) -> _FileSnapshot:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or resolved != path.absolute():
        raise ValueError("dataset snapshot path cannot be a symlink")
    details = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(details.st_mode):
        raise ValueError("dataset snapshot path is not a regular file")
    return _FileSnapshot(
        path=path.absolute(),
        display_path=display_path,
        device=details.st_dev,
        inode=details.st_ino,
        size=details.st_size,
        expected_sha256=expected_sha256,
    )


def _read_jsonl_snapshot(snapshot: _FileSnapshot) -> list[dict[str, Any]] | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(snapshot.path, flags)
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_dev != snapshot.device
            or details.st_ino != snapshot.inode
            or details.st_size != snapshot.size
        ):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        if snapshot.expected_sha256 is not None and hashlib.sha256(
            raw
        ).hexdigest() != snapshot.expected_sha256:
            return None
        rows = []
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                return None
            rows.append(row)
        return rows
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)

# Directory names probed inside each tenant when listing eval runs. The repo
# convention is ``evals/``, but eval configs can point output_dir anywhere, so
# we probe a few common spellings.
_RUN_PARENT_DIRS = ("evals", "runs", "eval_outputs", "outputs")

# A directory is treated as an eval run if it contains at least one of these.
_RUN_MARKERS = ("results.jsonl", "run_config.json", "summary.md", "progress.json")

# Tenants historically use ``configs/``; support ``config/`` as an alias for
# local projects that use the singular spelling.
_CONFIG_DIRS = ("config", "configs")

# Editable text assets surfaced under the Prompts tab. Each entry maps a tenant
# subdirectory to the ``kind`` tag reported for files found beneath it. Prompts
# and skills are both optimizable markdown, so they live together here. Adding a
# new asset subtree is just a new entry — discovery is otherwise path-agnostic.
_PROMPT_ASSET_DIRS = (("prompts", "prompt"), ("skills", "skill"))

_EVALUATION_STAGE_PATTERNS = {
    "raw_inputs": (
        "stages/01_raw_inputs/*.jsonl",
        "raw_inputs/*.jsonl",
    ),
    "prepared_inputs": (
        "stages/02_prepared_inputs/normalized_feedback.jsonl",
        "stages/02_prepared_inputs/intent_records.jsonl",
        "prepared_inputs/normalized_feedback.jsonl",
        "prepared_inputs/intent_records.jsonl",
    ),
    "rubric_extraction": (
        "stages/03_evaluation_guidelines/feedback_evidence.jsonl",
        "stages/03_evaluation_guidelines/candidate_guidelines.jsonl",
        "stages/03_evaluation_guidelines/evaluation_guidelines.jsonl",
        "stages/03_evaluation_guidelines/trusted_intents.jsonl",
        "stages/03_evaluation_guidelines/trusted_cases.jsonl",
        "stages/03_rubric_extraction/feedback_evidence.jsonl",
        "stages/03_rubric_extraction/candidate_guidelines.jsonl",
        "stages/03_rubric_extraction/evaluation_guidelines.jsonl",
        "stages/03_rubric_extraction/feedback_rubrics.jsonl",
        "stages/03_rubric_extraction/trusted_intents.jsonl",
        "stages/03_rubric_extraction/trusted_cases.jsonl",
        "decision_assets/feedback_rubrics.jsonl",
        "prepared_inputs/trusted_intents.jsonl",
        "prepared_inputs/trusted_cases.jsonl",
    ),
    "intent_clustering": (
        "stages/04_intent_clustering/intent_inventory.jsonl",
        "stages/04_intent_clustering/cluster_lineage.jsonl",
        "decision_assets/intent_inventory.jsonl",
    ),
    "coverage_decisions": (
        "stages/05_coverage_decisions/intent_matches.jsonl",
        "stages/05_coverage_decisions/coverage_report.md",
        "stages/05_coverage_decisions/review_queue/labeling_queue.jsonl",
        "decision_assets/intent_matches.jsonl",
        "decision_assets/coverage_report.md",
        "review_queues/labeling_queue.jsonl",
    ),
    "label_inference": (
        "stages/06_label_inference/inferred_unlabeled_cluster_rubrics.jsonl",
        "stages/06_label_inference/inferred_unlabeled_labels.jsonl",
        "stages/06_label_inference/missing_labeled_feedback_clusters.jsonl",
        "stages/06_label_inference/missing_labeled_feedback_report.md",
        "stages/06_label_inference/inferred_cases.jsonl",
        "decision_assets/inferred_unlabeled_cluster_rubrics.jsonl",
        "decision_assets/inferred_unlabeled_labels.jsonl",
        "decision_assets/missing_labeled_feedback_clusters.jsonl",
        "decision_assets/missing_labeled_feedback_report.md",
        "prepared_inputs/inferred_cases.jsonl",
    ),
    "synthetic_coverage": (
        "stages/07_synthetic_coverage/synthetic_candidates.jsonl",
        "stages/07_synthetic_coverage/rejected_synthetic.jsonl",
        "stages/07_synthetic_coverage/synthetic_filter_issues.jsonl",
        "stages/07_synthetic_coverage/synthetic_cases.jsonl",
        "decision_assets/synthetic_candidates.jsonl",
        "decision_assets/rejected_synthetic.jsonl",
        "decision_assets/synthetic_filter_issues.jsonl",
        "prepared_inputs/synthetic_cases.jsonl",
    ),
    "dataset_splits": (
        "stages/08_dataset_splits/*",
        "dataset_splits/*",
    ),
}

_ARTIFACT_GROUP_ORDER = {
    "Key outputs": 0,
    "Needs attention": 1,
    "Supporting data": 2,
    "Diagnostics": 3,
}

_ARTIFACT_CATALOG = {
    "labeled_feedback.jsonl": (
        "Labeled source records",
        "Immutable canonical feedback input copied into this asset.",
        "Key outputs",
    ),
    "unlabeled.jsonl": (
        "Unlabeled source records",
        "Immutable canonical traffic input copied into this asset.",
        "Key outputs",
    ),
    "normalized_feedback.jsonl": (
        "Prepared feedback",
        "Redacted feedback records used for evaluation guideline creation.",
        "Key outputs",
    ),
    "intent_records.jsonl": (
        "Prepared intent records",
        "Redacted unlabeled records with canonical intent text.",
        "Key outputs",
    ),
    "feedback_evidence.jsonl": (
        "Trusted feedback evidence",
        "Atomic claims and uncertainties extracted directly from user feedback.",
        "Supporting data",
    ),
    "candidate_guidelines.jsonl": (
        "Candidate guidelines",
        "Uncompiled proposals synthesized across compatible evidence.",
        "Diagnostics",
    ),
    "evaluation_guidelines.jsonl": (
        "Evaluation guidelines",
        "Reusable criteria with provenance, applicability, and evaluator plans.",
        "Key outputs",
    ),
    "feedback_rubrics.jsonl": (
        "Legacy feedback rubrics",
        "Compatibility artifact from assets created before guideline creation.",
        "Supporting data",
    ),
    "trusted_intents.jsonl": (
        "Trusted intent catalog",
        "Intent labels and support derived from evaluation guidelines.",
        "Supporting data",
    ),
    "trusted_cases.jsonl": (
        "Trusted evaluation cases",
        "Evaluation cases built directly from trusted feedback.",
        "Key outputs",
    ),
    "intent_inventory.jsonl": (
        "Intent cluster inventory",
        "Cluster membership, representative records, and top terms.",
        "Key outputs",
    ),
    "cluster_lineage.jsonl": (
        "Cluster lineage",
        "Previous-to-current cluster continuity after an intent refresh.",
        "Diagnostics",
    ),
    "intent_matches.jsonl": (
        "Cluster coverage decisions",
        "Machine-readable trusted-intent match result for every cluster.",
        "Supporting data",
    ),
    "coverage_report.md": (
        "Coverage report",
        "Readable summary of supported clusters and labeling gaps.",
        "Key outputs",
    ),
    "labeling_queue.jsonl": (
        "Traces to label",
        "Representative traces sampled from clusters lacking enough trusted evidence.",
        "Needs attention",
    ),
    "inferred_unlabeled_cluster_rubrics.jsonl": (
        "Inferred cluster rubrics",
        "Review-required rubrics inferred for supported clusters.",
        "Supporting data",
    ),
    "inferred_unlabeled_labels.jsonl": (
        "Inferred trace labels",
        "Review-required labels attached to real supported traces.",
        "Key outputs",
    ),
    "missing_labeled_feedback_clusters.jsonl": (
        "Unsupported cluster details",
        "Structured description of clusters that remain outside trusted coverage.",
        "Needs attention",
    ),
    "missing_labeled_feedback_report.md": (
        "Unsupported cluster report",
        "Readable explanation of remaining feedback needs.",
        "Needs attention",
    ),
    "inferred_cases.jsonl": (
        "Inferred evaluation cases",
        "Evaluation cases created from supported real traces.",
        "Key outputs",
    ),
    "synthetic_candidates.jsonl": (
        "Generated candidates",
        "Unfiltered synthetic candidates produced for supported clusters.",
        "Supporting data",
    ),
    "synthetic_cases.jsonl": (
        "Accepted synthetic cases",
        "Synthetic evaluation cases that passed all filters.",
        "Key outputs",
    ),
    "rejected_synthetic.jsonl": (
        "Rejected synthetic candidates",
        "Candidates excluded by validation or quality filters.",
        "Diagnostics",
    ),
    "synthetic_filter_issues.jsonl": (
        "Synthetic filter audit",
        "Reasons synthetic candidates were rejected.",
        "Diagnostics",
    ),
    "dataset_manifest.json": (
        "Dataset manifest",
        "Counts, provenance, split policy, and review policy for the final dataset.",
        "Key outputs",
    ),
    "train.jsonl": (
        "Training dataset",
        "Combined group-safe training split.",
        "Key outputs",
    ),
    "validation.jsonl": (
        "Validation dataset",
        "Combined group-safe validation split.",
        "Key outputs",
    ),
    "test.jsonl": (
        "Test dataset",
        "Combined group-safe test split.",
        "Key outputs",
    ),
    "regression_trusted.jsonl": (
        "Trusted regression gate",
        "Automatic trusted-only regression holdout.",
        "Key outputs",
    ),
    "triage_hold.jsonl": (
        "Triage hold",
        "Cases held out because their groups conflict with regression isolation.",
        "Needs attention",
    ),
}


def _artifact_metadata(relative_path: str) -> Dict[str, Any]:
    """Return stable user-facing semantics without changing artifact filenames."""
    name = Path(relative_path).name
    catalog_item = _ARTIFACT_CATALOG.get(name)
    if catalog_item is not None:
        display_name, description, group = catalog_item
    elif (
        name.endswith("_trusted.jsonl")
        or name.endswith("_inferred.jsonl")
        or name.endswith("_synthetic.jsonl")
    ):
        display_name = name.removesuffix(".jsonl").replace("_", " ").title()
        description = "Provenance-specific view of a combined dataset split."
        group = "Supporting data"
    elif name.endswith("manifest.json") or name.endswith("manifest.jsonl"):
        display_name = name.rsplit(".", 1)[0].replace("_", " ").title()
        description = "Machine-readable provenance and count metadata."
        group = "Diagnostics"
    else:
        display_name = name.rsplit(".", 1)[0].replace("_", " ").title()
        description = "Supporting artifact produced by this pipeline stage."
        group = "Supporting data"
    return {
        "display_name": display_name,
        "description": description,
        "group": group,
        "group_order": _ARTIFACT_GROUP_ORDER[group],
    }


def _read_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    text = _read_text(path)
    if text is None:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _evaluation_asset_preview(
    path: Path,
    tenant_dir: Path,
    preview_limit: int,
) -> Dict[str, Any]:
    """Build a bounded preview for a known file inside an evaluation asset."""
    relative_path = path.relative_to(tenant_dir).as_posix()
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    metadata = _artifact_metadata(relative_path)
    if path.suffix.lower() == ".jsonl":
        rows: List[Any] = []
        row_count = 0
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    text = line.strip()
                    if not text:
                        continue
                    row_count += 1
                    if len(rows) >= preview_limit:
                        continue
                    try:
                        rows.append(json.loads(text))
                    except json.JSONDecodeError:
                        rows.append(text)
        except (OSError, UnicodeDecodeError):
            pass
        return {
            "name": path.name,
            "path": relative_path,
            "kind": "jsonl",
            "bytes": size,
            "row_count": row_count,
            "preview": rows,
            **metadata,
        }
    if path.suffix.lower() == ".json":
        content = _read_json(path)
        return {
            "name": path.name,
            "path": relative_path,
            "kind": "json",
            "bytes": size,
            "row_count": 1 if content is not None else 0,
            "preview": [content] if content is not None else [],
            **metadata,
        }
    text = _read_text(path) or ""
    rendered_limit = 100_000
    return {
        "name": path.name,
        "path": relative_path,
        "kind": "markdown",
        "bytes": size,
        "row_count": None,
        "preview": text[:4000],
        "content": text[:rendered_limit],
        "content_truncated": len(text) > rendered_limit,
        **metadata,
    }


def _evaluation_cluster_summaries(
    layout: EvaluationAssetLayout,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Return compact real cluster data separately from one-row file previews."""
    inventory_path = layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    )
    clusters = _read_jsonl(inventory_path)[:limit]
    representative_ids = {
        str(record_id)
        for cluster in clusters
        for record_id in cluster.get("representative_ids", [])
    }
    records_by_id = {
        str(row.get("record_id")): row
        for row in _read_jsonl(
            layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "intent_records.jsonl",
            )
        )
        if str(row.get("record_id")) in representative_ids
    }
    summaries = []
    for cluster in clusters:
        representatives = [
            records_by_id.get(str(record_id), {})
            for record_id in cluster.get("representative_ids", [])
        ]
        summaries.append(
            {
                "cluster_id": cluster.get("cluster_id"),
                "route": cluster.get("route"),
                "size": cluster.get("size", len(cluster.get("record_ids", []))),
                "top_terms": cluster.get("top_terms", []),
                "representatives": [
                    row.get("user_input") or row.get("canonical_intent_text")
                    for row in representatives
                    if row
                ],
                "tools": sorted(
                    {
                        str(tool)
                        for row in representatives
                        for tool in row.get("tool_names", [])
                    }
                ),
            }
        )
    return summaries


class TenantStore:
    """Resolves and reads tenant artifacts under a single tenants root."""

    def __init__(
        self,
        tenants_root: Path,
        *,
        repository_base: Path | None = None,
    ) -> None:
        effective_base = repository_base if repository_base is not None else Path.cwd()
        probe = EvaluationAssetLayout(
            tenants_root,
            "store",
            "layout",
            repository_base=effective_base,
        )
        self.root = probe.tenants_root
        self.repository_base = probe.repository_base

    # -- path safety -----------------------------------------------------

    def _tenant_dir(self, tenant_id: str) -> Optional[Path]:
        """Return the tenant directory, or None if it isn't a real tenant."""
        candidate = (self.root / tenant_id).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            return None  # path traversal attempt
        if not candidate.is_dir():
            return None
        if (
            not (candidate / "__init__.py").exists()
            and not (candidate / "storage").exists()
            and not (candidate / "evaluation_assets").exists()
        ):
            # Skip stray dirs like __pycache__.
            return None
        return candidate

    # -- listings --------------------------------------------------------

    def list_tenants(self) -> List[Dict[str, Any]]:
        tenants: List[Dict[str, Any]] = []
        if not self.root.is_dir():
            return tenants
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            tenant_dir = self._tenant_dir(child.name)
            if tenant_dir is None:
                continue
            runs = self._run_dirs(tenant_dir)
            iterations = self._iteration_rows(tenant_dir)
            evaluation_assets = self.list_evaluation_assets(child.name)
            tenants.append(
                {
                    "tenant_id": child.name,
                    "run_count": len(runs),
                    "iteration_count": len(iterations),
                    "prompt_count": len(self._prompt_paths(tenant_dir)),
                    "dataset_count": len(self._ordinary_dataset_paths(tenant_dir)),
                    "config_count": len(self._config_paths(tenant_dir)),
                    "doc_count": len(self._doc_paths(tenant_dir)),
                    "has_readme": (tenant_dir / "README.md").exists(),
                    "evaluation_asset_count": len(evaluation_assets),
                    "evaluation_asset": evaluation_assets[0] if evaluation_assets else None,
                }
            )
        return tenants

    def overview(self, tenant_ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Aggregate cross-tenant stats for the landing dashboard.

        Returns global totals plus a per-tenant card with its most recent run
        (status, score, model, timestamp) so the UI can render a dashboard in a
        single request rather than fanning out per tenant.

        ``all_tenants`` always lists every tenant id (for the filter UI). The
        aggregated panels cover only *tenant_ids* when provided, otherwise all.
        """
        all_tenants = self.list_tenants()
        selected = set(tenant_ids) if tenant_ids is not None else None

        tenant_cards: List[Dict[str, Any]] = []
        total_runs = 0
        total_variants = 0
        total_prompts = 0
        scored_runs: List[float] = []
        recent_runs: List[Dict[str, Any]] = []

        for tenant in all_tenants:
            tenant_id = tenant["tenant_id"]
            if selected is not None and tenant_id not in selected:
                continue
            runs = self.list_runs(tenant_id)
            total_runs += len(runs)
            variant_count = self._variants_tried(tenant_id)
            total_variants += variant_count
            total_prompts += tenant["prompt_count"]
            latest = runs[0] if runs else None  # list_runs is sorted newest-first
            if latest and latest.get("avg_composite_score") is not None:
                scored_runs.append(float(latest["avg_composite_score"]))
            for run in runs:
                recent_runs.append({**run, "tenant_id": tenant_id})
            tenant_cards.append(
                {
                    "tenant_id": tenant_id,
                    "run_count": tenant["run_count"],
                    "iteration_count": tenant["iteration_count"],
                    "variant_count": variant_count,
                    "prompt_count": tenant["prompt_count"],
                    "config_count": tenant["config_count"],
                    "dataset_count": tenant["dataset_count"],
                    "doc_count": tenant["doc_count"],
                    "latest_run": latest,
                    "evaluation_asset_count": tenant["evaluation_asset_count"],
                    "evaluation_asset": tenant["evaluation_asset"],
                }
            )

        recent_runs.sort(key=lambda r: (r.get("updated_at") or "", r["name"]), reverse=True)

        return {
            "totals": {
                "tenants": len(tenant_cards),
                "runs": total_runs,
                "variants": total_variants,
                "prompt_templates": total_prompts,
                "avg_latest_score": (
                    sum(scored_runs) / len(scored_runs) if scored_runs else None
                ),
            },
            "all_tenants": [t["tenant_id"] for t in all_tenants],
            "tenants": tenant_cards,
            "recent_runs": recent_runs[:8],
        }

    def list_evaluation_assets(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List self-contained evaluation assets without reading tenant code/docs."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        assets: List[Dict[str, Any]] = []
        for layout in list_asset_layouts(
            self.root,
            tenant_id,
            repository_base=self.repository_base,
        ):
            try:
                config = layout.load_config().to_dict()
                state = layout.load_state().to_dict()
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
            assets.append(
                {
                    **layout.artifact_summary(),
                    "config": config,
                    "state": state,
                }
            )
        return assets

    def get_evaluation_asset_stage(
        self,
        tenant_id: str,
        asset_id: str,
        stage: str,
    ) -> Optional[Dict[str, Any]]:
        """Return one pipeline stage with safe, bounded artifact previews."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None or stage not in _EVALUATION_STAGE_PATTERNS:
            return None
        try:
            layout = EvaluationAssetLayout(
                self.root,
                tenant_id,
                asset_id,
                repository_base=self.repository_base,
            )
            config = layout.load_config()
            state = layout.load_state()
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None

        stage_state = next(
            (item for item in state.stages if item.stage == stage),
            None,
        )
        artifacts = []
        seen: set[Path] = set()
        for pattern in _EVALUATION_STAGE_PATTERNS[stage]:
            for path in sorted(layout.root.glob(pattern)):
                resolved = path.resolve()
                if (
                    resolved in seen
                    or layout.root.resolve() not in resolved.parents
                    or not resolved.is_file()
                ):
                    continue
                if resolved.suffix.lower() not in {".json", ".jsonl", ".md"}:
                    continue
                seen.add(resolved)
                artifacts.append(
                    _evaluation_asset_preview(
                        resolved,
                        tenant_dir,
                        preview_limit=1,
                    )
                )
        artifacts.sort(
            key=lambda item: (
                int(item["group_order"]),
                str(item["display_name"]),
                str(item["name"]),
            )
        )

        response = {
            "stage": stage,
            "label": STAGE_LABELS[PipelineStage(stage)],
            "status": stage_state.status if stage_state else "pending",
            "message": stage_state.message if stage_state else "",
            "started_at": stage_state.started_at if stage_state else None,
            "completed_at": stage_state.completed_at if stage_state else None,
            "config": config.to_dict(),
            "counts": state.counts,
            "artifacts": artifacts,
        }
        if stage == "intent_clustering":
            response["clusters"] = _evaluation_cluster_summaries(layout)
        return response

    def _variants_tried(self, tenant_id: str) -> int:
        """Sum of ``variants_tried`` across a tenant's iteration records."""
        total = 0
        for row in self.list_iterations(tenant_id):
            value = row.get("variants_tried")
            if isinstance(value, (int, float)):
                total += int(value)
        return total

    def _run_dirs(self, tenant_dir: Path) -> List[Path]:
        found: set[Path] = set()
        for parent_name in _RUN_PARENT_DIRS:
            parent = tenant_dir / parent_name
            if not parent.is_dir():
                continue
            for marker in _RUN_MARKERS:
                for marker_path in parent.rglob(marker):
                    if marker_path.is_file():
                        found.add(marker_path.parent)
        return sorted(found)

    def list_runs(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        runs: List[Dict[str, Any]] = []
        for run_dir in self._run_dirs(tenant_dir):
            progress = _read_json(run_dir / "progress.json") or {}
            run_config = _read_json(run_dir / "run_config.json") or {}
            results_path = run_dir / "results.jsonl"
            rel = run_dir.relative_to(tenant_dir).as_posix()
            runs.append(
                {
                    "run_dir": rel,
                    "name": run_dir.name,
                    "run_id": progress.get("run_id") or run_config.get("run_id") or run_dir.name,
                    "status": progress.get("status"),
                    "total_cases": progress.get("total_cases"),
                    "completed_cases": progress.get("completed_cases"),
                    "avg_composite_score": progress.get("avg_composite_score"),
                    "weighted_avg_score": progress.get("weighted_avg_score"),
                    "started_at": progress.get("started_at"),
                    "updated_at": progress.get("updated_at"),
                    "failed_case_ids": progress.get("failed_case_ids", []),
                    "model": (run_config.get("provider_settings") or {}).get("model"),
                    "provider": run_config.get("provider"),
                    "has_results": results_path.exists(),
                }
            )
        # Most-recently-updated first, falling back to name.
        runs.sort(key=lambda r: (r.get("updated_at") or "", r["name"]), reverse=True)
        return runs

    def get_run(self, tenant_id: str, run_dir_rel: str) -> Optional[Dict[str, Any]]:
        run_dir = self._resolve_run_dir(tenant_id, run_dir_rel)
        if run_dir is None:
            return None
        tenant_dir = self._tenant_dir(tenant_id)
        assert tenant_dir is not None
        results = _read_jsonl(run_dir / "results.jsonl")
        cases = [self._case_summary(i, row) for i, row in enumerate(results)]
        return {
            "tenant_id": tenant_id,
            "run_dir": run_dir.relative_to(tenant_dir).as_posix(),
            "run_config": _read_json(run_dir / "run_config.json"),
            "progress": _read_json(run_dir / "progress.json"),
            "summary_md": _read_text(run_dir / "summary.md"),
            "cases": cases,
        }

    def get_case(self, tenant_id: str, run_dir_rel: str, index: int) -> Optional[Dict[str, Any]]:
        snapshot, _ = self.prepare_case(tenant_id, run_dir_rel, index)
        return self.materialize_case(snapshot)

    def get_case_with_policy(
        self,
        tenant_id: str,
        run_dir_rel: str,
        index: int,
    ) -> tuple[Optional[Dict[str, Any]], bool]:
        """Compatibility wrapper around the two-phase protected case read."""
        snapshot, studio_data = self.prepare_case(
            tenant_id,
            run_dir_rel,
            index,
        )
        return self.materialize_case(snapshot), studio_data

    def prepare_case(
        self,
        tenant_id: str,
        run_dir_rel: str,
        index: int,
    ) -> tuple[_CaseSnapshot | None, bool]:
        """Resolve case and dataset files without reading protected row bytes."""
        run_dir = self._resolve_run_dir(tenant_id, run_dir_rel)
        if run_dir is None:
            return None, False
        if index < 0:
            return None, False
        dataset_rel = self._run_dataset_rel(tenant_id, run_dir)
        dataset_snapshot: _FileSnapshot | _DeferredDatasetSnapshot | None = None
        studio_data = False
        if dataset_rel is not None:
            dataset_snapshot, studio_data = self.prepare_dataset(
                tenant_id,
                dataset_rel,
            )
        try:
            results_snapshot = _capture_file_snapshot(
                run_dir / "results.jsonl",
                (run_dir / "results.jsonl").as_posix(),
            )
        except (OSError, ValueError):
            return None, studio_data
        return _CaseSnapshot(
            results=results_snapshot,
            dataset=dataset_snapshot,
            dataset_rel=dataset_rel,
            index=index,
        ), studio_data

    def materialize_case(
        self,
        snapshot: _CaseSnapshot | None,
    ) -> Optional[Dict[str, Any]]:
        """Read a previously classified case snapshot after authorization."""
        if snapshot is None:
            return None
        results = _read_jsonl_snapshot(snapshot.results)
        if results is None or snapshot.index >= len(results):
            return None
        case = results[snapshot.index]
        ground_truth = self._ground_truth_from_snapshot(
            snapshot.dataset,
            snapshot.dataset_rel,
            case.get("case_id"),
        )
        return {
            "index": snapshot.index,
            "case": case,
            "ground_truth": ground_truth,
        }

    def _ground_truth_from_snapshot(
        self,
        snapshot: _FileSnapshot | _DeferredDatasetSnapshot | None,
        dataset_rel: str | None,
        case_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if snapshot is None or dataset_rel is None or case_id is None:
            return None
        rows = self._dataset_snapshot_rows(snapshot)
        if rows is None:
            return None
        for row in rows:
            if str(row.get("case_id")) == str(case_id):
                return {
                    "dataset": dataset_rel,
                    "expected": row.get("expected"),
                    "context": row.get("context"),
                    "metadata": row.get("metadata"),
                }
        return {
            "dataset": dataset_rel,
            "expected": None,
            "context": None,
            "metadata": None,
        }

    def run_uses_evaluation_asset_dataset(
        self,
        tenant_id: str,
        run_dir_rel: str,
    ) -> bool:
        """Return whether case detail would join a published Studio dataset."""
        run_dir = self._resolve_run_dir(tenant_id, run_dir_rel)
        if run_dir is None:
            return False
        dataset_rel = self._run_dataset_rel(tenant_id, run_dir)
        return bool(
            dataset_rel
            and self.is_evaluation_asset_dataset(tenant_id, dataset_rel)
        )

    def _ground_truth_for(
        self,
        tenant_id: str,
        run_dir: Path,
        case_id: Optional[str],
        *,
        dataset_rel: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Look up the dataset row's ``expected`` block for a result case.

        Joins on ``case_id`` against the dataset referenced by the run's
        ``run_config.json`` (falling back to the tenant's only dataset). Returns
        None if the dataset isn't available locally or the case isn't found.
        """
        if case_id is None:
            return None
        if dataset_rel is None:
            dataset_rel = self._run_dataset_rel(tenant_id, run_dir)
        if dataset_rel is None:
            return None
        rows = self._dataset_rows(tenant_id, dataset_rel)
        for row in rows:
            if str(row.get("case_id")) == str(case_id):
                return {
                    "dataset": dataset_rel,
                    "expected": row.get("expected"),
                    "context": row.get("context"),
                    "metadata": row.get("metadata"),
                }
        return {"dataset": dataset_rel, "expected": None, "context": None, "metadata": None}

    def _run_dataset_rel(self, tenant_id: str, run_dir: Path) -> Optional[str]:
        """Resolve the tenant-relative dataset path used by a run."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        run_config = _read_json(run_dir / "run_config.json") or {}
        dataset_path = run_config.get("dataset_path")
        if dataset_path:
            # Stored repo-relative (e.g. tenants/<id>/datasets/x.jsonl); reduce
            # to tenant-relative so it composes with _tenant_dir.
            candidate = Path(dataset_path)
            try:
                resolved = (self.root.parent / candidate).resolve()
            except (OSError, ValueError):
                resolved = None
            if resolved and tenant_dir in resolved.parents and resolved.is_file():
                return resolved.relative_to(tenant_dir).as_posix()
        # Fall back to the tenant's datasets when config is absent or stale.
        datasets = self._ordinary_dataset_paths(tenant_dir)
        if len(datasets) == 1 and not self._studio_catalogs(tenant_dir):
            return datasets[0].relative_to(tenant_dir).as_posix()
        return None

    def _resolve_run_dir(self, tenant_id: str, run_dir_rel: str) -> Optional[Path]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        run_dir = (tenant_dir / run_dir_rel).resolve()
        if tenant_dir not in run_dir.parents:
            return None  # traversal guard
        if not run_dir.is_dir():
            return None
        return run_dir

    @staticmethod
    def _case_summary(index: int, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "index": index,
            "case_id": row.get("case_id"),
            "task_type": row.get("task_type"),
            "composite_score": row.get("composite_score"),
            "total_tool_calls": row.get("total_tool_calls"),
            "failed_tool_calls": row.get("failed_tool_calls"),
            "score_breakdown": row.get("score_breakdown", {}),
        }

    # -- datasets --------------------------------------------------------

    def _ordinary_dataset_paths(self, tenant_dir: Path) -> List[Path]:
        """Return ordinary datasets without opening Studio release evidence."""
        datasets_dir = tenant_dir / "datasets"
        if not datasets_dir.is_dir():
            return []
        published_dir = datasets_dir / "evaluation_assets"
        try:
            published_resolved = published_dir.resolve()
        except (OSError, RuntimeError):
            published_resolved = published_dir.absolute()
        paths: list[Path] = []
        for path in datasets_dir.rglob("*.jsonl"):
            try:
                resolved = path.resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if (
                path.is_file()
                and published_dir not in path.parents
                and not _path_is_within(resolved, published_resolved)
            ):
                paths.append(path)
        return sorted(paths)

    @staticmethod
    def _studio_catalogs(tenant_dir: Path) -> tuple[Path, ...]:
        """Classify possible Studio catalogs using directory metadata only."""
        published_dir = tenant_dir / "datasets" / "evaluation_assets"
        if published_dir.is_symlink() or not published_dir.is_dir():
            return ()
        return tuple(
            catalog
            for catalog in sorted(published_dir.iterdir())
            if not catalog.is_symlink() and catalog.is_dir()
        )

    def _dataset_paths(self, tenant_dir: Path) -> List[Path]:
        """Resolve all programmatic dataset paths with full Studio validation."""
        paths = self._ordinary_dataset_paths(tenant_dir)
        for catalog in self._studio_catalogs(tenant_dir):
            try:
                release = resolve_evaluation_asset_release(
                    catalog,
                    expected_tenant_id=tenant_dir.name,
                    expected_asset_id=catalog.name,
                    trusted_root=tenant_dir,
                )
            except (OSError, TypeError, UnicodeError, ValueError):
                continue
            paths.extend(release.files.values())
        return sorted(paths)

    def has_evaluation_asset_datasets(self, tenant_id: str) -> bool:
        """Return whether a dataset listing would include published Studio data."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return False
        datasets_dir = tenant_dir / "datasets"
        published_dir = datasets_dir / "evaluation_assets"
        if published_dir.is_symlink() or not published_dir.is_dir():
            return False
        for catalog in published_dir.iterdir():
            if catalog.is_symlink() or not catalog.is_dir():
                continue
            try:
                release = resolve_evaluation_asset_release(
                    catalog,
                    expected_tenant_id=tenant_id,
                    expected_asset_id=catalog.name,
                    trusted_root=tenant_dir,
                )
            except (OSError, TypeError, UnicodeError, ValueError):
                continue
            if release.files:
                return True
        return False

    def is_evaluation_asset_dataset(
        self,
        tenant_id: str,
        dataset_rel: str,
    ) -> bool:
        """Return whether a requested dataset resolves under the Studio catalog."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return False
        try:
            relative = Path(dataset_rel)
            if relative.is_absolute() or ".." in relative.parts:
                return False
        except (OSError, ValueError):
            return False
        if relative.parts[:2] == ("datasets", "evaluation_assets"):
            return True
        try:
            resolved = (tenant_dir / relative).resolve(strict=True)
            published = (tenant_dir / "datasets" / "evaluation_assets").resolve()
        except (OSError, RuntimeError):
            return False
        return _path_is_within(resolved, published)

    def list_datasets(self, tenant_id: str) -> List[Dict[str, Any]]:
        snapshots, _ = self.prepare_dataset_listing(tenant_id)
        return self.materialize_dataset_listing(snapshots)

    def list_datasets_with_policy(
        self,
        tenant_id: str,
    ) -> tuple[List[Dict[str, Any]], bool]:
        """Compatibility wrapper around the two-phase protected listing read."""
        snapshots, studio_data = self.prepare_dataset_listing(tenant_id)
        return self.materialize_dataset_listing(snapshots), studio_data

    def prepare_dataset_listing(
        self,
        tenant_id: str,
    ) -> tuple[_DatasetListingSnapshot | None, bool]:
        """Classify Studio catalogs without opening protected release bytes."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None, False
        snapshots: list[_FileSnapshot] = []
        for path in self._ordinary_dataset_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            try:
                snapshots.append(_capture_file_snapshot(path, rel))
            except (OSError, ValueError):
                continue
        studio_catalogs = self._studio_catalogs(tenant_dir)
        return (
            _DatasetListingSnapshot(
                tenant_dir=tenant_dir,
                ordinary=tuple(snapshots),
                studio_catalogs=studio_catalogs,
            ),
            bool(studio_catalogs),
        )

    def materialize_dataset_listing(
        self,
        snapshot: _DatasetListingSnapshot | None,
    ) -> List[Dict[str, Any]]:
        if snapshot is None:
            return []
        snapshots = list(snapshot.ordinary)
        for catalog in snapshot.studio_catalogs:
            try:
                release = resolve_evaluation_asset_release(
                    catalog,
                    expected_tenant_id=snapshot.tenant_dir.name,
                    expected_asset_id=catalog.name,
                    trusted_root=snapshot.tenant_dir,
                )
                snapshots.extend(
                    _capture_file_snapshot(
                        path,
                        path.relative_to(snapshot.tenant_dir).as_posix(),
                        expected_sha256=release.descriptor["logical_files"][split][
                            "sha256"
                        ],
                    )
                    for split, path in release.files.items()
                )
            except (OSError, TypeError, UnicodeError, ValueError):
                continue
        datasets: List[Dict[str, Any]] = []
        for file_snapshot in sorted(
            snapshots,
            key=lambda item: item.display_path,
        ):
            rows = _read_jsonl_snapshot(file_snapshot)
            if rows is None:
                continue
            datasets.append(
                {
                    "path": file_snapshot.display_path,
                    "name": file_snapshot.path.name,
                    "bytes": file_snapshot.size,
                    "row_count": len(rows),
                }
            )
        return datasets

    def _dataset_rows(self, tenant_id: str, dataset_rel: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        path = self._resolve_dataset_path(tenant_dir, dataset_rel)
        if path is None:
            return []
        return _read_jsonl(path)

    def get_dataset(
        self, tenant_id: str, dataset_rel: str, offset: int = 0, limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        snapshot, _ = self.prepare_dataset(
            tenant_id,
            dataset_rel,
        )
        return self.materialize_dataset(snapshot, offset=offset, limit=limit)

    def get_dataset_with_policy(
        self,
        tenant_id: str,
        dataset_rel: str,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Optional[Dict[str, Any]], bool]:
        """Compatibility wrapper around the two-phase protected dataset read."""
        snapshot, studio_data = self.prepare_dataset(tenant_id, dataset_rel)
        return (
            self.materialize_dataset(snapshot, offset=offset, limit=limit),
            studio_data,
        )

    def prepare_dataset(
        self,
        tenant_id: str,
        dataset_rel: str,
    ) -> tuple[_FileSnapshot | _DeferredDatasetSnapshot | None, bool]:
        """Classify one dataset without opening protected Studio evidence."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None, False
        studio_data = self.is_evaluation_asset_dataset(tenant_id, dataset_rel)
        if studio_data:
            return _DeferredDatasetSnapshot(tenant_dir, dataset_rel), True
        path = self._resolve_dataset_path(tenant_dir, dataset_rel)
        if path is None:
            return None, studio_data
        try:
            return _capture_file_snapshot(path, dataset_rel), studio_data
        except (OSError, ValueError):
            return None, studio_data

    def materialize_dataset(
        self,
        snapshot: _FileSnapshot | _DeferredDatasetSnapshot | None,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """Read one previously classified dataset snapshot after authorization."""
        if snapshot is None:
            return None
        rows = self._dataset_snapshot_rows(snapshot)
        if rows is None:
            return None
        total = len(rows)
        offset = max(0, offset)
        window = rows[offset : offset + max(0, limit)]
        return {
            "path": snapshot.dataset_rel
            if isinstance(snapshot, _DeferredDatasetSnapshot)
            else snapshot.display_path,
            "total": total,
            "offset": offset,
            "limit": limit,
            "rows": window,
        }

    def _dataset_snapshot_rows(
        self,
        snapshot: _FileSnapshot | _DeferredDatasetSnapshot,
    ) -> list[dict[str, Any]] | None:
        if isinstance(snapshot, _FileSnapshot):
            return _read_jsonl_snapshot(snapshot)
        path = self._resolve_dataset_path(
            snapshot.tenant_dir,
            snapshot.dataset_rel,
        )
        if path is None:
            return None
        try:
            expected_sha256 = self._studio_split_sha256(
                snapshot.tenant_dir,
                snapshot.dataset_rel,
            )
            file_snapshot = _capture_file_snapshot(
                path,
                snapshot.dataset_rel,
                expected_sha256=expected_sha256,
            )
        except (OSError, TypeError, UnicodeError, ValueError):
            return None
        return _read_jsonl_snapshot(file_snapshot)

    @staticmethod
    def _studio_split_sha256(tenant_dir: Path, dataset_rel: str) -> str:
        relative = Path(dataset_rel)
        parts = relative.parts
        generation = validate_historical_generation(
            tenant_dir.joinpath(*parts[:5]),
            expected_tenant_id=tenant_dir.name,
            expected_asset_id=parts[2],
            trusted_root=tenant_dir,
        )
        return str(
            generation.descriptor["logical_files"][Path(parts[5]).stem]["sha256"]
        )

    def _resolve_dataset_path(
        self,
        tenant_dir: Path,
        dataset_rel: str,
    ) -> Optional[Path]:
        """Resolve an ordinary dataset or one fully validated Studio generation."""
        try:
            relative = Path(dataset_rel)
            if relative.is_absolute() or ".." in relative.parts:
                return None
        except (OSError, ValueError):
            return None
        if relative.parts[:2] == ("datasets", "evaluation_assets"):
            parts = relative.parts
            if (
                len(parts) != 6
                or parts[3] != "generations"
                or parts[5]
                not in {
                    "train.jsonl",
                    "validation.jsonl",
                    "test.jsonl",
                    "regression_trusted.jsonl",
                }
            ):
                return None
            generation_dir = tenant_dir.joinpath(*parts[:5])
            try:
                generation = validate_historical_generation(
                    generation_dir,
                    expected_tenant_id=tenant_dir.name,
                    expected_asset_id=parts[2],
                    trusted_root=tenant_dir,
                )
            except (OSError, TypeError, UnicodeError, ValueError):
                return None
            logical_split = Path(parts[5]).stem
            return generation.files[logical_split]
        path = (tenant_dir / relative).resolve()
        datasets_dir = (tenant_dir / "datasets").resolve()
        published_dir = (datasets_dir / "evaluation_assets").resolve()
        if datasets_dir not in path.parents:
            return None
        if _path_is_within(path, published_dir):
            return None
        if path.suffix != ".jsonl" or not path.is_file():
            return None
        return path

    # -- iterations ------------------------------------------------------

    def _iteration_rows(self, tenant_dir: Path) -> List[Dict[str, Any]]:
        return _read_jsonl(tenant_dir / "docs" / "iteration-memory.jsonl")

    def list_iterations(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        rows = self._iteration_rows(tenant_dir)
        for i, row in enumerate(rows):
            row.setdefault("_index", i)
        return rows

    # -- prompts & skills ------------------------------------------------

    def _prompt_paths(self, tenant_dir: Path) -> List[Path]:
        """All editable text assets (prompts + skills) as markdown paths.

        Scans each configured asset subtree (``prompts/``, ``skills/``) for
        ``*.md``. Path-agnostic within a subtree: any nesting depth is fine.
        """
        paths: List[Path] = []
        for dirname, _kind in _PROMPT_ASSET_DIRS:
            asset_dir = tenant_dir / dirname
            if not asset_dir.is_dir():
                continue
            paths.extend(p for p in asset_dir.rglob("*.md") if p.is_file())
        return sorted(paths)

    @staticmethod
    def _asset_kind(tenant_dir: Path, path: Path) -> str:
        """Tag a path by which asset subtree it lives under (prompt/skill)."""
        rel_parts = path.relative_to(tenant_dir).parts
        top = rel_parts[0] if rel_parts else ""
        for dirname, kind in _PROMPT_ASSET_DIRS:
            if top == dirname:
                return kind
        return "prompt"

    @staticmethod
    def _asset_group(tenant_dir: Path, path: Path) -> str:
        """Group label for an asset: its immediate parent directory name.

        For ``prompts/modules/agent/variant-001.md`` this is ``agent``; for
        ``skills/superlative-index-questions/variant-001.md`` it is the skill
        name. Falls back to the subtree name for a file sitting directly in it.
        """
        rel_parts = path.relative_to(tenant_dir).parts
        if len(rel_parts) >= 2:
            return rel_parts[-2]
        return rel_parts[0] if rel_parts else ""

    def list_prompts(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        prompts: List[Dict[str, Any]] = []
        for path in self._prompt_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            prompts.append(
                {
                    "path": rel,
                    "name": path.name,
                    "bytes": size,
                    "kind": self._asset_kind(tenant_dir, path),
                    "group": self._asset_group(tenant_dir, path),
                }
            )
        return prompts

    def get_prompt(self, tenant_id: str, prompt_rel: str) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        path = (tenant_dir / prompt_rel).resolve()
        if tenant_dir not in path.parents:
            return None  # traversal guard
        # Only serve markdown under a known asset subtree (prompts/ or skills/).
        in_asset_dir = False
        for dirname, _kind in _PROMPT_ASSET_DIRS:
            asset_dir = (tenant_dir / dirname).resolve()
            if asset_dir in path.parents or path.parent == asset_dir:
                in_asset_dir = True
                break
        if not in_asset_dir:
            return None
        if path.suffix != ".md" or not path.is_file():
            return None
        return {
            "path": prompt_rel,
            "content": _read_text(path),
            "kind": self._asset_kind(tenant_dir, path),
            "group": self._asset_group(tenant_dir, path),
        }

    # -- configs ---------------------------------------------------------

    def _config_paths(self, tenant_dir: Path) -> List[Path]:
        paths: List[Path] = []
        for dirname in _CONFIG_DIRS:
            config_dir = tenant_dir / dirname
            if config_dir.is_dir():
                paths.extend(
                    p for p in config_dir.rglob("*") if p.is_file() and not p.name.startswith(".")
                )
        return sorted(paths)

    def list_configs(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        configs: List[Dict[str, Any]] = []
        for path in self._config_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            configs.append({"path": rel, "name": path.name, "bytes": size})
        return configs

    def get_config(self, tenant_id: str, config_rel: str) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        path = (tenant_dir / config_rel).resolve()
        if tenant_dir not in path.parents:
            return None  # traversal guard
        config_dirs = [(tenant_dir / dirname).resolve() for dirname in _CONFIG_DIRS]
        in_config_dir = any(
            config_dir in path.parents or path.parent == config_dir for config_dir in config_dirs
        )
        if not in_config_dir or not path.is_file():
            return None
        return {"path": config_rel, "content": _read_text(path)}

    # -- docs ------------------------------------------------------------

    def _doc_paths(self, tenant_dir: Path) -> List[Path]:
        """Markdown docs for a tenant: top-level README plus docs/*.md."""
        paths: List[Path] = []
        readme = tenant_dir / "README.md"
        if readme.is_file():
            paths.append(readme)
        docs_dir = tenant_dir / "docs"
        if docs_dir.is_dir():
            paths.extend(sorted(p for p in docs_dir.rglob("*.md") if p.is_file()))
        return paths

    def list_docs(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        docs: List[Dict[str, Any]] = []
        for path in self._doc_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            docs.append({"path": rel, "name": path.name, "bytes": size})
        return docs

    def get_doc(self, tenant_id: str, doc_rel: str) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        path = (tenant_dir / doc_rel).resolve()
        if tenant_dir not in path.parents:
            return None  # traversal guard
        # Only serve the tenant README or markdown under docs/.
        docs_dir = (tenant_dir / "docs").resolve()
        is_readme = path == (tenant_dir / "README.md").resolve()
        in_docs = docs_dir in path.parents or path.parent == docs_dir
        if not is_readme and not in_docs:
            return None
        if path.suffix != ".md" or not path.is_file():
            return None
        return {"path": doc_rel, "content": _read_text(path)}
