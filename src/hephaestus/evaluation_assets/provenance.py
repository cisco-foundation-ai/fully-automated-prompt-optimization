# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Allowlisted provenance identities for evaluation-asset releases."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import selectors
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.artifact_io import atomic_write_jsonl
from src.hephaestus.evaluation_assets.lineage_validation import (
    validate_parent_release_evidence,
    validate_provenance_lineage_identity,
)

SOURCE_FIXED_MEMBERS = (
    "pyproject.toml",
    "src/__init__.py",
    "src/hephaestus/__init__.py",
    "src/hephaestus/artifact_io.py",
    "src/hephaestus/datasets/__init__.py",
    "src/hephaestus/datasets/embedding_providers.py",
    "src/hephaestus/datasets/evaluation_assets.py",
    "src/hephaestus/datasets/intent_assets.py",
    "src/hephaestus/datasets/rubric_providers.py",
    "src/hephaestus/evaluation_assets/__init__.py",
    "src/hephaestus/evaluation_assets/control_jsonl.py",
    "src/hephaestus/evaluation_assets/durability.py",
    "src/hephaestus/evaluation_assets/input_contract.py",
    "src/hephaestus/evaluation_assets/journal_transitions.py",
    "src/hephaestus/evaluation_assets/journal_validation.py",
    "src/hephaestus/evaluation_assets/legacy_validation.py",
    "src/hephaestus/evaluation_assets/lineage_validation.py",
    "src/hephaestus/evaluation_assets/models.py",
    "src/hephaestus/evaluation_assets/pipeline.py",
    "src/hephaestus/evaluation_assets/provenance.py",
    "src/hephaestus/evaluation_assets/publication.py",
    "src/hephaestus/evaluation_assets/service.py",
    "src/hephaestus/evaluation_assets/stage_three_contract.py",
    "src/hephaestus/evaluation_assets/workspace.py",
)

UNAVAILABLE_REASONS = {
    "git_command_unavailable",
    "not_a_git_worktree",
    "package_metadata_unavailable",
    "provider_does_not_expose_field",
    "optional_metadata_protocol_absent",
    "metadata_failed_validation",
    "legacy_checkpoint_predates_provenance",
}
NOT_APPLICABLE_REASONS = {
    "native_asset_has_no_parent",
    "local_deterministic_provider",
    "provider_does_not_use_sampling",
    "stage_has_no_provider_role",
    "stage_made_no_provider_calls",
    "provider_does_not_expose_field",
}

_GIT_OBJECT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_SECRET = re.compile(r"(?i)(?:\bsk-[a-z0-9_-]+|bearer\s+|api[_-]?key)")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

PROVIDER_CALL_SCHEMA_VERSION = "fapo-provider-call-v1"
STAGE_PROVENANCE_SCHEMA_VERSION = "fapo-stage-provenance-v1"
BUILD_PROVENANCE_SCHEMA_VERSION = "fapo-evaluation-build-provenance-v1"
BUILD_IDENTITY_SCHEMA_VERSION = "fapo-evaluation-build-identity-v1"
PROVIDER_STAGE_ROLES = {
    "raw_inputs": (),
    "prepared_inputs": (),
    "rubric_extraction": ("rubric",),
    "intent_clustering": ("embedding",),
    "coverage_decisions": ("embedding",),
    "label_inference": ("rubric",),
    "synthetic_coverage": ("rubric",),
    "dataset_splits": (),
}
PROMPT_REVISIONS = {
    "evidence_extraction": "v1",
    "guideline_synthesis": "v1",
    "label_inference": "v1",
    "synthetic_coverage": "v1",
}


def unavailable(reason: str) -> dict[str, str]:
    """Return one exact unavailable provenance marker."""
    if reason not in UNAVAILABLE_REASONS:
        raise ValueError(f"Unsupported unavailable provenance reason: {reason}")
    return {"status": "unavailable", "reason": reason}


def not_applicable(reason: str) -> dict[str, str]:
    """Return one exact not-applicable provenance marker."""
    if reason not in NOT_APPLICABLE_REASONS:
        raise ValueError(f"Unsupported not-applicable provenance reason: {reason}")
    return {"status": "not_applicable", "reason": reason}


def canonical_sha256(payload: Any) -> str:
    """Hash deterministic JSON without accepting non-finite numbers."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def declared_source_dependencies(repository_root: Path) -> tuple[Path, ...]:
    """Return the complete regular, non-symlink local dependency inventory."""
    root = repository_root.resolve()
    candidates = {root / relative for relative in SOURCE_FIXED_MEMBERS}
    declared_studio = {
        path
        for path in candidates
        if path.parent == root / "src/hephaestus/evaluation_assets"
    }
    discovered_studio = set(
        (root / "src/hephaestus/evaluation_assets").glob("*.py")
    )
    if discovered_studio != declared_studio:
        raise ValueError("declared source dependency inventory is incomplete")
    dependencies: list[Path] = []
    for path in sorted(candidates, key=lambda item: item.as_posix()):
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise ValueError("declared source dependency escapes repository") from exc
        if path.is_symlink() or not path.is_file() or not relative.parts:
            raise ValueError(
                f"declared source dependency is missing or unsafe: {relative.as_posix()}"
            )
        dependencies.append(path)
    return tuple(dependencies)


def working_source_identity(repository_root: Path) -> dict[str, Any]:
    """Hash every declared local dependency using repository-relative names."""
    root = repository_root.resolve()
    members = []
    for path in declared_source_dependencies(root):
        data = path.read_bytes()
        members.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "algorithm": "fapo-working-source-fingerprint-v1",
        "members": members,
        "fingerprint": canonical_sha256(members),
    }


def collect_git_evidence(repository_root: Path) -> dict[str, Any]:
    """Collect bounded Git audit facts without persisting command output."""
    root = repository_root.resolve()
    marker_reason = "not_a_git_worktree"
    try:
        top = _run_git(root, "rev-parse", "--show-toplevel")
        if Path(top).resolve() != root:
            raise ValueError("wrong Git root")
        commit = _run_git(root, "rev-parse", "--verify", "HEAD")
        tree = _run_git(root, "rev-parse", "--verify", "HEAD^{tree}")
        if not _GIT_OBJECT.fullmatch(commit) or not _GIT_OBJECT.fullmatch(tree):
            raise ValueError("malformed Git object identity")
        repository_status = _run_git(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            max_output_bytes=1,
            stop_after_output=True,
        )
        relative_members = [
            path.relative_to(root).as_posix()
            for path in declared_source_dependencies(root)
        ]
        dependency_status = _run_git(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            *relative_members,
            max_output_bytes=1,
            stop_after_output=True,
        )
    except FileNotFoundError:
        marker_reason = "git_command_unavailable"
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        pass
    else:
        return {
            "commit": commit,
            "committed_tree": tree,
            "repository_dirty": bool(repository_status),
            "dependency_set_dirty": bool(dependency_status),
        }
    marker = unavailable(marker_reason)
    return {
        "commit": dict(marker),
        "committed_tree": dict(marker),
        "repository_dirty": dict(marker),
        "dependency_set_dirty": dict(marker),
    }


def sanitize_call_metadata(value: Any) -> list[dict[str, Any]]:
    """Validate provider transport metadata and discard every unknown field."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("provider call metadata must be a sequence")
    rows: list[dict[str, Any]] = []
    for expected_ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            raise ValueError("provider call metadata row must be an object")
        ordinal = raw.get("transport_ordinal")
        if ordinal != expected_ordinal:
            raise ValueError("provider transport ordinals must be contiguous")
        usage = raw.get("usage")
        usage_row = usage if isinstance(usage, Mapping) else {}
        rows.append(
            {
                "transport_ordinal": expected_ordinal,
                "response_id": _metadata_string(raw, "response_id"),
                "request_id": _metadata_string(raw, "request_id"),
                "model": _metadata_string(raw, "model"),
                "system_fingerprint": _metadata_string(
                    raw,
                    "system_fingerprint",
                ),
                "usage": {
                    "input_tokens": _metadata_integer(usage_row, "input_tokens"),
                    "output_tokens": _metadata_integer(
                        usage_row,
                        "output_tokens",
                        not_applicable_when_missing=True,
                    ),
                    "total_tokens": _metadata_integer(usage_row, "total_tokens"),
                },
                "retry_count": _metadata_integer(raw, "retry_count"),
            }
        )
    return rows


def provider_response_metadata(
    response: Any,
    *,
    transport_ordinal: int,
    retry_count: int,
    output_tokens_not_applicable: bool,
) -> dict[str, Any]:
    """Project one SDK response into the optional metadata protocol."""
    usage = _value(response, "usage", None)
    prompt_tokens = _value(usage, "prompt_tokens", _value(usage, "input_tokens", None))
    completion_tokens = _value(
        usage,
        "completion_tokens",
        _value(usage, "output_tokens", None),
    )
    row = {
        "transport_ordinal": 1,
        "response_id": _value(response, "id", None),
        "request_id": _value(response, "_request_id", None),
        "model": _value(response, "model", None),
        "system_fingerprint": _value(response, "system_fingerprint", None),
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": _value(usage, "total_tokens", None),
        },
        "retry_count": retry_count,
    }
    sanitized = sanitize_call_metadata([row])[0]
    sanitized["transport_ordinal"] = transport_ordinal
    if output_tokens_not_applicable and completion_tokens is None:
        sanitized["usage"]["output_tokens"] = not_applicable(
            "provider_does_not_expose_field"
        )
    return sanitized


def provider_settings(
    provider: Any,
    *,
    role: str,
    identity: Mapping[str, Any],
    pipeline_batch_size: int,
) -> dict[str, Any]:
    """Project generation-relevant provider settings without object inspection."""
    marker = unavailable("provider_does_not_expose_field")

    missing = object()

    def value(name: str) -> Any:
        item = getattr(provider, name, missing) if provider is not None else missing
        if isinstance(item, bool) or isinstance(item, (int, float, str)):
            return item
        if _is_marker(item):
            return dict(item)
        return dict(marker)

    if role == "rubric":
        settings = {
            "timeout_seconds": value("timeout_seconds"),
            "max_retries": value("max_retries"),
            "retry_backoff_seconds": value("retry_backoff_seconds"),
            "pipeline_batch_size": pipeline_batch_size,
            "max_output_tokens": value("max_output_tokens"),
            "temperature": value("temperature"),
            "response_format": value("response_format"),
            "seed": value("seed"),
        }
        interface = "generate_json-v1"
    elif role == "embedding":
        settings = {
            "timeout_seconds": value("timeout_seconds"),
            "max_retries": value("max_retries"),
            "retry_backoff_seconds": value("retry_backoff_seconds"),
            "provider_batch_size": value("batch_size"),
            "response_format": value("response_format"),
            "seed": value("seed"),
        }
        interface = "embed_texts-v1"
    else:
        raise ValueError(f"Unsupported provider role: {role}")
    return {
        "provider": identity["provider"],
        "model": identity["model"],
        "source": identity["source"],
        "interface": interface,
        "settings": settings,
    }


def build_algorithm_inventory(
    config: Mapping[str, Any],
    *,
    extension: bool,
) -> dict[str, Any]:
    """Return the exact generation-affecting algorithm inventory."""
    return {
        "raw_inputs": "fapo-evaluation-input-v1",
        "prepared_inputs": "fapo-evaluation-canonical-preparation-v1",
        "rubric_extraction": "fapo-evaluation-guideline-v1",
        "intent_clustering": {
            "algorithm": "deterministic-cosine-fixed-count-v1",
            "embedding": (
                "smoothed-unigram-tfidf-v1"
                if config.get("embedding_provider") == "tfidf"
                else "provider-dense-v1"
            ),
            "max_iterations": 50,
            "max_representatives": 3,
        },
        "coverage_decisions": {
            "algorithm": "route-constrained-cosine-v1",
            "labeling_queue": "deterministic-centroid-nearest-v1",
            "sample_ratio": 0.1,
            "minimum_per_cluster": 1,
            "maximum_per_cluster": 3,
        },
        "label_inference": "trusted-guideline-inference-v1",
        "synthetic_coverage": "fapo-synthetic-filter-v1",
        "dataset_splits": {
            "algorithm": (
                "group-safe-stable-fraction-extension-v1"
                if extension
                else "group-safe-random-v1"
            ),
            "regression_fraction": 0.2,
        },
    }


def build_provider_call(
    *,
    stage: str,
    ordinal: int,
    provider_role: str,
    provider: str,
    model: str,
    request: Mapping[str, Any],
    response: Any,
    metadata: Any,
) -> dict[str, Any]:
    """Build one body-free logical provider-call ledger row."""
    if ordinal < 1:
        raise ValueError("provider call ordinal must be positive")
    request_sha256 = canonical_sha256(dict(request))
    response_sha256 = canonical_sha256(response)
    if metadata is None:
        identity: Any = unavailable("optional_metadata_protocol_absent")
        audit: Any = unavailable("optional_metadata_protocol_absent")
    elif isinstance(metadata, Mapping):
        marker = unavailable("metadata_failed_validation")
        if metadata != marker:
            raise ValueError("provider call metadata marker is invalid")
        identity = dict(marker)
        audit = dict(marker)
    else:
        rows = sanitize_call_metadata(metadata)
        identity = [
            {
                "transport_ordinal": row["transport_ordinal"],
                "model": row["model"],
                "system_fingerprint": row["system_fingerprint"],
            }
            for row in rows
        ]
        audit = [
            {
                "transport_ordinal": row["transport_ordinal"],
                "response_id": row["response_id"],
                "request_id": row["request_id"],
                "usage": row["usage"],
                "retry_count": row["retry_count"],
            }
            for row in rows
        ]
    return {
        "schema_version": PROVIDER_CALL_SCHEMA_VERSION,
        "stage": stage,
        "ordinal": ordinal,
        "provider_role": provider_role,
        "provider": provider,
        "model": model,
        "request_sha256": request_sha256,
        "response_sha256": response_sha256,
        "transport_identity": identity,
        "transport_audit": audit,
    }


def validate_provider_calls(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_stage: str,
) -> list[dict[str, Any]]:
    """Strictly validate one complete ordered stage provider-call ledger."""
    if expected_stage not in PROVIDER_STAGE_ROLES:
        raise ValueError("provider call ledger stage is unsupported")
    allowed_roles = PROVIDER_STAGE_ROLES[expected_stage]
    expected_fields = {
        "schema_version",
        "stage",
        "ordinal",
        "provider_role",
        "provider",
        "model",
        "request_sha256",
        "response_sha256",
        "transport_identity",
        "transport_audit",
    }
    result: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(rows, start=1):
        if not isinstance(raw, Mapping) or set(raw) != expected_fields:
            raise ValueError("provider call ledger row schema is invalid")
        if (
            raw.get("schema_version") != PROVIDER_CALL_SCHEMA_VERSION
            or raw.get("stage") != expected_stage
            or raw.get("ordinal") != ordinal
            or raw.get("provider_role") not in allowed_roles
            or not isinstance(raw.get("provider"), str)
            or not raw["provider"]
            or not isinstance(raw.get("model"), str)
            or not raw["model"]
        ):
            raise ValueError("provider call ledger provider role or identity is invalid")
        for field in ("request_sha256", "response_sha256"):
            if not isinstance(raw.get(field), str) or not _SHA256.fullmatch(raw[field]):
                raise ValueError("provider call ledger hash is invalid")
        transport_identity = raw.get("transport_identity")
        transport_audit = raw.get("transport_audit")
        if isinstance(transport_identity, list):
            if not isinstance(transport_audit, list) or len(transport_identity) != len(
                transport_audit
            ):
                raise ValueError("provider transport evidence is inconsistent")
            for index, (identity, audit) in enumerate(
                zip(transport_identity, transport_audit), start=1
            ):
                if (
                    not isinstance(identity, Mapping)
                    or set(identity)
                    != {"transport_ordinal", "model", "system_fingerprint"}
                    or identity.get("transport_ordinal") != index
                    or not isinstance(audit, Mapping)
                    or set(audit)
                    != {
                        "transport_ordinal",
                        "response_id",
                        "request_id",
                        "usage",
                        "retry_count",
                    }
                    or audit.get("transport_ordinal") != index
                ):
                    raise ValueError("provider transport evidence is invalid")
                usage = audit.get("usage")
                if (
                    not _valid_sanitized_metadata_string(identity.get("model"))
                    or not _valid_sanitized_metadata_string(
                        identity.get("system_fingerprint")
                    )
                    or not _valid_sanitized_metadata_string(audit.get("response_id"))
                    or not _valid_sanitized_metadata_string(audit.get("request_id"))
                    or not isinstance(usage, Mapping)
                    or set(usage)
                    != {"input_tokens", "output_tokens", "total_tokens"}
                    or not _valid_sanitized_metadata_integer(
                        usage.get("input_tokens")
                    )
                    or not _valid_sanitized_metadata_integer(
                        usage.get("output_tokens"),
                        allow_not_applicable=True,
                    )
                    or not _valid_sanitized_metadata_integer(
                        usage.get("total_tokens")
                    )
                    or not _valid_sanitized_metadata_integer(
                        audit.get("retry_count")
                    )
                ):
                    raise ValueError("provider transport metadata is invalid")
        else:
            valid_markers = {
                canonical_sha256(unavailable("optional_metadata_protocol_absent")),
                canonical_sha256(unavailable("metadata_failed_validation")),
            }
            if (
                not isinstance(transport_identity, Mapping)
                or not isinstance(transport_audit, Mapping)
                or canonical_sha256(transport_identity) not in valid_markers
                or transport_audit != transport_identity
            ):
                raise ValueError("provider transport unavailable marker is invalid")
        result.append(dict(raw))
    return result


def write_provider_call_ledger(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    stage: str,
) -> None:
    """Validate then atomically persist one stage-local call ledger."""
    atomic_write_jsonl(path, validate_provider_calls(rows, expected_stage=stage))


def build_stage_provenance(
    *,
    stage: str,
    provider_identity: Mapping[str, Any],
    prompt_values: Mapping[str, str],
    calls: Sequence[Mapping[str, Any]] | None,
    code: Mapping[str, Any],
    seeds: Mapping[str, Any],
    algorithms: Mapping[str, Any],
) -> dict[str, Any]:
    """Build strict body-free provenance for one stage before its receipt."""
    prompts = [
        {
            "name": name,
            "revision": PROMPT_REVISIONS[name],
            "bytes": len(value.encode("utf-8")),
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        }
        for name, value in sorted(prompt_values.items())
    ]
    return {
        "schema_version": STAGE_PROVENANCE_SCHEMA_VERSION,
        "stage": stage,
        "provider_identity": dict(provider_identity),
        "prompts": prompts,
        "calls": (
            [dict(row) for row in calls]
            if calls is not None
            else not_applicable("stage_has_no_provider_role")
        ),
        "seeds": dict(seeds),
        "algorithms": dict(algorithms),
        "source": dict(code),
    }


def build_provenance(
    *,
    repository_root: Path,
    resolved_configuration: Mapping[str, Any],
    copied_inputs: Mapping[str, Mapping[str, Any]],
    lineage: Mapping[str, Any] | None,
    providers: Mapping[str, Mapping[str, Any]],
    prompt_values: Mapping[str, str],
    calls: Sequence[Mapping[str, Any]],
    seeds: Mapping[str, Any],
    algorithms: Mapping[str, Any],
    lineage_files: Mapping[str, Any] | None,
    created_at: str,
) -> dict[str, Any]:
    """Build complete provenance with deterministic identity and audit separated."""
    by_stage: dict[str, list[Mapping[str, Any]]] = {}
    for row in calls:
        by_stage.setdefault(str(row.get("stage")), []).append(row)
    identity_calls, audit_calls = _provider_call_projections(by_stage)
    prompts = [
        {
            "name": name,
            "revision": PROMPT_REVISIONS[name],
            "bytes": len(value.encode("utf-8")),
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        }
        for name, value in sorted(prompt_values.items())
    ]
    config_values = dict(resolved_configuration)
    identity = {
        "schema_version": BUILD_IDENTITY_SCHEMA_VERSION,
        "hash_algorithm": "sha256",
        "resolved_configuration": {
            "values": config_values,
            "sha256": canonical_sha256(config_values),
        },
        "source": working_source_identity(repository_root),
        "runtime_dependencies": _runtime_dependencies(config_values),
        "inputs": {name: dict(value) for name, value in sorted(copied_inputs.items())},
        "lineage": (
            _lineage_identity(lineage, lineage_files=lineage_files)
            if lineage
            else not_applicable("native_asset_has_no_parent")
        ),
        "providers": {
            name: dict(value) for name, value in sorted(providers.items())
        },
        "prompts": prompts,
        "calls": identity_calls,
        "seeds": dict(seeds),
        "algorithms": dict(algorithms),
    }
    return {
        "schema_version": BUILD_PROVENANCE_SCHEMA_VERSION,
        "identity": identity,
        "identity_sha256": canonical_sha256(identity),
        "audit": {
            "git": collect_git_evidence(repository_root),
            "calls": audit_calls,
            "lineage_files": (
                dict(lineage_files)
                if lineage_files is not None
                else not_applicable("native_asset_has_no_parent")
            ),
        },
        "created_at": created_at,
    }


def validate_build_provenance(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact nested build provenance without accepting opaque bodies."""
    if set(payload) != {
        "schema_version",
        "identity",
        "identity_sha256",
        "audit",
        "created_at",
    } or payload.get("schema_version") != BUILD_PROVENANCE_SCHEMA_VERSION:
        raise ValueError("build provenance schema is invalid")
    identity = payload.get("identity")
    if not isinstance(identity, Mapping) or payload.get(
        "identity_sha256"
    ) != canonical_sha256(identity):
        raise ValueError("build provenance identity is inconsistent")
    expected_identity = {
        "schema_version",
        "hash_algorithm",
        "resolved_configuration",
        "source",
        "runtime_dependencies",
        "inputs",
        "lineage",
        "providers",
        "prompts",
        "calls",
        "seeds",
        "algorithms",
    }
    if set(identity) != expected_identity:
        raise ValueError("build provenance identity schema is invalid")
    if (
        identity.get("schema_version") != BUILD_IDENTITY_SCHEMA_VERSION
        or identity.get("hash_algorithm") != "sha256"
    ):
        raise ValueError("build provenance identity schema is invalid")
    _validate_resolved_configuration(identity.get("resolved_configuration"))
    _validate_source_identity(identity.get("source"))
    _validate_runtime_dependencies(identity.get("runtime_dependencies"))
    _validate_input_inventory(identity.get("inputs"))
    _validate_lineage_identity(identity.get("lineage"))
    _validate_provider_inventory(identity.get("providers"))
    _validate_prompt_inventory(identity.get("prompts"))
    _validate_json_value(identity.get("seeds"), "provenance seeds")
    _validate_json_value(identity.get("algorithms"), "provenance algorithms")
    if not isinstance(payload.get("audit"), Mapping) or set(payload["audit"]) != {
        "git",
        "calls",
        "lineage_files",
    }:
        raise ValueError("build provenance audit schema is invalid")
    _validate_git_audit(payload["audit"].get("git"))
    _validate_call_evidence(
        identity.get("calls"),
        payload["audit"].get("calls"),
    )
    _validate_lineage_files(payload["audit"].get("lineage_files"))
    legacy_marker = unavailable("legacy_checkpoint_predates_provenance")
    if identity.get("source") == legacy_marker:
        _validate_legacy_build_profile(identity, payload["audit"], legacy_marker)
    else:
        _validate_native_build_profile(identity, payload["audit"])
    created_at = payload.get("created_at")
    try:
        parsed_created_at = datetime.fromisoformat(str(created_at))
    except ValueError as exc:
        raise ValueError("build provenance timestamp is invalid") from exc
    if (
        not isinstance(created_at, str)
        or parsed_created_at.tzinfo is None
        or parsed_created_at.utcoffset() != timedelta(0)
        or parsed_created_at.isoformat() != created_at
    ):
        raise ValueError("build provenance timestamp is invalid")
    return dict(payload)


def validate_build_provenance_call_ledgers(
    payload: Mapping[str, Any],
    stage_ledgers: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    """Bind native build call projections to every authenticated stage ledger."""
    validate_build_provenance(payload)
    required_stages = {
        stage for stage, roles in PROVIDER_STAGE_ROLES.items() if roles
    }
    if set(stage_ledgers) != required_stages:
        raise ValueError("build provenance call ledger inventory is incomplete")
    identity_calls, audit_calls = _provider_call_projections(stage_ledgers)
    identity = payload["identity"]
    audit = payload["audit"]
    if (
        canonical_sha256(identity.get("calls"))
        != canonical_sha256(identity_calls)
        or canonical_sha256(audit.get("calls")) != canonical_sha256(audit_calls)
    ):
        raise ValueError("build provenance call ledger projections differ")


def _provider_call_projections(
    stage_ledgers: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validated_calls: list[dict[str, Any]] = []
    for stage in sorted(stage_ledgers):
        validated_calls.extend(
            validate_provider_calls(stage_ledgers[stage], expected_stage=stage)
        )
    identity_calls = [
        {
            key: row[key]
            for key in (
                "stage",
                "ordinal",
                "provider_role",
                "provider",
                "model",
                "request_sha256",
                "response_sha256",
                "transport_identity",
            )
        }
        for row in validated_calls
    ]
    audit_calls = [
        {
            "stage": row["stage"],
            "ordinal": row["ordinal"],
            "provider_role": row["provider_role"],
            "transport_audit": row["transport_audit"],
        }
        for row in validated_calls
    ]
    return identity_calls, audit_calls


def _validate_resolved_configuration(value: Any) -> None:
    if not isinstance(value, Mapping) or set(value) != {"values", "sha256"}:
        raise ValueError("build provenance configuration schema is invalid")
    values = value.get("values")
    if (
        not isinstance(values, Mapping)
        or value.get("sha256") != canonical_sha256(values)
    ):
        raise ValueError("build provenance configuration hash is invalid")
    _validate_json_value(values, "provenance configuration")


def _validate_source_identity(value: Any) -> None:
    if _is_marker(value, status="unavailable"):
        return
    if not isinstance(value, Mapping) or set(value) != {
        "algorithm",
        "members",
        "fingerprint",
    } or value.get("algorithm") != "fapo-working-source-fingerprint-v1":
        raise ValueError("build provenance source schema is invalid")
    members = value.get("members")
    if not isinstance(members, list) or not members:
        raise ValueError("build provenance source inventory is invalid")
    paths: list[str] = []
    for member in members:
        if not isinstance(member, Mapping) or set(member) != {
            "path",
            "bytes",
            "sha256",
        }:
            raise ValueError("build provenance source member is invalid")
        path = member.get("path")
        relative = Path(path) if isinstance(path, str) else Path("..")
        if (
            not isinstance(path, str)
            or not path
            or relative.is_absolute()
            or ".." in relative.parts
            or not isinstance(member.get("bytes"), int)
            or isinstance(member.get("bytes"), bool)
            or member["bytes"] < 0
            or not _valid_sha256(member.get("sha256"))
        ):
            raise ValueError("build provenance source member is invalid")
        paths.append(path)
    if (
        paths != sorted(paths)
        or len(paths) != len(set(paths))
        or value.get("fingerprint") != canonical_sha256(members)
    ):
        raise ValueError("build provenance source fingerprint is invalid")


def _validate_runtime_dependencies(value: Any) -> None:
    expected = {
        "python_implementation",
        "python_version",
        "hephaestus_distribution_version",
        "openai_sdk_version",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("build provenance runtime schema is invalid")
    for item in value.values():
        if not (isinstance(item, str) and item and not _SECRET.search(item)) and not (
            _is_marker(item)
        ):
            raise ValueError("build provenance runtime value is invalid")


def _validate_input_inventory(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("build provenance input inventory is invalid")
    for name, row in value.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(row, Mapping)
            or set(row) != {"path", "bytes", "rows", "sha256"}
        ):
            raise ValueError("build provenance input row is invalid")
        path = row.get("path")
        relative = Path(path) if isinstance(path, str) else Path("..")
        if (
            not isinstance(path, str)
            or not path
            or relative.is_absolute()
            or ".." in relative.parts
            or any(
                isinstance(row.get(field), bool)
                or not isinstance(row.get(field), int)
                or row[field] < 0
                for field in ("bytes", "rows")
            )
            or not _valid_sha256(row.get("sha256"))
        ):
            raise ValueError("build provenance input row is invalid")


def _validate_lineage_identity(value: Any) -> None:
    if _is_marker(value, status="not_applicable"):
        return
    allowed = {
        "parent_asset_id",
        "clustering_mode",
        "added_labeled_record_ids",
        "added_unlabeled_record_ids",
        "parent_input_counts",
        "extended_input_counts",
        "parent_generation_id",
        "file_dependencies",
    }
    if not isinstance(value, Mapping) or not value or not set(value) <= allowed:
        raise ValueError("build provenance lineage schema is invalid")
    dependencies = value.get("file_dependencies")
    if dependencies is not None:
        _validate_lineage_file_mapping(dependencies)
    _validate_json_value(value, "provenance lineage")


def _validate_provider_inventory(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("build provenance provider inventory is invalid")
    for role, row in value.items():
        if role not in {"rubric", "embedding"}:
            raise ValueError("build provenance provider role is invalid")
        if _is_marker(row, status="unavailable"):
            continue
        if not isinstance(row, Mapping) or set(row) != {
            "provider",
            "model",
            "source",
            "interface",
            "settings",
        }:
            raise ValueError("build provenance provider schema is invalid")
        if any(
            not isinstance(row.get(field), str)
            or not row[field]
            or _SECRET.search(row[field])
            for field in ("provider", "model", "source", "interface")
        ) or not isinstance(row.get("settings"), Mapping):
            raise ValueError("build provenance provider schema is invalid")
        _validate_json_value(row["settings"], "provenance provider settings")


def _validate_prompt_inventory(value: Any) -> None:
    if _is_marker(value, status="unavailable"):
        return
    if not isinstance(value, list):
        raise ValueError("build provenance prompt inventory is invalid")
    names: list[str] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {
            "name",
            "revision",
            "bytes",
            "sha256",
        }:
            raise ValueError("build provenance prompt row is invalid")
        name = row.get("name")
        if (
            name not in PROMPT_REVISIONS
            or row.get("revision") != PROMPT_REVISIONS[name]
            or not isinstance(row.get("bytes"), int)
            or isinstance(row.get("bytes"), bool)
            or row["bytes"] < 0
            or not _valid_sha256(row.get("sha256"))
        ):
            raise ValueError("build provenance prompt row is invalid")
        names.append(str(name))
    if names != sorted(names) or len(names) != len(set(names)):
        raise ValueError("build provenance prompt inventory is invalid")


def _validate_call_evidence(identity_calls: Any, audit_calls: Any) -> None:
    if _is_marker(identity_calls, status="unavailable"):
        if audit_calls != identity_calls:
            raise ValueError("build provenance call markers are inconsistent")
        return
    if not isinstance(identity_calls, list) or not isinstance(audit_calls, list):
        raise ValueError("build provenance call inventory is invalid")
    if len(identity_calls) != len(audit_calls):
        raise ValueError("build provenance call inventories differ")
    reconstructed: list[dict[str, Any]] = []
    for identity_row, audit_row in zip(identity_calls, audit_calls):
        if not isinstance(identity_row, Mapping) or set(identity_row) != {
            "stage",
            "ordinal",
            "provider_role",
            "provider",
            "model",
            "request_sha256",
            "response_sha256",
            "transport_identity",
        } or not isinstance(audit_row, Mapping) or set(audit_row) != {
            "stage",
            "ordinal",
            "provider_role",
            "transport_audit",
        }:
            raise ValueError("build provenance call row is invalid")
        if any(
            audit_row.get(field) != identity_row.get(field)
            for field in ("stage", "ordinal", "provider_role")
        ):
            raise ValueError("build provenance call audit is inconsistent")
        reconstructed.append(
            {
                "schema_version": PROVIDER_CALL_SCHEMA_VERSION,
                **dict(identity_row),
                "transport_audit": audit_row["transport_audit"],
            }
        )
    by_stage: dict[str, list[dict[str, Any]]] = {}
    for row in reconstructed:
        by_stage.setdefault(str(row["stage"]), []).append(row)
    for stage, rows in by_stage.items():
        validate_provider_calls(rows, expected_stage=stage)


def _validate_git_audit(value: Any) -> None:
    if _is_marker(value, status="unavailable"):
        return
    if not isinstance(value, Mapping) or set(value) != {
        "commit",
        "committed_tree",
        "repository_dirty",
        "dependency_set_dirty",
    }:
        raise ValueError("build provenance Git audit is invalid")
    object_values = (value.get("commit"), value.get("committed_tree"))
    if not all(
        (isinstance(item, str) and bool(_GIT_OBJECT.fullmatch(item)))
        or _is_marker(item, status="unavailable")
        for item in object_values
    ) or not all(
        isinstance(value.get(field), bool)
        or _is_marker(value.get(field), status="unavailable")
        for field in ("repository_dirty", "dependency_set_dirty")
    ):
        raise ValueError("build provenance Git audit is invalid")


def _validate_lineage_files(value: Any) -> None:
    if _is_marker(value):
        return
    _validate_lineage_file_mapping(value)


def _validate_lineage_file_mapping(value: Any) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "lineage_sha256",
        "reuse_manifest_sha256",
        "parent_release",
    } or not _valid_sha256(value.get("lineage_sha256")) or not _valid_sha256(
        value.get("reuse_manifest_sha256")
    ) or not isinstance(value.get("parent_release"), Mapping):
        raise ValueError("build provenance lineage files are invalid")
    validate_parent_release_evidence(value["parent_release"])


def _validate_json_value(value: Any, label: str) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError(f"{label} contains a non-finite number")
        return
    if isinstance(value, str):
        if _SECRET.search(value):
            raise ValueError(f"{label} contains secret-like content")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, label)
        return
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError(f"{label} has a non-string key")
        for item in value.values():
            _validate_json_value(item, label)
        return
    raise ValueError(f"{label} contains an unsupported value")


def _is_marker(value: Any, *, status: str | None = None) -> bool:
    if not isinstance(value, Mapping) or set(value) != {"status", "reason"}:
        return False
    marker_status = value.get("status")
    reason = value.get("reason")
    if marker_status not in {"unavailable", "not_applicable"} or (
        status is not None and marker_status != status
    ) or not isinstance(reason, str):
        return False
    allowed = (
        UNAVAILABLE_REASONS
        if marker_status == "unavailable"
        else NOT_APPLICABLE_REASONS
    )
    return reason in allowed


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _validate_native_build_profile(
    identity: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> None:
    source = identity.get("source")
    source_members = source.get("members") if isinstance(source, Mapping) else None
    if not isinstance(source_members, list) or [
        member.get("path") for member in source_members if isinstance(member, Mapping)
    ] != sorted(SOURCE_FIXED_MEMBERS):
        raise ValueError("native build provenance source inventory is incomplete")
    if set(_mapping_keys(identity.get("inputs"))) != {
        "labeled_feedback",
        "unlabeled",
    } or set(_mapping_keys(identity.get("providers"))) != {
        "rubric",
        "embedding",
    }:
        raise ValueError("native build provenance inventory is incomplete")
    prompts = identity.get("prompts")
    if not isinstance(prompts, list) or {
        row.get("name") for row in prompts if isinstance(row, Mapping)
    } != set(PROMPT_REVISIONS):
        raise ValueError("native build provenance prompt inventory is incomplete")
    providers = identity.get("providers")
    if not isinstance(providers, Mapping) or any(
        not isinstance(providers.get(role), Mapping)
        or providers[role].get("interface") != interface
        for role, interface in (
            ("rubric", "generate_json-v1"),
            ("embedding", "embed_texts-v1"),
        )
    ):
        raise ValueError("native build provenance providers are unavailable")
    seeds = identity.get("seeds")
    configuration = identity["resolved_configuration"]
    config = configuration["values"]
    _validate_native_configuration(config)
    _validate_native_runtime_profile(identity.get("runtime_dependencies"), config)
    _validate_native_git_profile(audit.get("git"))
    for role in ("rubric", "embedding"):
        _validate_native_provider_profile(role, providers[role], config)
    expected_sampling = not_applicable("provider_does_not_use_sampling")
    if set(_mapping_keys(seeds)) != {
        "split",
        "rubric_sampling",
        "embedding_sampling",
    } or isinstance(seeds["split"], bool) or not isinstance(
        seeds["split"], int
    ) or seeds["split"] != config.get("split_seed") or seeds.get(
        "rubric_sampling"
    ) != expected_sampling or seeds.get("embedding_sampling") != expected_sampling:
        raise ValueError("native build provenance seed schema is inconsistent")
    lineage = identity.get("lineage")
    lineage_files = audit.get("lineage_files")
    native_marker = not_applicable("native_asset_has_no_parent")
    extension = lineage != native_marker
    calls = identity.get("calls")
    if identity.get("algorithms") != build_algorithm_inventory(
        config,
        extension=extension,
    ) or not isinstance(calls, list):
        raise ValueError("native build provenance algorithm schema is inconsistent")
    for call in calls:
        if not isinstance(call, Mapping):
            raise ValueError("native build provenance call schema is invalid")
        provider = providers.get(call.get("provider_role"))
        if not isinstance(provider, Mapping) or any(
            call.get(field) != provider.get(field) for field in ("provider", "model")
        ):
            raise ValueError("native build provenance call provider is inconsistent")
    for role in ("rubric", "embedding"):
        provider = providers[role]
        if provider.get("source") != "injected":
            continue
        differs_from_config = any(
            provider.get(field) != config[f"{role}_{field}"]
            for field in ("provider", "model")
        )
        has_call_evidence = any(
            call.get("provider_role") == role for call in calls
        )
        if differs_from_config and not has_call_evidence:
            raise ValueError(
                "native build provenance injected provider lacks call evidence"
            )
    if lineage == native_marker:
        if lineage_files != native_marker:
            raise ValueError("native build provenance lineage markers differ")
    else:
        if (
            not isinstance(lineage, Mapping)
            or not isinstance(lineage_files, Mapping)
            or lineage.get("file_dependencies") != lineage_files
        ):
            raise ValueError("native extension provenance lineage is incomplete")
        validate_provenance_lineage_identity(lineage)


def _validate_native_configuration(value: Any) -> None:
    from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig

    if not isinstance(value, Mapping):
        raise ValueError("native build provenance configuration is invalid")
    try:
        resolved = EvaluationAssetConfig.from_dict(value).to_dict()
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("native build provenance configuration is invalid") from exc
    if canonical_sha256(resolved) != canonical_sha256(dict(value)):
        raise ValueError("native build provenance configuration is incomplete")


def _validate_native_provider_profile(
    role: str,
    value: Mapping[str, Any],
    config: Mapping[str, Any],
) -> None:
    expected_settings = (
        {
            "timeout_seconds",
            "max_retries",
            "retry_backoff_seconds",
            "pipeline_batch_size",
            "max_output_tokens",
            "temperature",
            "response_format",
            "seed",
        }
        if role == "rubric"
        else {
            "timeout_seconds",
            "max_retries",
            "retry_backoff_seconds",
            "provider_batch_size",
            "response_format",
            "seed",
        }
    )
    settings = value.get("settings")
    if (
        value.get("source") not in {"default", "injected"}
        or not isinstance(settings, Mapping)
        or set(settings) != expected_settings
        or any(
            not _valid_native_provider_setting(name, item)
            for name, item in settings.items()
        )
        or (
            role == "rubric"
            and settings.get("pipeline_batch_size") != config["batch_size"]
        )
    ):
        raise ValueError("native build provenance provider settings are invalid")
    if value["source"] == "injected":
        return
    configured_provider = config[f"{role}_provider"]
    configured_model = config[f"{role}_model"]
    if (
        value.get("provider") != configured_provider
        or value.get("model") != configured_model
    ):
        raise ValueError("native build provenance default provider is inconsistent")

    identity = {
        "provider": configured_provider,
        "model": configured_model,
        "source": "default",
    }
    if role == "rubric" and configured_provider == "openai":
        from src.hephaestus.datasets.rubric_providers import OpenAIRubricProvider

        provider: Any = OpenAIRubricProvider(
            model=configured_model,
            max_output_tokens=16384,
        )
    elif role == "embedding" and configured_provider == "openai":
        from src.hephaestus.datasets.embedding_providers import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(model=configured_model)
    elif role == "embedding" and configured_provider == "tfidf":
        provider = None
    else:
        raise ValueError("native build provenance default provider is unsupported")
    expected = provider_settings(
        provider,
        role=role,
        identity=identity,
        pipeline_batch_size=int(config["batch_size"]),
    )
    if canonical_sha256(value) != canonical_sha256(expected):
        raise ValueError("native build provenance default provider profile differs")


def _valid_native_provider_setting(name: str, value: Any) -> bool:
    if _is_marker(value):
        return dict(value) in (
            unavailable("provider_does_not_expose_field"),
            not_applicable("provider_does_not_use_sampling"),
        )
    if name in {
        "max_retries",
        "pipeline_batch_size",
        "provider_batch_size",
        "max_output_tokens",
    }:
        minimum = 0 if name == "max_retries" else 1
        return not isinstance(value, bool) and isinstance(value, int) and value >= minimum
    if name in {"timeout_seconds", "retry_backoff_seconds", "temperature"}:
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and value == value
            and value not in {float("inf"), float("-inf")}
            and value >= 0
        )
    if name == "response_format":
        return isinstance(value, str) and bool(value) and not _SECRET.search(value)
    if name == "seed":
        return not isinstance(value, bool) and isinstance(value, int)
    return False


def _validate_native_runtime_profile(value: Any, config: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("native build provenance runtime profile is invalid")
    python_values = (value.get("python_implementation"), value.get("python_version"))
    local_marker = not_applicable("local_deterministic_provider")
    uses_openai = any(
        config.get(field) == "openai"
        for field in ("rubric_provider", "embedding_provider")
    )
    if (
        any(
            not isinstance(item, str) or not item or _SECRET.search(item)
            for item in python_values
        )
        or not _native_package_version(value.get("hephaestus_distribution_version"))
        or (
            not _native_package_version(value.get("openai_sdk_version"))
            if uses_openai
            else value.get("openai_sdk_version") != local_marker
        )
    ):
        raise ValueError("native build provenance runtime profile is invalid")


def _native_package_version(value: Any) -> bool:
    return (
        isinstance(value, str) and bool(value) and not _SECRET.search(value)
    ) or value == unavailable("package_metadata_unavailable")


def _validate_native_git_profile(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("native build provenance Git profile is invalid")
    fields = ("commit", "committed_tree", "repository_dirty", "dependency_set_dirty")
    facts = tuple(value.get(field) for field in fields)
    if (
        all(isinstance(item, str) and bool(_GIT_OBJECT.fullmatch(item)) for item in facts[:2])
        and all(isinstance(item, bool) for item in facts[2:])
    ):
        return
    for reason in ("not_a_git_worktree", "git_command_unavailable"):
        marker = unavailable(reason)
        if all(item == marker for item in facts):
            return
    raise ValueError("native build provenance Git profile is inconsistent")


def _validate_legacy_build_profile(
    identity: Mapping[str, Any],
    audit: Mapping[str, Any],
    marker: Mapping[str, str],
) -> None:
    if set(_mapping_keys(identity.get("inputs"))) != {
        "labeled_feedback",
        "unlabeled",
    } or identity.get("providers") != {
        "rubric": marker,
        "embedding": marker,
    } or identity.get("prompts") != marker or identity.get("calls") != marker or (
        identity.get("algorithms") != marker
    ) or audit.get("git") != marker or audit.get("calls") != marker or audit.get(
        "lineage_files"
    ) != marker:
        raise ValueError("legacy build provenance profile is inconsistent")
    runtime = identity.get("runtime_dependencies")
    if not isinstance(runtime, Mapping) or any(
        value != marker for value in runtime.values()
    ):
        raise ValueError("legacy build provenance runtime profile is inconsistent")
    seeds = identity.get("seeds")
    if not isinstance(seeds, Mapping) or set(seeds) != {
        "split",
        "rubric_sampling",
        "embedding_sampling",
    } or seeds.get("rubric_sampling") != marker or seeds.get(
        "embedding_sampling"
    ) != marker:
        raise ValueError("legacy build provenance seed profile is inconsistent")
    lineage = identity.get("lineage")
    if not _is_marker(lineage, status="not_applicable"):
        required = {
            "parent_asset_id",
            "clustering_mode",
            "added_labeled_record_ids",
            "added_unlabeled_record_ids",
            "parent_input_counts",
            "extended_input_counts",
            "parent_generation_id",
        }
        if not isinstance(lineage, Mapping) or set(lineage) != required:
            raise ValueError("legacy extension provenance lineage is incomplete")


def _mapping_keys(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, Mapping) else ()


def build_legacy_provenance(
    *,
    resolved_configuration: Mapping[str, Any],
    copied_inputs: Mapping[str, Mapping[str, Any]],
    lineage: Mapping[str, Any] | None,
    split_seed: int,
    created_at: str,
) -> dict[str, Any]:
    """Build explicit historical-unavailable provenance for pre-v2 adoption."""
    marker = unavailable("legacy_checkpoint_predates_provenance")
    config_values = dict(resolved_configuration)
    identity = {
        "schema_version": BUILD_IDENTITY_SCHEMA_VERSION,
        "hash_algorithm": "sha256",
        "resolved_configuration": {
            "values": config_values,
            "sha256": canonical_sha256(config_values),
        },
        "source": dict(marker),
        "runtime_dependencies": {
            "python_implementation": dict(marker),
            "python_version": dict(marker),
            "hephaestus_distribution_version": dict(marker),
            "openai_sdk_version": dict(marker),
        },
        "inputs": {name: dict(value) for name, value in sorted(copied_inputs.items())},
        "lineage": (
            _lineage_identity(lineage)
            if lineage
            else not_applicable("native_asset_has_no_parent")
        ),
        "providers": {"rubric": dict(marker), "embedding": dict(marker)},
        "prompts": dict(marker),
        "calls": dict(marker),
        "seeds": {
            "split": split_seed,
            "rubric_sampling": dict(marker),
            "embedding_sampling": dict(marker),
        },
        "algorithms": dict(marker),
    }
    payload = {
        "schema_version": BUILD_PROVENANCE_SCHEMA_VERSION,
        "identity": identity,
        "identity_sha256": canonical_sha256(identity),
        "audit": {
            "git": dict(marker),
            "calls": dict(marker),
            "lineage_files": dict(marker),
        },
        "created_at": created_at,
    }
    validate_build_provenance(payload)
    return payload


def build_legacy_stage_provenance(stage: str) -> dict[str, Any]:
    """Build one explicit historical-unavailable stage provenance record."""
    marker = unavailable("legacy_checkpoint_predates_provenance")
    return {
        "schema_version": STAGE_PROVENANCE_SCHEMA_VERSION,
        "stage": stage,
        "provider_identity": dict(marker),
        "prompts": dict(marker),
        "calls": dict(marker),
        "seeds": dict(marker),
        "algorithms": dict(marker),
        "source": dict(marker),
    }


def _runtime_dependencies(config: Mapping[str, Any]) -> dict[str, Any]:
    def distribution(name: str, *, applicable: bool = True) -> Any:
        if not applicable:
            return not_applicable("local_deterministic_provider")
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return unavailable("package_metadata_unavailable")

    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "hephaestus_distribution_version": distribution("hephaestus"),
        "openai_sdk_version": distribution(
            "openai",
            applicable=(
                config.get("rubric_provider") == "openai"
                or config.get("embedding_provider") == "openai"
            ),
        ),
    }


def _lineage_identity(
    lineage: Mapping[str, Any],
    *,
    lineage_files: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = {
        key: lineage[key]
        for key in (
            "parent_asset_id",
            "clustering_mode",
            "added_labeled_record_ids",
            "added_unlabeled_record_ids",
            "parent_input_counts",
            "extended_input_counts",
        )
        if key in lineage
    }
    parent_release = lineage.get("parent_release")
    if isinstance(parent_release, Mapping) and isinstance(
        parent_release.get("generation_id"), str
    ):
        identity["parent_generation_id"] = parent_release["generation_id"]
    if lineage_files is not None:
        stable_parent = lineage_files.get("parent_release")
        identity["file_dependencies"] = {
            "lineage_sha256": lineage_files.get("lineage_sha256"),
            "reuse_manifest_sha256": lineage_files.get(
                "reuse_manifest_sha256"
            ),
            "parent_release": (
                {
                    key: stable_parent[key]
                    for key in sorted(stable_parent)
                }
                if isinstance(stable_parent, Mapping)
                else stable_parent
            ),
        }
    return identity


def _run_git(
    root: Path,
    *arguments: str,
    max_output_bytes: int = 4096,
    stop_after_output: bool = False,
) -> str:
    """Run Git without a shell, timeout, or unbounded captured output."""
    if max_output_bytes < 1:
        raise ValueError("Git output bound must be positive")
    process = subprocess.Popen(
        ["git", "-C", str(root), *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    if process.stdout is None:  # pragma: no cover - guaranteed by stdout=PIPE
        process.kill()
        raise OSError("Git stdout pipe was not created")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 5
    output = bytearray()
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, 5)
            if not selector.select(remaining):
                raise subprocess.TimeoutExpired(process.args, 5)
            chunk = os.read(
                process.stdout.fileno(),
                min(4096, max_output_bytes + 1 - len(output)),
            )
            if not chunk:
                break
            output.extend(chunk)
            if stop_after_output:
                process.terminate()
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
                return output.decode("utf-8", errors="strict")
            if len(output) > max_output_bytes:
                raise ValueError("Git command output exceeded its bound")
        return_code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
        if return_code != 0:
            raise ValueError("Git command failed")
        return output.decode("utf-8", errors="strict").rstrip("\n")
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=1)


def _metadata_string(value: Mapping[str, Any], field: str) -> Any:
    if field not in value or value[field] is None:
        return unavailable("provider_does_not_expose_field")
    item = value[field]
    if (
        not isinstance(item, str)
        or not item
        or len(item) > 256
        or any(ord(character) < 32 for character in item)
        or _SECRET.search(item)
    ):
        return unavailable("metadata_failed_validation")
    return item


def _metadata_integer(
    value: Mapping[str, Any],
    field: str,
    *,
    not_applicable_when_missing: bool = False,
) -> Any:
    if field not in value or value[field] is None:
        if not_applicable_when_missing:
            return not_applicable("provider_does_not_expose_field")
        return unavailable("provider_does_not_expose_field")
    item = value[field]
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        return unavailable("metadata_failed_validation")
    return item


def _valid_sanitized_metadata_string(value: Any) -> bool:
    if isinstance(value, str):
        return bool(
            value
            and len(value) <= 256
            and not any(ord(character) < 32 for character in value)
            and not _SECRET.search(value)
        )
    return value in (
        unavailable("provider_does_not_expose_field"),
        unavailable("metadata_failed_validation"),
    )


def _valid_sanitized_metadata_integer(
    value: Any,
    *,
    allow_not_applicable: bool = False,
) -> bool:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return True
    markers = [
        unavailable("provider_does_not_expose_field"),
        unavailable("metadata_failed_validation"),
    ]
    if allow_not_applicable:
        markers.append(not_applicable("provider_does_not_expose_field"))
    return value in markers


def _value(item: Any, key: str, default: Any) -> Any:
    if item is None:
        return default
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)
