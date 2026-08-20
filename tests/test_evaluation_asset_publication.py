# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for immutable Evaluation Asset Studio catalog generations."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pytest

from src.hephaestus import artifact_io
from src.hephaestus.evaluation_assets.publication import (
    LOGICAL_SPLITS,
    build_generation_descriptor,
    build_release_pointer,
    install_generation,
    resolve_evaluation_asset_release,
    validate_historical_generation,
    write_release_pointer,
)


def _splits(root: Path, suffix: str = "one") -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for split in LOGICAL_SPLITS:
        path = root / "workspace" / f"{split}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"case_id": f"{split}-{suffix}"}) + "\n",
            encoding="utf-8",
        )
        paths[split] = path
    return paths


def test_generation_descriptor_is_content_addressed_and_audit_independent(
    tmp_path: Path,
) -> None:
    """Only split bytes and deterministic build fingerprint address a generation."""
    splits = _splits(tmp_path)

    first = build_generation_descriptor(splits, "a" * 64)
    repeated = build_generation_descriptor(splits, "a" * 64)

    assert first == repeated
    assert set(first) == {
        "schema_version",
        "hash_algorithm",
        "build_fingerprint",
        "logical_files",
    }
    assert list(first["logical_files"]) == sorted(LOGICAL_SPLITS)
    changed = dict(first)
    changed["build_fingerprint"] = "b" * 64
    assert changed != first


def test_generation_install_reuses_exact_content_and_rejects_collision(
    tmp_path: Path,
) -> None:
    """An immutable address is reused exactly and never overwritten on mismatch."""
    catalog = tmp_path / "catalog"
    splits = _splits(tmp_path)
    first = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=splits,
        build_fingerprint="a" * 64,
    )
    before = {
        path.name: path.read_bytes() for path in first.generation_dir.iterdir()
    }

    repeated = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=splits,
        build_fingerprint="a" * 64,
    )
    assert repeated.generation_id == first.generation_id
    assert {
        path.name: path.read_bytes() for path in first.generation_dir.iterdir()
    } == before

    (first.generation_dir / "train.jsonl").write_text("collision\n", encoding="utf-8")
    with pytest.raises(ValueError, match="immutable generation collision"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=splits,
            build_fingerprint="a" * 64,
        )
    assert (first.generation_dir / "train.jsonl").read_text() == "collision\n"


def test_resolver_returns_one_frozen_pointer_snapshot_and_rejects_symlink(
    tmp_path: Path,
) -> None:
    """A resolver captures one complete immutable release and rejects symlinks."""
    catalog = tmp_path / "catalog"
    generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path),
        build_fingerprint="a" * 64,
    )
    pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=generation,
        stage_8_receipt_sha256="b" * 64,
        build_provenance_sha256="c" * 64,
        published_at="2026-08-20T00:00:00+00:00",
    )
    write_release_pointer(catalog, pointer)

    resolved = resolve_evaluation_asset_release(
        catalog,
        expected_tenant_id="tenant",
        expected_asset_id="asset",
    )
    assert resolved.generation_id == generation.generation_id
    assert resolved.pointer_sha256 == hashlib.sha256(
        (catalog / "release.json").read_bytes()
    ).hexdigest()
    with pytest.raises(TypeError):
        resolved.files["train"] = tmp_path / "other"  # type: ignore[index]
    with pytest.raises(TypeError):
        resolved.pointer["logical_files"]["train"] = "other.jsonl"
    with pytest.raises(TypeError):
        resolved.descriptor["logical_files"]["train"]["sha256"] = "0" * 64

    target = generation.files["train"]
    saved = target.read_bytes()
    target.unlink()
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes(saved)
    target.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        resolve_evaluation_asset_release(catalog)


def test_pointer_switch_exposes_only_complete_old_or_new_snapshot(tmp_path: Path) -> None:
    """Replacing one pointer switches the four-file release as one unit."""
    catalog = tmp_path / "catalog"
    old = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "old", "old"),
        build_fingerprint="a" * 64,
    )
    new = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "new", "new"),
        build_fingerprint="b" * 64,
    )
    old_pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=old,
        stage_8_receipt_sha256="c" * 64,
        build_provenance_sha256="d" * 64,
        published_at="2026-08-20T00:00:00+00:00",
    )
    new_pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=new,
        stage_8_receipt_sha256="e" * 64,
        build_provenance_sha256="f" * 64,
        published_at="2026-08-20T00:00:01+00:00",
    )
    write_release_pointer(catalog, old_pointer)
    captured_old = resolve_evaluation_asset_release(catalog)
    write_release_pointer(catalog, new_pointer)
    captured_new = resolve_evaluation_asset_release(catalog)

    assert {path.read_bytes() for path in captured_old.files.values()} == {
        path.read_bytes() for path in old.files.values()
    }
    assert {path.read_bytes() for path in captured_new.files.values()} == {
        path.read_bytes() for path in new.files.values()
    }
    assert captured_old.generation_id != captured_new.generation_id


def test_concurrent_pointer_switch_readers_observe_only_old_or_new(
    tmp_path: Path,
) -> None:
    """Pointer-once resolution never combines files across racing generations."""
    catalog = tmp_path / "catalog"
    old = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "old", "old"),
        build_fingerprint="1" * 64,
    )
    new = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "new", "new"),
        build_fingerprint="2" * 64,
    )
    pointers = [
        build_release_pointer(
            tenant_id="tenant",
            asset_id="asset",
            generation=generation,
            stage_8_receipt_sha256=receipt_hash,
            build_provenance_sha256=provenance_hash,
            published_at=published_at,
        )
        for generation, receipt_hash, provenance_hash, published_at in (
            (old, "3" * 64, "4" * 64, "2026-08-20T00:00:00+00:00"),
            (new, "5" * 64, "6" * 64, "2026-08-20T00:00:01+00:00"),
        )
    ]
    write_release_pointer(catalog, pointers[0])
    start = threading.Event()
    failures: list[str] = []
    observed: set[str] = set()

    def writer() -> None:
        start.wait()
        for index in range(100):
            write_release_pointer(catalog, pointers[index % 2])

    def reader() -> None:
        start.wait()
        for _ in range(100):
            snapshot = resolve_evaluation_asset_release(catalog)
            suffixes = {
                json.loads(path.read_text(encoding="utf-8"))["case_id"].split("-")[-1]
                for path in snapshot.files.values()
            }
            expected = "old" if snapshot.generation_id == old.generation_id else "new"
            if snapshot.generation_id not in {old.generation_id, new.generation_id}:
                failures.append("unknown generation")
            elif suffixes != {expected}:
                failures.append(f"mixed snapshot: {sorted(suffixes)}")
            observed.add(expected)

    threads = [threading.Thread(target=writer), *[
        threading.Thread(target=reader) for _ in range(3)
    ]]
    for thread in threads:
        thread.start()
    start.set()
    for thread in threads:
        thread.join(timeout=10)

    assert not any(thread.is_alive() for thread in threads)
    assert failures == []
    assert observed <= {"old", "new"}
    assert observed


def test_pointer_replace_failure_preserves_exact_old_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed pointer replacement leaves the new generation nonauthoritative."""
    catalog = tmp_path / "catalog"
    old = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "old", "old"),
        build_fingerprint="1" * 64,
    )
    new = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "new", "new"),
        build_fingerprint="2" * 64,
    )
    old_pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=old,
        stage_8_receipt_sha256="3" * 64,
        build_provenance_sha256="4" * 64,
        published_at="2026-08-20T00:00:00+00:00",
    )
    new_pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=new,
        stage_8_receipt_sha256="5" * 64,
        build_provenance_sha256="6" * 64,
        published_at="2026-08-20T00:00:01+00:00",
    )
    write_release_pointer(catalog, old_pointer)
    pointer_path = catalog / "release.json"
    pointer_bytes = pointer_path.read_bytes()
    old_snapshot = {
        split: path.read_bytes() for split, path in old.files.items()
    }
    real_replace = artifact_io.os.replace

    def fail_release_replace(source: Path, destination: Path) -> None:
        if Path(destination) == pointer_path:
            raise OSError("injected pointer replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(artifact_io.os, "replace", fail_release_replace)
    with pytest.raises(OSError, match="pointer replace failure"):
        write_release_pointer(catalog, new_pointer)

    assert pointer_path.read_bytes() == pointer_bytes
    resolved = resolve_evaluation_asset_release(catalog)
    assert resolved.generation_id == old.generation_id
    assert {
        split: path.read_bytes() for split, path in resolved.files.items()
    } == old_snapshot
    assert new.generation_dir.is_dir()
    assert new.generation_id != resolved.generation_id


def test_historical_generation_rejects_noncanonical_path(tmp_path: Path) -> None:
    """Explicit historical reads cannot smuggle parent traversal components."""
    catalog = tmp_path / "catalog"
    generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path),
        build_fingerprint="1" * 64,
    )
    noncanonical = (
        catalog
        / "generations"
        / ".."
        / "generations"
        / generation.generation_id
    )

    with pytest.raises(ValueError, match="path"):
        validate_historical_generation(noncanonical)


def test_catalog_rejects_symlinked_ancestor_inside_trusted_root(
    tmp_path: Path,
) -> None:
    """A catalog cannot cross a symlink below its caller-declared trust root."""
    trusted = tmp_path / "trusted"
    actual = tmp_path / "actual" / "tenant"
    actual.mkdir(parents=True)
    trusted.mkdir()
    (trusted / "tenant").symlink_to(actual, target_is_directory=True)
    catalog = trusted / "tenant" / "datasets" / "evaluation_assets" / "asset"

    with pytest.raises(ValueError, match="symlink"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(tmp_path),
            build_fingerprint="1" * 64,
            trusted_root=trusted,
        )


def test_catalog_rejects_parent_traversal_below_trusted_root(tmp_path: Path) -> None:
    """Lexical parent components cannot make trusted-root containment ambiguous."""
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    catalog = trusted / "tenant" / ".." / "outside" / "asset"

    with pytest.raises(ValueError, match="canonical"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(tmp_path),
            build_fingerprint="1" * 64,
            trusted_root=trusted,
        )


@pytest.mark.parametrize(
    ("expected_tenant_id", "expected_asset_id"),
    [("other-tenant", "asset"), ("tenant", "other-asset")],
)
def test_historical_generation_binds_manifest_to_requested_catalog_identity(
    tmp_path: Path,
    expected_tenant_id: str,
    expected_asset_id: str,
) -> None:
    """Historical paths cannot reuse generation bytes across tenant/asset catalogs."""
    catalog = tmp_path / "tenant" / "datasets" / "evaluation_assets" / "asset"
    generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path),
        build_fingerprint="1" * 64,
    )

    with pytest.raises(ValueError, match="identity"):
        validate_historical_generation(
            generation.generation_dir,
            expected_tenant_id=expected_tenant_id,
            expected_asset_id=expected_asset_id,
            trusted_root=tmp_path,
        )
