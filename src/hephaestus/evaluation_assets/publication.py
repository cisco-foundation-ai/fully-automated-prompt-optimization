# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Immutable content-addressed publication for evaluation assets."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from src.hephaestus.artifact_io import (
    atomic_write_bytes_at,
    rename_noreplace_at,
)
from src.hephaestus.evaluation_assets.control_jsonl import (
    LocalAuthorityFile,
    open_local_authority_directory,
    read_local_authority_file_with_identity_at,
    resolve_local_authority_file,
)
from src.hephaestus.evaluation_assets.provenance import canonical_sha256

GENERATION_DESCRIPTOR_SCHEMA_VERSION = (
    "fapo-evaluation-generation-descriptor-v1"
)
GENERATION_MANIFEST_SCHEMA_VERSION = "fapo-evaluation-generation-manifest-v1"
RELEASE_SCHEMA_VERSION = "fapo-evaluation-release-v1"
LOGICAL_SPLITS = ("train", "validation", "test", "regression_trusted")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GENERATION_ID = re.compile(r"^sha256-[0-9a-f]{64}$")
_DESCRIPTOR_FIELDS = {
    "schema_version",
    "hash_algorithm",
    "build_fingerprint",
    "logical_files",
}
_MANIFEST_FIELDS = {
    "schema_version",
    "tenant_id",
    "asset_id",
    "generation_id",
    "descriptor",
}
_RELEASE_FIELDS = {
    "schema_version",
    "tenant_id",
    "asset_id",
    "generation_id",
    "generation_manifest_sha256",
    "stage_8_receipt_sha256",
    "build_provenance_sha256",
    "build_fingerprint",
    "logical_files",
    "published_at",
}


@dataclass(frozen=True)
class InstalledGeneration:
    """One verified immutable generation available below a catalog root."""

    generation_id: str
    generation_dir: Path
    generation_manifest_sha256: str
    descriptor: Mapping[str, Any]
    manifest: Mapping[str, Any]
    files: Mapping[str, Path]


@dataclass(frozen=True)
class ResolvedEvaluationAssetRelease:
    """One pointer-once immutable release snapshot for readers."""

    pointer_path: Path
    pointer_sha256: str
    pointer: Mapping[str, Any]
    generation_id: str
    generation_dir: Path
    generation_manifest_sha256: str
    stage_8_receipt_sha256: str
    build_provenance_sha256: str
    build_fingerprint: str
    descriptor: Mapping[str, Any]
    manifest: Mapping[str, Any]
    files: Mapping[str, Path]

    def path_for(self, logical_split: str) -> Path:
        """Return one split from this already captured release snapshot."""
        try:
            return self.files[logical_split]
        except KeyError as exc:
            raise ValueError(f"Unknown evaluation split: {logical_split}") from exc


def build_generation_descriptor(
    split_paths: Mapping[str, Path],
    build_fingerprint: str,
    *,
    trusted_root: Path | None = None,
    split_payloads: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Build the deterministic identity that addresses one generation."""
    descriptor, _ = _generation_descriptor_and_bytes(
        split_paths,
        build_fingerprint,
        trusted_root=trusted_root,
        split_payloads=split_payloads,
    )
    return descriptor


def _generation_descriptor_and_bytes(
    split_paths: Mapping[str, Path],
    build_fingerprint: str,
    *,
    trusted_root: Path | None,
    split_payloads: Mapping[str, bytes] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Capture split identity and payload from the same no-follow handles."""
    _require_sha256(build_fingerprint, "build fingerprint")
    _require_logical_keys(split_paths)
    if split_payloads is not None:
        _require_logical_keys(split_payloads)
        if any(not isinstance(payload, bytes) for payload in split_payloads.values()):
            raise TypeError("captured generation split payloads must be bytes")
    logical_files: dict[str, dict[str, Any]] = {}
    payloads: dict[str, bytes] = {}
    for split in sorted(LOGICAL_SPLITS):
        path = Path(split_paths[split]).absolute()
        payload = (
            split_payloads[split]
            if split_payloads is not None
            else _authority_bytes(
                path,
                (
                    Path(trusted_root).absolute()
                    if trusted_root is not None
                    else path.parent
                ),
                f"generation source {split}",
            )
        )
        payloads[split] = payload
        logical_files[split] = {
            "filename": f"{split}.jsonl",
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    descriptor = {
        "schema_version": GENERATION_DESCRIPTOR_SCHEMA_VERSION,
        "hash_algorithm": "sha256",
        "build_fingerprint": build_fingerprint,
        "logical_files": logical_files,
    }
    return descriptor, payloads


def generation_id_for_descriptor(descriptor: Mapping[str, Any]) -> str:
    """Return the immutable address for one valid generation descriptor."""
    _validate_descriptor(descriptor)
    return f"sha256-{canonical_sha256(dict(descriptor))}"


def install_generation(
    catalog_root: Path,
    *,
    tenant_id: str,
    asset_id: str,
    split_paths: Mapping[str, Path],
    build_fingerprint: str,
    fault_hook: Callable[[str], None] | None = None,
    trusted_root: Path | None = None,
    split_payloads: Mapping[str, bytes] | None = None,
) -> InstalledGeneration:
    """Materialize, validate, and install one immutable generation."""
    root = Path(catalog_root).absolute()
    authority_root = (
        Path(trusted_root).absolute()
        if trusted_root is not None
        else _nearest_existing_ancestor(root)
    )
    _require_symlink_free_path(root, authority_root)
    descriptor, split_payloads = _generation_descriptor_and_bytes(
        split_paths,
        build_fingerprint,
        trusted_root=trusted_root,
        split_payloads=split_payloads,
    )
    generation_id = generation_id_for_descriptor(descriptor)
    manifest = {
        "schema_version": GENERATION_MANIFEST_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "asset_id": asset_id,
        "generation_id": generation_id,
        "descriptor": descriptor,
    }
    with open_local_authority_directory(
        root,
        authority_root,
        create=True,
    ) as catalog_descriptor:
        generations_descriptor = _open_or_create_child_directory(
            catalog_descriptor,
            "generations",
        )
        try:
            if _exact_directory_entry_exists(
                generations_descriptor,
                generation_id,
            ):
                return _validate_generation(
                    root,
                    generation_id,
                    expected_tenant_id=tenant_id,
                    expected_asset_id=asset_id,
                    expected_descriptor=descriptor,
                    collision=True,
                    trusted_root=authority_root,
                )

            temporary_name = f".{generation_id}.{uuid.uuid4().hex}.tmp"
            os.mkdir(temporary_name, 0o700, dir_fd=generations_descriptor)
            temporary_descriptor = _open_exact_child_directory(
                generations_descriptor,
                temporary_name,
            )
            try:
                if os.listdir(temporary_descriptor):
                    raise ValueError(
                        "new temporary generation was replaced before opening"
                    )
                temporary_stat = os.fstat(temporary_descriptor)
                temporary_identity = (
                    temporary_stat.st_dev,
                    temporary_stat.st_ino,
                    stat.S_IFMT(temporary_stat.st_mode),
                )
                _call_fault(fault_hook, "after_generation_temp_created")
                for split in LOGICAL_SPLITS:
                    atomic_write_bytes_at(
                        temporary_descriptor,
                        f"{split}.jsonl",
                        split_payloads[split],
                    )
                    _call_fault(fault_hook, f"after_generation_split_{split}")
                atomic_write_bytes_at(
                    temporary_descriptor,
                    "generation_manifest.json",
                    _persisted_json_bytes(manifest),
                )
                _call_fault(fault_hook, "after_generation_manifest_write")
                os.fsync(temporary_descriptor)
                _call_fault(fault_hook, "after_generation_temp_sync")
                _validate_generation_directory_descriptor(
                    temporary_descriptor,
                    manifest,
                    split_payloads,
                )
                named_temporary = os.stat(
                    temporary_name,
                    dir_fd=generations_descriptor,
                    follow_symlinks=False,
                )
                if (
                    named_temporary.st_dev,
                    named_temporary.st_ino,
                    stat.S_IFMT(named_temporary.st_mode),
                ) != temporary_identity:
                    raise ValueError(
                        "temporary generation changed before installation"
                    )
                if not rename_noreplace_at(
                    generations_descriptor,
                    temporary_name,
                    generation_id,
                    expected_source=temporary_identity,
                ):
                    return _validate_generation(
                        root,
                        generation_id,
                        expected_tenant_id=tenant_id,
                        expected_asset_id=asset_id,
                        expected_descriptor=descriptor,
                        collision=True,
                        trusted_root=authority_root,
                    )
                installed_stat = os.stat(
                    generation_id,
                    dir_fd=generations_descriptor,
                    follow_symlinks=False,
                )
                installed_identity = (
                    installed_stat.st_dev,
                    installed_stat.st_ino,
                    stat.S_IFMT(installed_stat.st_mode),
                )
                if installed_identity != temporary_identity:
                    raise ValueError(
                        "temporary generation changed during installation"
                    )
                try:
                    _validate_generation_directory_descriptor(
                        temporary_descriptor,
                        manifest,
                        split_payloads,
                    )
                except (OSError, TypeError, UnicodeError, ValueError) as exc:
                    rejected_name = (
                        f".{generation_id}.{uuid.uuid4().hex}.rejected"
                    )
                    if not rename_noreplace_at(
                        generations_descriptor,
                        generation_id,
                        rejected_name,
                        expected_source=temporary_identity,
                    ):
                        raise OSError(
                            "raced generation install could not be quarantined"
                        ) from exc
                    raise ValueError(
                        "temporary generation content changed during installation"
                    ) from exc
                os.fsync(generations_descriptor)
                _call_fault(fault_hook, "after_generation_install")
            finally:
                # A failed install retains its uniquely named staging tree.
                # Portable unlink/rmdir APIs address reusable names rather
                # than the opened inode, so cleanup could delete raced nodes.
                os.close(temporary_descriptor)
        finally:
            os.close(generations_descriptor)
    return _validate_generation(
        root,
        generation_id,
        expected_tenant_id=tenant_id,
        expected_asset_id=asset_id,
        expected_descriptor=descriptor,
        trusted_root=authority_root,
    )


def build_release_pointer(
    *,
    tenant_id: str,
    asset_id: str,
    generation: InstalledGeneration,
    stage_8_receipt_sha256: str,
    build_provenance_sha256: str,
    published_at: str,
) -> dict[str, Any]:
    """Build the sole mutable authority pointer for a release."""
    _require_sha256(stage_8_receipt_sha256, "Stage 8 receipt hash")
    _require_sha256(build_provenance_sha256, "build provenance hash")
    _require_canonical_utc(published_at)
    pointer = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "asset_id": asset_id,
        "generation_id": generation.generation_id,
        "generation_manifest_sha256": generation.generation_manifest_sha256,
        "stage_8_receipt_sha256": stage_8_receipt_sha256,
        "build_provenance_sha256": build_provenance_sha256,
        "build_fingerprint": generation.descriptor["build_fingerprint"],
        "logical_files": {
            split: f"{split}.jsonl" for split in sorted(LOGICAL_SPLITS)
        },
        "published_at": published_at,
    }
    _validate_release_pointer(pointer)
    return pointer


def write_release_pointer(
    catalog_root: Path,
    pointer: Mapping[str, Any],
    *,
    trusted_root: Path | None = None,
    expected_current: bytes | None = None,
    check_expected_current: bool = False,
) -> LocalAuthorityFile:
    """Atomically replace the sole release authority after strict validation."""
    _validate_release_pointer(pointer)
    root = Path(catalog_root).absolute()
    return resolve_local_authority_file(
        root / "release.json",
        Path(trusted_root).absolute() if trusted_root is not None else root,
        access="write",
        write_data=_persisted_json_bytes(pointer),
        expected_write_data=expected_current,
        check_expected_write_data=check_expected_current,
    )


def resolve_evaluation_asset_release(
    catalog_root: Path,
    *,
    expected_tenant_id: str | None = None,
    expected_asset_id: str | None = None,
    expected_stage_8_receipt_sha256: str | None = None,
    trusted_root: Path | None = None,
) -> ResolvedEvaluationAssetRelease:
    """Read the pointer once and return one fully verified frozen snapshot."""
    root = Path(catalog_root).absolute()
    pointer_path = root / "release.json"
    pointer_bytes = _authority_bytes(
        pointer_path,
        Path(trusted_root).absolute() if trusted_root is not None else root,
        "release pointer",
    )
    pointer = _strict_json_object(pointer_bytes, "release pointer")
    return validate_evaluation_asset_release_candidate(
        root,
        pointer,
        expected_tenant_id=expected_tenant_id,
        expected_asset_id=expected_asset_id,
        expected_stage_8_receipt_sha256=expected_stage_8_receipt_sha256,
        pointer_path=pointer_path,
        pointer_bytes=pointer_bytes,
        trusted_root=trusted_root,
    )


def validate_evaluation_asset_release_candidate(
    catalog_root: Path,
    pointer: Mapping[str, Any],
    *,
    expected_tenant_id: str | None = None,
    expected_asset_id: str | None = None,
    expected_stage_8_receipt_sha256: str | None = None,
    pointer_path: Path | None = None,
    pointer_bytes: bytes | None = None,
    trusted_root: Path | None = None,
) -> ResolvedEvaluationAssetRelease:
    """Validate an in-memory pointer before it becomes release authority."""
    root = Path(catalog_root).absolute()
    candidate = dict(pointer)
    if pointer_bytes is None:
        pointer_bytes = _persisted_json_bytes(candidate)
    _validate_release_pointer(pointer)
    if expected_tenant_id is not None and candidate["tenant_id"] != expected_tenant_id:
        raise ValueError("release pointer tenant identity is inconsistent")
    if expected_asset_id is not None and candidate["asset_id"] != expected_asset_id:
        raise ValueError("release pointer asset identity is inconsistent")
    if (
        expected_stage_8_receipt_sha256 is not None
        and candidate["stage_8_receipt_sha256"]
        != expected_stage_8_receipt_sha256
    ):
        raise ValueError("release pointer Stage 8 receipt is inconsistent")
    generation = _validate_generation(
        root,
        candidate["generation_id"],
        expected_tenant_id=candidate["tenant_id"],
        expected_asset_id=candidate["asset_id"],
        trusted_root=trusted_root or root,
    )
    if (
        candidate["generation_manifest_sha256"]
        != generation.generation_manifest_sha256
        or candidate["build_fingerprint"]
        != generation.descriptor["build_fingerprint"]
        or candidate["logical_files"]
        != {split: f"{split}.jsonl" for split in sorted(LOGICAL_SPLITS)}
    ):
        raise ValueError("release pointer generation links are inconsistent")
    return ResolvedEvaluationAssetRelease(
        pointer_path=pointer_path or root / "release.json",
        pointer_sha256=hashlib.sha256(pointer_bytes).hexdigest(),
        pointer=_freeze_json(candidate),
        generation_id=generation.generation_id,
        generation_dir=generation.generation_dir,
        generation_manifest_sha256=generation.generation_manifest_sha256,
        stage_8_receipt_sha256=candidate["stage_8_receipt_sha256"],
        build_provenance_sha256=candidate["build_provenance_sha256"],
        build_fingerprint=candidate["build_fingerprint"],
        descriptor=generation.descriptor,
        manifest=generation.manifest,
        files=generation.files,
    )


def _persisted_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def validate_historical_generation(
    generation_dir: Path,
    *,
    expected_tenant_id: str | None = None,
    expected_asset_id: str | None = None,
    trusted_root: Path | None = None,
) -> InstalledGeneration:
    """Validate an explicitly requested immutable historical generation path."""
    supplied = Path(generation_dir)
    if ".." in supplied.parts:
        raise ValueError("historical generation path is not canonical")
    directory = supplied.absolute()
    generation_id = directory.name
    if not _GENERATION_ID.fullmatch(generation_id):
        raise ValueError("historical generation path has an invalid identity")
    catalog_root = directory.parent.parent
    expected = catalog_root / "generations" / generation_id
    if directory != expected:
        raise ValueError("historical generation path escapes its catalog")
    return _validate_generation(
        catalog_root,
        generation_id,
        expected_tenant_id=expected_tenant_id,
        expected_asset_id=expected_asset_id,
        trusted_root=trusted_root or catalog_root,
    )


def _require_symlink_free_path(path: Path, trusted_root: Path) -> None:
    """Reject symlinks on every lexical component below a declared trust root."""
    supplied = Path(path)
    supplied_anchor = Path(trusted_root)
    if ".." in supplied.parts or ".." in supplied_anchor.parts:
        raise ValueError("evaluation asset trusted path is not canonical")
    candidate = supplied.absolute()
    anchor = supplied_anchor.absolute()
    if candidate != anchor and anchor not in candidate.parents:
        raise ValueError("evaluation asset path escapes its trusted root")
    current = anchor
    if current.is_symlink():
        raise ValueError("evaluation asset trusted path cannot be a symlink")
    for part in candidate.relative_to(anchor).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("evaluation asset trusted path cannot contain a symlink")


def _validate_generation(
    catalog_root: Path,
    generation_id: str,
    *,
    expected_tenant_id: str | None = None,
    expected_asset_id: str | None = None,
    expected_descriptor: Mapping[str, Any] | None = None,
    collision: bool = False,
    trusted_root: Path | None = None,
) -> InstalledGeneration:
    try:
        if not _GENERATION_ID.fullmatch(generation_id):
            raise ValueError("generation identity is invalid")
        directory = catalog_root / "generations" / generation_id
        member_payloads = _capture_generation_directory(
            directory,
            Path(trusted_root or catalog_root).absolute(),
        )
        manifest_bytes = member_payloads["generation_manifest.json"]
        manifest = _strict_json_object(manifest_bytes, "generation manifest")
        descriptor = _validate_generation_directory(
            manifest,
            member_payloads,
            expected_descriptor=expected_descriptor,
        )
        if manifest["generation_id"] != generation_id:
            raise ValueError("generation manifest identity is inconsistent")
        if expected_tenant_id is not None and manifest["tenant_id"] != expected_tenant_id:
            raise ValueError("generation tenant identity is inconsistent")
        if expected_asset_id is not None and manifest["asset_id"] != expected_asset_id:
            raise ValueError("generation asset identity is inconsistent")
        files = MappingProxyType(
            {split: directory / f"{split}.jsonl" for split in LOGICAL_SPLITS}
        )
        return InstalledGeneration(
            generation_id=generation_id,
            generation_dir=directory,
            generation_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            descriptor=_freeze_json(descriptor),
            manifest=_freeze_json(manifest),
            files=files,
        )
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        if collision:
            raise ValueError("immutable generation collision") from exc
        raise


def _validate_generation_directory(
    manifest: Mapping[str, Any],
    member_payloads: Mapping[str, bytes],
    *,
    expected_descriptor: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if set(manifest) != _MANIFEST_FIELDS:
        raise ValueError("generation manifest schema is invalid")
    if (
        manifest.get("schema_version") != GENERATION_MANIFEST_SCHEMA_VERSION
        or not isinstance(manifest.get("tenant_id"), str)
        or not manifest["tenant_id"]
        or not isinstance(manifest.get("asset_id"), str)
        or not manifest["asset_id"]
        or not isinstance(manifest.get("descriptor"), Mapping)
    ):
        raise ValueError("generation manifest schema is invalid")
    descriptor = manifest["descriptor"]
    _validate_descriptor(descriptor)
    if expected_descriptor is not None and descriptor != expected_descriptor:
        raise ValueError("generation descriptor does not match requested content")
    if manifest.get("generation_id") != generation_id_for_descriptor(descriptor):
        raise ValueError("generation manifest address is invalid")
    for split in LOGICAL_SPLITS:
        payload = member_payloads[f"{split}.jsonl"]
        record = descriptor["logical_files"][split]
        if (
            len(payload) != record["bytes"]
            or hashlib.sha256(payload).hexdigest() != record["sha256"]
        ):
            raise ValueError("generation split content is inconsistent")
    return descriptor


def _capture_generation_directory(
    directory: Path,
    trusted_root: Path,
) -> dict[str, bytes]:
    """Capture exact generation inventory and bytes through one bound dirfd."""
    expected_names = {
        "generation_manifest.json",
        *(f"{split}.jsonl" for split in LOGICAL_SPLITS),
    }
    with open_local_authority_directory(
        directory,
        trusted_root,
    ) as directory_descriptor:
        names_before = set(os.listdir(directory_descriptor))
        if names_before != expected_names:
            raise ValueError("generation file inventory is invalid")
        identities: dict[str, tuple[int, int, int]] = {}
        for name in sorted(expected_names):
            details = os.stat(
                name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
                raise ValueError("generation member is not an exact regular file")
            identities[name] = (
                details.st_dev,
                details.st_ino,
                stat.S_IFMT(details.st_mode),
            )
        payloads: dict[str, bytes] = {}
        for name in sorted(expected_names):
            payload, opened_identity = read_local_authority_file_with_identity_at(
                directory_descriptor,
                name,
            )
            rebound = os.stat(
                name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            rebound_identity = (
                rebound.st_dev,
                rebound.st_ino,
                stat.S_IFMT(rebound.st_mode),
            )
            if opened_identity != identities[name] or rebound_identity != identities[name]:
                raise ValueError("generation member changed while reading")
            payloads[name] = payload
        if set(os.listdir(directory_descriptor)) != names_before:
            raise ValueError("generation file inventory changed while reading")
    return payloads


def _validate_descriptor(descriptor: Mapping[str, Any]) -> None:
    if set(descriptor) != _DESCRIPTOR_FIELDS:
        raise ValueError("generation descriptor schema is invalid")
    if (
        descriptor.get("schema_version") != GENERATION_DESCRIPTOR_SCHEMA_VERSION
        or descriptor.get("hash_algorithm") != "sha256"
    ):
        raise ValueError("generation descriptor schema is invalid")
    _require_sha256(descriptor.get("build_fingerprint"), "build fingerprint")
    logical_files = descriptor.get("logical_files")
    if not isinstance(logical_files, Mapping):
        raise ValueError("generation logical files are invalid")
    _require_logical_keys(logical_files)
    for split in LOGICAL_SPLITS:
        row = logical_files[split]
        if not isinstance(row, Mapping) or set(row) != {
            "filename",
            "bytes",
            "sha256",
        }:
            raise ValueError("generation logical file record is invalid")
        if row.get("filename") != f"{split}.jsonl":
            raise ValueError("generation logical filename is invalid")
        size = row.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("generation logical file size is invalid")
        _require_sha256(row.get("sha256"), "generation logical file hash")


def _validate_release_pointer(pointer: Mapping[str, Any]) -> None:
    if set(pointer) != _RELEASE_FIELDS:
        raise ValueError("release pointer schema is invalid")
    if pointer.get("schema_version") != RELEASE_SCHEMA_VERSION:
        raise ValueError("release pointer schema is invalid")
    for name in ("tenant_id", "asset_id"):
        if not isinstance(pointer.get(name), str) or not pointer[name]:
            raise ValueError("release pointer identity is invalid")
    if not isinstance(pointer.get("generation_id"), str) or not _GENERATION_ID.fullmatch(
        pointer["generation_id"]
    ):
        raise ValueError("release pointer generation identity is invalid")
    for name in (
        "generation_manifest_sha256",
        "stage_8_receipt_sha256",
        "build_provenance_sha256",
        "build_fingerprint",
    ):
        _require_sha256(pointer.get(name), f"release pointer {name}")
    logical_files = pointer.get("logical_files")
    if logical_files != {
        split: f"{split}.jsonl" for split in sorted(LOGICAL_SPLITS)
    }:
        raise ValueError("release pointer logical files are invalid")
    _require_canonical_utc(pointer.get("published_at"))


def _strict_json_object(data: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"{label} contains duplicate keys")
            result[key] = value
        return result

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError(f"{label} contains a non-finite number")
            ),
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_logical_keys(value: Mapping[str, Any]) -> None:
    if set(value) != set(LOGICAL_SPLITS):
        raise ValueError("generation requires the exact logical split set")


def _freeze_json(value: Any) -> Any:
    """Return a recursively immutable defensive snapshot of JSON data."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 value")


def _require_canonical_utc(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("publication timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("publication timestamp is invalid") from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() != timedelta(0)
        or parsed.isoformat() != value
    ):
        raise ValueError("publication timestamp is invalid")


def _authority_bytes(path: Path, trusted_root: Path, label: str) -> bytes:
    last_error: OSError | ValueError | None = None
    for _ in range(32):
        try:
            authority = resolve_local_authority_file(
                path,
                trusted_root,
                access="read",
            )
        except (OSError, ValueError) as exc:
            last_error = exc
            if "file changed while opening" in str(exc):
                continue
            break
        if authority.data is None:
            raise ValueError(f"{label} local authority bytes are missing")
        return authority.data
    raise ValueError(
        f"{label} must be a regular non-symlink local authority file"
    ) from last_error


def _open_or_create_child_directory(
    parent_descriptor: int,
    name: str,
) -> int:
    """Open one exact child directory, creating it relative to a stable parent."""
    try:
        return _open_exact_child_directory(parent_descriptor, name)
    except FileNotFoundError:
        os.mkdir(name, 0o755, dir_fd=parent_descriptor)
        descriptor = _open_exact_child_directory(parent_descriptor, name)
        if os.listdir(descriptor):
            os.close(descriptor)
            raise ValueError(
                "new generation directory was replaced before opening"
            )
        return descriptor


def _open_exact_child_directory(
    parent_descriptor: int,
    name: str,
) -> int:
    """Open and identity-bind one non-symlink directory entry."""
    before = os.stat(
        name,
        dir_fd=parent_descriptor,
        follow_symlinks=False,
    )
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise ValueError("generation authority directory is not exact")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    opened = os.fstat(descriptor)
    if (
        opened.st_dev != before.st_dev
        or opened.st_ino != before.st_ino
        or stat.S_IFMT(opened.st_mode) != stat.S_IFMT(before.st_mode)
    ):
        os.close(descriptor)
        raise ValueError("generation authority directory changed while opening")
    return descriptor


def _nearest_existing_ancestor(path: Path) -> Path:
    """Return the nearest lexical directory usable as an implicit trust root."""
    candidate = path.absolute()
    while True:
        try:
            details = os.lstat(candidate)
        except FileNotFoundError:
            parent = candidate.parent
            if parent == candidate:
                raise ValueError("evaluation asset catalog has no safe ancestor") from None
            candidate = parent
            continue
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
            raise ValueError("evaluation asset catalog ancestor is not exact")
        return candidate


def _exact_directory_entry_exists(
    parent_descriptor: int,
    name: str,
) -> bool:
    """Return whether one exact non-symlink child directory exists."""
    try:
        details = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
        raise ValueError("immutable generation target is not an exact directory")
    return True


def _descriptor_file_bytes(directory_descriptor: int, name: str) -> bytes:
    """Read one regular child file through a stable directory descriptor."""
    before = os.stat(
        name,
        dir_fd=directory_descriptor,
        follow_symlinks=False,
    )
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("generation temporary file is not exact")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, dir_fd=directory_descriptor)
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
            or stat.S_IFMT(opened.st_mode) != stat.S_IFMT(before.st_mode)
        ):
            raise ValueError("generation temporary file changed while opening")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _validate_generation_directory_descriptor(
    directory_descriptor: int,
    manifest: Mapping[str, Any],
    split_payloads: Mapping[str, bytes],
) -> None:
    """Validate the exact temporary inventory without reopening lexical paths."""
    expected_names = {
        "generation_manifest.json",
        *(f"{split}.jsonl" for split in LOGICAL_SPLITS),
    }
    if set(os.listdir(directory_descriptor)) != expected_names:
        raise ValueError("generation file inventory is invalid")
    if _descriptor_file_bytes(
        directory_descriptor,
        "generation_manifest.json",
    ) != _persisted_json_bytes(manifest):
        raise ValueError("generation manifest content is inconsistent")
    for split in LOGICAL_SPLITS:
        if (
            _descriptor_file_bytes(directory_descriptor, f"{split}.jsonl")
            != split_payloads[split]
        ):
            raise ValueError("generation split content is inconsistent")


def _call_fault(hook: Callable[[str], None] | None, name: str) -> None:
    if hook is not None:
        hook(name)
