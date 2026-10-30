# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Read-only filesystem layer for the web UI.

Walks ``tenants/<tenant_id>/`` and surfaces the artifacts a user wants to
navigate: eval runs (``evals/<run>/``), iteration history
(``docs/iteration-memory.jsonl``), prompt and skill variants
(``prompts/**/*.md`` and ``skills/**/*.md``), datasets (``datasets/**/*.jsonl``
and ``evaluation_assets/<asset_id>/datasets/**/*.jsonl``), and per-case eval
outputs (``results.jsonl``).

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

from src.hephaestus.local_authority_io import (
    BoundDirectory,
    BoundFile,
    open_bound_directory,
    open_child_directory,
    open_child_file,
    read_bound_file,
    validate_existing_directory_chain,
)
from src.hephaestus.runs.bundle import ValidatedRunBundle, load_run_bundle


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
    authority_root: Path | None = None


@dataclass(frozen=True)
class _AuthenticatedDatasetSnapshot:
    """A dataset file bound to the exact bytes and case order a run bundle recorded."""

    file: _FileSnapshot
    ordered_case_ids: tuple[str, ...]


def _bind_exact_directory(authority_root: Path, path: Path) -> BoundDirectory:
    """Open every lexical directory component without following aliases."""
    root = Path(os.path.abspath(os.fspath(authority_root)))
    candidate = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes its authority root") from exc
    current = open_bound_directory(root)
    try:
        for part in relative.parts:
            child = open_child_directory(current, part)
            current.close()
            current = child
        return current
    except BaseException:
        current.close()
        raise


def _open_exact_file(authority_root: Path, path: Path) -> BoundFile:
    """Open one exact regular file through an exact directory chain."""
    absolute = Path(os.path.abspath(os.fspath(path)))
    parent = _bind_exact_directory(authority_root, absolute.parent)
    try:
        return open_child_file(parent, absolute.name)
    finally:
        parent.close()


def _exact_directory(authority_root: Path, path: Path) -> Path | None:
    """Return a lexical exact directory beneath an authority root."""
    absolute = Path(os.path.abspath(os.fspath(path)))
    try:
        bound = _bind_exact_directory(authority_root, absolute)
    except (OSError, ValueError):
        return None
    bound.close()
    return absolute


def _capture_file_snapshot(
    path: Path,
    display_path: str,
    *,
    expected_sha256: str | None = None,
    authority_root: Path | None = None,
) -> _FileSnapshot:
    absolute = Path(os.path.abspath(os.fspath(path)))
    bound: BoundFile | None = None
    if authority_root is not None:
        bound = _open_exact_file(authority_root, absolute)
        resolved = absolute
    else:
        resolved = path.resolve(strict=True)
        if path.is_symlink() or resolved != path.absolute():
            raise ValueError("snapshot path cannot be a symlink")
    try:
        details = absolute.stat(follow_symlinks=False)
        if (
            bound is not None
            and os.name != "nt"
            and (details.st_dev, details.st_ino) != bound.identity[:2]
        ):
            raise ValueError("snapshot path changed while binding")
        device, inode = (
            bound.identity[:2]
            if bound is not None
            else (details.st_dev, details.st_ino)
        )
    finally:
        if bound is not None:
            bound.close()
    if not stat.S_ISREG(details.st_mode):
        raise ValueError("snapshot path is not a regular file")
    return _FileSnapshot(
        path=absolute,
        display_path=display_path,
        device=device,
        inode=inode,
        size=details.st_size,
        expected_sha256=expected_sha256,
        authority_root=(
            Path(os.path.abspath(os.fspath(authority_root)))
            if authority_root is not None
            else None
        ),
    )


def _read_snapshot_bytes(snapshot: _FileSnapshot) -> bytes | None:
    descriptor: int | None = None
    bound: BoundFile | None = None
    try:
        if snapshot.authority_root is not None:
            bound = _open_exact_file(snapshot.authority_root, snapshot.path)
            if bound.identity[:2] != (snapshot.device, snapshot.inode):
                return None
            raw = read_bound_file(bound)
        else:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
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
        if len(raw) != snapshot.size:
            return None
        if snapshot.expected_sha256 is not None and hashlib.sha256(
            raw
        ).hexdigest() != snapshot.expected_sha256:
            return None
        return raw
    except (OSError, ValueError):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if bound is not None:
            bound.close()


def _read_jsonl_snapshot(snapshot: _FileSnapshot) -> list[dict[str, Any]] | None:
    raw = _read_snapshot_bytes(snapshot)
    if raw is None:
        return None
    try:
        rows = []
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                return None
            rows.append(row)
        return rows
    except (UnicodeError, json.JSONDecodeError):
        return None


def _read_json_snapshot(snapshot: _FileSnapshot | None) -> Any | None:
    if snapshot is None:
        return None
    raw = _read_snapshot_bytes(snapshot)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None


def _read_text_snapshot(snapshot: _FileSnapshot | None) -> str | None:
    if snapshot is None:
        return None
    raw = _read_snapshot_bytes(snapshot)
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        return None


def _capture_optional_snapshot(
    authority_root: Path,
    path: Path,
) -> _FileSnapshot | None:
    try:
        return _capture_file_snapshot(
            path,
            path.as_posix(),
            authority_root=authority_root,
        )
    except (OSError, ValueError):
        return None


# Directory names probed inside each tenant when listing eval runs. The repo
# convention is ``evals/``, but eval configs can point output_dir anywhere, so
# we probe a few common spellings.
_RUN_PARENT_DIRS = ("evals", "runs", "eval_outputs", "outputs")

# A directory is treated as an eval run if it contains at least one of these.
_RUN_MARKERS = (
    "results.jsonl",
    "run_config.json",
    "summary.md",
    "progress.json",
    "run_manifest.json",
)

# Tenants historically use ``configs/``; support ``config/`` as an alias for
# local projects that use the singular spelling.
_CONFIG_DIRS = ("config", "configs")

# Editable text assets surfaced under the Prompts tab. Each entry maps a tenant
# subdirectory to the ``kind`` tag reported for files found beneath it. Prompts
# and skills are both optimizable markdown, so they live together here. Adding a
# new asset subtree is just a new entry — discovery is otherwise path-agnostic.
_PROMPT_ASSET_DIRS = (("prompts", "prompt"), ("skills", "skill"))


class TenantStore:
    """Resolves and reads tenant artifacts under a single tenants root."""

    def __init__(
        self,
        tenants_root: Path,
        *,
        repository_base: Path | None = None,
    ) -> None:
        base = Path(
            os.path.abspath(os.fspath(repository_base if repository_base is not None else Path.cwd()))
        )
        root = Path(
            os.path.abspath(os.fspath(tenants_root if tenants_root.is_absolute() else base / tenants_root))
        )
        try:
            validate_existing_directory_chain(base, root)
        except (OSError, ValueError) as exc:
            raise ValueError("tenants root must remain within the exact repository base") from exc
        self.root = root
        self.repository_base = base

    # -- path safety -----------------------------------------------------

    def _tenant_dir(self, tenant_id: str) -> Optional[Path]:
        """Return the tenant directory, or None if it isn't a real tenant."""
        if (
            not isinstance(tenant_id, str)
            or not tenant_id
            or tenant_id in {".", ".."}
            or "/" in tenant_id
            or "\\" in tenant_id
            or "\x00" in tenant_id
        ):
            return None
        candidate = _exact_directory(self.root, self.root / tenant_id)
        if candidate is None or candidate.name != tenant_id:
            return None
        init_marker = _capture_optional_snapshot(
            candidate,
            candidate / "__init__.py",
        )
        storage_dir = _exact_directory(candidate, candidate / "storage")
        assets_dir = _exact_directory(candidate, candidate / "evaluation_assets")
        if (
            init_marker is None
            and storage_dir is None
            and assets_dir is None
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
            runs = self.list_runs(child.name)
            iterations = self._iteration_rows(tenant_dir)
            tenants.append(
                {
                    "tenant_id": child.name,
                    "run_count": len(runs),
                    "iteration_count": len(iterations),
                    "prompt_count": len(self._prompt_paths(tenant_dir)),
                    "dataset_count": len(self._dataset_paths(tenant_dir)),
                    "config_count": len(self._config_paths(tenant_dir)),
                    "doc_count": len(self._doc_paths(tenant_dir)),
                    "has_readme": _capture_optional_snapshot(
                        tenant_dir,
                        tenant_dir / "README.md",
                    )
                    is not None,
                }
            )
        return tenants

    def overview(self, tenant_ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Aggregate cross-tenant stats for the landing dashboard.

        Returns global totals plus a per-tenant card with its most recent
        authoritative completed run (status, score, model, timestamp) so the UI
        can render a dashboard in a single request rather than fanning out per
        tenant. Unverified runs remain in the recent operational list but never
        contribute headline score evidence.

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
            latest = next(
                (
                    run
                    for run in runs
                    if run.get("authority") == "authoritative"
                    and run.get("status") == "completed"
                ),
                None,
            )
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

    @staticmethod
    def _run_artifact_snapshot(
        tenant_dir: Path,
        run_dir: Path,
        name: str,
    ) -> _FileSnapshot | None:
        """Bind one direct run artifact beneath the exact tenant directory."""
        if Path(name).name != name:
            return None
        return _capture_optional_snapshot(tenant_dir, run_dir / name)

    @classmethod
    def _run_json(
        cls,
        tenant_dir: Path,
        run_dir: Path,
        name: str,
    ) -> Any | None:
        return _read_json_snapshot(
            cls._run_artifact_snapshot(tenant_dir, run_dir, name)
        )

    def _run_dirs(self, tenant_dir: Path) -> List[Path]:
        found: set[Path] = set()
        for parent_name in _RUN_PARENT_DIRS:
            parent = _exact_directory(tenant_dir, tenant_dir / parent_name)
            if parent is None:
                continue
            for marker in _RUN_MARKERS:
                try:
                    marker_paths = parent.rglob(marker)
                    for marker_path in marker_paths:
                        run_dir = _exact_directory(tenant_dir, marker_path.parent)
                        if run_dir is None:
                            continue
                        if self._run_artifact_snapshot(
                            tenant_dir,
                            run_dir,
                            marker,
                        ) is not None:
                            found.add(run_dir)
                except OSError:
                    continue
        return sorted(found)

    @staticmethod
    def _safe_manifest_facts(bundle: ValidatedRunBundle) -> Dict[str, Any]:
        """Return the manifest facts that are safe and useful to UI consumers."""
        return {
            field: bundle.manifest[field]
            for field in (
                "schema_version",
                "hash_algorithm",
                "run_id",
                "status",
                "run_identity_fingerprint",
                "ordered_case_ids_fingerprint",
                "result_count",
                "successful_result_count",
                "failed_result_count",
            )
        }

    def _run_authority(
        self,
        tenant_dir: Path,
        run_dir: Path,
    ) -> tuple[str, ValidatedRunBundle | None]:
        """Classify a run without treating loose terminal files as authority."""
        manifest_path = run_dir / "run_manifest.json"
        if os.path.lexists(manifest_path):
            try:
                bundle = load_run_bundle(run_dir)
            except (OSError, TypeError, UnicodeError, ValueError):
                return "invalid_unverified", None
            if bundle.run_config.get("tenant_id") != tenant_dir.name:
                return "foreign_rejected", None
            return "authoritative", bundle
        progress = self._run_json(tenant_dir, run_dir, "progress.json") or {}
        if not isinstance(progress, dict):
            progress = {}
        if progress.get("status") in {"completed", "degraded", "failed"}:
            return "legacy_unverified", None
        return "live_unverified", None

    def _authenticated_dataset_snapshot(
        self,
        tenant_dir: Path,
        bundle: ValidatedRunBundle,
    ) -> tuple[_AuthenticatedDatasetSnapshot | None, str | None]:
        """Bind a join to the exact dataset bytes and case order a bundle recorded.

        The recorded dataset must be a file beneath one of the tenant's exact
        dataset roots (see ``_dataset_roots``).
        """
        controls = bundle.run_identity.get("always_controls")
        if not isinstance(controls, dict):
            return None, None
        dataset_path = controls.get("dataset_path")
        dataset = controls.get("dataset")
        if (
            not isinstance(dataset_path, str)
            or bundle.run_config.get("dataset_path") != dataset_path
            or not isinstance(dataset, dict)
            or dataset.get("status") != "available"
            or not isinstance(dataset.get("fingerprint"), str)
        ):
            return None, None
        ordered_case_ids = controls.get("ordered_case_ids")
        if (
            not isinstance(ordered_case_ids, list)
            or any(not isinstance(case_id, str) or not case_id for case_id in ordered_case_ids)
        ):
            return None, None
        try:
            literal = Path(dataset_path)
            if not literal.is_absolute() and ".." in literal.parts:
                return None, None
            candidate = literal if literal.is_absolute() else self.repository_base / literal
            absolute = Path(os.path.abspath(os.fspath(candidate)))
            if not _path_is_within(absolute, tenant_dir):
                return None, None
            relative = absolute.relative_to(tenant_dir)
            root = self._dataset_root(tenant_dir, relative)
            if root is None or absolute == root:
                return None, None
            dataset_rel = relative.as_posix()
            file = _capture_file_snapshot(
                absolute,
                dataset_rel,
                expected_sha256=dataset["fingerprint"].removeprefix("sha256:"),
                authority_root=tenant_dir,
            )
        except (OSError, RuntimeError, ValueError):
            return None, None
        return (
            _AuthenticatedDatasetSnapshot(
                file=file,
                ordered_case_ids=tuple(ordered_case_ids),
            ),
            dataset_rel,
        )

    def list_runs(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        runs: List[Dict[str, Any]] = []
        for run_dir in self._run_dirs(tenant_dir):
            authority, bundle = self._run_authority(tenant_dir, run_dir)
            if authority == "foreign_rejected":
                continue
            progress = (
                dict(bundle.progress)
                if bundle is not None
                else (self._run_json(tenant_dir, run_dir, "progress.json") or {})
            )
            run_config = (
                dict(bundle.run_config)
                if bundle is not None
                else (self._run_json(tenant_dir, run_dir, "run_config.json") or {})
            )
            if not isinstance(progress, dict):
                progress = {}
            if not isinstance(run_config, dict):
                run_config = {}
            results_snapshot = self._run_artifact_snapshot(
                tenant_dir,
                run_dir,
                "results.jsonl",
            )
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
                    "has_results": bool(bundle is not None or results_snapshot is not None),
                    "authority": authority,
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
        authority, bundle = self._run_authority(tenant_dir, run_dir)
        if authority == "foreign_rejected":
            return None
        if bundle is not None:
            results = [dict(row) for row in bundle.results]
            run_config: Any = dict(bundle.run_config)
            progress: Any = dict(bundle.progress)
            summary: Any = bundle.summary
        else:
            results_snapshot = self._run_artifact_snapshot(
                tenant_dir,
                run_dir,
                "results.jsonl",
            )
            results = (
                _read_jsonl_snapshot(results_snapshot)
                if results_snapshot is not None
                else None
            ) or []
            run_config = self._run_json(tenant_dir, run_dir, "run_config.json")
            progress = self._run_json(tenant_dir, run_dir, "progress.json")
            summary = _read_text_snapshot(
                self._run_artifact_snapshot(
                    tenant_dir,
                    run_dir,
                    "summary.md",
                )
            )
        cases = [self._case_summary(i, row) for i, row in enumerate(results)]
        response: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "run_dir": run_dir.relative_to(tenant_dir).as_posix(),
            "run_config": run_config,
            "progress": progress,
            "summary_md": summary,
            "cases": cases,
            "authority": authority,
        }
        if bundle is not None:
            # ``load_run_bundle`` validates the strict, privacy-safe identity
            # schema before this data reaches the HTTP serializer.
            response["run_manifest"] = self._safe_manifest_facts(bundle)
            response["run_identity"] = dict(bundle.run_identity)
        return response

    def get_case(self, tenant_id: str, run_dir_rel: str, index: int) -> Optional[Dict[str, Any]]:
        """Return one result row of a run, joined with its dataset ground truth.

        Args:
            tenant_id: Tenant directory name.
            run_dir_rel: Tenant-relative run directory.
            index: Zero-based position of the case in the run's results.

        Returns:
            The case payload, or None when the run, its results, or the index is
            not available.
        """
        run_dir = self._resolve_run_dir(tenant_id, run_dir_rel)
        if run_dir is None or index < 0:
            return None
        tenant_dir = self._tenant_dir(tenant_id)
        assert tenant_dir is not None
        authority, bundle = self._run_authority(tenant_dir, run_dir)
        if authority == "foreign_rejected":
            return None
        dataset: _FileSnapshot | _AuthenticatedDatasetSnapshot | None = None
        results: list[dict[str, Any]] | None
        if bundle is not None:
            results = [dict(row) for row in bundle.results]
            dataset, dataset_rel = self._authenticated_dataset_snapshot(tenant_dir, bundle)
        else:
            dataset_rel = self._run_dataset_rel(tenant_id, run_dir)
            if authority != "invalid_unverified" and dataset_rel is not None:
                dataset = self._dataset_snapshot(tenant_dir, dataset_rel)
            try:
                results_snapshot = _capture_file_snapshot(
                    run_dir / "results.jsonl",
                    (run_dir / "results.jsonl").as_posix(),
                    authority_root=tenant_dir,
                )
            except (OSError, ValueError):
                return None
            results = _read_jsonl_snapshot(results_snapshot)
        if results is None or index >= len(results):
            return None
        case = dict(results[index])
        return {
            "index": index,
            "case": case,
            "ground_truth": self._ground_truth_from_snapshot(
                dataset,
                dataset_rel,
                case.get("case_id"),
            ),
            "authority": authority,
        }

    def _ground_truth_from_snapshot(
        self,
        snapshot: _FileSnapshot | _AuthenticatedDatasetSnapshot | None,
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

    def _run_dataset_rel(self, tenant_id: str, run_dir: Path) -> Optional[str]:
        """Resolve the tenant-relative dataset path used by a run."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        run_config = self._run_json(tenant_dir, run_dir, "run_config.json") or {}
        if not isinstance(run_config, dict):
            run_config = {}
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
        # Fall back to the tenant's only dataset when config is absent or stale.
        datasets = self._dataset_paths(tenant_dir)
        if len(datasets) == 1:
            return datasets[0].relative_to(tenant_dir).as_posix()
        return None

    def _resolve_run_dir(self, tenant_id: str, run_dir_rel: str) -> Optional[Path]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        if not isinstance(run_dir_rel, str) or not run_dir_rel:
            return None
        literal = Path(run_dir_rel)
        if literal.is_absolute() or ".." in literal.parts:
            return None
        run_dir = _exact_directory(tenant_dir, tenant_dir / literal)
        if run_dir is None or run_dir == tenant_dir:
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

    @staticmethod
    def _dataset_roots(tenant_dir: Path) -> List[Path]:
        """Return the exact directories whose ``*.jsonl`` files are datasets.

        These are ``datasets/`` and, for assets built by ``assets build``, each
        ``evaluation_assets/<asset_id>/datasets/``. Nothing else in an asset
        directory (inputs, cache, lessons, rubrics, catalog) is a dataset.
        """
        roots: List[Path] = []
        datasets_dir = _exact_directory(tenant_dir, tenant_dir / "datasets")
        if datasets_dir is not None:
            roots.append(datasets_dir)
        assets_dir = _exact_directory(tenant_dir, tenant_dir / "evaluation_assets")
        if assets_dir is None:
            return roots
        try:
            asset_dirs = sorted(assets_dir.iterdir())
        except OSError:
            return roots
        for asset_dir in asset_dirs:
            asset_datasets_dir = _exact_directory(tenant_dir, asset_dir / "datasets")
            if asset_datasets_dir is not None:
                roots.append(asset_datasets_dir)
        return roots

    @staticmethod
    def _dataset_root(tenant_dir: Path, relative: Path) -> Optional[Path]:
        """Return the exact dataset root named by a tenant-relative path's prefix."""
        parts = relative.parts
        if parts[:1] == ("datasets",):
            prefix = parts[:1]
        elif len(parts) >= 3 and parts[0] == "evaluation_assets" and parts[2] == "datasets":
            prefix = parts[:3]
        else:
            return None
        return _exact_directory(tenant_dir, tenant_dir.joinpath(*prefix))

    def _dataset_paths(self, tenant_dir: Path) -> List[Path]:
        """Return every ``*.jsonl`` regular file beneath the tenant's dataset roots."""
        paths: List[Path] = []
        for root in self._dataset_roots(tenant_dir):
            try:
                for path in root.rglob("*.jsonl"):
                    if _capture_optional_snapshot(tenant_dir, path) is not None:
                        paths.append(path)
            except OSError:
                continue
        return sorted(paths)

    def _resolve_dataset_path(
        self,
        tenant_dir: Path,
        dataset_rel: str,
    ) -> Optional[Path]:
        """Resolve a tenant-relative ``*.jsonl`` file beneath an exact dataset root."""
        try:
            relative = Path(dataset_rel)
            if relative.is_absolute() or ".." in relative.parts:
                return None
        except (OSError, ValueError):
            return None
        root = self._dataset_root(tenant_dir, relative)
        if root is None:
            return None
        path = Path(os.path.abspath(os.fspath(tenant_dir / relative)))
        if path == root or not _path_is_within(path, root) or path.suffix != ".jsonl":
            return None
        if _capture_optional_snapshot(tenant_dir, path) is None:
            return None
        return path

    def _dataset_snapshot(self, tenant_dir: Path, dataset_rel: str) -> _FileSnapshot | None:
        """Bind one dataset file under the tenant-relative path it was requested by."""
        path = self._resolve_dataset_path(tenant_dir, dataset_rel)
        if path is None:
            return None
        try:
            return _capture_file_snapshot(path, dataset_rel, authority_root=tenant_dir)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _dataset_snapshot_rows(
        snapshot: _FileSnapshot | _AuthenticatedDatasetSnapshot,
    ) -> list[dict[str, Any]] | None:
        if isinstance(snapshot, _FileSnapshot):
            return _read_jsonl_snapshot(snapshot)
        rows = _read_jsonl_snapshot(snapshot.file)
        if rows is None:
            return None
        if tuple(row.get("case_id") for row in rows) != snapshot.ordered_case_ids:
            return None
        return rows

    def list_datasets(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List the tenant's dataset files with their sizes and row counts."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        datasets: List[Dict[str, Any]] = []
        for path in self._dataset_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            try:
                snapshot = _capture_file_snapshot(path, rel, authority_root=tenant_dir)
            except (OSError, ValueError):
                continue
            rows = _read_jsonl_snapshot(snapshot)
            if rows is None:
                continue
            datasets.append(
                {
                    "path": rel,
                    "name": path.name,
                    "bytes": snapshot.size,
                    "row_count": len(rows),
                }
            )
        datasets.sort(key=lambda item: item["path"])
        return datasets

    def get_dataset(
        self, tenant_id: str, dataset_rel: str, offset: int = 0, limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """Return one page of a dataset's rows, or None if it is not a dataset file."""
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        snapshot = self._dataset_snapshot(tenant_dir, dataset_rel)
        if snapshot is None:
            return None
        rows = _read_jsonl_snapshot(snapshot)
        if rows is None:
            return None
        offset = max(0, offset)
        return {
            "path": snapshot.display_path,
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "rows": rows[offset : offset + max(0, limit)],
        }

    # -- iterations ------------------------------------------------------

    def _iteration_rows(self, tenant_dir: Path) -> List[Dict[str, Any]]:
        docs_dir = _exact_directory(tenant_dir, tenant_dir / "docs")
        if docs_dir is None:
            return []
        snapshot = _capture_optional_snapshot(
            tenant_dir,
            docs_dir / "iteration-memory.jsonl",
        )
        if snapshot is None:
            return []
        return _read_jsonl_snapshot(snapshot) or []

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
            asset_dir = _exact_directory(tenant_dir, tenant_dir / dirname)
            if asset_dir is None:
                continue
            try:
                paths.extend(
                    path
                    for path in asset_dir.rglob("*.md")
                    if _capture_optional_snapshot(tenant_dir, path) is not None
                )
            except OSError:
                continue
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
            snapshot = _capture_optional_snapshot(tenant_dir, path)
            if snapshot is None:
                continue
            prompts.append(
                {
                    "path": rel,
                    "name": path.name,
                    "bytes": snapshot.size,
                    "kind": self._asset_kind(tenant_dir, path),
                    "group": self._asset_group(tenant_dir, path),
                }
            )
        return prompts

    def get_prompt(self, tenant_id: str, prompt_rel: str) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        relative = Path(prompt_rel)
        if relative.is_absolute() or ".." in relative.parts:
            return None
        allowed_roots = {dirname for dirname, _kind in _PROMPT_ASSET_DIRS}
        if not relative.parts or relative.parts[0] not in allowed_roots:
            return None
        asset_dir = _exact_directory(tenant_dir, tenant_dir / relative.parts[0])
        if asset_dir is None:
            return None
        path = Path(os.path.abspath(os.fspath(tenant_dir / relative)))
        if path.suffix != ".md" or not _path_is_within(path, asset_dir):
            return None
        snapshot = _capture_optional_snapshot(tenant_dir, path)
        content = _read_text_snapshot(snapshot)
        if content is None:
            return None
        return {
            "path": prompt_rel,
            "content": content,
            "kind": self._asset_kind(tenant_dir, path),
            "group": self._asset_group(tenant_dir, path),
        }

    # -- configs ---------------------------------------------------------

    def _config_paths(self, tenant_dir: Path) -> List[Path]:
        paths: List[Path] = []
        for dirname in _CONFIG_DIRS:
            config_dir = _exact_directory(tenant_dir, tenant_dir / dirname)
            if config_dir is not None:
                try:
                    candidates = config_dir.rglob("*")
                    paths.extend(
                        path
                        for path in candidates
                        if not path.name.startswith(".")
                        and _capture_optional_snapshot(tenant_dir, path) is not None
                    )
                except OSError:
                    continue
        return sorted(paths)

    def list_configs(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        configs: List[Dict[str, Any]] = []
        for path in self._config_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            snapshot = _capture_optional_snapshot(tenant_dir, path)
            if snapshot is None:
                continue
            configs.append(
                {"path": rel, "name": path.name, "bytes": snapshot.size}
            )
        return configs

    def get_config(self, tenant_id: str, config_rel: str) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        relative = Path(config_rel)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or relative.parts[0] not in _CONFIG_DIRS
        ):
            return None
        config_dir = _exact_directory(tenant_dir, tenant_dir / relative.parts[0])
        if config_dir is None:
            return None
        path = Path(os.path.abspath(os.fspath(tenant_dir / relative)))
        if not _path_is_within(path, config_dir):
            return None
        content = _read_text_snapshot(_capture_optional_snapshot(tenant_dir, path))
        if content is None:
            return None
        return {"path": config_rel, "content": content}

    # -- docs ------------------------------------------------------------

    def _doc_paths(self, tenant_dir: Path) -> List[Path]:
        """Markdown docs for a tenant: top-level README plus docs/*.md."""
        paths: List[Path] = []
        readme = tenant_dir / "README.md"
        if _capture_optional_snapshot(tenant_dir, readme) is not None:
            paths.append(readme)
        docs_dir = _exact_directory(tenant_dir, tenant_dir / "docs")
        if docs_dir is not None:
            try:
                paths.extend(
                    sorted(
                        path
                        for path in docs_dir.rglob("*.md")
                        if _capture_optional_snapshot(tenant_dir, path) is not None
                    )
                )
            except OSError:
                pass
        return paths

    def list_docs(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return []
        docs: List[Dict[str, Any]] = []
        for path in self._doc_paths(tenant_dir):
            rel = path.relative_to(tenant_dir).as_posix()
            snapshot = _capture_optional_snapshot(tenant_dir, path)
            if snapshot is None:
                continue
            docs.append({"path": rel, "name": path.name, "bytes": snapshot.size})
        return docs

    def get_doc(self, tenant_id: str, doc_rel: str) -> Optional[Dict[str, Any]]:
        tenant_dir = self._tenant_dir(tenant_id)
        if tenant_dir is None:
            return None
        relative = Path(doc_rel)
        if relative.is_absolute() or ".." in relative.parts:
            return None
        is_readme = relative.parts == ("README.md",)
        if not is_readme and (
            not relative.parts or relative.parts[0] != "docs"
        ):
            return None
        if not is_readme and _exact_directory(
            tenant_dir,
            tenant_dir / "docs",
        ) is None:
            return None
        path = Path(os.path.abspath(os.fspath(tenant_dir / relative)))
        if path.suffix != ".md":
            return None
        content = _read_text_snapshot(_capture_optional_snapshot(tenant_dir, path))
        if content is None:
            return None
        return {"path": doc_rel, "content": content}
