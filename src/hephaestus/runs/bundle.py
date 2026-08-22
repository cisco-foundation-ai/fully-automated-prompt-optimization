# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Collision-safe authority for one evaluation run output bundle."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from src.hephaestus import local_authority_io as authority_io
from src.hephaestus.artifact_io import atomic_write_bytes_at, rename_noreplace_at
from src.hephaestus.runs.identity import validate_run_identity_payload

RUN_MANIFEST_FILENAME = "run_manifest.json"
RUN_MANIFEST_SCHEMA_VERSION = "fapo-run-bundle-manifest-v1"
TERMINAL_ARTIFACT_NAMES = (
    "progress.json",
    "results.jsonl",
    "run_config.json",
    "run_identity.json",
    "summary.md",
)
_TERMINAL_STATUSES = frozenset({"completed", "degraded", "failed"})
_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "hash_algorithm",
        "run_id",
        "status",
        "run_identity_fingerprint",
        "ordered_case_ids_fingerprint",
        "result_count",
        "successful_result_count",
        "failed_result_count",
        "artifacts",
    }
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(
        (
            json.dumps(
                dict(row),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        for row in rows
    )


def _sha256(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is invalid: {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is invalid: {key}")
        result[key] = value
    return result


def _json_object(content: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _jsonl_objects(content: bytes) -> tuple[dict[str, Any], ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("results.jsonl is not valid UTF-8") from exc
    rows: list[dict[str, Any]] = []
    for row_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"results.jsonl row {row_number} is blank")
        rows.append(_json_object(line.encode("utf-8"), f"results.jsonl row {row_number}"))
    return tuple(rows)


@dataclass(frozen=True)
class ValidatedRunBundle:
    """One manifest-authenticated run bundle snapshot."""

    output_dir: Path
    run_id: str
    status: str
    manifest: Mapping[str, Any]
    run_config: Mapping[str, Any]
    run_identity: Mapping[str, Any]
    results: tuple[Mapping[str, Any], ...]
    summary: str
    progress: Mapping[str, Any]


@dataclass(frozen=True)
class RunBundleWriter:
    """Capability for the exact output directory reserved by one run."""

    output_dir: Path
    run_id: str
    _directory_identity: tuple[int, int, int]

    @classmethod
    def reserve(cls, output_dir: Path, *, run_id: str) -> RunBundleWriter:
        """Atomically reserve a previously absent output directory."""
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be a non-empty string")
        lexical = Path(os.path.abspath(os.fspath(output_dir)))
        if not lexical.name or lexical.parent == lexical:
            raise ValueError("run output must name one directory below a parent")
        parent = authority_io.open_or_create_bound_directory(lexical.parent)
        child: authority_io.BoundDirectory | None = None
        try:
            try:
                child = authority_io.create_child_directory(
                    parent,
                    lexical.name,
                    mode=0o700,
                )
            except FileExistsError as exc:
                raise FileExistsError(
                    f"run output already exists: {lexical}"
                ) from exc
            authority_io.sync_bound_directory(parent)
            identity = child.identity
        finally:
            if child is not None:
                child.close()
            parent.close()
        return cls(lexical, run_id, identity)

    def write_progress(self, progress: Mapping[str, Any]) -> None:
        """Atomically write mutable live progress before bundle publication."""
        if not isinstance(progress, Mapping):
            raise TypeError("run progress must be a mapping")
        if progress.get("run_id") != self.run_id:
            raise ValueError("run progress run_id does not match its reservation")
        content = _json_bytes(progress)
        directory = authority_io.open_bound_directory(self.output_dir)
        try:
            with authority_io.exclusive_parent_namespace_lock(directory):
                self._require_reserved_directory(directory)
                if authority_io.optional_stat_child(
                    directory,
                    RUN_MANIFEST_FILENAME,
                ) is not None:
                    raise ValueError("authoritative run bundle is already published")
                atomic_write_bytes_at(directory, "progress.json", content)
        finally:
            directory.close()

    def publish(
        self,
        *,
        run_config: Mapping[str, Any],
        run_identity: Mapping[str, Any],
        results: Iterable[Mapping[str, Any]],
        summary: str,
        progress: Mapping[str, Any],
        fault_hook: Callable[[str], None] | None = None,
    ) -> ValidatedRunBundle:
        """Publish terminal artifacts, installing manifest authority last."""
        if not isinstance(run_config, Mapping):
            raise TypeError("run_config must be a mapping")
        if not isinstance(run_identity, Mapping):
            raise TypeError("run_identity must be a mapping")
        if not isinstance(progress, Mapping):
            raise TypeError("run progress must be a mapping")
        if not isinstance(summary, str):
            raise TypeError("run summary must be a string")
        result_rows = tuple(results)
        if any(not isinstance(row, Mapping) for row in result_rows):
            raise TypeError("run results must contain only mappings")

        validated_identity = validate_run_identity_payload(run_identity).to_dict()
        status = _validate_terminal_cross_links(
            expected_run_id=self.run_id,
            run_config=run_config,
            run_identity=validated_identity,
            results=result_rows,
            progress=progress,
        )
        artifacts = {
            "progress.json": _json_bytes(progress),
            "results.jsonl": _jsonl_bytes(result_rows),
            "run_config.json": _json_bytes(run_config),
            "run_identity.json": _json_bytes(validated_identity),
            "summary.md": summary.encode("utf-8"),
        }
        successful_count = sum(
            row["execution_status"] == "succeeded" for row in result_rows
        )
        manifest = {
            "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
            "hash_algorithm": "sha256",
            "run_id": self.run_id,
            "status": status,
            "run_identity_fingerprint": validated_identity["identity_fingerprint"],
            "ordered_case_ids_fingerprint": validated_identity["always_controls"][
                "ordered_case_ids_fingerprint"
            ],
            "result_count": len(result_rows),
            "successful_result_count": successful_count,
            "failed_result_count": len(result_rows) - successful_count,
            "artifacts": {
                name: {"bytes": len(content), "sha256": _sha256(content)}
                for name, content in sorted(artifacts.items())
            },
        }
        manifest_bytes = _json_bytes(manifest)
        published = ValidatedRunBundle(
            output_dir=self.output_dir,
            run_id=self.run_id,
            status=status,
            manifest=manifest,
            run_config=dict(run_config),
            run_identity=validated_identity,
            results=tuple(dict(row) for row in result_rows),
            summary=summary,
            progress=dict(progress),
        )

        directory = authority_io.open_bound_directory(self.output_dir)
        try:
            with authority_io.exclusive_parent_namespace_lock(directory):
                self._require_reserved_directory(directory)
                existing_names = set(authority_io.list_children(directory))
                if RUN_MANIFEST_FILENAME in existing_names:
                    raise FileExistsError("authoritative run bundle already exists")
                if existing_names - {"progress.json"}:
                    raise ValueError("reserved run output contains unexpected artifacts")
                for name in (
                    "run_config.json",
                    "run_identity.json",
                    "results.jsonl",
                    "summary.md",
                ):
                    atomic_write_bytes_at(
                        directory,
                        name,
                        artifacts[name],
                        expected_target=None,
                    )
                    _call_fault(fault_hook, f"after_{name}")
                atomic_write_bytes_at(
                    directory,
                    "progress.json",
                    artifacts["progress.json"],
                )
                _call_fault(fault_hook, "after_progress.json")
                _verify_terminal_artifacts(directory, artifacts)
                _call_fault(fault_hook, "before_manifest_install")
                return _install_manifest_last(
                    directory,
                    manifest_bytes,
                    artifacts,
                    published,
                )
        finally:
            directory.close()

    def _require_reserved_directory(
        self,
        directory: authority_io.BoundDirectory,
    ) -> None:
        if directory.identity != self._directory_identity:
            raise ValueError("reserved run output directory identity changed")


def _call_fault(
    fault_hook: Callable[[str], None] | None,
    phase: str,
) -> None:
    if fault_hook is not None:
        fault_hook(phase)


def _read_exact_file(
    directory: authority_io.BoundDirectory,
    name: str,
) -> bytes:
    before = authority_io.stat_child(directory, name)
    if before.kind != "file":
        raise ValueError(f"run bundle member is not a regular file: {name}")
    file = authority_io.open_child_file(directory, name)
    try:
        content = authority_io.read_bound_file(file)
        if file.identity != before.identity:
            raise ValueError(f"run bundle member changed while reading: {name}")
    finally:
        file.close()
    after = authority_io.stat_child(directory, name)
    if after.identity != before.identity:
        raise ValueError(f"run bundle member changed while reading: {name}")
    return content


def _verify_terminal_artifacts(
    directory: authority_io.BoundDirectory,
    expected: Mapping[str, bytes],
    *,
    allowed_extra_names: Iterable[str] = (),
) -> None:
    expected_names = set(TERMINAL_ARTIFACT_NAMES) | set(allowed_extra_names)
    if set(authority_io.list_children(directory)) != expected_names:
        raise ValueError("terminal run artifact inventory is invalid")
    for name in TERMINAL_ARTIFACT_NAMES:
        if _read_exact_file(directory, name) != expected[name]:
            raise ValueError(f"terminal run artifact content changed: {name}")
    if set(authority_io.list_children(directory)) != expected_names:
        raise ValueError("terminal run artifact inventory changed while validating")


def _install_manifest_last(
    directory: authority_io.BoundDirectory,
    content: bytes,
    terminal_artifacts: Mapping[str, bytes],
    published: ValidatedRunBundle,
) -> ValidatedRunBundle:
    """Install manifest authority with the no-replace rename as final mutation."""
    temporary_name = f".{RUN_MANIFEST_FILENAME}.{uuid.uuid4().hex}.staged"
    temporary_identity = atomic_write_bytes_at(
        directory,
        temporary_name,
        content,
        expected_target=None,
    )
    try:
        temporary = authority_io.stat_child(directory, temporary_name)
        if temporary.kind != "file" or temporary.identity != temporary_identity:
            raise ValueError("staged run manifest identity changed")
        if _read_exact_file(directory, temporary_name) != content:
            raise ValueError("staged run manifest content changed")
        expected_names = {*TERMINAL_ARTIFACT_NAMES, temporary_name}
        observed_names = set(authority_io.list_children(directory))
        if RUN_MANIFEST_FILENAME in observed_names:
            raise ValueError("authority target appeared before installation")
        if observed_names != expected_names:
            raise ValueError("run bundle inventory changed before manifest commit")
        _verify_terminal_artifacts(
            directory,
            terminal_artifacts,
            allowed_extra_names=(temporary_name,),
        )
    except BaseException:
        authority_io.reclaim_owned_leaf(
            directory,
            authority_io.OwnedNode(
                temporary_name,
                temporary_identity,
                "file",
            ),
        )
        raise

    if not rename_noreplace_at(
        directory,
        temporary_name,
        RUN_MANIFEST_FILENAME,
        expected_source=temporary_identity,
    ):
        authority_io.reclaim_owned_leaf(
            directory,
            authority_io.OwnedNode(
                temporary_name,
                temporary_identity,
                "file",
            ),
        )
        raise ValueError("authority target appeared before installation")
    return published


def _validate_terminal_cross_links(
    *,
    expected_run_id: str,
    run_config: Mapping[str, Any],
    run_identity: Mapping[str, Any],
    results: tuple[Mapping[str, Any], ...],
    progress: Mapping[str, Any],
) -> str:
    if run_config.get("run_id") != expected_run_id:
        raise ValueError("run_config run_id does not match its reservation")
    if progress.get("run_id") != expected_run_id:
        raise ValueError("run progress run_id does not match its reservation")
    status = progress.get("status")
    if status not in _TERMINAL_STATUSES:
        raise ValueError("run progress is not terminal")
    controls = run_identity.get("always_controls")
    if not isinstance(controls, Mapping):
        raise ValueError("run identity always_controls is invalid")
    ordered_case_ids = controls.get("ordered_case_ids")
    if (
        not isinstance(ordered_case_ids, list)
        or any(not isinstance(case_id, str) or not case_id for case_id in ordered_case_ids)
        or len(set(ordered_case_ids)) != len(ordered_case_ids)
    ):
        raise ValueError("run identity ordered case IDs are invalid")
    if run_config.get("dataset_path") != controls.get("dataset_path"):
        raise ValueError("run_config dataset_path does not match run identity")
    _require_string(
        controls.get("ordered_case_ids_fingerprint"),
        "ordered case ID fingerprint",
    )
    _require_string(
        run_identity.get("identity_fingerprint"),
        "run identity fingerprint",
    )
    result_case_ids: list[str] = []
    successful_case_ids: list[str] = []
    failed_case_ids: list[str] = []
    for row in results:
        case_id = _require_string(row.get("case_id"), "result case_id")
        execution_status = row.get("execution_status")
        if execution_status == "succeeded":
            successful_case_ids.append(case_id)
        elif execution_status == "failed":
            failed_case_ids.append(case_id)
        else:
            raise ValueError("result execution_status is invalid")
        result_case_ids.append(case_id)
    if len(set(result_case_ids)) != len(result_case_ids):
        raise ValueError("run results contain duplicate case IDs")
    result_ids = set(result_case_ids)
    if any(case_id not in set(ordered_case_ids) for case_id in result_case_ids):
        raise ValueError("run results contain a case outside the run identity")
    if result_case_ids != [case_id for case_id in ordered_case_ids if case_id in result_ids]:
        raise ValueError("run results are not in dataset order")
    if progress.get("total_cases") != len(ordered_case_ids):
        raise ValueError("run progress total_cases does not match run identity")
    if progress.get("completed_cases") != len(results):
        raise ValueError("run progress completed_cases does not match results")
    if progress.get("successful_cases") != len(successful_case_ids):
        raise ValueError("run progress successful_cases does not match results")
    if progress.get("attempted_case_ids") != result_case_ids:
        raise ValueError("run progress attempted case IDs do not match results")
    if progress.get("successful_case_ids") != successful_case_ids:
        raise ValueError("run progress successful case IDs do not match results")
    if progress.get("failed_case_ids") != failed_case_ids:
        raise ValueError("run progress failed case IDs do not match results")
    if progress.get("in_flight_case_ids") != []:
        raise ValueError("terminal run progress has in-flight cases")
    expected_status = (
        "completed"
        if successful_case_ids
        and len(successful_case_ids) == len(ordered_case_ids)
        else "degraded"
        if successful_case_ids
        else "failed"
    )
    if status != expected_status:
        raise ValueError("run progress status does not match execution outcomes")
    return status


def load_run_bundle(output_dir: Path) -> ValidatedRunBundle:
    """Load a run only when its complete manifest authority validates."""
    lexical = Path(os.path.abspath(os.fspath(output_dir)))
    try:
        directory = authority_io.open_bound_directory(lexical)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        raise ValueError("run bundle output directory is missing or unsafe") from exc
    try:
        expected_names = {*TERMINAL_ARTIFACT_NAMES, RUN_MANIFEST_FILENAME}
        if set(authority_io.list_children(directory)) != expected_names:
            raise ValueError("run bundle file inventory is invalid")
        payloads = {
            name: _read_exact_file(directory, name)
            for name in sorted(expected_names)
        }
        if set(authority_io.list_children(directory)) != expected_names:
            raise ValueError("run bundle inventory changed while reading")
    finally:
        directory.close()

    manifest = _json_object(payloads[RUN_MANIFEST_FILENAME], RUN_MANIFEST_FILENAME)
    if set(manifest) != _MANIFEST_FIELDS:
        raise ValueError("run manifest schema is invalid")
    if (
        manifest.get("schema_version") != RUN_MANIFEST_SCHEMA_VERSION
        or manifest.get("hash_algorithm") != "sha256"
    ):
        raise ValueError("run manifest schema is invalid")
    run_id = _require_string(manifest.get("run_id"), "manifest run_id")
    status = manifest.get("status")
    if status not in _TERMINAL_STATUSES:
        raise ValueError("run manifest status is invalid")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(TERMINAL_ARTIFACT_NAMES):
        raise ValueError("run manifest artifact inventory is invalid")
    for name in TERMINAL_ARTIFACT_NAMES:
        record = artifacts[name]
        if not isinstance(record, dict) or set(record) != {"bytes", "sha256"}:
            raise ValueError(f"run manifest artifact record is invalid: {name}")
        size = record.get("bytes")
        digest = record.get("sha256")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(digest, str)
            or not _SHA256.fullmatch(digest)
        ):
            raise ValueError(f"run manifest artifact record is invalid: {name}")
        content = payloads[name]
        if size != len(content) or digest != _sha256(content):
            raise ValueError(f"run bundle artifact does not match manifest: {name}")

    run_config = _json_object(payloads["run_config.json"], "run_config.json")
    run_identity = validate_run_identity_payload(
        _json_object(payloads["run_identity.json"], "run_identity.json")
    ).to_dict()
    progress = _json_object(payloads["progress.json"], "progress.json")
    results = _jsonl_objects(payloads["results.jsonl"])
    try:
        summary = payloads["summary.md"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("summary.md is not valid UTF-8") from exc
    validated_status = _validate_terminal_cross_links(
        expected_run_id=run_id,
        run_config=run_config,
        run_identity=run_identity,
        results=results,
        progress=progress,
    )
    controls = run_identity["always_controls"]
    successful_count = sum(row["execution_status"] == "succeeded" for row in results)
    expected_cross_links = {
        "status": validated_status,
        "run_identity_fingerprint": run_identity["identity_fingerprint"],
        "ordered_case_ids_fingerprint": controls["ordered_case_ids_fingerprint"],
        "result_count": len(results),
        "successful_result_count": successful_count,
        "failed_result_count": len(results) - successful_count,
    }
    for field, expected in expected_cross_links.items():
        if manifest.get(field) != expected:
            raise ValueError(f"run manifest cross-link is invalid: {field}")
    return ValidatedRunBundle(
        output_dir=lexical,
        run_id=run_id,
        status=validated_status,
        manifest=manifest,
        run_config=run_config,
        run_identity=run_identity,
        results=results,
        summary=summary,
        progress=progress,
    )
