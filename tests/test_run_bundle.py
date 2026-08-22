# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import importlib
import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Iterable, Mapping

import pytest

from src.hephaestus.runs.identity import build_run_identity

_TERMINAL_ARTIFACTS = {
    "progress.json",
    "results.jsonl",
    "run_config.json",
    "run_identity.json",
    "summary.md",
}


def _bundle_module() -> ModuleType:
    try:
        return importlib.import_module("src.hephaestus.runs.bundle")
    except ModuleNotFoundError as exc:
        pytest.fail(f"run bundle module is unavailable: {exc}")


def _run_identity(case_ids: list[str]) -> dict[str, object]:
    return build_run_identity(
        ordered_case_ids=case_ids,
        dataset_path="datasets/releases/example/test.jsonl",
        dataset_fingerprint="sha256:" + "a" * 64,
        split_fingerprint="sha256:" + "b" * 64,
        scorer_fingerprint="sha256:" + "c" * 64,
        metric_fingerprint="sha256:" + "d" * 64,
    ).to_dict()


def _terminal_progress(
    *,
    run_id: str = "run-001",
    status: str = "completed",
    attempted: list[str] | None = None,
    successful: list[str] | None = None,
    failed: list[str] | None = None,
) -> dict[str, object]:
    attempted = list(["case-1", "case-2"] if attempted is None else attempted)
    successful = list(attempted if successful is None else successful)
    failed = list([] if failed is None else failed)
    return {
        "run_id": run_id,
        "status": status,
        "total_cases": 2,
        "completed_cases": len(attempted),
        "successful_cases": len(successful),
        "attempted_case_ids": attempted,
        "successful_case_ids": successful,
        "failed_case_ids": failed,
        "in_flight_case_ids": [],
        "trust_tier_summaries": {},
    }


def _publish(
    writer: object,
    *,
    results: Iterable[Mapping[str, object]] | None = None,
    progress: Mapping[str, object] | None = None,
    fault_hook: object = None,
) -> object:
    result_rows = list(results) if results is not None else [
        {"case_id": "case-1", "execution_status": "succeeded"},
        {"case_id": "case-2", "execution_status": "succeeded"},
    ]
    return writer.publish(
        run_config={
            "run_id": "run-001",
            "tenant_id": "example",
            "dataset_path": "datasets/releases/example/test.jsonl",
        },
        run_identity=_run_identity(["case-1", "case-2"]),
        results=result_rows,
        summary="# Evaluation Summary\n",
        progress=progress or _terminal_progress(),
        fault_hook=fault_hook,
    )


def test_reservation_rejects_an_existing_directory_without_mutating_it(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "existing-run"
    output_dir.mkdir()
    marker = output_dir / "marker.bin"
    marker.write_bytes(b"ORIGINAL")

    with pytest.raises(FileExistsError, match="already exists"):
        _bundle_module().RunBundleWriter.reserve(output_dir, run_id="run-001")

    assert marker.read_bytes() == b"ORIGINAL"
    assert sorted(path.name for path in output_dir.iterdir()) == ["marker.bin"]


def test_reservation_rejects_an_existing_file_without_mutating_it(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "existing-run"
    output_path.write_bytes(b"ORIGINAL")

    with pytest.raises(FileExistsError, match="already exists"):
        _bundle_module().RunBundleWriter.reserve(output_path, run_id="run-001")

    assert output_path.read_bytes() == b"ORIGINAL"


def test_reservation_rejects_an_existing_symlink_without_following_it(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    marker = target / "marker.bin"
    marker.write_bytes(b"ORIGINAL")
    output_path = tmp_path / "existing-run"
    try:
        output_path.symlink_to(target, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(FileExistsError, match="already exists"):
        _bundle_module().RunBundleWriter.reserve(output_path, run_id="run-001")

    assert output_path.is_symlink()
    assert os.readlink(output_path) == os.fspath(target)
    assert marker.read_bytes() == b"ORIGINAL"


def test_reservation_rejects_a_symlinked_intermediate_ancestor_before_writes(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    outside = tmp_path / "outside"
    trusted.mkdir()
    outside.mkdir()
    linked_ancestor = trusted / "linked"
    try:
        linked_ancestor.symlink_to(outside, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(ValueError, match="ancestor"):
        _bundle_module().RunBundleWriter.reserve(
            linked_ancestor / "new-parent" / "run",
            run_id="run-001",
        )

    assert not (outside / "new-parent").exists()
    assert linked_ancestor.is_symlink()


def test_concurrent_reservations_have_exactly_one_owner(tmp_path: Path) -> None:
    output_dir = tmp_path / "one-run"
    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def reserve() -> None:
        barrier.wait()
        try:
            _bundle_module().RunBundleWriter.reserve(output_dir, run_id="run-001")
        except FileExistsError:
            outcome = "collision"
        else:
            outcome = "reserved"
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=reserve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["collision", "reserved"]
    assert output_dir.is_dir()


def test_live_progress_is_atomically_replaceable_before_publication(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    initial = {
        "run_id": "run-001",
        "status": "running",
        "total_cases": 2,
        "completed_cases": 0,
    }
    updated = {
        "run_id": "run-001",
        "status": "running",
        "total_cases": 2,
        "completed_cases": 1,
    }

    writer.write_progress(initial)
    writer.write_progress(updated)

    assert json.loads((output_dir / "progress.json").read_text()) == updated
    assert not list(output_dir.glob(".*.tmp"))


def test_progress_update_cannot_cross_terminal_publication_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A progress call already past its precheck must serialize before publish."""
    output_dir = tmp_path / "run"
    bundle = _bundle_module()
    writer = bundle.RunBundleWriter.reserve(output_dir, run_id="run-001")
    writer.write_progress(
        {
            "run_id": "run-001",
            "status": "running",
            "total_cases": 2,
            "completed_cases": 0,
        }
    )
    real_atomic_write = bundle.atomic_write_bytes_at
    progress_at_write = threading.Event()
    release_progress = threading.Event()
    progress_errors: list[BaseException] = []
    publish_errors: list[BaseException] = []
    publish_done = threading.Event()

    def pause_late_progress(
        directory: object,
        filename: str,
        content: bytes,
        **kwargs: object,
    ) -> object:
        if (
            threading.current_thread().name == "late-progress"
            and filename == "progress.json"
        ):
            progress_at_write.set()
            if not release_progress.wait(5):
                raise RuntimeError("late progress test gate timed out")
        return real_atomic_write(directory, filename, content, **kwargs)

    monkeypatch.setattr(bundle, "atomic_write_bytes_at", pause_late_progress)

    def write_late_progress() -> None:
        try:
            writer.write_progress(
                {
                    "run_id": "run-001",
                    "status": "running",
                    "total_cases": 2,
                    "completed_cases": 1,
                }
            )
        except BaseException as exc:  # pragma: no cover - assertion below
            progress_errors.append(exc)

    def publish() -> None:
        try:
            _publish(writer)
        except BaseException as exc:  # pragma: no cover - assertion below
            publish_errors.append(exc)
        finally:
            publish_done.set()

    progress_thread = threading.Thread(
        target=write_late_progress,
        name="late-progress",
    )
    publish_thread = threading.Thread(target=publish, name="terminal-publish")
    progress_thread.start()
    assert progress_at_write.wait(5)
    publish_thread.start()
    publish_crossed_progress = publish_done.wait(1)
    release_progress.set()
    progress_thread.join(5)
    publish_thread.join(5)

    assert not progress_thread.is_alive()
    assert not publish_thread.is_alive()
    assert not publish_crossed_progress
    assert progress_errors == []
    assert publish_errors == []
    loaded = bundle.load_run_bundle(output_dir)
    assert loaded.status == "completed"
    assert loaded.progress == _terminal_progress()


def test_publish_installs_a_hash_bound_manifest_after_all_terminal_artifacts(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    identity = _run_identity(["case-1", "case-2"])
    results = [
        {
            "case_id": "case-1",
            "execution_status": "succeeded",
            "composite_score": 0.0,
        },
        {
            "case_id": "case-2",
            "execution_status": "succeeded",
            "composite_score": 100.0,
        },
    ]
    phases: list[str] = []

    published = writer.publish(
        run_config={
            "run_id": "run-001",
            "tenant_id": "example",
            "dataset_path": "datasets/releases/example/test.jsonl",
        },
        run_identity=identity,
        results=results,
        summary="# Evaluation Summary\n",
        progress=_terminal_progress(),
        fault_hook=phases.append,
    )

    assert published.run_id == "run-001"
    assert published.status == "completed"
    assert phases[-1] == "before_manifest_install"
    assert set(path.name for path in output_dir.iterdir()) == {
        *_TERMINAL_ARTIFACTS,
        "run_manifest.json",
    }
    manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert manifest == published.manifest
    assert manifest["schema_version"] == "fapo-run-bundle-manifest-v1"
    assert manifest["hash_algorithm"] == "sha256"
    assert manifest["run_id"] == "run-001"
    assert manifest["status"] == "completed"
    assert manifest["run_identity_fingerprint"] == identity["identity_fingerprint"]
    assert manifest["ordered_case_ids_fingerprint"] == identity["always_controls"][
        "ordered_case_ids_fingerprint"
    ]
    assert manifest["result_count"] == 2
    assert manifest["successful_result_count"] == 2
    assert manifest["failed_result_count"] == 0
    assert set(manifest["artifacts"]) == _TERMINAL_ARTIFACTS
    for name, record in manifest["artifacts"].items():
        content = (output_dir / name).read_bytes()
        assert record == {
            "bytes": len(content),
            "sha256": f"sha256:{hashlib.sha256(content).hexdigest()}",
        }


def test_load_run_bundle_returns_only_a_fully_authenticated_snapshot(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    identity = _run_identity(["case-1", "case-2"])
    results = [
        {"case_id": "case-1", "execution_status": "succeeded"},
        {"case_id": "case-2", "execution_status": "succeeded"},
    ]
    writer.publish(
        run_config={
            "run_id": "run-001",
            "tenant_id": "example",
            "dataset_path": "datasets/releases/example/test.jsonl",
        },
        run_identity=identity,
        results=results,
        summary="# Evaluation Summary\n",
        progress=_terminal_progress(),
    )

    loaded = _bundle_module().load_run_bundle(output_dir)

    assert loaded.output_dir == output_dir
    assert loaded.run_id == "run-001"
    assert loaded.status == "completed"
    assert loaded.run_config["tenant_id"] == "example"
    assert loaded.run_identity["identity_fingerprint"] == identity[
        "identity_fingerprint"
    ]
    assert [row["case_id"] for row in loaded.results] == ["case-1", "case-2"]
    assert loaded.summary == "# Evaluation Summary\n"
    assert loaded.progress["successful_cases"] == 2


@pytest.mark.parametrize(
    "fault_phase",
    [
        "after_run_config.json",
        "after_run_identity.json",
        "after_results.jsonl",
        "after_summary.md",
        "after_progress.json",
        "before_manifest_install",
    ],
)
def test_faults_before_manifest_install_never_create_run_authority(
    tmp_path: Path,
    fault_phase: str,
) -> None:
    output_dir = tmp_path / fault_phase.replace(".", "-")
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )

    def fail_at_phase(phase: str) -> None:
        if phase == fault_phase:
            raise RuntimeError(f"fault at {phase}")

    with pytest.raises(RuntimeError, match="fault at"):
        _publish(writer, fault_hook=fail_at_phase)

    assert not (output_dir / "run_manifest.json").exists()
    with pytest.raises(ValueError, match="inventory"):
        _bundle_module().load_run_bundle(output_dir)


def test_pre_manifest_hook_mutation_is_revalidated_before_authority(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )

    def mutate_verified_artifact(phase: str) -> None:
        if phase == "before_manifest_install":
            (output_dir / "run_config.json").write_bytes(b"FOREIGN")

    with pytest.raises(ValueError, match="content changed: run_config.json"):
        _publish(writer, fault_hook=mutate_verified_artifact)

    assert not (output_dir / "run_manifest.json").exists()


def test_manifest_staging_mutation_is_revalidated_before_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "run"
    bundle = _bundle_module()
    writer = bundle.RunBundleWriter.reserve(output_dir, run_id="run-001")
    real_atomic_write = bundle.atomic_write_bytes_at

    def mutate_after_manifest_staging(
        directory: object,
        filename: str,
        content: bytes,
        **kwargs: object,
    ) -> object:
        installed = real_atomic_write(directory, filename, content, **kwargs)
        if filename.startswith(".run_manifest.json.") and filename.endswith(".staged"):
            (output_dir / "run_config.json").write_bytes(b"FOREIGN")
        return installed

    monkeypatch.setattr(bundle, "atomic_write_bytes_at", mutate_after_manifest_staging)

    with pytest.raises(ValueError, match="content changed: run_config.json"):
        _publish(writer)

    assert not (output_dir / "run_manifest.json").exists()
    assert not list(output_dir.glob(".run_manifest.json.*.staged"))


def test_result_serialization_failure_preserves_live_progress(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    live_progress = {
        "run_id": "run-001",
        "status": "running",
        "total_cases": 2,
        "completed_cases": 0,
    }
    writer.write_progress(live_progress)
    original = (output_dir / "progress.json").read_bytes()

    def failing_results() -> Iterable[Mapping[str, object]]:
        yield {"case_id": "case-1", "execution_status": "succeeded"}
        raise RuntimeError("result iteration failed")

    with pytest.raises(RuntimeError, match="result iteration failed"):
        _publish(writer, results=failing_results())

    assert (output_dir / "progress.json").read_bytes() == original
    assert set(path.name for path in output_dir.iterdir()) == {"progress.json"}


def test_unexpected_terminal_artifact_collision_preserves_existing_bytes(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    collision = output_dir / "run_config.json"
    collision.write_bytes(b"ORIGINAL")

    with pytest.raises(ValueError, match="unexpected artifacts"):
        _publish(writer)

    assert collision.read_bytes() == b"ORIGINAL"
    assert set(path.name for path in output_dir.iterdir()) == {"run_config.json"}


def test_manifest_install_race_preserves_the_competing_bytes(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )

    def create_competing_manifest(phase: str) -> None:
        if phase == "before_manifest_install":
            (output_dir / "run_manifest.json").write_bytes(b"ORIGINAL")

    with pytest.raises(ValueError, match="target appeared"):
        _publish(writer, fault_hook=create_competing_manifest)

    assert (output_dir / "run_manifest.json").read_bytes() == b"ORIGINAL"
    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        _bundle_module().load_run_bundle(output_dir)


def test_manifest_install_rejects_a_replaced_staged_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A distinct staged-name replacement cannot become run authority."""
    output_dir = tmp_path / "run"
    bundle = _bundle_module()
    writer = bundle.RunBundleWriter.reserve(output_dir, run_id="run-001")
    real_rename = bundle.rename_noreplace_at
    replacement = b"FOREIGN-STAGED-MANIFEST"
    parked = tmp_path / "original-staged-manifest"

    def replace_staged_source(
        directory: object,
        source: str,
        destination: str,
        **kwargs: object,
    ) -> bool:
        staged = output_dir / source
        staged.rename(parked)
        try:
            staged.write_bytes(replacement)
            expected_source = kwargs.get("expected_source")
            assert expected_source is not None
            assert (
                bundle.authority_io.stat_child(directory, source).identity
                != expected_source
            )
            return real_rename(directory, source, destination, **kwargs)
        finally:
            parked.unlink()

    monkeypatch.setattr(bundle, "rename_noreplace_at", replace_staged_source)

    with pytest.raises(ValueError, match="rename source"):
        _publish(writer)

    assert not (output_dir / "run_manifest.json").exists()
    assert not parked.exists()
    staged = list(output_dir.glob(".run_manifest.json.*.staged"))
    assert len(staged) == 1
    assert staged[0].read_bytes() == replacement


def test_manifest_commit_has_no_fallible_filesystem_step_after_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "run"
    bundle = _bundle_module()
    writer = bundle.RunBundleWriter.reserve(output_dir, run_id="run-001")
    real_sync = bundle.authority_io.sync_bound_directory

    def reject_post_manifest_sync(directory: object) -> None:
        if bundle.authority_io.optional_stat_child(
            directory,
            "run_manifest.json",
        ) is not None:
            raise OSError("filesystem rejected post-manifest work")
        real_sync(directory)

    monkeypatch.setattr(
        bundle.authority_io,
        "sync_bound_directory",
        reject_post_manifest_sync,
    )

    published = _publish(writer)

    assert published.status == "completed"
    assert (output_dir / "run_manifest.json").is_file()


def test_republication_rejects_before_mutating_an_authoritative_bundle(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    _publish(writer)
    original = {
        path.name: path.read_bytes()
        for path in output_dir.iterdir()
        if path.is_file()
    }

    with pytest.raises(FileExistsError, match="already exists"):
        _publish(writer)

    assert {
        path.name: path.read_bytes()
        for path in output_dir.iterdir()
        if path.is_file()
    } == original


@pytest.mark.parametrize(
    ("status", "results", "progress"),
    [
        (
            "degraded",
            [
                {"case_id": "case-1", "execution_status": "succeeded"},
                {"case_id": "case-2", "execution_status": "failed"},
            ],
            _terminal_progress(
                status="degraded",
                successful=["case-1"],
                failed=["case-2"],
            ),
        ),
        (
            "failed",
            [
                {"case_id": "case-1", "execution_status": "failed"},
                {"case_id": "case-2", "execution_status": "failed"},
            ],
            _terminal_progress(
                status="failed",
                successful=[],
                failed=["case-1", "case-2"],
            ),
        ),
        (
            "failed",
            [],
            _terminal_progress(
                status="failed",
                attempted=[],
                successful=[],
                failed=[],
            ),
        ),
    ],
)
def test_terminal_status_is_cross_linked_to_execution_outcomes(
    tmp_path: Path,
    status: str,
    results: list[Mapping[str, object]],
    progress: Mapping[str, object],
) -> None:
    output_dir = tmp_path / status
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )

    published = _publish(writer, results=results, progress=progress)
    loaded = _bundle_module().load_run_bundle(output_dir)

    assert published.status == status
    assert loaded.status == status


def test_zero_scheduled_cases_cannot_be_published_as_a_successful_run(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "empty-run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    progress = {
        "run_id": "run-001",
        "status": "failed",
        "total_cases": 0,
        "completed_cases": 0,
        "successful_cases": 0,
        "attempted_case_ids": [],
        "successful_case_ids": [],
        "failed_case_ids": [],
        "in_flight_case_ids": [],
        "trust_tier_summaries": {},
    }

    published = writer.publish(
        run_config={
            "run_id": "run-001",
            "tenant_id": "example",
            "dataset_path": "datasets/releases/example/test.jsonl",
        },
        run_identity=_run_identity([]),
        results=[],
        summary="# Evaluation Summary\n",
        progress=progress,
    )

    assert published.status == "failed"
    assert _bundle_module().load_run_bundle(output_dir).status == "failed"


def test_loader_rejects_artifact_hash_tampering(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    _publish(writer)
    with (output_dir / "results.jsonl").open("ab") as handle:
        handle.write(b"{}\n")

    with pytest.raises(ValueError, match="does not match manifest: results.jsonl"):
        _bundle_module().load_run_bundle(output_dir)


def test_loader_rejects_extra_files_even_when_manifested_members_are_intact(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    _publish(writer)
    (output_dir / "unlisted.txt").write_text("extra", encoding="utf-8")

    with pytest.raises(ValueError, match="file inventory"):
        _bundle_module().load_run_bundle(output_dir)


def test_loader_rejects_a_self_consistent_manifest_cross_link_forgery(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    _publish(writer)
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "failed"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="cross-link is invalid: status"):
        _bundle_module().load_run_bundle(output_dir)


def test_loader_rejects_a_hash_updated_dataset_path_cross_link_forgery(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    _publish(writer)
    run_config_path = output_dir / "run_config.json"
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    run_config["dataset_path"] = "datasets/releases/other/test.jsonl"
    run_config_content = (json.dumps(run_config) + "\n").encode("utf-8")
    run_config_path.write_bytes(run_config_content)
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["run_config.json"] = {
        "bytes": len(run_config_content),
        "sha256": f"sha256:{hashlib.sha256(run_config_content).hexdigest()}",
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="dataset_path does not match"):
        _bundle_module().load_run_bundle(output_dir)


def test_loader_rejects_a_hash_updated_forged_identity(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    _publish(writer)
    identity_path = output_dir / "run_identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    identity["always_controls"]["dataset_path"] = "datasets/releases/other/test.jsonl"
    identity_content = (json.dumps(identity) + "\n").encode("utf-8")
    identity_path.write_bytes(identity_content)
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["run_identity.json"] = {
        "bytes": len(identity_content),
        "sha256": f"sha256:{hashlib.sha256(identity_content).hexdigest()}",
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="identity_fingerprint does not match"):
        _bundle_module().load_run_bundle(output_dir)


def test_publish_rejects_mismatched_cross_links_before_writing_artifacts(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"
    writer = _bundle_module().RunBundleWriter.reserve(
        output_dir,
        run_id="run-001",
    )
    progress = deepcopy(_terminal_progress())
    progress["successful_cases"] = 1

    with pytest.raises(ValueError, match="successful_cases does not match"):
        _publish(writer, progress=progress)

    assert not list(output_dir.iterdir())
