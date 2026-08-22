# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib.metadata
import inspect
import json
import logging
import os
import platform
import sys
import tempfile
import threading
import time
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Any, Dict, List

from src.hephaestus.chains.loader import load_chain_factory
from src.hephaestus.datasets.jsonl_loader import (
    LoadedCasesWithIdentity,
    load_cases_with_identity,
)
from src.hephaestus.evaluation_assets.provenance import collect_git_evidence
from src.hephaestus.evaluation_assets.trust_tiers import CURRENT_TRUST_TIERS
from src.hephaestus.mcp.manager import MCPServerManager
from src.hephaestus.mcp.types import MCPConfig, MCPServerConfig
from src.hephaestus.providers import (
    build_provider_client,
    resolve_provider_settings,
    safe_provider_facts,
)
from src.hephaestus.providers.base import ProviderClient
from src.hephaestus.runs.bundle import RunBundleWriter
from src.hephaestus.runs.errors import sanitize_execution_error
from src.hephaestus.runs.identity import (
    ALLOWED_VARIANT_DIMENSIONS,
    RunIdentity,
    build_run_identity,
    fingerprint_value,
)
from src.hephaestus.runs.io_utils import render_summary
from src.hephaestus.runs.mcp_facts import safe_mcp_facts
from src.hephaestus.runs.progress import ProgressTracker
from src.hephaestus.runs.run_id import generate_run_id, validate_run_id
from src.hephaestus.scoring.runtime import (
    extract_score_diagnostics,
    load_tenant_scorer,
    validate_score_payload,
)
from src.hephaestus.scoring.scorer import Scorer
from src.hephaestus.types import ChainConfig, EvalCase, EvalCaseResult, EvalConfig

logger = logging.getLogger(__name__)

ALLOWED_PROVIDERS = {"baseten", "base10", "sagemaker", "openai"}

_RUNTIME_SOURCE_GLOBS = (
    "src/hephaestus/chains/*.py",
    "src/hephaestus/engine/*.py",
    "src/hephaestus/mcp/*.py",
    "src/hephaestus/providers/*.py",
    "src/hephaestus/runs/*.py",
    "src/hephaestus/scoring/*.py",
)
_RUNTIME_SOURCE_FILES = (
    "pyproject.toml",
    "src/hephaestus/analysis/step_attribution.py",
    "src/hephaestus/artifact_io.py",
    "src/hephaestus/datasets/jsonl_loader.py",
    "src/hephaestus/evaluation_assets/provenance.py",
    "src/hephaestus/evaluation_assets/trust_tiers.py",
    "src/hephaestus/loader.py",
    "src/hephaestus/local_authority_io.py",
    "src/hephaestus/types.py",
)
_RUNTIME_PACKAGES = (
    "hephaestus",
    "httpx",
    "langgraph",
    "mcp",
    "openai",
    "pydantic",
    "requests",
)
_OPENAI_TEXT_ONLY_MODEL_PREFIXES = ("o1", "o3", "o4", "gpt-5", "gpt5")


@dataclasses.dataclass(frozen=True)
class _RuntimeInputSnapshot:
    logical_config: EvalConfig
    execution_config: EvalConfig
    execution_cases: tuple[EvalCase, ...]
    evaluation_provenance: tuple[dict[str, str], ...]
    prompt_artifacts: tuple[dict[str, Any], ...]
    skill_artifacts: tuple[dict[str, Any], ...]
    chain_source_artifacts: tuple[dict[str, Any], ...]
    scorer_source_artifacts: tuple[dict[str, Any], ...]
    split_fingerprint: str
    runtime_facts: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class _PythonPackageAlias:
    namespace_root: Path
    top_level_name: str
    owner_prefix: str


@dataclasses.dataclass(frozen=True)
class _CapturedPythonScope:
    source_root: Path
    recursive: bool
    namespace_root: Path
    member_fingerprints: tuple[tuple[Path, str], ...]
    mirrored_entries: Mapping[Path, Path]


@dataclasses.dataclass
class _PythonSnapshotCache:
    entries: dict[Path, _CapturedPythonScope] = dataclasses.field(
        default_factory=dict
    )
    scopes: list[_CapturedPythonScope] = dataclasses.field(default_factory=list)
    aliases: dict[str, _PythonPackageAlias] = dataclasses.field(
        default_factory=dict
    )


_PYTHON_SNAPSHOT_IMPORT_LOCK = threading.RLock()
_MISSING_MODULE_PATH = object()


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _sha256_file(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _read_executable_artifact(
    path: Path,
    *,
    label: str,
    required: bool = True,
) -> bytes | None:
    if path.is_symlink():
        raise ValueError(f"{label} executable artifact must not be a symlink: {path}")
    if not path.exists():
        if required:
            raise FileNotFoundError(f"{label} executable artifact not found: {path}")
        return None
    if not path.is_file():
        raise ValueError(f"{label} executable artifact must be a regular file: {path}")
    return path.read_bytes()


def _python_package_root(path: Path, *, label: str) -> Path | None:
    package_root: Path | None = None
    cursor = path.parent
    while True:
        package_init = cursor / "__init__.py"
        if package_init.is_symlink():
            raise ValueError(
                f"{label} package executable artifact must not be a symlink: "
                f"{package_init}"
            )
        if not package_init.exists():
            break
        if not package_init.is_file():
            raise ValueError(
                f"{label} package executable artifact must be a regular file: "
                f"{package_init}"
            )
        package_root = cursor
        cursor = cursor.parent
    return package_root


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _require_no_symlink_components(
    path: Path,
    *,
    boundary: Path,
    label: str,
) -> None:
    if not _is_within(path, boundary):
        raise ValueError(f"{label} executable artifact is outside its package scope")
    cursor = boundary
    components = (boundary,)
    relative = path.relative_to(boundary)
    for part in relative.parts:
        cursor = cursor / part
        components += (cursor,)
    for component in components:
        if component.is_symlink():
            raise ValueError(
                f"{label} executable artifact ancestor must not be a symlink: "
                f"{component}"
            )


def _validate_tenant_scoped_path(
    path: Path,
    *,
    tenant_id: str,
    repository_root: Path,
    label: str,
) -> Path:
    lexical_path = _lexical_absolute(path)
    tenants_root = _lexical_absolute(repository_root / "tenants")
    if not _is_within(lexical_path, tenants_root):
        return lexical_path

    tenant_root = _lexical_absolute(tenants_root / tenant_id)
    if tenant_root.parent != tenants_root:
        raise ValueError("tenant_id must identify one tenant directory")
    scoped_label = f"{label} tenant-scoped"
    if not _is_within(lexical_path, tenant_root):
        raise ValueError(
            f"{scoped_label} artifact crosses tenant boundary: {path}"
        )
    _require_no_symlink_components(
        lexical_path,
        boundary=tenants_root,
        label=scoped_label,
    )
    resolved_tenant_root = tenant_root.resolve(strict=False)
    resolved_path = lexical_path.resolve(strict=False)
    if not _is_within(resolved_path, resolved_tenant_root):
        raise ValueError(
            f"{scoped_label} artifact resolves outside tenant boundary: {path}"
        )
    return lexical_path


def _python_scope_plan(
    path: Path,
    *,
    tenant_id: str,
    repository_root: Path,
    label: str,
) -> tuple[Path, bool, Path, tuple[Path, ...], _PythonPackageAlias | None]:
    tenants_root = repository_root / "tenants"
    tenant_root = tenants_root / tenant_id
    if _is_within(path, tenants_root):
        if not _is_within(path, tenant_root):
            raise ValueError(
                f"{label} executable artifact crosses tenant boundary: {path}"
            )
        _require_no_symlink_components(
            path,
            boundary=tenants_root,
            label=label,
        )
        resolved_tenant_root = tenant_root.resolve(strict=False)
        resolved_path = path.resolve(strict=False)
        if not _is_within(resolved_path, resolved_tenant_root):
            raise ValueError(
                f"{label} executable artifact resolves outside tenant boundary: "
                f"{path}"
            )
        ancestor_initializers = tuple(
            candidate
            for candidate in (tenants_root / "__init__.py",)
            if candidate.exists() or candidate.is_symlink()
        )
        return (
            tenant_root,
            True,
            repository_root,
            ancestor_initializers,
            _PythonPackageAlias(
                namespace_root=Path(),
                top_level_name="tenants",
                owner_prefix=f"tenants.{tenant_id}",
            ),
        )

    package_root = _python_package_root(path, label=label)
    if package_root is None:
        return path, False, path.parent, (), None
    _require_no_symlink_components(
        path,
        boundary=package_root,
        label=label,
    )
    if not _is_within(path.resolve(strict=False), package_root.resolve(strict=False)):
        raise ValueError(
            f"{label} executable artifact resolves outside package boundary: {path}"
        )
    return (
        package_root,
        True,
        package_root.parent,
        (),
        _PythonPackageAlias(
            namespace_root=Path(),
            top_level_name=package_root.name,
            owner_prefix=package_root.name,
        ),
    )


def _render_python_source_artifacts(
    scope: _CapturedPythonScope,
    *,
    raw_path: str,
) -> tuple[dict[str, Any], ...]:
    absolute_labels = Path(raw_path).is_absolute()
    working_directory = _lexical_absolute(Path.cwd())
    return tuple(
        {
            "path": (
                str(member)
                if absolute_labels
                else os.path.relpath(member, working_directory)
            ),
            "sha256": fingerprint,
        }
        for member, fingerprint in scope.member_fingerprints
    )


def _snapshot_python_entry(
    raw_path: str,
    snapshot_root: Path,
    *,
    label: str,
    required: bool,
    tenant_id: str,
    repository_root: Path,
    cache: _PythonSnapshotCache,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    path = _lexical_absolute(Path(raw_path))
    cached_scope = cache.entries.get(path)
    if cached_scope is not None:
        return (
            str(cached_scope.mirrored_entries[path]),
            _render_python_source_artifacts(cached_scope, raw_path=raw_path),
        )
    for captured_scope in cache.scopes:
        if captured_scope.recursive and _is_within(path, captured_scope.source_root):
            if required:
                raise FileNotFoundError(
                    f"{label} executable artifact not found in frozen Python scope: "
                    f"{Path(raw_path)}"
                )
            return raw_path, ()

    source_root, recursive, anchor, ancestor_initializers, alias = _python_scope_plan(
        path,
        tenant_id=tenant_id,
        repository_root=repository_root,
        label=label,
    )
    entry_content = _read_executable_artifact(
        path,
        label=label,
        required=required,
    )
    if entry_content is None:
        return raw_path, ()

    members = list(source_root.rglob("*.py")) if recursive else [path]
    members.extend(ancestor_initializers)
    if path not in members:
        members.append(path)
    members = sorted(set(members), key=lambda item: item.as_posix())

    anchor_digest = hashlib.sha256(os.fsencode(anchor)).hexdigest()
    namespace_root = snapshot_root / f"anchor-{anchor_digest}"
    member_fingerprints: list[tuple[Path, str]] = []
    mirrored_entries: dict[Path, Path] = {}
    for member in members:
        content = (
            entry_content
            if member == path
            else _read_executable_artifact(
                member,
                label=f"{label} package source",
            )
        )
        assert content is not None
        target = namespace_root / member.relative_to(anchor)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            captured_content = _read_executable_artifact(
                target,
                label="captured Python source",
            )
            if captured_content != content:
                raise ValueError(
                    f"conflicting Python sources share snapshot target: {member}"
                )
        else:
            target.write_bytes(content)
        fingerprint = _sha256_bytes(content)
        member_fingerprints.append((member, fingerprint))
        mirrored_entries[member] = target

    execution_entry = mirrored_entries.get(path)
    if execution_entry is None:
        raise ValueError(f"{label} package snapshot omitted its entry module: {path}")
    scope = _CapturedPythonScope(
        source_root=source_root,
        recursive=recursive,
        namespace_root=namespace_root,
        member_fingerprints=tuple(member_fingerprints),
        mirrored_entries=mirrored_entries,
    )
    cache.scopes.append(scope)
    cache.entries.update({member: scope for member in mirrored_entries})
    if alias is not None:
        captured_alias = dataclasses.replace(alias, namespace_root=namespace_root)
        existing_alias = cache.aliases.get(alias.owner_prefix)
        if existing_alias is not None and existing_alias != captured_alias:
            raise ValueError(
                "Python package alias resolves to multiple snapshot namespaces: "
                f"{alias.owner_prefix}"
            )
        cache.aliases[alias.owner_prefix] = captured_alias
    return (
        str(execution_entry),
        _render_python_source_artifacts(scope, raw_path=raw_path),
    )


def _module_matches_prefix(module_name: str, prefix: str) -> bool:
    return module_name == prefix or module_name.startswith(prefix + ".")


@contextmanager
def _activate_python_snapshot(cache: _PythonSnapshotCache) -> Iterator[None]:
    aliases = tuple(sorted(cache.aliases.values(), key=lambda item: item.owner_prefix))
    if not aliases:
        yield
        return

    with _PYTHON_SNAPSHOT_IMPORT_LOCK:
        original_sys_path = list(sys.path)
        saved_modules = {
            name: module
            for name, module in list(sys.modules.items())
            if any(
                _module_matches_prefix(name, alias.owner_prefix)
                for alias in aliases
            )
        }
        for name in saved_modules:
            sys.modules.pop(name, None)

        saved_top_paths: dict[str, object] = {}
        absent_nested_tops: set[str] = set()
        for alias in aliases:
            if alias.owner_prefix == alias.top_level_name:
                continue
            top_module = sys.modules.get(alias.top_level_name)
            if top_module is None:
                absent_nested_tops.add(alias.top_level_name)
                continue
            if alias.top_level_name not in saved_top_paths:
                saved_top_paths[alias.top_level_name] = getattr(
                    top_module,
                    "__path__",
                    _MISSING_MODULE_PATH,
                )
            top_module.__path__ = [
                str(alias.namespace_root / alias.top_level_name)
            ]

        namespace_roots = list(
            dict.fromkeys(str(alias.namespace_root) for alias in aliases)
        )
        sys.path[:0] = namespace_roots
        try:
            yield
        finally:
            for name in list(sys.modules):
                if any(
                    _module_matches_prefix(name, alias.owner_prefix)
                    for alias in aliases
                ):
                    sys.modules.pop(name, None)
            for top_level_name in absent_nested_tops:
                sys.modules.pop(top_level_name, None)
            for top_level_name, original_path in saved_top_paths.items():
                top_module = sys.modules.get(top_level_name)
                if top_module is None:
                    continue
                if original_path is _MISSING_MODULE_PATH:
                    try:
                        del top_module.__path__
                    except AttributeError:
                        pass
                else:
                    top_module.__path__ = original_path
            sys.modules.update(saved_modules)
            sys.path[:] = original_sys_path


def _snapshot_declared_artifact(
    raw_path: str,
    target: Path,
    *,
    label: str,
    tenant_id: str,
    repository_root: Path,
) -> tuple[str, str]:
    path = _validate_tenant_scoped_path(
        Path(raw_path),
        tenant_id=tenant_id,
        repository_root=repository_root,
        label=label,
    )
    content = _read_executable_artifact(path, label=label)
    assert content is not None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return str(target), _sha256_bytes(content)


def _artifact_inventory(paths: Mapping[str, str]) -> list[dict[str, Any]]:
    inventory = []
    for name, raw_path in sorted(paths.items()):
        path = Path(raw_path)
        inventory.append(
            {
                "name": name,
                "path": raw_path,
                "sha256": _sha256_file(path),
            }
        )
    return inventory


def _skill_inventory(paths: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {"ordinal": ordinal, "path": raw_path, "sha256": _sha256_file(Path(raw_path))}
        for ordinal, raw_path in enumerate(paths)
    ]


def _runtime_facts() -> dict[str, Any]:
    repository_root = _repository_root()
    source_paths = {
        path
        for pattern in _RUNTIME_SOURCE_GLOBS
        for path in repository_root.glob(pattern)
    }
    source_paths.update(repository_root / path for path in _RUNTIME_SOURCE_FILES)
    members = []
    for path in sorted(source_paths, key=lambda item: item.as_posix()):
        content = _read_executable_artifact(path, label="runtime source")
        assert content is not None
        members.append(
            {
                "path": path.relative_to(repository_root).as_posix(),
                "sha256": _sha256_bytes(content),
            }
        )
    packages: dict[str, Any] = {}
    for package in _RUNTIME_PACKAGES:
        try:
            packages[package] = {
                "status": "available",
                "version": importlib.metadata.version(package),
            }
        except importlib.metadata.PackageNotFoundError:
            packages[package] = {"status": "unavailable"}
    return {
        "source_members": members,
        "source_fingerprint": fingerprint_value(members),
        "git": collect_git_evidence(repository_root),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "packages": packages,
    }


def _split_membership_fingerprint(
    loaded: LoadedCasesWithIdentity,
    dataset_path: str,
) -> str:
    memberships = []
    for case in loaded.cases:
        split_value = None
        for key in ("split", "split_name", "evaluation_split"):
            candidate = case.metadata.get(key)
            if isinstance(candidate, str) and candidate:
                split_value = candidate
                break
        memberships.append(
            {
                "case_id": case.case_id,
                "split": split_value or "dataset_file_membership",
            }
        )
    return fingerprint_value(
        {"dataset_path": dataset_path, "memberships": memberships}
    )


def _safe_evaluation_provenance(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    trust_tier = value.get("trust_tier")
    if not isinstance(trust_tier, str) or trust_tier not in CURRENT_TRUST_TIERS:
        return {}
    return {"trust_tier": trust_tier}


@contextmanager
def _snapshot_runtime_inputs(
    config: EvalConfig,
    loaded: LoadedCasesWithIdentity,
) -> Iterator[_RuntimeInputSnapshot]:
    logical_config = copy.deepcopy(config)
    execution_config = copy.deepcopy(config)
    execution_cases = list(copy.deepcopy(loaded.cases))
    evaluation_provenance = tuple(
        _safe_evaluation_provenance(case.metadata) for case in execution_cases
    )

    with tempfile.TemporaryDirectory(prefix="fapo-eval-snapshot-") as temporary:
        snapshot_root = Path(temporary)
        repository_root = _lexical_absolute(_repository_root())
        python_cache = _PythonSnapshotCache()
        execution_chain_path, chain_sources = _snapshot_python_entry(
            logical_config.chain.path,
            snapshot_root / "python",
            label="chain",
            required=True,
            tenant_id=logical_config.tenant_id,
            repository_root=repository_root,
            cache=python_cache,
        )
        execution_config.chain.path = execution_chain_path

        scorer_sources: tuple[dict[str, Any], ...] = ()
        logical_scorer = logical_config.scoring_profile.get("scorer")
        execution_scorer = execution_config.scoring_profile.get("scorer")
        if isinstance(logical_scorer, Mapping) and isinstance(
            execution_scorer, Mapping
        ):
            scorer_path = logical_scorer.get("module_path")
            if isinstance(scorer_path, str) and scorer_path:
                execution_scorer_path, scorer_sources = _snapshot_python_entry(
                    scorer_path,
                    snapshot_root / "python",
                    label="scorer",
                    required=True,
                    tenant_id=logical_config.tenant_id,
                    repository_root=repository_root,
                    cache=python_cache,
                )
                rewritten_scorer = dict(execution_scorer)
                rewritten_scorer["module_path"] = execution_scorer_path
                execution_config.scoring_profile["scorer"] = rewritten_scorer

        prompt_artifacts: list[dict[str, Any]] = []
        logical_prompts = logical_config.chain.config.get("prompt_paths", {})
        execution_prompts = execution_config.chain.config.get("prompt_paths", {})
        if isinstance(logical_prompts, Mapping) and isinstance(
            execution_prompts, Mapping
        ):
            rewritten_prompts = dict(execution_prompts)
            for ordinal, (name, raw_path) in enumerate(
                sorted(logical_prompts.items(), key=lambda item: str(item[0]))
            ):
                logical_path = str(raw_path)
                suffix = Path(logical_path).suffix or ".artifact"
                execution_path, fingerprint = _snapshot_declared_artifact(
                    logical_path,
                    snapshot_root / "prompts" / f"{ordinal}{suffix}",
                    label="prompt",
                    tenant_id=logical_config.tenant_id,
                    repository_root=repository_root,
                )
                rewritten_prompts[name] = execution_path
                prompt_artifacts.append(
                    {
                        "name": str(name),
                        "path": logical_path,
                        "sha256": fingerprint,
                    }
                )
            execution_config.chain.config["prompt_paths"] = rewritten_prompts

        skill_artifacts: list[dict[str, Any]] = []
        logical_skills = logical_config.chain.config.get("skill_paths", []) or []
        if isinstance(logical_skills, Sequence) and not isinstance(
            logical_skills, (str, bytes, bytearray)
        ):
            rewritten_skills = []
            for ordinal, raw_path in enumerate(logical_skills):
                logical_path = str(raw_path)
                logical_skill_path = Path(logical_path)
                display_name = logical_skill_path.parent.name
                if not display_name:
                    display_name = logical_skill_path.stem
                if display_name in {".", ".."}:
                    raise ValueError(
                        "skill executable artifact has an unsafe display identity: "
                        f"{logical_path}"
                    )
                filename = logical_skill_path.name
                execution_path, fingerprint = _snapshot_declared_artifact(
                    logical_path,
                    snapshot_root
                    / "skills"
                    / f"{ordinal:08d}"
                    / display_name
                    / filename,
                    label="skill",
                    tenant_id=logical_config.tenant_id,
                    repository_root=repository_root,
                )
                rewritten_skills.append(execution_path)
                skill_artifacts.append(
                    {
                        "ordinal": ordinal,
                        "path": logical_path,
                        "sha256": fingerprint,
                    }
                )
            execution_config.chain.config["skill_paths"] = rewritten_skills

        for ordinal, case in enumerate(execution_cases):
            logical_path = case.prompt_template_path
            if not logical_path:
                continue
            suffix = Path(logical_path).suffix or ".artifact"
            execution_path, fingerprint = _snapshot_declared_artifact(
                logical_path,
                snapshot_root / "case-prompts" / f"{ordinal}{suffix}",
                label="case prompt",
                tenant_id=logical_config.tenant_id,
                repository_root=repository_root,
            )
            case.prompt_template_path = execution_path
            prompt_artifacts.append(
                {
                    "name": f"case:{case.case_id}",
                    "path": logical_path,
                    "sha256": fingerprint,
                }
            )

        input_snapshot = _RuntimeInputSnapshot(
            logical_config=logical_config,
            execution_config=execution_config,
            execution_cases=tuple(execution_cases),
            evaluation_provenance=evaluation_provenance,
            prompt_artifacts=tuple(prompt_artifacts),
            skill_artifacts=tuple(skill_artifacts),
            chain_source_artifacts=chain_sources,
            scorer_source_artifacts=scorer_sources,
            split_fingerprint=_split_membership_fingerprint(
                loaded,
                logical_config.dataset_path,
            ),
            runtime_facts=_runtime_facts(),
        )
        with _activate_python_snapshot(python_cache):
            yield input_snapshot


def _resolved_provider_supports_tools(
    provider_facts: Mapping[str, Any],
    tool_names: Sequence[str],
) -> bool:
    if not tool_names or provider_facts.get("provider") != "openai":
        return False
    model = provider_facts.get("model")
    if not isinstance(model, str) or not model:
        return False
    model_lower = model.lower()
    return not any(
        model_lower.startswith(prefix)
        for prefix in _OPENAI_TEXT_ONLY_MODEL_PREFIXES
    )


def _build_identity_and_config(
    config: EvalConfig,
    loaded: LoadedCasesWithIdentity,
    *,
    run_id: str,
    resolved_provider_settings: Mapping[str, object],
    provider_facts: Mapping[str, Any],
    mcp_facts: Mapping[str, Any],
    input_snapshot: _RuntimeInputSnapshot | None = None,
) -> tuple[RunIdentity, dict[str, Any]]:
    if input_snapshot is None:
        prompt_paths_raw = config.chain.config.get("prompt_paths", {})
        prompt_paths = (
            {str(key): str(value) for key, value in prompt_paths_raw.items()}
            if isinstance(prompt_paths_raw, Mapping)
            else {}
        )
        skill_paths_raw = config.chain.config.get("skill_paths", []) or []
        skill_paths = (
            [str(item) for item in skill_paths_raw]
            if isinstance(skill_paths_raw, Sequence)
            and not isinstance(skill_paths_raw, (str, bytes, bytearray))
            else []
        )
        prompts = _artifact_inventory(prompt_paths)
        skills = _skill_inventory(skill_paths)
        runtime = _runtime_facts()
        chain_source = _sha256_file(Path(config.chain.path))
        chain_sources = (
            [{"path": config.chain.path, "sha256": chain_source}]
            if chain_source is not None
            else []
        )
        split_fingerprint = _split_membership_fingerprint(
            loaded,
            config.dataset_path,
        )
    else:
        prompts = [dict(item) for item in input_snapshot.prompt_artifacts]
        skills = [dict(item) for item in input_snapshot.skill_artifacts]
        runtime = copy.deepcopy(input_snapshot.runtime_facts)
        chain_sources = [
            dict(item) for item in input_snapshot.chain_source_artifacts
        ]
        split_fingerprint = input_snapshot.split_fingerprint

    scorer_raw = config.scoring_profile.get("scorer", {})
    scorer_path = (
        str(scorer_raw.get("module_path", ""))
        if isinstance(scorer_raw, Mapping)
        else ""
    )
    scorer_class = (
        str(scorer_raw.get("class_name", "Scorer"))
        if isinstance(scorer_raw, Mapping)
        else "Scorer"
    )
    if input_snapshot is None:
        scorer_source = _sha256_file(Path(scorer_path)) if scorer_path else None
        scorer_sources = (
            [{"path": scorer_path, "sha256": scorer_source}]
            if scorer_source is not None
            else []
        )
    else:
        scorer_sources = [
            dict(item) for item in input_snapshot.scorer_source_artifacts
        ]
    scorer_fingerprint = (
        fingerprint_value(
            {
                "module_path": scorer_path,
                "class_name": scorer_class,
                "source_artifacts": scorer_sources,
            }
        )
        if scorer_sources
        else None
    )
    metric_fingerprint = fingerprint_value(config.scoring_profile)

    parameter_config = {
        key: value
        for key, value in config.chain.config.items()
        if key not in {"prompt_paths", "skill_paths"}
    }
    model_fact = provider_facts.get("model")
    resolved_model = model_fact if isinstance(model_fact, str) else None
    sampling = provider_facts.get("sampling")
    resolved_sampling = dict(sampling) if isinstance(sampling, Mapping) else None
    server_names = sorted(
        str(item.get("name"))
        for item in mcp_facts.get("servers", [])
        if isinstance(item, Mapping) and item.get("name")
    )
    tool_names = sorted(
        str(item.get("name"))
        for item in mcp_facts.get("discovered_capabilities", [])
        if isinstance(item, Mapping) and item.get("name")
    )
    resolved_mcp_capabilities = {
        "server_names": server_names,
        "tool_names": tool_names,
        "supports_tool_calling": _resolved_provider_supports_tools(
            provider_facts,
            tool_names,
        ),
    }
    chain_structure = {
        "module_path": config.chain.path,
        "function": config.chain.fn,
        "source_artifacts": chain_sources,
        "runtime": runtime,
    }
    provider_dimension_facts = {
        key: copy.deepcopy(provider_facts.get(key))
        for key in (
            "provider",
            "limits",
            "credential_env_names",
            "endpoint",
            "provider_revision",
            "api_revision",
            "provider_request_id",
            "provider_response_id",
        )
    }
    model_dimension_facts = {
        "model": copy.deepcopy(model_fact),
        "model_revision": copy.deepcopy(provider_facts.get("model_revision")),
    }
    dimensions = {
        "prompts": fingerprint_value(prompts),
        "skills": fingerprint_value(skills),
        "chain_parameters": fingerprint_value(parameter_config),
        "chain_structure": fingerprint_value(chain_structure),
        "provider": fingerprint_value(provider_dimension_facts),
        "model": (
            fingerprint_value(model_dimension_facts)
            if resolved_model is not None
            else None
        ),
        "sampling": fingerprint_value(sampling),
        "mcp_capabilities": fingerprint_value(mcp_facts),
    }
    identity = build_run_identity(
        ordered_case_ids=loaded.ordered_case_ids,
        dataset_path=config.dataset_path,
        dataset_fingerprint="sha256:" + loaded.raw_sha256,
        split_fingerprint=split_fingerprint,
        scorer_fingerprint=scorer_fingerprint,
        metric_fingerprint=metric_fingerprint,
        dimension_fingerprints=dimensions,
        variant_dimensions=config.comparison_variant_dimensions,
        resolved_provider=str(provider_facts["provider"]),
        resolved_model=resolved_model,
        resolved_sampling=resolved_sampling,
        resolved_mcp_capabilities=resolved_mcp_capabilities,
    )
    safe_config = {
        "schema_version": "fapo-run-config-v2",
        "run_id": run_id,
        "tenant_id": config.tenant_id,
        "provider": provider_facts["provider"],
        "provider_settings": {
            "model": resolved_model,
            **(resolved_sampling or {}),
            **dict(provider_facts.get("limits", {})),
        },
        "provider_facts": dict(provider_facts),
        "dataset_path": config.dataset_path,
        "dataset_sha256": "sha256:" + loaded.raw_sha256,
        "scoring_profile": {
            "scorer_module_path": scorer_path,
            "scorer_class_name": scorer_class,
            "scorer_source_artifacts": scorer_sources,
            "scorer_fingerprint": scorer_fingerprint
            or {"status": "unavailable"},
            "metric_fingerprint": metric_fingerprint,
        },
        "max_workers": config.max_workers,
        "chain": {
            "path": config.chain.path,
            "fn": config.chain.fn,
            "source_artifacts": chain_sources,
            "prompt_artifacts": prompts,
            "skill_artifacts": skills,
            "parameter_fingerprint": dimensions["chain_parameters"],
            "structure_fingerprint": dimensions["chain_structure"],
        },
        "mcp": dict(mcp_facts),
        "comparison": {
            "variant_dimensions": list(config.comparison_variant_dimensions),
        },
        "runtime": runtime,
        "resolved_provider_settings_fingerprint": fingerprint_value(
            {
                "provider": provider_facts.get("provider"),
                "model": model_fact,
                "sampling": sampling,
                "limits": provider_facts.get("limits"),
                "endpoint": provider_facts.get("endpoint"),
            }
        ),
    }
    return identity, safe_config


def load_eval_config(path: Path) -> EvalConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))

    if "chain" not in raw:
        raise ValueError("Config must specify 'chain'")

    chain_raw = raw["chain"]
    chain_path = chain_raw.get("path", "")
    if not chain_path:
        raise ValueError("Config missing chain.path")
    chain_config = ChainConfig(
        path=str(chain_path),
        fn=str(chain_raw.get("fn", "build_chain")),
        config=dict(chain_raw.get("config", {})),
    )

    comparison_raw = raw.get("comparison")
    if comparison_raw is None:
        variant_dimensions = []
        if chain_config.config.get("prompt_paths"):
            variant_dimensions.append("prompts")
        if chain_config.config.get("skill_paths"):
            variant_dimensions.append("skills")
    else:
        if not isinstance(comparison_raw, dict):
            raise ValueError("comparison must be an object")
        dimensions_raw = comparison_raw.get("variant_dimensions")
        if not isinstance(dimensions_raw, list) or any(
            not isinstance(item, str) for item in dimensions_raw
        ):
            raise ValueError("comparison.variant_dimensions must be an array of strings")
        if len(dimensions_raw) != len(set(dimensions_raw)):
            raise ValueError("comparison.variant_dimensions must not contain duplicates")
        unsupported = sorted(
            set(dimensions_raw) - set(ALLOWED_VARIANT_DIMENSIONS)
        )
        if unsupported:
            raise ValueError(
                "comparison.variant_dimensions contains unsupported dimensions: "
                f"{unsupported}"
            )
        requested = set(dimensions_raw)
        variant_dimensions = [
            item for item in ALLOWED_VARIANT_DIMENSIONS if item in requested
        ]

    dataset = raw.get("dataset", {})
    dataset_path = dataset.get("path")
    if not dataset_path:
        raise ValueError("Config missing dataset.path")

    provider = str(raw.get("provider", "")).strip().lower()
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(f"Unsupported provider '{provider}'. Supported: {sorted(ALLOWED_PROVIDERS)}")

    max_workers = raw.get("max_workers")
    if max_workers is not None:
        if not isinstance(max_workers, int) or isinstance(max_workers, bool) or max_workers < 1:
            raise ValueError(f"max_workers must be a positive integer, got {max_workers!r}")

    run_id = raw.get("run_id")
    if run_id is not None:
        run_id = str(run_id)
        validate_run_id(run_id)

    # Parse MCP configuration if present
    mcp_config = None
    if "mcp" in raw:
        mcp_raw = raw["mcp"]
        servers = []
        for srv in mcp_raw.get("servers", []):
            servers.append(
                MCPServerConfig(
                    name=srv["name"],
                    command=srv["command"],
                    args=srv.get("args", []),
                    env=srv.get("env", {}),
                    enabled=srv.get("enabled", True),
                    timeout_seconds=srv.get("timeout_seconds", 30),
                )
            )

        tool_exec = mcp_raw.get("tool_execution", {})
        mcp_config = MCPConfig(
            servers=servers,
            max_iterations=tool_exec.get("max_iterations", 10),
            max_tool_calls_per_iteration=tool_exec.get("max_tool_calls_per_iteration", 5),
            timeout_seconds=tool_exec.get("timeout_seconds", 30),
        )

    return EvalConfig(
        tenant_id=str(raw["tenant_id"]),
        provider=provider,
        provider_settings=dict(raw.get("provider_settings", {})),
        dataset_path=str(dataset_path),
        scoring_profile=dict(raw.get("scoring_profile", {})),
        output_dir=str(raw["output_dir"]),
        chain=chain_config,
        max_workers=max_workers,
        run_id=run_id,
        mcp=mcp_config,
        comparison_variant_dimensions=variant_dimensions,
    )


def _validate_eval_paths(config: EvalConfig) -> None:
    """Check that dataset, chain module, and prompt files exist before running."""
    repository_root = _repository_root()
    dataset = _validate_tenant_scoped_path(
        Path(config.dataset_path),
        tenant_id=config.tenant_id,
        repository_root=repository_root,
        label="dataset",
    )
    if not dataset.exists():
        raise FileNotFoundError(
            f"Dataset not found: {dataset}. "
            "Run `python -m hephaestus.cli customer-data pull` to fetch datasets."
        )

    chain_path = _validate_tenant_scoped_path(
        Path(config.chain.path),
        tenant_id=config.tenant_id,
        repository_root=repository_root,
        label="chain",
    )
    if not chain_path.exists():
        raise FileNotFoundError(
            f"Chain module not found: {chain_path}. Check chain.path in your eval config."
        )

    for step_name, prompt_path_str in config.chain.config.get("prompt_paths", {}).items():
        prompt_path = _validate_tenant_scoped_path(
            Path(prompt_path_str),
            tenant_id=config.tenant_id,
            repository_root=repository_root,
            label="prompt",
        )
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found for step '{step_name}': {prompt_path}. "
                "Check chain.config.prompt_paths in your eval config."
            )

    for skill_path_str in config.chain.config.get("skill_paths", []) or []:
        skill_path = _validate_tenant_scoped_path(
            Path(skill_path_str),
            tenant_id=config.tenant_id,
            repository_root=repository_root,
            label="skill",
        )
        if not skill_path.exists():
            raise FileNotFoundError(
                f"Skill file not found: {skill_path}. "
                "Check chain.config.skill_paths in your eval config."
            )

    # optimization_target selects which textual artifacts the optimization agent
    # iterates on. "skill"/"both" only make sense for agentic chains (skills tell
    # the agent how to wield its tools), so require an MCP section for those.
    target = config.chain.config.get("optimization_target", "both")
    if target not in ("prompt", "skill", "both"):
        raise ValueError(
            f"Invalid chain.config.optimization_target: {target!r}. "
            "Expected one of: 'prompt', 'skill', 'both'."
        )
    if target in ("skill", "both") and config.chain.config.get("skill_paths"):
        has_mcp = bool(config.mcp and getattr(config.mcp, "servers", None))
        if not has_mcp:
            raise ValueError(
                "chain.config.optimization_target includes skills but no MCP "
                "servers are configured. Skill optimization is only supported "
                "for agentic (MCP-enabled) chains. Set optimization_target to "
                "'prompt' or add an mcp section."
            )


def _ensure_chain(config: EvalConfig, provider: ProviderClient, mcp_manager=None) -> Any:
    """Load a chain from the eval config.

    Args:
        config: Evaluation configuration
        provider: LLM provider client
        mcp_manager: Optional MCP server manager for agentic workflows

    Returns:
        Compiled LangGraph chain
    """
    factory = load_chain_factory(config.chain.path, config.chain.fn)

    # Try calling factory with mcp_manager parameter (new signature)
    # Fall back to legacy signature if it doesn't accept mcp_manager
    sig = inspect.signature(factory)
    if "mcp_manager" in sig.parameters:
        return factory(provider, config.chain.config, mcp_manager=mcp_manager)
    else:
        # Legacy chain - no MCP support
        if mcp_manager:
            logger.warning(
                f"Chain {config.chain.path} does not accept mcp_manager parameter. "
                "MCP tools will not be available."
            )
        return factory(provider, config.chain.config)


def _safe_diagnostics(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, Sequence) or isinstance(
        value,
        (bytes, bytearray),
    ):
        return []
    return [item for item in value if isinstance(item, str)]


def _safe_output_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _safe_step_outputs(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {key: item for key, item in value.items() if isinstance(key, str)}


def _safe_tool_call_history(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _evaluate_single_case(
    case: EvalCase,
    chain: Any,
    scorer: Scorer,
    scoring_profile: Dict[str, Any],
    worker_index: int = 0,
    *,
    evaluation_provenance: Mapping[str, Any] | None = None,
) -> EvalCaseResult:
    """Run a single eval case through the chain and scorer.

    Thread-safety: this function is called concurrently when ``max_workers > 1``.
    ``chain`` and ``scorer`` must be safe to invoke from multiple threads
    (no mutable instance state).

    Infrastructure failures become explicit failed results so that remaining
    cases can still run without fabricating a scored empty answer.
    """
    frozen_provenance = _safe_evaluation_provenance(
        case.metadata if evaluation_provenance is None else evaluation_provenance
    )
    initial_state: Dict[str, Any] = {
        "context": copy.deepcopy(case.context),
        "output_text": "",
        "step_outputs": {},
        "diagnostics": [],
        "_worker_index": worker_index,
    }

    step_timings: List[List] = []
    final_state = dict(initial_state)
    chain_set_output_text = False
    tool_call_history = []

    try:
        t0 = time.monotonic()
        for chunk in chain.stream(initial_state):
            elapsed = time.monotonic() - t0
            for node_name in chunk:
                step_timings.append([node_name, round(elapsed, 3)])
                logger.info(
                    "case=%s step=%d node=%s elapsed=%.3fs",
                    case.case_id,
                    len(step_timings),
                    node_name,
                    elapsed,
                )
                if "output_text" in chunk[node_name]:
                    chain_set_output_text = True
                final_state.update(chunk[node_name])
            t0 = time.monotonic()
    except Exception as exc:
        execution_error = sanitize_execution_error(exc, phase="chain")
        logger.error(
            "Chain execution failed for case %s (category=%s).",
            case.case_id,
            execution_error["category"],
        )
        diagnostics = _safe_diagnostics(final_state.get("diagnostics"))
        diagnostics.append(execution_error["summary"])
        tool_call_history = _safe_tool_call_history(
            final_state.get("tool_call_history")
        )
        return EvalCaseResult(
            case_id=case.case_id,
            task_type=case.task_type,
            diagnostics=diagnostics,
            score_breakdown={},
            composite_score=0.0,
            output_text=_safe_output_text(final_state.get("output_text")),
            step_outputs=_safe_step_outputs(final_state.get("step_outputs")),
            step_timings=step_timings,
            tool_call_history=tool_call_history if tool_call_history else None,
            total_tool_calls=len(tool_call_history),
            failed_tool_calls=sum(
                1 for tool_call in tool_call_history if tool_call.get("error")
            ),
            execution_status="failed",
            execution_error=execution_error,
            evaluation_provenance=frozen_provenance,
        )

    if not chain_set_output_text:
        logger.warning(
            "Chain for case %s did not produce 'output_text'; defaulting to empty string.",
            case.case_id,
        )
    output_text = _safe_output_text(final_state.get("output_text"))
    step_outputs = _safe_step_outputs(final_state.get("step_outputs"))

    # Extract tool call history if present (from agentic workflows)
    tool_call_history = _safe_tool_call_history(
        final_state.get("tool_call_history")
    )
    total_tool_calls = len(tool_call_history)
    failed_tool_calls = sum(1 for tc in tool_call_history if tc.get("error"))

    try:
        # Only pass tool_call_history to scorers that accept it. Legacy scorers
        # override score_pipeline_case with the original signature (no
        # tool_call_history param); passing it would raise TypeError.
        score_kwargs: Dict[str, Any] = {"output_text": output_text}
        sig = inspect.signature(scorer.score_pipeline_case)
        if "tool_call_history" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        ):
            score_kwargs["tool_call_history"] = tool_call_history
        score_payload = scorer.score_pipeline_case(
            case, step_outputs, scoring_profile, **score_kwargs,
        )
        composite_score, score_breakdown = validate_score_payload(score_payload)
        score_diagnostics = extract_score_diagnostics(score_payload)
    except Exception as exc:
        execution_error = sanitize_execution_error(exc, phase="scorer")
        logger.error(
            "Scorer execution failed for case %s (category=%s).",
            case.case_id,
            execution_error["category"],
        )
        diagnostics = _safe_diagnostics(final_state.get("diagnostics"))
        diagnostics.append(execution_error["summary"])
        return EvalCaseResult(
            case_id=case.case_id,
            task_type=case.task_type,
            diagnostics=diagnostics,
            score_breakdown={},
            composite_score=0.0,
            output_text=output_text,
            step_outputs=step_outputs,
            step_timings=step_timings,
            tool_call_history=tool_call_history if tool_call_history else None,
            total_tool_calls=total_tool_calls,
            failed_tool_calls=failed_tool_calls,
            execution_status="failed",
            execution_error=execution_error,
            evaluation_provenance=frozen_provenance,
        )

    # Merge the chain's diagnostics with any free-text notes the scorer emits
    # (e.g. an LLM judge's rationale) so they persist into the case result.
    diagnostics = _safe_diagnostics(final_state.get("diagnostics"))
    diagnostics.extend(score_diagnostics)

    return EvalCaseResult(
        case_id=case.case_id,
        task_type=case.task_type,
        diagnostics=diagnostics,
        score_breakdown=score_breakdown,
        composite_score=composite_score,
        output_text=output_text,
        step_outputs=step_outputs,
        step_timings=step_timings,
        tool_call_history=tool_call_history if tool_call_history else None,
        total_tool_calls=total_tool_calls,
        failed_tool_calls=failed_tool_calls,
        execution_status="succeeded",
        evaluation_provenance=frozen_provenance,
    )


def _evaluate_and_track(
    case: EvalCase,
    chain: Any,
    scorer: Scorer,
    scoring_profile: Dict[str, Any],
    tracker: ProgressTracker,
    worker_index: int = 0,
    *,
    evaluation_provenance: Mapping[str, Any] | None = None,
) -> EvalCaseResult:
    """Run a single case and record progress."""
    tracker.record_start(case.case_id)
    result = _evaluate_single_case(
        case,
        chain,
        scorer,
        scoring_profile,
        worker_index=worker_index,
        evaluation_provenance=evaluation_provenance,
    )
    tracker.record_result(result)
    return result


def run_evaluation(config: EvalConfig) -> List[Dict]:
    logical_config = copy.deepcopy(config)
    _validate_eval_paths(logical_config)
    run_id = logical_config.run_id or generate_run_id(logical_config.tenant_id)

    dataset_path = _validate_tenant_scoped_path(
        Path(logical_config.dataset_path),
        tenant_id=logical_config.tenant_id,
        repository_root=_repository_root(),
        label="dataset",
    )
    loaded_cases = load_cases_with_identity(dataset_path)
    output_dir = Path(logical_config.output_dir)
    writer = RunBundleWriter.reserve(output_dir, run_id=run_id)
    tracker: ProgressTracker | None = ProgressTracker(
        output_dir,
        total_cases=len(loaded_cases.cases),
        run_id=run_id,
        case_ids=loaded_cases.ordered_case_ids,
        progress_sink=writer.write_progress,
    )
    mcp_manager: MCPServerManager | None = None
    try:
        with _snapshot_runtime_inputs(logical_config, loaded_cases) as input_snapshot:
            execution_config = input_snapshot.execution_config
            cases = list(input_snapshot.execution_cases)
            scoring_profile = copy.deepcopy(execution_config.scoring_profile)
            try:
                resolved_provider_settings = copy.deepcopy(
                    resolve_provider_settings(
                        logical_config.provider,
                        copy.deepcopy(logical_config.provider_settings),
                    )
                )
                provider_facts = copy.deepcopy(
                    safe_provider_facts(
                        logical_config.provider,
                        copy.deepcopy(resolved_provider_settings),
                    )
                )
                scorer = load_tenant_scorer(scoring_profile)
                for case in cases:
                    scorer.validate_case(case, scoring_profile)

                discovered_tools: dict[str, Any] | None = None
                if execution_config.mcp:
                    logger.info("Starting MCP servers for agentic workflow support")
                    mcp_manager = MCPServerManager(
                        execution_config.tenant_id,
                        config=copy.deepcopy(execution_config.mcp),
                    )
                    mcp_manager.start_servers()
                    discovered_tools = copy.deepcopy(dict(mcp_manager.tools))

                provider = build_provider_client(
                    execution_config.provider,
                    copy.deepcopy(resolved_provider_settings),
                )
                # Call with the legacy 2-arg form unless an MCP manager is active, so
                # existing callers/overrides of _ensure_chain(config, provider) keep working.
                if mcp_manager is not None:
                    chain = _ensure_chain(
                        execution_config,
                        provider,
                        mcp_manager=mcp_manager,
                    )
                else:
                    chain = _ensure_chain(execution_config, provider)

                max_workers = logical_config.max_workers
                if max_workers is not None and max_workers > 1:
                    evaluate = partial(
                        _evaluate_and_track,
                        chain=chain,
                        scorer=scorer,
                        scoring_profile=scoring_profile,
                        tracker=tracker,
                    )
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_idx = {
                            executor.submit(
                                evaluate,
                                case,
                                worker_index=i % max_workers,
                                evaluation_provenance=(
                                    input_snapshot.evaluation_provenance[i]
                                ),
                            ): i
                            for i, case in enumerate(cases)
                        }
                        results: List[EvalCaseResult] = [None] * len(cases)  # type: ignore[list-item]
                        for future in as_completed(future_to_idx):
                            idx = future_to_idx[future]
                            results[idx] = future.result()
                else:
                    results = [
                        _evaluate_and_track(
                            case,
                            chain,
                            scorer,
                            scoring_profile,
                            tracker,
                            evaluation_provenance=(
                                input_snapshot.evaluation_provenance[index]
                            ),
                        )
                        for index, case in enumerate(cases)
                    ]

                if mcp_manager is not None:
                    manager = mcp_manager
                    mcp_manager = None
                    manager.stop_servers()
                mcp_facts = safe_mcp_facts(
                    logical_config.mcp,
                    discovered_tools,
                )
                identity, run_config = _build_identity_and_config(
                    input_snapshot.logical_config,
                    loaded_cases,
                    run_id=run_id,
                    resolved_provider_settings=resolved_provider_settings,
                    provider_facts=provider_facts,
                    mcp_facts=mcp_facts,
                    input_snapshot=input_snapshot,
                )
                result_dicts = [dataclasses.asdict(r) for r in results]
                summary = render_summary(result_dicts, cases=loaded_cases.cases)
                tracker.mark_completed()
                progress_payload = tracker.snapshot_payload()
                identity_payload = identity.to_dict()
            except (Exception, KeyboardInterrupt, SystemExit):
                if mcp_manager is not None:
                    try:
                        mcp_manager.stop_servers()
                    except BaseException:  # preserve the active failure exactly
                        logger.error(
                            "Could not stop MCP servers after evaluation failure."
                        )
                raise

        writer.publish(
            run_config=run_config,
            run_identity=identity_payload,
            results=result_dicts,
            summary=summary,
            progress=progress_payload,
        )
        return result_dicts
    except (Exception, KeyboardInterrupt, SystemExit):
        if tracker is not None:
            try:
                tracker.mark_failed()
            except BaseException:  # preserve the active failure exactly
                logger.error("Could not persist failed evaluation progress.")
        raise
