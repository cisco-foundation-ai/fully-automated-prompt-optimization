# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Read-only filesystem layer for the web UI.

Walks ``tenants/<tenant_id>/`` and surfaces the artifacts a user wants to
navigate: eval runs (``evals/<run>/``), iteration history
(``docs/iteration-memory.jsonl``), prompt variants (``prompts/**/*.md``), and
per-case eval outputs (``results.jsonl``).

Nothing here mutates tenant data. Paths are resolved relative to the tenants
root and validated to stay inside it, so the HTTP layer cannot read arbitrary
files on disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Directory names probed inside each tenant when listing eval runs. The repo
# convention is ``evals/``, but eval configs can point output_dir anywhere, so
# we probe a few common spellings.
_RUN_PARENT_DIRS = ("evals", "runs", "eval_outputs", "outputs")

# A directory is treated as an eval run if it contains at least one of these.
_RUN_MARKERS = ("results.jsonl", "run_config.json", "summary.md", "progress.json")


def _read_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
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


class TenantStore:
    """Resolves and reads tenant artifacts under a single tenants root."""

    def __init__(self, tenants_root: Path) -> None:
        self.root = tenants_root.resolve()

    # -- path safety -----------------------------------------------------

    def _tenant_dir(self, tenant_id: str) -> Optional[Path]:
        """Return the tenant directory, or None if it isn't a real tenant."""
        candidate = (self.root / tenant_id).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            return None  # path traversal attempt
        if not candidate.is_dir():
            return None
        if not (candidate / "__init__.py").exists() and not (candidate / "storage").exists():
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
            tenants.append(
                {
                    "tenant_id": child.name,
                    "run_count": len(runs),
                    "iteration_count": len(iterations),
                    "prompt_count": len(self._prompt_paths(tenant_dir)),
                    "dataset_count": len(self._dataset_paths(tenant_dir)),
                    "doc_count": len(self._doc_paths(tenant_dir)),
                    "has_readme": (tenant_dir / "README.md").exists(),
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
                    "dataset_count": tenant["dataset_count"],
                    "doc_count": tenant["doc_count"],
                    "latest_run": latest,
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
        run_dir = self._resolve_run_dir(tenant_id, run_dir_rel)
        if run_dir is None:
            return None
        results = _read_jsonl(run_dir / "results.jsonl")
        if index < 0 or index >= len(results):
            return None
        case = results[index]
        ground_truth = self._ground_truth_for(tenant_id, run_dir, case.get("case_id"))
        return {"index": index, "case": case, "ground_truth": ground_truth}

    def _ground_truth_for(
        self, tenant_id: str, run_dir: Path, case_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Look up the dataset row's ``expected`` block for a result case.

        Joins on ``case_id`` against the dataset referenced by the run's
        ``run_config.json`` (falling back to the tenant's only dataset). Returns
        None if the dataset isn't available locally or the case isn't found.
        """
        if case_id is None:
            return None
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
        datasets = self._dataset_paths(tenant_dir)
        if len(datasets) == 1:
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

    def _dataset_paths(self, tenant_dir: Path) -> List[Path]:
        datasets_dir = tenant_dir / "datasets"
        if not datasets_dir.is_dir():
            return []
        return sorted(p for p in datasets_dir.rglob("*.jsonl") if p.is_file())

    def list_datasets(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        datasets: List[Dict[str, Any]] = []
        for path in self._dataset_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            rows = _read_jsonl(path)
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            datasets.append(
                {
                    "path": rel,
                    "name": path.name,
                    "bytes": size,
                    "row_count": len(rows),
                }
            )
        return datasets

    def _dataset_rows(self, tenant_id: str, dataset_rel: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        path = (tenant_dir / dataset_rel).resolve()
        datasets_dir = (tenant_dir / "datasets").resolve()
        if datasets_dir not in path.parents:
            return []  # traversal guard
        if path.suffix != ".jsonl" or not path.is_file():
            return []
        return _read_jsonl(path)

    def get_dataset(
        self, tenant_id: str, dataset_rel: str, offset: int = 0, limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        path = (tenant_dir / dataset_rel).resolve()
        datasets_dir = (tenant_dir / "datasets").resolve()
        if datasets_dir not in path.parents:
            return None  # traversal guard
        if path.suffix != ".jsonl" or not path.is_file():
            return None
        rows = _read_jsonl(path)
        total = len(rows)
        offset = max(0, offset)
        window = rows[offset : offset + max(0, limit)]
        return {
            "path": dataset_rel,
            "total": total,
            "offset": offset,
            "limit": limit,
            "rows": window,
        }

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

    # -- prompts ---------------------------------------------------------

    def _prompt_paths(self, tenant_dir: Path) -> List[Path]:
        prompts_dir = tenant_dir / "prompts"
        if not prompts_dir.is_dir():
            return []
        return sorted(p for p in prompts_dir.rglob("*.md") if p.is_file())

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
            prompts.append({"path": rel, "name": path.name, "bytes": size})
        return prompts

    def get_prompt(self, tenant_id: str, prompt_rel: str) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        path = (tenant_dir / prompt_rel).resolve()
        if tenant_dir not in path.parents:
            return None  # traversal guard
        # Only serve markdown prompts under the prompts/ subtree.
        if (tenant_dir / "prompts").resolve() not in path.parents and path.parent != (
            tenant_dir / "prompts"
        ).resolve():
            return None
        if path.suffix != ".md" or not path.is_file():
            return None
        return {"path": prompt_rel, "content": _read_text(path)}

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
