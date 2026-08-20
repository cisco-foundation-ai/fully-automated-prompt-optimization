# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Immutable content-addressed publication for evaluation assets."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from src.hephaestus.artifact_io import (
    atomic_copy_file,
    atomic_write_json,
    sync_directory,
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
) -> dict[str, Any]:
    """Build the deterministic identity that addresses one generation."""
    _require_sha256(build_fingerprint, "build fingerprint")
    _require_logical_keys(split_paths)
    logical_files: dict[str, dict[str, Any]] = {}
    for split in sorted(LOGICAL_SPLITS):
        path = Path(split_paths[split])
        _require_regular_file(path, f"generation source {split}")
        logical_files[split] = {
            "filename": f"{split}.jsonl",
            "bytes": path.stat().st_size,
            "sha256": _file_sha256(path),
        }
    return {
        "schema_version": GENERATION_DESCRIPTOR_SCHEMA_VERSION,
        "hash_algorithm": "sha256",
        "build_fingerprint": build_fingerprint,
        "logical_files": logical_files,
    }


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
) -> InstalledGeneration:
    """Materialize, validate, and install one immutable generation."""
    descriptor = build_generation_descriptor(split_paths, build_fingerprint)
    generation_id = generation_id_for_descriptor(descriptor)
    manifest = {
        "schema_version": GENERATION_MANIFEST_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "asset_id": asset_id,
        "generation_id": generation_id,
        "descriptor": descriptor,
    }
    root = Path(catalog_root).absolute()
    _require_symlink_free_path(root, trusted_root or root)
    generations_root = root / "generations"
    if root.is_symlink() or generations_root.is_symlink():
        raise ValueError("evaluation asset catalog cannot be a symlink")
    generations_root.mkdir(parents=True, exist_ok=True)
    target = generations_root / generation_id
    if target.exists() or target.is_symlink():
        return _validate_generation(
            root,
            generation_id,
            expected_tenant_id=tenant_id,
            expected_asset_id=asset_id,
            expected_descriptor=descriptor,
            collision=True,
        )

    temporary = Path(
        tempfile.mkdtemp(
            dir=generations_root,
            prefix=f".{generation_id}.",
            suffix=".tmp",
        )
    )
    try:
        _call_fault(fault_hook, "after_generation_temp_created")
        for split in LOGICAL_SPLITS:
            atomic_copy_file(split_paths[split], temporary / f"{split}.jsonl")
            _call_fault(fault_hook, f"after_generation_split_{split}")
        atomic_write_json(temporary / "generation_manifest.json", manifest)
        _call_fault(fault_hook, "after_generation_manifest_write")
        sync_directory(temporary)
        _call_fault(fault_hook, "after_generation_temp_sync")
        _validate_generation_directory(
            temporary,
            manifest,
            expected_descriptor=descriptor,
        )
        if target.exists() or target.is_symlink():
            return _validate_generation(
                root,
                generation_id,
                expected_tenant_id=tenant_id,
                expected_asset_id=asset_id,
                expected_descriptor=descriptor,
                collision=True,
            )
        os.rename(temporary, target)
        temporary = None
        sync_directory(generations_root)
        _call_fault(fault_hook, "after_generation_install")
    finally:
        if temporary is not None:
            _remove_owned_temporary(temporary, generations_root, generation_id)
    return _validate_generation(
        root,
        generation_id,
        expected_tenant_id=tenant_id,
        expected_asset_id=asset_id,
        expected_descriptor=descriptor,
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


def write_release_pointer(catalog_root: Path, pointer: Mapping[str, Any]) -> None:
    """Atomically replace the sole release authority after strict validation."""
    _validate_release_pointer(pointer)
    atomic_write_json(Path(catalog_root) / "release.json", pointer)


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
    _require_symlink_free_path(root, trusted_root or root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("evaluation asset catalog is missing or a symlink")
    pointer_path = root / "release.json"
    _require_regular_file(pointer_path, "release pointer")
    pointer_bytes = pointer_path.read_bytes()
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
    _require_symlink_free_path(root, trusted_root or root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("evaluation asset catalog is missing or a symlink")
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
    _require_symlink_free_path(catalog_root, trusted_root or catalog_root)
    if catalog_root.is_symlink():
        raise ValueError("historical generation catalog cannot be a symlink")
    expected = catalog_root / "generations" / generation_id
    if directory != expected:
        raise ValueError("historical generation path escapes its catalog")
    return _validate_generation(
        catalog_root,
        generation_id,
        expected_tenant_id=expected_tenant_id,
        expected_asset_id=expected_asset_id,
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
) -> InstalledGeneration:
    try:
        if not _GENERATION_ID.fullmatch(generation_id):
            raise ValueError("generation identity is invalid")
        generations_root = catalog_root / "generations"
        if generations_root.is_symlink() or not generations_root.is_dir():
            raise ValueError("generation root is missing or a symlink")
        directory = generations_root / generation_id
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("generation directory is missing or a symlink")
        manifest_path = directory / "generation_manifest.json"
        _require_regular_file(manifest_path, "generation manifest")
        manifest_bytes = manifest_path.read_bytes()
        manifest = _strict_json_object(manifest_bytes, "generation manifest")
        descriptor = _validate_generation_directory(
            directory,
            manifest,
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
    directory: Path,
    manifest: Mapping[str, Any],
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
    expected_names = {
        "generation_manifest.json",
        *(f"{split}.jsonl" for split in LOGICAL_SPLITS),
    }
    if {path.name for path in directory.iterdir()} != expected_names:
        raise ValueError("generation file inventory is invalid")
    for split in LOGICAL_SPLITS:
        path = directory / f"{split}.jsonl"
        _require_regular_file(path, f"generation split {split}")
        record = descriptor["logical_files"][split]
        if path.stat().st_size != record["bytes"] or _file_sha256(path) != record[
            "sha256"
        ]:
            raise ValueError("generation split content is inconsistent")
    return descriptor


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


def _require_regular_file(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"{label} cannot be a symlink")
    if not path.is_file():
        raise ValueError(f"{label} must be a regular file")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _call_fault(hook: Callable[[str], None] | None, name: str) -> None:
    if hook is not None:
        hook(name)


def _remove_owned_temporary(
    temporary: Path,
    generations_root: Path,
    generation_id: str,
) -> None:
    expected_prefix = f".{generation_id}."
    if (
        temporary.parent == generations_root
        and temporary.name.startswith(expected_prefix)
        and temporary.name.endswith(".tmp")
        and not temporary.is_symlink()
    ):
        shutil.rmtree(temporary)
