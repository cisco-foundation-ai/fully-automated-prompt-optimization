# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for immutable Evaluation Asset Studio catalog generations."""

from __future__ import annotations

import hashlib
import json
import shutil
import threading
from pathlib import Path
from typing import Any

import pytest

from src.hephaestus import artifact_io
from src.hephaestus.evaluation_assets import control_jsonl as control_jsonl_module
from src.hephaestus.evaluation_assets import publication as publication_module
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
    with pytest.raises(ValueError, match="exact regular file"):
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
    real_exchange = artifact_io.rename_exchange_at

    def fail_release_exchange(
        directory_descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> None:
        if destination == "release.json":
            raise OSError("injected pointer replace failure")
        real_exchange(directory_descriptor, source, destination, **kwargs)

    monkeypatch.setattr(artifact_io, "rename_exchange_at", fail_release_exchange)
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


def test_pointer_write_retains_verified_parent_through_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A checked catalog cannot be redirected before pointer replacement."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    catalog = trusted_root / "catalog"
    generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(trusted_root),
        build_fingerprint="a" * 64,
        trusted_root=trusted_root,
    )
    pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=generation,
        stage_8_receipt_sha256="b" * 64,
        build_provenance_sha256="c" * 64,
        published_at="2026-08-20T00:00:00+00:00",
    )
    parked_catalog = tmp_path / "parked-catalog"
    external_catalog = tmp_path / "external-catalog"
    external_catalog.mkdir()
    original_resolver = publication_module.resolve_local_authority_file
    original_bound_write = control_jsonl_module.atomic_write_bytes_at
    swapped = False

    def swap_catalog() -> None:
        nonlocal swapped
        if swapped:
            return
        swapped = True
        catalog.rename(parked_catalog)
        catalog.symlink_to(external_catalog, target_is_directory=True)

    def swap_after_prospective_validation(
        path: Path,
        root: Path,
        *,
        access: str,
        write_data: bytes | None = None,
        **kwargs: Any,
    ) -> Any:
        if access == "write" and write_data is None:
            result = original_resolver(path, root, access=access)
            swap_catalog()
            return result
        return original_resolver(
            path,
            root,
            access=access,
            write_data=write_data,
            **kwargs,
        )

    def swap_before_bound_replace(
        directory_descriptor: int,
        filename: str,
        content: bytes,
        *,
        expected_target: tuple[int, int, int] | None | object,
    ) -> None:
        swap_catalog()
        original_bound_write(
            directory_descriptor,
            filename,
            content,
            expected_target=expected_target,
        )

    monkeypatch.setattr(
        publication_module,
        "resolve_local_authority_file",
        swap_after_prospective_validation,
    )
    monkeypatch.setattr(
        control_jsonl_module,
        "atomic_write_bytes_at",
        swap_before_bound_replace,
    )

    with pytest.raises(ValueError):
        write_release_pointer(
            catalog,
            pointer,
            trusted_root=trusted_root,
        )

    assert swapped
    assert catalog.is_symlink()
    assert not (external_catalog / "release.json").exists()


def test_generation_fault_cleanup_cannot_follow_swapped_catalog(
    tmp_path: Path,
) -> None:
    """Temporary cleanup remains bound to the created generation directory."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    catalog = trusted_root / "catalog"
    generations_root = catalog / "generations"
    parked_generations = tmp_path / "parked-generations"
    external_generations = tmp_path / "external-generations"
    external_victim: Path | None = None

    def swap_before_fault_cleanup(phase: str) -> None:
        nonlocal external_victim
        if phase != "after_generation_temp_created":
            return
        temporary_names = [
            child.name
            for child in generations_root.iterdir()
            if child.name.endswith(".tmp")
        ]
        assert len(temporary_names) == 1
        generations_root.rename(parked_generations)
        external_generations.mkdir()
        external_victim = external_generations / temporary_names[0]
        external_victim.mkdir()
        (external_victim / "victim.txt").write_text("KEEP", encoding="utf-8")
        generations_root.symlink_to(
            external_generations,
            target_is_directory=True,
        )
        raise RuntimeError("injected generation fault")

    with pytest.raises(RuntimeError, match="generation fault"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(trusted_root),
            build_fingerprint="a" * 64,
            fault_hook=swap_before_fault_cleanup,
            trusted_root=trusted_root,
        )

    assert external_victim is not None
    assert (external_victim / "victim.txt").read_text(encoding="utf-8") == "KEEP"
    retained = list(parked_generations.iterdir())
    assert len(retained) == 1
    assert retained[0].name.endswith(".tmp")
    assert not any(retained[0].iterdir())


def test_generation_fault_cleanup_never_removes_a_replacement_directory(
    tmp_path: Path,
) -> None:
    """Cleanup retains a raced leaf rather than deleting it by reusable name."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    catalog = trusted_root / "catalog"
    generations_root = catalog / "generations"
    external_victim = tmp_path / "external-victim"
    external_victim.mkdir()
    victim_identity = external_victim.stat()
    parked = tmp_path / "parked-owned-temp"
    swapped = False

    def fail_after_creation(phase: str) -> None:
        nonlocal swapped
        if phase == "after_generation_temp_created":
            temporary = next(generations_root.glob(".*.tmp"))
            temporary.rename(parked)
            external_victim.rename(temporary)
            swapped = True
            raise RuntimeError("injected cleanup race")

    with pytest.raises(RuntimeError, match="cleanup race"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(trusted_root),
            build_fingerprint="a" * 64,
            fault_hook=fail_after_creation,
            trusted_root=trusted_root,
        )

    replacement = next(generations_root.glob(".*.tmp"))
    assert swapped
    assert replacement.stat().st_ino == victim_identity.st_ino
    assert parked.is_dir()
    assert not any(parked.iterdir())


def test_generation_install_atomically_rejects_a_raced_target_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A no-replace install never overwrites a concurrent generation entry."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    catalog = trusted_root / "catalog"
    external_victim = tmp_path / "external-victim"
    external_victim.mkdir()
    victim_identity = external_victim.stat()
    original = publication_module.rename_noreplace_at
    installed_victim: Path | None = None

    def race_target(
        descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> bool:
        nonlocal installed_victim
        installed_victim = catalog / "generations" / destination
        external_victim.rename(installed_victim)
        return original(descriptor, source, destination, **kwargs)

    monkeypatch.setattr(
        publication_module,
        "rename_noreplace_at",
        race_target,
    )

    with pytest.raises(ValueError, match="collision"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(trusted_root),
            build_fingerprint="a" * 64,
            trusted_root=trusted_root,
        )

    assert installed_victim is not None
    assert installed_victim.stat().st_ino == victim_identity.st_ino


def test_bound_atomic_writer_rejects_target_replacement_without_data_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raced target is restored and rejected without deleting either file."""
    target = tmp_path / "target.json"
    target.write_bytes(b"OLD")
    target_identity = target.stat()
    parked = tmp_path / "parked-target.json"
    victim = tmp_path / "victim.json"
    victim.write_bytes(b"KEEP")
    victim_identity = victim.stat()
    original = artifact_io.rename_exchange_at
    swapped = False

    def exchange_after_race(
        descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> None:
        nonlocal swapped
        if not swapped:
            target.rename(parked)
            victim.rename(target)
            swapped = True
        original(descriptor, source, destination, **kwargs)

    monkeypatch.setattr(artifact_io, "rename_exchange_at", exchange_after_race)
    descriptor = artifact_io.os.open(tmp_path, artifact_io.os.O_RDONLY)
    try:
        with pytest.raises(ValueError):
            artifact_io.atomic_write_bytes_at(
                descriptor,
                target.name,
                b"NEW",
                expected_target=(
                    target_identity.st_dev,
                    target_identity.st_ino,
                    target_identity.st_mode & 0o170000,
                ),
            )
    finally:
        artifact_io.os.close(descriptor)

    assert swapped
    assert target.read_bytes() == b"KEEP"
    assert target.stat().st_ino == victim_identity.st_ino
    assert parked.read_bytes() == b"OLD"


@pytest.mark.parametrize("existing_target", [False, True])
def test_bound_atomic_writer_rejects_temporary_source_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_target: bool,
) -> None:
    """A raced temporary name cannot install foreign bytes as authority."""
    target = tmp_path / "target.json"
    if existing_target:
        target.write_bytes(b"OLD")
    parked = tmp_path / "parked-owned-temporary.json"
    victim = tmp_path / "external-victim.json"
    victim.write_bytes(b"VICTIM")
    swapped = False
    original = (
        artifact_io.rename_exchange_at
        if existing_target
        else artifact_io.rename_noreplace_at
    )

    def race_source(
        descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> Any:
        nonlocal swapped
        if not swapped:
            (tmp_path / source).rename(parked)
            victim.rename(tmp_path / source)
            swapped = True
        return original(descriptor, source, destination, **kwargs)

    monkeypatch.setattr(
        artifact_io,
        "rename_exchange_at" if existing_target else "rename_noreplace_at",
        race_source,
    )
    descriptor = artifact_io.os.open(tmp_path, artifact_io.os.O_RDONLY)
    try:
        with pytest.raises(ValueError):
            artifact_io.atomic_write_bytes_at(
                descriptor,
                target.name,
                b"NEW",
            )
    finally:
        artifact_io.os.close(descriptor)

    assert swapped
    assert parked.read_bytes() == b"NEW"
    if existing_target:
        assert target.read_bytes() == b"OLD"
    else:
        assert not target.exists()
    assert any(path.read_bytes() == b"VICTIM" for path in tmp_path.iterdir() if path.is_file())


def test_generation_install_rejects_temporary_source_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raced generation staging name cannot publish a foreign directory."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    catalog = trusted_root / "catalog"
    victim = tmp_path / "external-victim"
    victim.mkdir()
    (victim / "KEEP").write_text("external", encoding="utf-8")
    parked = tmp_path / "parked-owned-generation"
    original = publication_module.rename_noreplace_at
    swapped = False

    def race_source(
        descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> bool:
        nonlocal swapped
        if not swapped:
            (catalog / "generations" / source).rename(parked)
            victim.rename(catalog / "generations" / source)
            swapped = True
        return original(descriptor, source, destination, **kwargs)

    monkeypatch.setattr(publication_module, "rename_noreplace_at", race_source)

    with pytest.raises(ValueError):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(trusted_root),
            build_fingerprint="a" * 64,
            trusted_root=trusted_root,
        )

    assert swapped
    assert parked.is_dir()
    assert (parked / "generation_manifest.json").is_file()
    assert not any(
        child.name.startswith("sha256-")
        for child in (catalog / "generations").iterdir()
    )
    assert any(
        child.is_dir() and (child / "KEEP").is_file()
        for child in (catalog / "generations").iterdir()
    )


@pytest.mark.parametrize("existing_target", [False, True])
def test_bound_atomic_writer_rejects_temporary_content_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_target: bool,
) -> None:
    """Same-inode temp mutation cannot install bytes other than the write payload."""
    target = tmp_path / "target.json"
    if existing_target:
        target.write_bytes(b"OLD")
    original = (
        artifact_io.rename_exchange_at
        if existing_target
        else artifact_io.rename_noreplace_at
    )
    mutated = False

    def mutate_source(
        descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> Any:
        nonlocal mutated
        if not mutated:
            (tmp_path / source).write_bytes(b"EVIL")
            mutated = True
        return original(descriptor, source, destination, **kwargs)

    monkeypatch.setattr(
        artifact_io,
        "rename_exchange_at" if existing_target else "rename_noreplace_at",
        mutate_source,
    )
    descriptor = artifact_io.os.open(tmp_path, artifact_io.os.O_RDONLY)
    try:
        with pytest.raises(ValueError, match="temporary.*content"):
            artifact_io.atomic_write_bytes_at(descriptor, target.name, b"NEW")
    finally:
        artifact_io.os.close(descriptor)

    assert mutated
    if existing_target:
        assert target.read_bytes() == b"OLD"
    else:
        assert not target.exists()
    assert any(path.read_bytes() == b"EVIL" for path in tmp_path.iterdir() if path.is_file())


def test_generation_install_quarantines_same_inode_content_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-inode staged corruption cannot poison a content-addressed generation."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    catalog = trusted_root / "catalog"
    original = publication_module.rename_noreplace_at
    mutated = False

    def mutate_source(
        descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> bool:
        nonlocal mutated
        if not mutated:
            (catalog / "generations" / source / "train.jsonl").write_bytes(b"EVIL")
            mutated = True
        return original(descriptor, source, destination, **kwargs)

    monkeypatch.setattr(publication_module, "rename_noreplace_at", mutate_source)
    with pytest.raises(ValueError, match="temporary generation content changed"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(trusted_root),
            build_fingerprint="a" * 64,
            trusted_root=trusted_root,
        )

    assert mutated
    assert not any(
        child.name.startswith("sha256-")
        for child in (catalog / "generations").iterdir()
    )
    monkeypatch.setattr(publication_module, "rename_noreplace_at", original)
    installed = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(trusted_root),
        build_fingerprint="a" * 64,
        trusted_root=trusted_root,
    )
    assert installed.generation_dir.is_dir()


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


def test_generation_inventory_and_members_share_one_bound_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-name clean directory cannot hide an unexpected generation member."""
    catalog = tmp_path / "catalog"
    generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path),
        build_fingerprint="a" * 64,
    )
    replacement = tmp_path / "clean-generation"
    parked = tmp_path / "parked-generation"
    shutil.copytree(generation.generation_dir, replacement)
    (generation.generation_dir / "unexpected.txt").write_text(
        "unexpected\n",
        encoding="utf-8",
    )
    original_listdir = publication_module.os.listdir
    swapped = False

    def swap_before_inventory(path: int | str | bytes | Path) -> list[str]:
        nonlocal swapped
        if not swapped and isinstance(path, int):
            generation.generation_dir.rename(parked)
            replacement.rename(generation.generation_dir)
            swapped = True
        return original_listdir(path)

    monkeypatch.setattr(publication_module.os, "listdir", swap_before_inventory)
    try:
        with pytest.raises(ValueError, match="inventory"):
            validate_historical_generation(generation.generation_dir)
    finally:
        if swapped:
            generation.generation_dir.rename(replacement)
            parked.rename(generation.generation_dir)

    assert swapped
    assert (generation.generation_dir / "unexpected.txt").is_file()


def test_generation_capture_binds_member_bytes_to_inventoried_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient valid file cannot authenticate persistent corrupt bytes."""
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
    target = generation.files["train"]
    genuine = tmp_path / "genuine-train.jsonl"
    genuine.write_bytes(target.read_bytes())
    target.write_bytes(b'{"case_id":"CORRUPT"}\n')
    parked = tmp_path / "parked-corrupt-train.jsonl"
    original = control_jsonl_module.read_local_authority_file_with_identity_at
    attacked = False

    def supply_transient_genuine_bytes(
        directory_descriptor: int,
        filename: str,
    ) -> tuple[bytes, tuple[int, int, int]]:
        nonlocal attacked
        if filename != "train.jsonl":
            return original(directory_descriptor, filename)
        target.rename(parked)
        genuine.rename(target)
        try:
            result = original(directory_descriptor, filename)
        finally:
            target.rename(genuine)
            parked.rename(target)
        attacked = True
        return result

    monkeypatch.setattr(
        publication_module,
        "read_local_authority_file_with_identity_at",
        supply_transient_genuine_bytes,
    )

    with pytest.raises(ValueError, match="changed while reading"):
        resolve_evaluation_asset_release(
            catalog,
            expected_tenant_id="tenant",
            expected_asset_id="asset",
        )

    assert attacked
    assert target.read_bytes() == b'{"case_id":"CORRUPT"}\n'
    assert genuine.is_file()


def test_generation_install_does_not_quarantine_late_foreign_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-install replacement remains live and is never moved or deleted."""
    catalog = tmp_path / "catalog"
    parked = tmp_path / "parked-owned-generation"
    original = publication_module.rename_noreplace_at
    foreign_inode: int | None = None
    attacked = False

    def replace_after_install(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        **kwargs: Any,
    ) -> bool:
        nonlocal attacked, foreign_inode
        installed = original(
            directory_descriptor,
            source_name,
            target_name,
            **kwargs,
        )
        if installed and target_name.startswith("sha256-") and not attacked:
            target = catalog / "generations" / target_name
            target.rename(parked)
            target.mkdir()
            (target / "KEEP").write_bytes(b"KEEP")
            foreign_inode = target.stat().st_ino
            attacked = True
        return installed

    monkeypatch.setattr(
        publication_module,
        "rename_noreplace_at",
        replace_after_install,
    )

    with pytest.raises(ValueError, match="changed during installation"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(tmp_path),
            build_fingerprint="a" * 64,
        )

    live = next(
        path
        for path in (catalog / "generations").iterdir()
        if path.name.startswith("sha256-")
    )
    assert attacked
    assert live.stat().st_ino == foreign_inode
    assert (live / "KEEP").read_bytes() == b"KEEP"
    assert parked.is_dir()


def test_generation_temp_creation_rejects_foreign_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign directory replacing the new staging name is never populated."""
    catalog = tmp_path / "catalog"
    generations = catalog / "generations"
    generations.mkdir(parents=True)
    parked = generations / "parked-owned-staging"
    foreign = generations / "foreign-staging"
    foreign.mkdir()
    (foreign / "KEEP").write_bytes(b"KEEP")
    original = publication_module.os.mkdir
    attacked = False

    def replace_created_staging(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal attacked
        original(path, mode, dir_fd=dir_fd)
        if (
            isinstance(path, str)
            and path.startswith("..sha256-")
            and path.endswith(".directory")
            and dir_fd is not None
            and not attacked
        ):
            control_jsonl_module.fcntl.flock(
                dir_fd,
                control_jsonl_module.fcntl.LOCK_UN,
            )
            created = catalog / "generations" / path
            created.rename(parked)
            foreign.rename(created)
            attacked = True

    monkeypatch.setattr(publication_module.os, "mkdir", replace_created_staging)

    with pytest.raises(ValueError, match="replaced before opening"):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(tmp_path),
            build_fingerprint="a" * 64,
        )

    live = next(
        path
        for path in (catalog / "generations").iterdir()
        if path.name.endswith(".directory")
    )
    assert attacked
    assert (live / "KEEP").read_bytes() == b"KEEP"
    assert not any(parked.iterdir())


def test_release_pointer_exchange_race_restores_concurrent_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rejected pointer writer cannot remain authoritative after a raw race."""
    catalog = tmp_path / "catalog"
    old_generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "old", "old"),
        build_fingerprint="1" * 64,
    )
    new_generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path / "new", "new"),
        build_fingerprint="2" * 64,
    )
    old_pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=old_generation,
        stage_8_receipt_sha256="3" * 64,
        build_provenance_sha256="4" * 64,
        published_at="2026-08-20T00:00:00+00:00",
    )
    new_pointer = build_release_pointer(
        tenant_id="tenant",
        asset_id="asset",
        generation=new_generation,
        stage_8_receipt_sha256="5" * 64,
        build_provenance_sha256="6" * 64,
        published_at="2026-08-20T00:00:01+00:00",
    )
    write_release_pointer(catalog, old_pointer)
    pointer_path = catalog / "release.json"
    parked_old = catalog / "parked-old-release.json"
    original = artifact_io._rename_with_flags_at
    attacked = False

    def race_after_identity_check(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        *,
        darwin_flags: int,
        linux_flags: int,
    ) -> bool:
        nonlocal attacked
        if target_name == "release.json" and linux_flags == 2 and not attacked:
            pointer_path.rename(parked_old)
            pointer_path.write_bytes(b"FOREIGN-POINTER")
            attacked = True
        return original(
            directory_descriptor,
            source_name,
            target_name,
            darwin_flags=darwin_flags,
            linux_flags=linux_flags,
        )

    monkeypatch.setattr(
        artifact_io,
        "_rename_with_flags_at",
        race_after_identity_check,
    )
    with pytest.raises(ValueError):
        write_release_pointer(catalog, new_pointer)

    assert attacked
    assert pointer_path.read_bytes() == b"FOREIGN-POINTER"
    assert parked_old.read_bytes() == publication_module._persisted_json_bytes(
        old_pointer
    )
    assert any(
        path.read_bytes() == publication_module._persisted_json_bytes(new_pointer)
        for path in catalog.iterdir()
        if path.name.startswith(".release.json.")
    )

    monkeypatch.setattr(artifact_io, "_rename_with_flags_at", original)
    write_release_pointer(catalog, new_pointer)
    assert pointer_path.read_bytes() == publication_module._persisted_json_bytes(
        new_pointer
    )
    assert parked_old.read_bytes() == publication_module._persisted_json_bytes(
        old_pointer
    )


def test_generation_install_race_quarantines_foreign_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source-name race cannot install a foreign immutable generation."""
    catalog = tmp_path / "catalog"
    parked_owned = tmp_path / "parked-owned-generation"
    foreign = tmp_path / "foreign-generation"
    foreign.mkdir()
    (foreign / "KEEP").write_bytes(b"FOREIGN")
    original = artifact_io._rename_with_flags_at
    attacked = False

    def race_after_identity_check(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        *,
        darwin_flags: int,
        linux_flags: int,
    ) -> bool:
        nonlocal attacked
        if (
            target_name.startswith("sha256-")
            and source_name.endswith(".tmp")
            and linux_flags == 1
            and not attacked
        ):
            staging = catalog / "generations" / source_name
            staging.rename(parked_owned)
            foreign.rename(staging)
            attacked = True
        return original(
            directory_descriptor,
            source_name,
            target_name,
            darwin_flags=darwin_flags,
            linux_flags=linux_flags,
        )

    monkeypatch.setattr(
        artifact_io,
        "_rename_with_flags_at",
        race_after_identity_check,
    )
    with pytest.raises(ValueError):
        install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(tmp_path),
            build_fingerprint="a" * 64,
        )

    assert attacked
    assert not any(
        path.name.startswith("sha256-")
        for path in (catalog / "generations").iterdir()
    )
    assert parked_owned.is_dir()
    assert not (parked_owned / "KEEP").exists()
    assert any(
        (path / "KEEP").read_bytes() == b"FOREIGN"
        for path in (catalog / "generations").iterdir()
        if path.name.startswith(".sha256-") and (path / "KEEP").is_file()
    )

    monkeypatch.setattr(artifact_io, "_rename_with_flags_at", original)
    generation = install_generation(
        catalog,
        tenant_id="tenant",
        asset_id="asset",
        split_paths=_splits(tmp_path),
        build_fingerprint="a" * 64,
    )
    assert generation.generation_dir.is_dir()
    assert any(
        (path / "KEEP").read_bytes() == b"FOREIGN"
        for path in (catalog / "generations").iterdir()
        if path.name.startswith(".sha256-") and (path / "KEEP").is_file()
    )


def test_detectable_empty_foreign_generations_namespace_change_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An extra sibling trace fails before a foreign catalog is populated."""
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    parked_owned = catalog / "parked-owned-generations"
    foreign = catalog / "foreign-generations"
    foreign_descriptor: int | None = None
    original = publication_module.os.mkdir
    attacked = False

    def replace_created_generations(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal attacked, foreign_descriptor
        original(path, mode, dir_fd=dir_fd)
        if (
            isinstance(path, str)
            and path.startswith(".generations.")
            and path.endswith(".directory")
            and dir_fd is not None
            and not attacked
        ):
            created = catalog / path
            created.rename(parked_owned)
            original(foreign.name, mode, dir_fd=dir_fd)
            foreign_descriptor = publication_module.os.open(
                foreign,
                publication_module.os.O_RDONLY
                | getattr(publication_module.os, "O_DIRECTORY", 0),
            )
            foreign.rename(created)
            attacked = True

    monkeypatch.setattr(
        publication_module.os,
        "mkdir",
        replace_created_generations,
    )
    try:
        with pytest.raises(ValueError):
            install_generation(
                catalog,
                tenant_id="tenant",
                asset_id="asset",
                split_paths=_splits(tmp_path),
                build_fingerprint="a" * 64,
            )
        assert attacked
        assert foreign_descriptor is not None
        assert publication_module.os.listdir(foreign_descriptor) == []
        assert publication_module.os.listdir(parked_owned) == []
        monkeypatch.setattr(publication_module.os, "mkdir", original)
        generation = install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(tmp_path),
            build_fingerprint="a" * 64,
        )
        assert generation.generation_dir.is_dir()
        assert publication_module.os.listdir(foreign_descriptor) == []
    finally:
        if foreign_descriptor is not None:
            publication_module.os.close(foreign_descriptor)


def test_detectable_empty_foreign_staging_namespace_change_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An extra sibling trace fails before foreign staging is populated."""
    catalog = tmp_path / "catalog"
    generations = catalog / "generations"
    generations.mkdir(parents=True)
    parked_owned = generations / "parked-owned-staging"
    foreign = generations / "foreign-staging"
    foreign_descriptor: int | None = None
    original = publication_module.os.mkdir
    attacked = False

    def replace_created_staging(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal attacked, foreign_descriptor
        original(path, mode, dir_fd=dir_fd)
        if (
            isinstance(path, str)
            and path.startswith("..sha256-")
            and path.endswith(".directory")
            and dir_fd is not None
            and not attacked
        ):
            staging = catalog / "generations" / path
            staging.rename(parked_owned)
            original(foreign.name, mode, dir_fd=dir_fd)
            foreign_descriptor = publication_module.os.open(
                foreign,
                publication_module.os.O_RDONLY
                | getattr(publication_module.os, "O_DIRECTORY", 0),
            )
            foreign.rename(staging)
            attacked = True

    monkeypatch.setattr(publication_module.os, "mkdir", replace_created_staging)
    try:
        with pytest.raises(ValueError):
            install_generation(
                catalog,
                tenant_id="tenant",
                asset_id="asset",
                split_paths=_splits(tmp_path),
                build_fingerprint="a" * 64,
            )
        assert attacked
        assert foreign_descriptor is not None
        assert publication_module.os.listdir(foreign_descriptor) == []
        assert publication_module.os.listdir(parked_owned) == []
        assert not any(
            path.name.startswith("sha256-")
            for path in (catalog / "generations").iterdir()
        )
        monkeypatch.setattr(publication_module.os, "mkdir", original)
        generation = install_generation(
            catalog,
            tenant_id="tenant",
            asset_id="asset",
            split_paths=_splits(tmp_path),
            build_fingerprint="a" * 64,
        )
        assert generation.generation_dir.is_dir()
        assert publication_module.os.listdir(foreign_descriptor) == []
    finally:
        if foreign_descriptor is not None:
            publication_module.os.close(foreign_descriptor)


def test_generation_quarantine_raw_race_restores_concurrent_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generation-quarantine race restores the concurrent final directory."""
    catalog = tmp_path / "catalog"
    generations = catalog / "generations"
    generations.mkdir(parents=True)
    foreign = generations / "foreign-generation"
    foreign.mkdir()
    (foreign / "KEEP").write_bytes(b"FOREIGN")
    foreign_details = foreign.stat()
    foreign_identity = (
        foreign_details.st_dev,
        foreign_details.st_ino,
        foreign_details.st_mode & 0o170000,
    )
    foreign_descriptor = publication_module.os.open(
        foreign,
        publication_module.os.O_RDONLY
        | getattr(publication_module.os, "O_DIRECTORY", 0),
    )
    parked_owned = generations / "parked-owned-generation"
    original_install = publication_module.rename_noreplace_at
    original_raw = artifact_io._rename_with_flags_at
    mutated = False
    attacked = False
    final_name: str | None = None

    def mutate_staging(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        **kwargs: Any,
    ) -> bool:
        nonlocal mutated
        if target_name.startswith("sha256-") and not mutated:
            (generations / source_name / "train.jsonl").write_bytes(b"EVIL")
            mutated = True
        return original_install(
            directory_descriptor,
            source_name,
            target_name,
            **kwargs,
        )

    def race_quarantine(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        *,
        darwin_flags: int,
        linux_flags: int,
    ) -> bool:
        nonlocal attacked, final_name
        if (
            source_name.startswith("sha256-")
            and target_name.endswith(".rejected")
            and linux_flags == 1
            and not attacked
        ):
            final_name = source_name
            installed = generations / source_name
            installed.rename(parked_owned)
            foreign.rename(installed)
            attacked = True
        return original_raw(
            directory_descriptor,
            source_name,
            target_name,
            darwin_flags=darwin_flags,
            linux_flags=linux_flags,
        )

    monkeypatch.setattr(
        publication_module,
        "rename_noreplace_at",
        mutate_staging,
    )
    monkeypatch.setattr(
        artifact_io,
        "_rename_with_flags_at",
        race_quarantine,
    )
    try:
        with pytest.raises(ValueError):
            install_generation(
                catalog,
                tenant_id="tenant",
                asset_id="asset",
                split_paths=_splits(tmp_path),
                build_fingerprint="a" * 64,
            )

        assert mutated
        assert attacked
        assert final_name is not None
        restored = (generations / final_name).stat()
        assert (
            restored.st_dev,
            restored.st_ino,
            restored.st_mode & 0o170000,
        ) == foreign_identity
        assert publication_module.os.listdir(foreign_descriptor) == ["KEEP"]
        assert (parked_owned / "train.jsonl").read_bytes() == b"EVIL"
    finally:
        publication_module.os.close(foreign_descriptor)
