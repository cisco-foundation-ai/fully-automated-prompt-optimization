# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import ctypes
import multiprocessing
import os
import stat
import subprocess
import sys
import threading
from contextlib import nullcontext
from pathlib import Path, PureWindowsPath
from typing import Any

import pytest

from src.hephaestus import artifact_io
from src.hephaestus import local_authority_io as authority_io
from src.hephaestus.artifact_io import atomic_write_bytes_at
from src.hephaestus.evaluation_assets import control_jsonl as control_jsonl_module
from src.hephaestus.evaluation_assets.control_jsonl import (
    create_and_open_local_directory_at,
)


def test_atomic_text_writers_request_literal_lf_and_emit_portable_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared text primitives disable platform-native newline translation."""
    original = artifact_io.tempfile.NamedTemporaryFile
    requested_newlines: list[str | None] = []

    def named_temporary_file(*args: Any, **kwargs: Any) -> Any:
        requested_newlines.append(kwargs.get("newline"))
        return original(*args, **kwargs)

    monkeypatch.setattr(
        artifact_io.tempfile,
        "NamedTemporaryFile",
        named_temporary_file,
    )
    json_path = tmp_path / "payload.json"
    jsonl_path = tmp_path / "rows.jsonl"
    text_path = tmp_path / "report.md"

    artifact_io.atomic_write_json(json_path, {"value": "line"})
    artifact_io.atomic_write_jsonl(jsonl_path, [{"value": 1}, {"value": 2}])
    artifact_io.atomic_write_text(text_path, ["alpha\n", "beta\n"])

    assert requested_newlines == ["\n", "\n", "\n"]
    assert json_path.read_bytes() == b'{\n  "value": "line"\n}\n'
    assert jsonl_path.read_bytes() == b'{"value": 1}\n{"value": 2}\n'
    assert text_path.read_bytes() == b"alpha\nbeta\n"


def test_public_imports_survive_missing_fcntl_and_lock_fails_explicitly(
    tmp_path: Path,
) -> None:
    """A missing POSIX hard-lock module is an execution error, not import failure."""
    script = r'''
import builtins
import errno
import os
from pathlib import Path

real_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name == "fcntl":
        raise ModuleNotFoundError("injected missing fcntl")
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded_import

import src.hephaestus.evaluation_assets
import src.hephaestus.cli
from src.hephaestus.evaluation_assets.control_jsonl import acquire_local_authority_lock

root = Path(__import__("sys").argv[1])
root.mkdir()
if os.name == "nt":
    with acquire_local_authority_lock(root / "asset.lock", root, timeout=0):
        pass
else:
    try:
        with acquire_local_authority_lock(root / "asset.lock", root, timeout=0):
            raise AssertionError("unsupported hard lock yielded")
    except OSError as exc:
        assert exc.errno == errno.ENOTSUP, exc
    else:
        raise AssertionError("missing native hard lock did not fail")
'''
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "authority")],
        cwd=Path(__file__).parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def _create_bound_file(
    directory: authority_io.DirectoryLike,
    name: str,
    content: bytes,
) -> authority_io.NodeIdentity:
    file = authority_io.open_child_file(
        directory,
        name,
        writable=True,
        create_exclusive=True,
        delete_access=True,
    )
    try:
        authority_io.write_bound_file(file, content)
        authority_io.sync_bound_file(file)
        return file.identity
    finally:
        file.close()


def test_native_file_cas_returns_and_reclaims_exact_displaced_identity(
    tmp_path: Path,
) -> None:
    """The active platform backend preserves reversible file CAS semantics."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        source_identity = _create_bound_file(directory, "source", b"NEW")
        target_identity = _create_bound_file(directory, "target", b"OLD")

        displaced = authority_io.replace_with_backup(
            directory,
            "source",
            "target",
            expected_source=source_identity,
            expected_destination=target_identity,
        )

        assert (tmp_path / "target").read_bytes() == b"NEW"
        assert authority_io.stat_child(directory, "target").identity == source_identity
        assert authority_io.stat_child(directory, displaced.name).identity == target_identity
        assert (tmp_path / displaced.name).read_bytes() == b"OLD"
        assert authority_io.reclaim_owned_leaf(directory, displaced)
        assert authority_io.optional_stat_child(directory, displaced.name) is None
    finally:
        directory.close()


def test_native_noreplace_never_overwrites_file_or_directory(
    tmp_path: Path,
) -> None:
    """Native no-replace has the same collision contract for both node kinds."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        source_identity = _create_bound_file(directory, "source", b"SOURCE")
        _create_bound_file(directory, "target", b"TARGET")
        assert not authority_io.rename_noreplace(
            directory,
            "source",
            "target",
            expected_source=source_identity,
        )
        assert (tmp_path / "source").read_bytes() == b"SOURCE"
        assert (tmp_path / "target").read_bytes() == b"TARGET"

        source_dir = authority_io.create_child_directory(
            directory,
            "source-dir",
            mode=0o700,
        )
        source_dir.close()
        target_dir = authority_io.create_child_directory(
            directory,
            "target-dir",
            mode=0o700,
        )
        target_dir.close()
        assert not authority_io.rename_noreplace(
            directory,
            "source-dir",
            "target-dir",
            expected_source=authority_io.stat_child(
                directory,
                "source-dir",
            ).identity,
        )
        assert (tmp_path / "source-dir").is_dir()
        assert (tmp_path / "target-dir").is_dir()
    finally:
        directory.close()


def test_native_noreplace_supports_non_bmp_names_and_preserves_collision(
    tmp_path: Path,
) -> None:
    """One-component non-BMP names retain native no-replace semantics."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        source = "source-😀.json"
        destination = "destination-🧪.json"
        source_identity = _create_bound_file(directory, source, b"SOURCE")

        assert authority_io.rename_noreplace(
            directory,
            source,
            destination,
            expected_source=source_identity,
        )
        assert not (tmp_path / source).exists()
        assert (tmp_path / destination).read_bytes() == b"SOURCE"

        competing_source = "competing-🚀.json"
        competing_identity = _create_bound_file(
            directory,
            competing_source,
            b"COMPETING",
        )
        assert not authority_io.rename_noreplace(
            directory,
            competing_source,
            destination,
            expected_source=competing_identity,
        )
        assert (tmp_path / competing_source).read_bytes() == b"COMPETING"
        assert (tmp_path / destination).read_bytes() == b"SOURCE"
    finally:
        directory.close()


def test_native_atomic_replacement_leaves_no_owned_hidden_nodes(
    tmp_path: Path,
) -> None:
    """Ordinary absent and replacement writes reclaim every private leaf."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        first = atomic_write_bytes_at(directory, "authority.json", b"ONE")
        second = atomic_write_bytes_at(
            directory,
            "authority.json",
            b"TWO",
            expected_target=first,
            expected_target_content=b"ONE",
        )
        assert second != first
        assert (tmp_path / "authority.json").read_bytes() == b"TWO"
        assert not any(
            path.name.endswith((".tmp", ".removed", ".rejected"))
            for path in tmp_path.iterdir()
        )
    finally:
        directory.close()


def test_native_atomic_replacement_rollback_restores_original(
    tmp_path: Path,
) -> None:
    """A content mismatch reverses CAS and reclaims the rejected replacement."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        first = atomic_write_bytes_at(directory, "authority.json", b"ONE")

        with pytest.raises(ValueError, match="target bytes changed"):
            atomic_write_bytes_at(
                directory,
                "authority.json",
                b"TWO",
                expected_target=first,
                expected_target_content=b"WRONG",
            )

        assert (tmp_path / "authority.json").read_bytes() == b"ONE"
        assert authority_io.stat_child(directory, "authority.json").identity == first
        assert not any(
            path.name.endswith((".tmp", ".removed", ".rejected"))
            for path in tmp_path.iterdir()
        )
    finally:
        directory.close()


def test_atomic_replacement_prepares_replaces_rebinds_and_syncs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Path replacement releases its source before CAS and rebinds afterward."""
    directory = authority_io.open_bound_directory(tmp_path)
    captured: dict[str, authority_io.BoundFile] = {}
    events: list[str] = []
    real_open = authority_io.open_child_file
    real_replace = authority_io.replace_with_backup
    real_sync = authority_io.sync_bound_file
    try:
        first = atomic_write_bytes_at(directory, "authority.json", b"ONE")

        def capture_open(
            parent: authority_io.DirectoryLike,
            name: str,
            **kwargs: Any,
        ) -> authority_io.BoundFile:
            opened = real_open(parent, name, **kwargs)
            if kwargs.get("create_exclusive"):
                captured["source"] = opened
            return opened

        def prepare(source: authority_io.BoundFile) -> None:
            assert source is captured["source"]
            events.append("prepare")
            source.close()

        def replace(
            parent: authority_io.DirectoryLike,
            source: str,
            destination: str,
            *,
            expected_source: authority_io.NodeIdentity,
            expected_destination: authority_io.NodeIdentity,
        ) -> authority_io.OwnedNode:
            events.append("replace")
            if not captured["source"].closed:
                failure = OSError("injected Windows source sharing violation")
                failure.winerror = 32  # type: ignore[attr-defined]
                raise failure
            return real_replace(
                parent,
                source,
                destination,
                expected_source=expected_source,
                expected_destination=expected_destination,
            )

        def bind(
            parent: authority_io.DirectoryLike,
            name: str,
            *,
            expected: authority_io.NodeIdentity,
            previous: authority_io.BoundFile,
        ) -> authority_io.BoundFile:
            assert previous is captured["source"]
            assert previous.closed
            events.append("bind")
            rebound = real_open(
                parent,
                name,
                writable=True,
                delete_access=True,
            )
            assert rebound.identity == expected
            captured["rebound"] = rebound
            return rebound

        def sync(file: authority_io.BoundFile) -> None:
            if file is captured.get("rebound"):
                events.append("sync")
            real_sync(file)

        monkeypatch.setattr(authority_io, "open_child_file", capture_open)
        monkeypatch.setattr(
            authority_io,
            "prepare_file_source_replace",
            prepare,
            raising=False,
        )
        monkeypatch.setattr(authority_io, "replace_with_backup", replace)
        monkeypatch.setattr(
            authority_io,
            "bind_replaced_file",
            bind,
            raising=False,
        )
        monkeypatch.setattr(authority_io, "sync_bound_file", sync)

        second = atomic_write_bytes_at(
            directory,
            "authority.json",
            b"TWO",
            expected_target=first,
            expected_target_content=b"ONE",
        )

        assert second != first
        assert events == ["prepare", "replace", "bind", "sync"]
        assert (tmp_path / "authority.json").read_bytes() == b"TWO"
        assert not any(
            path.name.endswith((".tmp", ".removed", ".rejected"))
            for path in tmp_path.iterdir()
        )
    finally:
        directory.close()


def test_native_reclamation_retains_a_foreign_name_replacement(
    tmp_path: Path,
) -> None:
    """An ownership token never authorizes deleting a replacement identity."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        owned_identity = _create_bound_file(directory, ".owned.tmp", b"OWNED")
        token = authority_io.OwnedNode(".owned.tmp", owned_identity, "file")
        (tmp_path / ".owned.tmp").rename(tmp_path / "parked-owned")
        (tmp_path / ".owned.tmp").write_bytes(b"FOREIGN")

        assert not authority_io.reclaim_owned_leaf(directory, token)
        assert (tmp_path / ".owned.tmp").read_bytes() == b"FOREIGN"
        assert (tmp_path / "parked-owned").read_bytes() == b"OWNED"
    finally:
        directory.close()


def test_native_exact_file_lock_is_reentrant_for_same_thread(tmp_path: Path) -> None:
    """Nested acquisition reuses the exact outer native lock in one thread."""
    directory = authority_io.open_bound_directory(tmp_path)
    first: authority_io.BoundFile | None = None
    second: authority_io.BoundFile | None = None
    try:
        _create_bound_file(directory, "asset.lock", b"")
        first = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        second = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        with authority_io.exact_file_lock(first, timeout=0):
            with authority_io.exact_file_lock(second, timeout=0):
                assert first.identity == second.identity
    finally:
        if second is not None:
            second.close()
        if first is not None:
            first.close()
        directory.close()


def test_native_exact_file_lock_contends_across_threads(tmp_path: Path) -> None:
    """A distinct thread still times out on the exact outer native lock."""
    directory = authority_io.open_bound_directory(tmp_path)
    outer: authority_io.BoundFile | None = None
    outcome: list[str] = []
    started = threading.Event()

    def contend() -> None:
        other_directory = authority_io.open_bound_directory(tmp_path)
        other: authority_io.BoundFile | None = None
        try:
            other = authority_io.open_child_file(
                other_directory,
                "asset.lock",
                writable=True,
            )
            started.set()
            try:
                with authority_io.exact_file_lock(other, timeout=0):
                    outcome.append("acquired")
            except TimeoutError:
                outcome.append("busy")
        finally:
            if other is not None:
                other.close()
            other_directory.close()

    try:
        _create_bound_file(directory, "asset.lock", b"")
        outer = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        with authority_io.exact_file_lock(outer, timeout=0):
            thread = threading.Thread(target=contend)
            thread.start()
            assert started.wait(timeout=2)
            thread.join(timeout=2)
            assert not thread.is_alive()
        assert outcome == ["busy"]
    finally:
        if outer is not None:
            outer.close()
        directory.close()


def test_native_exact_file_lock_contends_across_threads_sharing_one_handle(
    tmp_path: Path,
) -> None:
    """One open-file description cannot make a second thread look reentrant."""
    directory = authority_io.open_bound_directory(tmp_path)
    file: authority_io.BoundFile | None = None
    outcome: list[str] = []

    def contend() -> None:
        assert file is not None
        try:
            with authority_io.exact_file_lock(file, timeout=0):
                outcome.append("acquired")
        except TimeoutError:
            outcome.append("busy")

    try:
        _create_bound_file(directory, "asset.lock", b"")
        file = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        with authority_io.exact_file_lock(file, timeout=0):
            thread = threading.Thread(target=contend)
            thread.start()
            thread.join(timeout=2)
            assert not thread.is_alive()
        assert outcome == ["busy"]
    finally:
        if file is not None:
            file.close()
        directory.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX inherited backend contract")
def test_bound_filelock_backend_rejects_inherited_pid_without_native_unlock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Old filelock release paths cannot unlock a caller-owned inherited fd."""
    directory = authority_io.open_bound_directory(tmp_path)
    file: authority_io.BoundFile | None = None
    try:
        _create_bound_file(directory, "asset.lock", b"")
        file = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        lock = authority_io._BoundFileLock(file, timeout=0)
        lock._context.lock_file_fd = file.native
        native_calls: list[tuple[int, int]] = []
        assert authority_io._fcntl is not None
        with monkeypatch.context() as patch:
            patch.setattr(
                authority_io.os,
                "getpid",
                lambda: file.opening_pid + 1,
            )
            patch.setattr(
                authority_io._fcntl,
                "flock",
                lambda descriptor, operation: native_calls.append(
                    (descriptor, operation)
                ),
            )
            with pytest.raises(ValueError, match="different process"):
                lock._acquire()
            lock._release()

        assert native_calls == []
        assert lock._context.lock_file_fd is None
        assert lock._descriptors_for_fork() == ()
    finally:
        if file is not None:
            file.close()
        directory.close()


def test_native_parent_lock_blocks_threads_sharing_one_directory_handle(
    tmp_path: Path,
) -> None:
    """A shared directory description still serializes distinct threads."""
    directory = authority_io.open_bound_directory(tmp_path)
    entered = threading.Event()

    def contend() -> None:
        with authority_io.exclusive_parent_namespace_lock(directory):
            entered.set()

    try:
        with authority_io.exclusive_parent_namespace_lock(directory):
            thread = threading.Thread(target=contend)
            thread.start()
            assert not entered.wait(timeout=0.1)
        assert entered.wait(timeout=2)
        thread.join(timeout=2)
        assert not thread.is_alive()
    finally:
        directory.close()


def test_mocked_windows_namespace_lock_surfaces_release_mutex_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed ReleaseMutex is reported after safe handle/registry cleanup."""
    identity = (7, 11, stat.S_IFDIR)
    directory = authority_io.BoundDirectory(Path("C:/authority"), 91, identity)
    closed: list[int] = []
    for name, value in {
        "_INFINITE": 0xFFFFFFFF,
        "_WAIT_OBJECT_0": 0,
        "_WAIT_ABANDONED": 0x80,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (identity, "directory"),
    )
    monkeypatch.setattr(authority_io, "_CreateMutexW", lambda *_args: 81, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_WaitForSingleObject",
        lambda *_args: 0,
        raising=False,
    )
    monkeypatch.setattr(authority_io, "_ReleaseMutex", lambda _handle: 0, raising=False)
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    monkeypatch.setattr(
        authority_io,
        "_raise_last_winerror",
        lambda _path: (_ for _ in ()).throw(OSError("ReleaseMutex failed")),
    )
    authority_io._reset_process_lock_state_after_fork()

    try:
        with pytest.raises(OSError, match="ReleaseMutex failed"):
            with authority_io.exclusive_parent_namespace_lock(directory):
                pass
        assert closed == [81]
        assert authority_io._NAMESPACE_LOCK_REGISTRY == {}
    finally:
        authority_io._reset_process_lock_state_after_fork()


@pytest.mark.skipif(
    os.name == "nt" or "fork" not in multiprocessing.get_all_start_methods(),
    reason="fork-inherited descriptor contract is POSIX-only",
)
def test_fork_inherited_bound_file_cannot_reenter_parent_lock(
    tmp_path: Path,
) -> None:
    """A child must reject a file handle opened by its parent process."""
    directory = authority_io.open_bound_directory(tmp_path)
    file: authority_io.BoundFile | None = None
    context = multiprocessing.get_context("fork")
    parent_connection, child_connection = context.Pipe(duplex=False)

    def contend_with_inherited_handle() -> None:
        assert file is not None
        try:
            with authority_io.exact_file_lock(file, timeout=0):
                outcome = "acquired"
        except ValueError as exc:
            outcome = f"rejected:{exc}"
        child_connection.send(outcome)
        child_connection.close()

    process: multiprocessing.Process | None = None
    try:
        _create_bound_file(directory, "asset.lock", b"")
        file = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        with authority_io.exact_file_lock(file, timeout=0):
            process = context.Process(target=contend_with_inherited_handle)
            process.start()
            child_connection.close()
            assert parent_connection.poll(2)
            assert parent_connection.recv().startswith("rejected:")
        process.join(timeout=2)
        assert process.exitcode == 0
    finally:
        parent_connection.close()
        child_connection.close()
        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=2)
        if file is not None:
            file.close()
        directory.close()


@pytest.mark.skipif(
    os.name == "nt" or "fork" not in multiprocessing.get_all_start_methods(),
    reason="fork-inherited descriptor contract is POSIX-only",
)
def test_fork_inherited_bound_directory_cannot_reenter_parent_lock(
    tmp_path: Path,
) -> None:
    """A child must reject a directory handle opened by its parent process."""
    directory = authority_io.open_bound_directory(tmp_path)
    context = multiprocessing.get_context("fork")
    parent_connection, child_connection = context.Pipe(duplex=False)

    def contend_with_inherited_handle() -> None:
        try:
            with authority_io.exclusive_parent_namespace_lock(directory):
                outcome = "acquired"
        except ValueError as exc:
            outcome = f"rejected:{exc}"
        child_connection.send(outcome)
        child_connection.close()

    process: multiprocessing.Process | None = None
    try:
        with authority_io.exclusive_parent_namespace_lock(directory):
            process = context.Process(target=contend_with_inherited_handle)
            process.start()
            child_connection.close()
            assert parent_connection.poll(2)
            assert parent_connection.recv().startswith("rejected:")
        process.join(timeout=2)
        assert process.exitcode == 0
    finally:
        parent_connection.close()
        child_connection.close()
        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=2)
        directory.close()


@pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "fork"),
    reason="forked context unwind contract is POSIX-only",
)
def test_fork_child_cannot_unwind_parent_exact_file_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A copied outer context never unlocks its parent's open-file description."""
    directory = authority_io.open_bound_directory(tmp_path)
    file: authority_io.BoundFile | None = None
    context: Any = None
    script = r'''
import sys
from pathlib import Path
from src.hephaestus import local_authority_io as authority_io

root = Path(sys.argv[1])
directory = authority_io.open_bound_directory(root)
file = authority_io.open_child_file(directory, "asset.lock", writable=True)
try:
    try:
        with authority_io.exact_file_lock(file, timeout=0):
            print("acquired")
    except TimeoutError:
        print("busy")
finally:
    file.close()
    directory.close()
'''

    def legacy_release(lock: authority_io._BoundFileLock, force: bool = False) -> None:
        del force
        lock._release()

    monkeypatch.setattr(authority_io._BoundFileLock, "release", legacy_release)

    def probe() -> str:
        completed = subprocess.run(
            [sys.executable, "-c", script, str(tmp_path)],
            cwd=Path(__file__).parents[1],
            text=True,
            capture_output=True,
            check=True,
            timeout=2,
        )
        return completed.stdout.strip()

    try:
        _create_bound_file(directory, "asset.lock", b"")
        file = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        context = authority_io.exact_file_lock(file, timeout=0)
        context.__enter__()
        child = os.fork()
        if child == 0:
            try:
                sentinel = RuntimeError("child sentinel")
                suppressed = context.__exit__(RuntimeError, sentinel, None)
            except BaseException:
                os._exit(19)
            os._exit(17 if suppressed else 0)
        waited, status = os.waitpid(child, 0)
        assert waited == child
        assert os.waitstatus_to_exitcode(status) == 0
        assert probe() == "busy"
    finally:
        if context is not None:
            context.__exit__(None, None, None)
        if file is not None:
            file.close()
        directory.close()

    assert probe() == "acquired"


@pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "fork"),
    reason="forked context unwind contract is POSIX-only",
)
def test_fork_child_cannot_unwind_parent_namespace_lock(tmp_path: Path) -> None:
    """A copied parent-lock context never unlocks the parent's directory OFD."""
    directory = authority_io.open_bound_directory(tmp_path)
    context: Any = authority_io.exclusive_parent_namespace_lock(directory)
    script = r'''
import sys
from pathlib import Path
from src.hephaestus import local_authority_io as authority_io

directory = authority_io.open_bound_directory(Path(sys.argv[1]))
try:
    with authority_io.exclusive_parent_namespace_lock(directory):
        print("acquired", flush=True)
finally:
    directory.close()
'''

    def start_probe() -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", script, str(tmp_path)],
            cwd=Path(__file__).parents[1],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    try:
        context.__enter__()
        child = os.fork()
        if child == 0:
            try:
                sentinel = RuntimeError("child sentinel")
                suppressed = context.__exit__(RuntimeError, sentinel, None)
            except BaseException:
                os._exit(19)
            os._exit(17 if suppressed else 0)
        waited, status = os.waitpid(child, 0)
        assert waited == child
        assert os.waitstatus_to_exitcode(status) == 0

        blocked = start_probe()
        try:
            with pytest.raises(subprocess.TimeoutExpired):
                blocked.communicate(timeout=0.2)
        finally:
            blocked.terminate()
            blocked.communicate(timeout=2)
    finally:
        context.__exit__(None, None, None)
        directory.close()

    acquired = start_probe()
    stdout, stderr = acquired.communicate(timeout=2)
    assert acquired.returncode == 0, stderr
    assert stdout.strip() == "acquired"


@pytest.mark.skipif(
    os.name == "nt" or "fork" not in multiprocessing.get_all_start_methods(),
    reason="fork-reopen lock contract is POSIX-only",
)
def test_fork_child_fresh_file_reopen_contends_then_acquires(
    tmp_path: Path,
) -> None:
    """At-fork state reset lets a fresh child handle use the native file lock."""
    directory = authority_io.open_bound_directory(tmp_path)
    file: authority_io.BoundFile | None = None
    context = multiprocessing.get_context("fork")
    parent_connection, child_connection = context.Pipe()
    release = context.Event()

    def contend_with_fresh_handle() -> None:
        child_directory = authority_io.open_bound_directory(tmp_path)
        child_file: authority_io.BoundFile | None = None
        try:
            child_file = authority_io.open_child_file(
                child_directory,
                "asset.lock",
                writable=True,
            )
            try:
                with authority_io.exact_file_lock(child_file, timeout=0):
                    initial = "acquired"
            except TimeoutError:
                initial = "busy"
            child_connection.send(initial)
            assert release.wait(timeout=2)
            with authority_io.exact_file_lock(child_file, timeout=1):
                child_connection.send("acquired-after-release")
        finally:
            if child_file is not None:
                child_file.close()
            child_directory.close()
            child_connection.close()

    process: multiprocessing.Process | None = None
    try:
        _create_bound_file(directory, "asset.lock", b"")
        file = authority_io.open_child_file(
            directory,
            "asset.lock",
            writable=True,
        )
        with authority_io.exact_file_lock(file, timeout=0):
            process = context.Process(target=contend_with_fresh_handle)
            process.start()
            child_connection.close()
            assert parent_connection.poll(2)
            assert parent_connection.recv() == "busy"
        release.set()
        assert parent_connection.poll(2)
        assert parent_connection.recv() == "acquired-after-release"
        process.join(timeout=2)
        assert process.exitcode == 0
    finally:
        release.set()
        parent_connection.close()
        child_connection.close()
        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=2)
        if file is not None:
            file.close()
        directory.close()


@pytest.mark.skipif(
    os.name == "nt" or "fork" not in multiprocessing.get_all_start_methods(),
    reason="fork-reopen lock contract is POSIX-only",
)
def test_fork_child_fresh_directory_reopen_waits_then_acquires(
    tmp_path: Path,
) -> None:
    """At-fork state reset lets a fresh child handle use the parent lock."""
    directory = authority_io.open_bound_directory(tmp_path)
    context = multiprocessing.get_context("fork")
    parent_connection, child_connection = context.Pipe()

    def contend_with_fresh_handle() -> None:
        child_directory = authority_io.open_bound_directory(tmp_path)
        try:
            child_connection.send("opened")
            with authority_io.exclusive_parent_namespace_lock(child_directory):
                child_connection.send("acquired-after-release")
        finally:
            child_directory.close()
            child_connection.close()

    process: multiprocessing.Process | None = None
    try:
        with authority_io.exclusive_parent_namespace_lock(directory):
            process = context.Process(target=contend_with_fresh_handle)
            process.start()
            child_connection.close()
            assert parent_connection.poll(2)
            assert parent_connection.recv() == "opened"
            assert not parent_connection.poll(0.1)
        assert parent_connection.poll(2)
        assert parent_connection.recv() == "acquired-after-release"
        process.join(timeout=2)
        assert process.exitcode == 0
    finally:
        parent_connection.close()
        child_connection.close()
        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=2)
        directory.close()


@pytest.mark.parametrize("fault_name", ["write_bound_file", "sync_bound_file"])
def test_atomic_write_reclaims_temp_created_before_write_or_sync_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Exclusive creation records ownership before any fallible file mutation."""
    directory = authority_io.open_bound_directory(tmp_path)

    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(f"injected {fault_name} failure")

    monkeypatch.setattr(authority_io, fault_name, fail)
    try:
        with pytest.raises(OSError, match=fault_name):
            atomic_write_bytes_at(directory, "authority.json", b"DATA")
        assert authority_io.list_children(directory) == ()
    finally:
        directory.close()


def test_atomic_write_reclaims_exclusive_temp_when_post_open_rebind_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The create primitive owns a temp before its final name recheck can fail."""
    directory = authority_io.open_bound_directory(tmp_path)
    real_stat_child = authority_io.stat_child
    injected = False

    def fail_first_temp_rebind(
        parent: authority_io.DirectoryLike,
        name: str,
    ) -> authority_io.NodeInfo:
        nonlocal injected
        if not injected and name.startswith(".authority.json."):
            injected = True
            raise OSError("injected exclusive-file rebind failure")
        return real_stat_child(parent, name)

    monkeypatch.setattr(authority_io, "stat_child", fail_first_temp_rebind)
    try:
        with pytest.raises(OSError, match="exclusive-file rebind failure"):
            atomic_write_bytes_at(
                directory,
                "authority.json",
                b"DATA",
                expected_target=None,
            )
        assert injected
        assert authority_io.list_children(directory) == ()
    finally:
        directory.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX create identity contract")
def test_atomic_write_reclaims_exclusive_temp_when_first_fstat_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O_EXCL ownership exists before the first descriptor identity read."""
    directory = authority_io.open_bound_directory(tmp_path)
    real_open = authority_io.os.open
    real_fstat = authority_io.os.fstat
    real_close = authority_io.os.close
    created_descriptor: int | None = None
    identity_failures = 0
    closed: list[int] = []

    def record_open(*args: Any, **kwargs: Any) -> int:
        nonlocal created_descriptor
        descriptor = real_open(*args, **kwargs)
        if str(args[0]).startswith(".authority.json."):
            created_descriptor = descriptor
        return descriptor

    def fail_created_descriptor_identity(descriptor: int) -> os.stat_result:
        nonlocal identity_failures
        if descriptor == created_descriptor:
            identity_failures += 1
            raise OSError("injected first exclusive-file identity failure")
        return real_fstat(descriptor)

    def record_close(descriptor: int) -> None:
        if descriptor == created_descriptor:
            closed.append(descriptor)
        real_close(descriptor)

    monkeypatch.setattr(authority_io.os, "open", record_open)
    monkeypatch.setattr(authority_io.os, "fstat", fail_created_descriptor_identity)
    monkeypatch.setattr(authority_io.os, "close", record_close)
    try:
        with pytest.raises(OSError, match="first exclusive-file identity failure"):
            atomic_write_bytes_at(
                directory,
                "authority.json",
                b"DATA",
                expected_target=None,
            )
        assert identity_failures >= 1
        assert created_descriptor is not None
        assert closed == [created_descriptor]
        assert authority_io.list_children(directory) == ()
    finally:
        directory.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX create identity contract")
def test_exclusive_file_identity_retry_retains_lexical_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recovered fd identity never authorizes deleting its replaced name."""
    directory = authority_io.open_bound_directory(tmp_path)
    real_open = authority_io.os.open
    real_fstat = authority_io.os.fstat
    created_descriptor: int | None = None
    created_name: str | None = None
    replaced = False

    def record_open(*args: Any, **kwargs: Any) -> int:
        nonlocal created_descriptor, created_name
        descriptor = real_open(*args, **kwargs)
        candidate = str(args[0])
        if created_descriptor is None and candidate.startswith(".authority.json."):
            created_descriptor = descriptor
            created_name = candidate
        return descriptor

    def replace_before_retry(descriptor: int) -> os.stat_result:
        nonlocal replaced
        if descriptor == created_descriptor and not replaced:
            assert created_name is not None
            replaced = True
            authority_io.os.rename(
                created_name,
                "parked-created",
                src_dir_fd=directory.native,
                dst_dir_fd=directory.native,
            )
            foreign = real_open(
                created_name,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
                dir_fd=directory.native,
            )
            try:
                authority_io.os.write(foreign, b"FOREIGN")
            finally:
                authority_io.os.close(foreign)
            raise OSError("injected first identity failure after replacement")
        return real_fstat(descriptor)

    monkeypatch.setattr(authority_io.os, "open", record_open)
    monkeypatch.setattr(authority_io.os, "fstat", replace_before_retry)
    try:
        with pytest.raises(OSError, match="identity failure after replacement"):
            atomic_write_bytes_at(
                directory,
                "authority.json",
                b"DATA",
                expected_target=None,
            )
        assert replaced
        assert created_name is not None
        assert (tmp_path / created_name).read_bytes() == b"FOREIGN"
        assert (tmp_path / "parked-created").read_bytes() == b""
    finally:
        directory.close()


def test_private_directory_create_reclaims_name_when_open_after_mkdir_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful mkdir is owned before the child descriptor can fail."""
    parent = authority_io.open_bound_directory(tmp_path)
    real_open_child = authority_io.open_child_directory
    injected = False

    def fail_first_private_open(
        directory: authority_io.DirectoryLike,
        name: str,
        *,
        expected: authority_io.NodeIdentity | None = None,
    ) -> authority_io.BoundDirectory:
        nonlocal injected
        if not injected and name.endswith(".directory"):
            injected = True
            raise OSError("injected post-mkdir open failure")
        return real_open_child(directory, name, expected=expected)

    monkeypatch.setattr(
        authority_io,
        "open_child_directory",
        fail_first_private_open,
    )
    try:
        with pytest.raises(OSError, match="post-mkdir open failure"):
            create_and_open_local_directory_at(
                parent,
                "installed",
                final_mode=0o700,
                replacement_error="injected replacement",
            )
        assert injected
        assert authority_io.list_children(parent) == ()
    finally:
        parent.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX create identity contract")
def test_private_directory_create_reclaims_name_when_identity_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A locked successful mkdir owns its empty name before identity reads."""
    parent = authority_io.open_bound_directory(tmp_path)
    real_stat_child = authority_io.stat_child
    injected = 0

    def fail_private_identity(
        directory: authority_io.DirectoryLike,
        name: str,
    ) -> authority_io.NodeInfo:
        nonlocal injected
        if name.endswith(".directory"):
            injected += 1
            raise OSError("injected unavailable directory identity")
        return real_stat_child(directory, name)

    monkeypatch.setattr(authority_io, "stat_child", fail_private_identity)
    try:
        with pytest.raises(OSError, match="unavailable directory identity"):
            create_and_open_local_directory_at(
                parent,
                "installed",
                final_mode=0o700,
                replacement_error="injected replacement",
            )
        assert injected >= 2
        assert authority_io.list_children(parent) == ()
    finally:
        parent.close()


def test_private_directory_wrapper_owns_descriptor_before_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wrapper captures identity before its post-create inventory recheck."""
    parent = authority_io.open_bound_directory(tmp_path)
    real_inventory = control_jsonl_module._local_directory_inventory_at
    inventory_calls = 0

    def fail_second_inventory(
        directory: authority_io.DirectoryLike,
    ) -> dict[str, authority_io.NodeIdentity]:
        nonlocal inventory_calls
        inventory_calls += 1
        if inventory_calls == 2:
            raise OSError("injected post-create inventory failure")
        return real_inventory(directory)

    monkeypatch.setattr(
        control_jsonl_module,
        "_local_directory_inventory_at",
        fail_second_inventory,
    )
    try:
        with pytest.raises(OSError, match="post-create inventory failure"):
            create_and_open_local_directory_at(
                parent,
                "installed",
                final_mode=0o700,
                replacement_error="injected replacement",
            )
        assert inventory_calls == 2
        assert authority_io.list_children(parent) == ()
    finally:
        parent.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX namespace race contract")
def test_posix_owned_leaf_reclaim_holds_parent_lock_through_unlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cooperating replacement cannot enter after the final leaf check."""
    directory = authority_io.open_bound_directory(tmp_path)
    owned_identity = _create_bound_file(directory, ".owned.tmp", b"OWNED")
    token = authority_io.OwnedNode(".owned.tmp", owned_identity, "file")
    unlink_entered = threading.Event()
    racer_finished = threading.Event()
    racer_saw_owned: list[bool] = []
    original_unlink = authority_io.os.unlink

    def pause_unlink(*args: Any, **kwargs: Any) -> None:
        unlink_entered.set()
        racer_finished.wait(timeout=0.2)
        original_unlink(*args, **kwargs)

    def replace_under_namespace_lock() -> None:
        other = authority_io.open_bound_directory(tmp_path)
        try:
            assert unlink_entered.wait(timeout=2)
            with authority_io.exclusive_parent_namespace_lock(other):
                current = authority_io.optional_stat_child(other, token.name)
                racer_saw_owned.append(current is not None)
                if current is not None:
                    assert authority_io.rename_noreplace(
                        other,
                        token.name,
                        "parked-owned",
                        expected_source=current.identity,
                    )
                _create_bound_file(other, token.name, b"FOREIGN")
            racer_finished.set()
        finally:
            other.close()

    monkeypatch.setattr(authority_io.os, "unlink", pause_unlink)
    thread = threading.Thread(target=replace_under_namespace_lock)
    thread.start()
    try:
        assert authority_io.reclaim_owned_leaf(directory, token)
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert racer_saw_owned == [False]
        assert (tmp_path / token.name).read_bytes() == b"FOREIGN"
        assert not (tmp_path / "parked-owned").exists()
    finally:
        directory.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX namespace race contract")
def test_posix_owned_tree_reclaim_holds_parent_lock_through_rmdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cooperating replacement cannot enter after the final tree check."""
    directory = authority_io.open_bound_directory(tmp_path)
    child = authority_io.create_child_directory(directory, ".owned.tmp", mode=0o700)
    token = authority_io.OwnedNode(
        ".owned.tmp",
        child.identity,
        "directory",
    )
    child.close()
    rmdir_entered = threading.Event()
    racer_finished = threading.Event()
    racer_saw_owned: list[bool] = []
    original_rmdir = authority_io.os.rmdir

    def pause_rmdir(*args: Any, **kwargs: Any) -> None:
        rmdir_entered.set()
        racer_finished.wait(timeout=0.2)
        original_rmdir(*args, **kwargs)

    def replace_under_namespace_lock() -> None:
        other = authority_io.open_bound_directory(tmp_path)
        try:
            assert rmdir_entered.wait(timeout=2)
            with authority_io.exclusive_parent_namespace_lock(other):
                current = authority_io.optional_stat_child(other, token.name)
                racer_saw_owned.append(current is not None)
                if current is not None:
                    assert authority_io.rename_noreplace(
                        other,
                        token.name,
                        "parked-owned",
                        expected_source=current.identity,
                    )
                replacement = authority_io.create_child_directory(
                    other,
                    token.name,
                    mode=0o700,
                )
                replacement.close()
            racer_finished.set()
        finally:
            other.close()

    monkeypatch.setattr(authority_io.os, "rmdir", pause_rmdir)
    thread = threading.Thread(target=replace_under_namespace_lock)
    thread.start()
    try:
        assert authority_io.reclaim_owned_tree(directory, token)
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert racer_saw_owned == [False]
        assert (tmp_path / token.name).is_dir()
        assert not (tmp_path / "parked-owned").exists()
    finally:
        directory.close()


def test_atomic_write_holds_parent_namespace_lock_for_complete_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cooperating observer enters only after atomic install and reclamation."""
    directory = authority_io.open_bound_directory(tmp_path)
    write_entered = threading.Event()
    racer_finished = threading.Event()
    target_visible: list[bool] = []
    original_write = authority_io.write_bound_file

    def pause_temporary_write(
        file: authority_io.BoundFile,
        content: bytes,
    ) -> None:
        write_entered.set()
        racer_finished.wait(timeout=0.2)
        original_write(file, content)

    def observe_under_namespace_lock() -> None:
        other = authority_io.open_bound_directory(tmp_path)
        try:
            assert write_entered.wait(timeout=2)
            with authority_io.exclusive_parent_namespace_lock(other):
                target_visible.append(
                    authority_io.optional_stat_child(other, "authority.json")
                    is not None
                )
            racer_finished.set()
        finally:
            other.close()

    monkeypatch.setattr(authority_io, "write_bound_file", pause_temporary_write)
    thread = threading.Thread(target=observe_under_namespace_lock)
    thread.start()
    try:
        atomic_write_bytes_at(directory, "authority.json", b"DATA")
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert target_visible == [True]
        assert (tmp_path / "authority.json").read_bytes() == b"DATA"
        assert not any(path.name.endswith(".tmp") for path in tmp_path.iterdir())
    finally:
        directory.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor cleanup contract")
def test_posix_open_bound_directory_closes_descriptor_when_fstat_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-open identity failure cannot leak the new directory descriptor."""
    opened: list[int] = []
    closed: list[int] = []
    real_open = authority_io.os.open
    real_close = authority_io.os.close

    def record_open(*args: Any, **kwargs: Any) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def record_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    with monkeypatch.context() as patch:
        real_fstat = authority_io.os.fstat

        def selective_fstat(descriptor: int) -> os.stat_result:
            if descriptor in opened:
                raise OSError("injected directory identity failure")
            return real_fstat(descriptor)

        patch.setattr(authority_io.os, "open", record_open)
        patch.setattr(authority_io.os, "fstat", selective_fstat)
        patch.setattr(authority_io.os, "close", record_close)
        with pytest.raises(OSError, match="directory identity failure"):
            authority_io.open_bound_directory(tmp_path)

    assert opened
    assert closed == opened


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor cleanup contract")
def test_posix_open_child_file_closes_descriptor_when_rebind_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-open namespace failure cannot leak the new file descriptor."""
    directory = authority_io.open_bound_directory(tmp_path)
    opened: list[int] = []
    closed: list[int] = []
    real_open = authority_io.os.open
    real_close = authority_io.os.close
    real_stat_child = authority_io.stat_child
    injected = False

    def record_open(*args: Any, **kwargs: Any) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def record_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    def fail_first_rebind(
        parent: authority_io.DirectoryLike,
        name: str,
    ) -> authority_io.NodeInfo:
        nonlocal injected
        if not injected and name == "leaked.tmp":
            injected = True
            raise OSError("injected file rebind failure")
        return real_stat_child(parent, name)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(authority_io.os, "open", record_open)
            patch.setattr(authority_io.os, "close", record_close)
            patch.setattr(
                authority_io,
                "stat_child",
                fail_first_rebind,
            )
            with pytest.raises(OSError, match="file rebind failure"):
                authority_io.open_child_file(
                    directory,
                    "leaked.tmp",
                    writable=True,
                    create_exclusive=True,
                )
        assert opened
        assert closed == opened
        assert injected
        assert not (tmp_path / "leaked.tmp").exists()
    finally:
        directory.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor cleanup contract")
def test_posix_open_child_directory_closes_descriptor_when_path_rebind_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-open path-binding failure cannot leak the child descriptor."""
    (tmp_path / "child").mkdir()
    directory = authority_io.open_bound_directory(tmp_path)
    opened: list[int] = []
    closed: list[int] = []
    real_open = authority_io.os.open
    real_close = authority_io.os.close

    def record_open(*args: Any, **kwargs: Any) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def record_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(authority_io.os, "open", record_open)
            patch.setattr(authority_io.os, "close", record_close)
            patch.setattr(
                authority_io,
                "_directory_path",
                lambda _directory: (_ for _ in ()).throw(
                    OSError("injected child path rebind failure")
                ),
            )
            with pytest.raises(OSError, match="child path rebind failure"):
                authority_io.open_child_directory(directory, "child")
        assert opened
        assert closed == opened
    finally:
        directory.close()


def test_windows_rename_payload_has_absolute_unicode_null_root_contract() -> None:
    """FILE_RENAME_INFO carries a terminated absolute Unicode DOS target."""
    destination = "C:\\verified\\资产\\target-😀.json"
    encoded = destination.encode("utf-16-le")
    buffer = authority_io._windows_rename_info_buffer(destination)
    prefix = ctypes.cast(
        buffer,
        ctypes.POINTER(authority_io._WindowsRenameInfoPrefix),
    ).contents
    offset = authority_io._WindowsRenameInfoPrefix.file_name.offset

    assert offset % ctypes.alignment(ctypes.c_void_p) in {0, 4}
    assert ctypes.c_uint32.from_buffer(buffer).value == 0
    assert prefix.replace_if_exists == 0
    assert prefix.root_directory is None
    assert prefix.file_name_length == len(encoded)
    assert bytes(buffer[offset : offset + len(encoded)]) == encoded
    assert bytes(buffer[offset : offset + len(encoded)]).decode("utf-16-le") == destination
    assert bytes(buffer[offset + len(encoded) : offset + len(encoded) + 2]) == b"\0\0"
    assert ctypes.sizeof(buffer) >= (
        ctypes.sizeof(authority_io._WindowsRenameInfoPrefix) + len(encoded)
    )


def test_mocked_windows_bound_directory_retains_ancestor_handle_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No-share-delete ancestors remain live until the leaf binding closes."""
    handles = iter([41, 42, 43])
    closed: list[int] = []
    identity = (7, 11, stat.S_IFDIR)
    for name, value in {
        "_FILE_LIST_DIRECTORY": 1,
        "_FILE_READ_ATTRIBUTES": 2,
        "_SYNCHRONIZE": 4,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_win_open_path",
        lambda *_args, **_kwargs: next(handles),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (identity, "directory"),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)

    directory = authority_io._win_open_directory_chain(Path("/authority/root"))

    assert directory.native == 43
    assert closed == []
    monkeypatch.setattr(authority_io.os, "name", "nt")
    directory.close()
    assert closed == [43, 42, 41]


def test_mocked_windows_directory_chain_closes_each_handle_once_on_rebind_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A final Windows identity failure releases leaf and ancestor guards once."""
    handles = iter([41, 42, 43])
    closed: list[int] = []
    for name, value in {
        "_FILE_LIST_DIRECTORY": 1,
        "_FILE_READ_ATTRIBUTES": 2,
        "_SYNCHRONIZE": 4,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_win_open_path",
        lambda *_args, **_kwargs: next(handles),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (_ for _ in ()).throw(OSError("identity failure")),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)

    with pytest.raises(OSError, match="identity failure"):
        authority_io._win_open_directory_chain(Path("/authority/root"))

    assert closed == [43, 42, 41]


@pytest.mark.parametrize("identity_stage", ["FileIdInfo", "AttributeTagInfo"])
def test_mocked_windows_open_path_closes_handle_on_identity_failure(
    monkeypatch: pytest.MonkeyPatch,
    identity_stage: str,
) -> None:
    """Every post-CreateFileW identity failure closes its no-share handle."""
    closed: list[int] = []
    for name, value in {
        "_FILE_FLAG_OPEN_REPARSE_POINT": 1,
        "_FILE_FLAG_BACKUP_SEMANTICS": 2,
        "_FILE_SHARE_READ": 4,
        "_FILE_SHARE_WRITE": 8,
        "_FILE_SHARE_DELETE": 16,
        "_INVALID_HANDLE_VALUE": -1,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io, "_CreateFileW", lambda *_args: 73, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (_ for _ in ()).throw(OSError(identity_stage)),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)

    with pytest.raises(OSError, match=identity_stage):
        authority_io._win_open_path(
            Path("C:/authority"),
            access=1,
            creation=3,
            directory=True,
            share_delete=False,
        )

    assert closed == [73]


@pytest.mark.parametrize("share_delete", [False, True])
def test_mocked_windows_create_new_disposes_handle_on_first_identity_failure(
    monkeypatch: pytest.MonkeyPatch,
    share_delete: bool,
) -> None:
    """CREATE_NEW cleanup retains exact handle authority before identity reads."""
    closed: list[int] = []
    disposed: list[tuple[int, Path]] = []
    create_calls: list[tuple[int, int]] = []
    path = Path("C:/authority/.authority.tmp")
    for name, value in {
        "_FILE_FLAG_OPEN_REPARSE_POINT": 1,
        "_FILE_FLAG_BACKUP_SEMANTICS": 2,
        "_FILE_SHARE_READ": 4,
        "_FILE_SHARE_WRITE": 8,
        "_FILE_SHARE_DELETE": 16,
        "_INVALID_HANDLE_VALUE": -1,
        "_CREATE_NEW": 1,
        "_DELETE": 32,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)

    def create_file(
        _path: str,
        access: int,
        share: int,
        *_args: Any,
    ) -> int:
        create_calls.append((access, share))
        return 73

    monkeypatch.setattr(authority_io, "_CreateFileW", create_file, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (_ for _ in ()).throw(OSError("first identity failure")),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_dispose",
        lambda handle, created_path: disposed.append((handle, created_path)),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)

    with pytest.raises(OSError, match="first identity failure"):
        authority_io._win_open_path(
            path,
            access=1,
            creation=1,
            directory=False,
            share_delete=share_delete,
        )

    assert disposed == [(73, path)]
    assert closed == [73]
    assert len(create_calls) == 1
    assert create_calls[0][0] & 32
    assert bool(create_calls[0][1] & 16) is share_delete


def test_mocked_windows_created_directory_disposes_first_bound_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new directory is handle-owned before its first identity can fail."""
    root = Path("C:/authority")
    created_path = root / ".private.directory"
    parent = authority_io.BoundDirectory(root, 91, (7, 9, stat.S_IFDIR))
    closed: list[int] = []
    disposed: list[tuple[int, Path]] = []
    create_calls: list[tuple[int, int]] = []
    fallback_removals: list[Path] = []
    for name, value in {
        "_FILE_FLAG_OPEN_REPARSE_POINT": 1,
        "_FILE_FLAG_BACKUP_SEMANTICS": 2,
        "_FILE_SHARE_READ": 4,
        "_FILE_SHARE_WRITE": 8,
        "_FILE_SHARE_DELETE": 16,
        "_INVALID_HANDLE_VALUE": -1,
        "_FILE_LIST_DIRECTORY": 32,
        "_FILE_READ_ATTRIBUTES": 64,
        "_SYNCHRONIZE": 128,
        "_DELETE": 256,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_directory_path", lambda _parent: root)
    monkeypatch.setattr(
        authority_io,
        "exclusive_parent_namespace_lock",
        lambda _parent: nullcontext(),
    )
    monkeypatch.setattr(
        authority_io,
        "_CreateDirectoryW",
        lambda *_args: True,
        raising=False,
    )

    def create_file(
        _path: str,
        access: int,
        share: int,
        *_args: Any,
    ) -> int:
        create_calls.append((access, share))
        return 83

    monkeypatch.setattr(authority_io, "_CreateFileW", create_file, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (_ for _ in ()).throw(OSError("directory identity failure")),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_dispose",
        lambda handle, path: disposed.append((handle, path)),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    monkeypatch.setattr(
        authority_io.os,
        "rmdir",
        lambda path: fallback_removals.append(path),
    )

    with pytest.raises(OSError, match="directory identity failure"):
        authority_io.create_child_directory(
            parent,
            ".private.directory",
            mode=0o700,
        )

    assert disposed == [(83, created_path)]
    assert closed == [83]
    assert fallback_removals == []
    assert len(create_calls) == 1
    assert create_calls[0][0] & 256
    assert not create_calls[0][1] & 16


def test_mocked_windows_created_directory_prehandle_failure_uses_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Before a child handle exists, the held parent lock guards name cleanup."""
    root = Path("C:/authority")
    created_path = root / ".private.directory"
    parent = authority_io.BoundDirectory(root, 91, (7, 9, stat.S_IFDIR))
    lock_held = False
    fallback_while_locked: list[Path] = []
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_directory_path", lambda _parent: root)
    for name, value in {
        "_FILE_LIST_DIRECTORY": 1,
        "_FILE_READ_ATTRIBUTES": 2,
        "_SYNCHRONIZE": 4,
        "_DELETE": 8,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_CreateDirectoryW",
        lambda *_args: True,
        raising=False,
    )

    class LockedContext:
        def __enter__(self) -> None:
            nonlocal lock_held
            lock_held = True

        def __exit__(self, *_args: Any) -> None:
            nonlocal lock_held
            lock_held = False

    monkeypatch.setattr(
        authority_io,
        "exclusive_parent_namespace_lock",
        lambda _parent: LockedContext(),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_open_path",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("injected pre-handle failure")
        ),
    )

    def remove_created(path: Path) -> None:
        assert lock_held
        fallback_while_locked.append(path)

    monkeypatch.setattr(authority_io.os, "rmdir", remove_created)

    with pytest.raises(OSError, match="pre-handle failure"):
        authority_io.create_child_directory(
            parent,
            ".private.directory",
            mode=0o700,
        )

    assert fallback_while_locked == [created_path]
    assert not lock_held


def test_mocked_windows_created_file_disposal_failure_uses_locked_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed exact disposition falls back before releasing the parent lock."""
    root = Path("C:/authority")
    created_path = root / "authority.lock"
    parent = authority_io.BoundDirectory(root, 91, (7, 9, stat.S_IFDIR))
    closed: list[int] = []
    fallback_removals: list[Path] = []
    lock_held = False
    for name, value in {
        "_FILE_FLAG_OPEN_REPARSE_POINT": 1,
        "_FILE_FLAG_BACKUP_SEMANTICS": 2,
        "_FILE_SHARE_READ": 4,
        "_FILE_SHARE_WRITE": 8,
        "_FILE_SHARE_DELETE": 16,
        "_INVALID_HANDLE_VALUE": -1,
        "_FILE_READ_ATTRIBUTES": 32,
        "_SYNCHRONIZE": 64,
        "_GENERIC_READ": 128,
        "_GENERIC_WRITE": 256,
        "_DELETE": 512,
        "_CREATE_NEW": 1,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_directory_path", lambda _parent: root)
    class LockedContext:
        def __enter__(self) -> None:
            nonlocal lock_held
            lock_held = True

        def __exit__(self, *_args: Any) -> None:
            nonlocal lock_held
            lock_held = False

    monkeypatch.setattr(
        authority_io,
        "exclusive_parent_namespace_lock",
        lambda _parent: LockedContext(),
    )
    monkeypatch.setattr(authority_io, "_CreateFileW", lambda *_args: 73, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (_ for _ in ()).throw(OSError("file identity failure")),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_dispose",
        lambda *_args: (_ for _ in ()).throw(OSError("disposition failure")),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    monkeypatch.setattr(
        authority_io.os,
        "unlink",
        lambda path: (
            fallback_removals.append(path)
            if lock_held
            else (_ for _ in ()).throw(AssertionError("fallback ran unlocked"))
        ),
    )

    with pytest.raises(OSError, match="file identity failure"):
        authority_io.open_child_file(
            parent,
            "authority.lock",
            writable=True,
            create_exclusive=True,
        )

    assert closed == [73]
    assert fallback_removals == [created_path]
    assert not lock_held


def test_mocked_windows_exclusive_file_preserves_no_share_delete_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create cleanup access does not weaken a persistent lock-name binding."""
    root = Path("C:/authority")
    identity = (7, 11, stat.S_IFREG)
    parent = authority_io.BoundDirectory(root, 91, (7, 9, stat.S_IFDIR))
    open_options: list[dict[str, Any]] = []
    closed: list[int] = []
    handles = iter([73, 74])
    for name, value in {
        "_FILE_READ_ATTRIBUTES": 1,
        "_SYNCHRONIZE": 2,
        "_GENERIC_READ": 4,
        "_GENERIC_WRITE": 8,
        "_DELETE": 16,
        "_CREATE_NEW": 1,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_directory_path", lambda _parent: root)
    monkeypatch.setattr(
        authority_io,
        "exclusive_parent_namespace_lock",
        lambda _parent: nullcontext(),
    )

    def open_path(_path: Path, **kwargs: Any) -> int:
        open_options.append(kwargs)
        return next(handles)

    monkeypatch.setattr(authority_io, "_win_open_path", open_path)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (identity, "file"),
    )
    monkeypatch.setattr(
        authority_io,
        "stat_child",
        lambda _parent, _name: authority_io.NodeInfo(
            identity,
            "file",
            stat.S_IFREG,
        ),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)

    file = authority_io.open_child_file(
        parent,
        "authority.lock",
        writable=True,
        create_exclusive=True,
        delete_access=False,
    )
    file.close()

    assert len(open_options) == 2
    assert open_options[0]["access"] & 16
    assert open_options[0]["share_delete"] is False
    assert open_options[0]["creation"] == 1
    assert not open_options[1]["access"] & 16
    assert open_options[1]["share_delete"] is False
    assert open_options[1]["creation"] == 3
    assert closed == [73, 74]


def test_mocked_windows_persistent_file_reopen_failure_reclaims_created_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed stable reopen reclaims only the exact provisional creation."""
    root = Path("C:/authority")
    identity = (7, 11, stat.S_IFREG)
    parent = authority_io.BoundDirectory(root, 91, (7, 9, stat.S_IFDIR))
    open_options: list[dict[str, Any]] = []
    closed: list[int] = []
    reclaimed: list[authority_io.OwnedNode] = []
    for name, value in {
        "_FILE_READ_ATTRIBUTES": 1,
        "_SYNCHRONIZE": 2,
        "_GENERIC_READ": 4,
        "_GENERIC_WRITE": 8,
        "_DELETE": 16,
        "_CREATE_NEW": 1,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_directory_path", lambda _parent: root)
    monkeypatch.setattr(
        authority_io,
        "exclusive_parent_namespace_lock",
        lambda _parent: nullcontext(),
    )

    def open_path(_path: Path, **kwargs: Any) -> int:
        open_options.append(kwargs)
        if len(open_options) == 2:
            raise OSError("injected stable reopen failure")
        return 73

    monkeypatch.setattr(authority_io, "_win_open_path", open_path)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (identity, "file"),
    )
    monkeypatch.setattr(
        authority_io,
        "stat_child",
        lambda _parent, _name: authority_io.NodeInfo(
            identity,
            "file",
            stat.S_IFREG,
        ),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    monkeypatch.setattr(
        authority_io,
        "_reclaim_owned_leaf_locked",
        lambda _parent, owned: reclaimed.append(owned) or True,
    )

    with pytest.raises(OSError, match="stable reopen failure"):
        authority_io.open_child_file(
            parent,
            "authority.lock",
            writable=True,
            create_exclusive=True,
            delete_access=False,
        )

    assert len(open_options) == 2
    assert closed == [73]
    assert reclaimed == [
        authority_io.OwnedNode("authority.lock", identity, "file")
    ]


def test_mocked_windows_persistent_file_reopen_retains_foreign_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stable reopen mismatch never makes the foreign identity reclaimable."""
    root = Path("C:/authority")
    created_identity = (7, 11, stat.S_IFREG)
    foreign_identity = (7, 12, stat.S_IFREG)
    parent = authority_io.BoundDirectory(root, 91, (7, 9, stat.S_IFDIR))
    handles = iter([73, 74])
    observations = iter(
        [created_identity, foreign_identity, foreign_identity]
    )
    closed: list[int] = []
    reclaimed: list[authority_io.OwnedNode] = []
    for name, value in {
        "_FILE_READ_ATTRIBUTES": 1,
        "_SYNCHRONIZE": 2,
        "_GENERIC_READ": 4,
        "_GENERIC_WRITE": 8,
        "_DELETE": 16,
        "_CREATE_NEW": 1,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_directory_path", lambda _parent: root)
    monkeypatch.setattr(
        authority_io,
        "exclusive_parent_namespace_lock",
        lambda _parent: nullcontext(),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_open_path",
        lambda *_args, **_kwargs: next(handles),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda handle: (
            created_identity if handle == 73 else foreign_identity,
            "file",
        ),
    )
    monkeypatch.setattr(
        authority_io,
        "stat_child",
        lambda _parent, _name: authority_io.NodeInfo(
            next(observations),
            "file",
            stat.S_IFREG,
        ),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    monkeypatch.setattr(
        authority_io,
        "_reclaim_owned_leaf_locked",
        lambda _parent, owned: reclaimed.append(owned) or False,
    )

    with pytest.raises(ValueError, match="stable identity"):
        authority_io.open_child_file(
            parent,
            "authority.lock",
            writable=True,
            create_exclusive=True,
            delete_access=False,
        )

    assert closed == [73, 74]
    assert reclaimed == [
        authority_io.OwnedNode("authority.lock", created_identity, "file")
    ]


def test_mocked_windows_open_child_file_closes_handle_on_rebind_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second file-identity failure cannot leak the opened Windows handle."""
    root = Path("C:/authority")
    parent = authority_io.BoundDirectory(root, 91, (7, 9, stat.S_IFDIR))
    closed: list[int] = []
    disposed: list[tuple[int, Path]] = []
    for name, value in {
        "_FILE_READ_ATTRIBUTES": 1,
        "_SYNCHRONIZE": 2,
        "_GENERIC_READ": 4,
        "_GENERIC_WRITE": 8,
        "_DELETE": 16,
        "_CREATE_NEW": 1,
        "_OPEN_EXISTING": 3,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_directory_path", lambda _parent: root)
    monkeypatch.setattr(
        authority_io,
        "exclusive_parent_namespace_lock",
        lambda _parent: nullcontext(),
    )
    monkeypatch.setattr(authority_io, "_win_open_path", lambda *_args, **_kwargs: 73)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (_ for _ in ()).throw(OSError("file rebind failure")),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_dispose",
        lambda handle, path: disposed.append((handle, path)),
    )
    monkeypatch.setattr(authority_io, "_win_close", closed.append)

    with pytest.raises(OSError, match="file rebind failure"):
        authority_io.open_child_file(
            parent,
            "authority.json",
            writable=True,
            create_exclusive=True,
        )

    assert disposed == [(73, root / "authority.json")]
    assert closed == [73]


def test_mocked_windows_closed_directory_never_reopens_lexical_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A closed Windows bound directory cannot regain authority by path."""
    root = Path("C:/authority")
    identity = (7, 11, stat.S_IFDIR)
    directory = authority_io.BoundDirectory(root, 72, identity, closed=True)
    rebound = authority_io.BoundDirectory(root, 73, identity)
    reopened: list[Path] = []
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_win_close", lambda _handle: None)

    def reopen(path: Path) -> authority_io.BoundDirectory:
        reopened.append(path)
        return rebound

    monkeypatch.setattr(authority_io, "_win_open_directory_chain", reopen)

    with pytest.raises(ValueError, match="closed"):
        authority_io._directory_path(directory)

    assert reopened == []


def test_mocked_windows_renamed_directory_closes_then_reopens_exact_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A movable Windows leaf is closed, renamed, then stably rebound."""
    root = Path("C:/authority")
    identity = (7, 11, stat.S_IFDIR)
    parent = authority_io.BoundDirectory(root, 71, (7, 9, stat.S_IFDIR))
    temporary = authority_io.BoundDirectory(root / ".temporary", 72, identity)
    stable = authority_io.BoundDirectory(root / "installed", 73, identity)
    events: list[str] = []
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (identity, "directory"),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_close",
        lambda handle: events.append(f"close:{handle}"),
    )

    def reopen(
        _parent: authority_io.DirectoryLike,
        name: str,
        *,
        expected: authority_io.NodeIdentity | None = None,
    ) -> authority_io.BoundDirectory:
        events.append(f"open:{name}:{expected}")
        return stable

    monkeypatch.setattr(authority_io, "open_child_directory", reopen)

    authority_io.prepare_directory_source_rename(temporary)
    rebound = authority_io.bind_renamed_directory(
        parent,
        "installed",
        expected=identity,
        previous=temporary,
    )

    assert rebound is stable
    assert temporary.closed
    assert events == ["close:72", f"open:installed:{identity}"]


def test_mocked_windows_replaced_file_closes_then_reopens_exact_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Windows replacement source closes, then rebinds with delete sharing."""
    root = Path("C:/authority")
    identity = (7, 11, stat.S_IFREG)
    parent = authority_io.BoundDirectory(root, 71, (7, 9, stat.S_IFDIR))
    temporary = authority_io.BoundFile(root / ".temporary", 72, identity)
    stable = authority_io.BoundFile(root / "installed", 73, identity)
    events: list[str] = []
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(
        authority_io,
        "_win_identity",
        lambda _handle: (identity, "file"),
    )
    monkeypatch.setattr(
        authority_io,
        "_win_close",
        lambda handle: events.append(f"close:{handle}"),
    )

    def reopen(
        _parent: authority_io.DirectoryLike,
        name: str,
        *,
        writable: bool = False,
        delete_access: bool = False,
        **_kwargs: Any,
    ) -> authority_io.BoundFile:
        events.append(f"open:{name}:{writable}:{delete_access}")
        return stable

    monkeypatch.setattr(authority_io, "open_child_file", reopen)

    authority_io.prepare_file_source_replace(temporary)
    rebound = authority_io.bind_replaced_file(
        parent,
        "installed",
        expected=identity,
        previous=temporary,
    )

    assert rebound is stable
    assert temporary.closed
    assert events == ["close:72", "open:installed:True:True"]


def test_mocked_windows_replaced_file_rejects_foreign_rebind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign installed identity is closed and never gains file authority."""
    root = Path("C:/authority")
    expected = (7, 11, stat.S_IFREG)
    foreign = authority_io.BoundFile(root / "installed", 73, (7, 12, stat.S_IFREG))
    previous = authority_io.BoundFile(root / ".temporary", 72, expected, closed=True)
    closed: list[int] = []
    monkeypatch.setattr(authority_io.os, "name", "nt")
    monkeypatch.setattr(authority_io, "_one_component", lambda name: name)
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    monkeypatch.setattr(authority_io, "open_child_file", lambda *_args, **_kwargs: foreign)

    with pytest.raises(ValueError, match="installed file changed"):
        authority_io.bind_replaced_file(
            authority_io.BoundDirectory(root, 71, (7, 9, stat.S_IFDIR)),
            "installed",
            expected=expected,
            previous=previous,
        )

    assert foreign.closed
    assert closed == [73]


def test_directory_creation_workflow_prepares_and_rebinds_installed_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Private-directory installation uses the close/rebind portability seam."""
    parent = authority_io.open_bound_directory(tmp_path)
    events: list[str] = []
    real_prepare = authority_io.prepare_directory_source_rename
    real_bind = authority_io.bind_renamed_directory

    def record_prepare(directory: authority_io.BoundDirectory) -> None:
        events.append(f"prepare:{directory.path.name}")
        real_prepare(directory)

    def record_bind(
        directory: authority_io.DirectoryLike,
        name: str,
        *,
        expected: authority_io.NodeIdentity,
        previous: authority_io.BoundDirectory,
    ) -> authority_io.BoundDirectory:
        events.append(f"bind:{name}")
        return real_bind(
            directory,
            name,
            expected=expected,
            previous=previous,
        )

    monkeypatch.setattr(
        authority_io,
        "prepare_directory_source_rename",
        record_prepare,
    )
    monkeypatch.setattr(authority_io, "bind_renamed_directory", record_bind)
    child: authority_io.BoundDirectory | None = None
    try:
        child, _ = create_and_open_local_directory_at(
            parent,
            "installed",
            final_mode=0o700,
            replacement_error="injected replacement",
        )
        assert events[0].startswith("prepare:.installed.")
        assert events[1] == "bind:installed"
    finally:
        if child is not None:
            child.close()
        parent.close()


def test_mocked_darwin_rejects_unicode_casefold_authority_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Darwin lookup rejects normalized case aliases before authority access."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        _create_bound_file(directory, "Åuthority.json", b"DATA")
        monkeypatch.setattr(authority_io.sys, "platform", "darwin")
        with pytest.raises(ValueError, match="case-insensitive alias"):
            authority_io.stat_child(directory, "A\u030authority.JSON")
    finally:
        directory.close()


def test_mocked_windows_noreplace_uses_exact_handle_and_absolute_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Win32 rename seam binds one parent path and one exact source handle."""
    expected = (7, 11, stat.S_IFREG)
    directory = authority_io.BoundDirectory(Path("ignored"), 91, (7, 9, stat.S_IFDIR))
    parent = PureWindowsPath("C:/verified/authority")
    path_calls: list[authority_io.DirectoryLike] = []
    open_calls: list[tuple[PureWindowsPath, int, int, bool | None, bool]] = []
    set_calls: list[tuple[int, int, int | None, str, int]] = []
    closed: list[int] = []
    monkeypatch.setattr(
        authority_io,
        "stat_child",
        lambda _directory, _name: authority_io.NodeInfo(
            expected,
            "file",
            stat.S_IFREG,
        ),
    )

    def verified_path(
        bound: authority_io.DirectoryLike,
    ) -> PureWindowsPath:
        path_calls.append(bound)
        return parent

    def open_path(
        path: PureWindowsPath,
        *,
        access: int,
        creation: int,
        directory: bool | None,
        share_delete: bool,
        **_kwargs: Any,
    ) -> int:
        open_calls.append((path, access, creation, directory, share_delete))
        return 77

    monkeypatch.setattr(authority_io, "_directory_path", verified_path)
    monkeypatch.setattr(
        authority_io,
        "_directory_native",
        lambda _directory: (_ for _ in ()).throw(
            AssertionError("rename must not reuse a directory HANDLE as RootDirectory")
        ),
    )
    monkeypatch.setattr(authority_io, "_win_open_path", open_path)
    monkeypatch.setattr(authority_io, "_win_identity", lambda _handle: (expected, "file"))
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    for name, value in {
        "_DELETE": 1,
        "_FILE_READ_ATTRIBUTES": 2,
        "_SYNCHRONIZE": 4,
        "_OPEN_EXISTING": 3,
        "_FILE_RENAME_INFO_CLASS": 3,
        "_ERROR_FILE_EXISTS": 80,
        "_ERROR_ALREADY_EXISTS": 183,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)

    def set_information(
        handle: int,
        info_class: int,
        buffer: ctypes.Array[Any],
        size: int,
    ) -> bool:
        prefix = ctypes.cast(
            buffer,
            ctypes.POINTER(authority_io._WindowsRenameInfoPrefix),
        ).contents
        offset = authority_io._WindowsRenameInfoPrefix.file_name.offset
        encoded = bytes(buffer[offset : offset + prefix.file_name_length])
        set_calls.append(
            (
                handle,
                info_class,
                prefix.root_directory,
                encoded.decode("utf-16-le"),
                size,
            )
        )
        return True

    monkeypatch.setattr(
        authority_io,
        "_SetFileInformationByHandle",
        set_information,
        raising=False,
    )

    assert authority_io._win_rename_noreplace(
        directory,
        "source.json",
        "target-😀.json",
        expected,
    )
    assert path_calls == [directory]
    assert open_calls == [
        (
            parent / "source.json",
            1 | 2 | 4,
            3,
            False,
            True,
        )
    ]
    assert set_calls == [
        (
            77,
            3,
            None,
            str(parent / "target-😀.json"),
            ctypes.sizeof(authority_io._WindowsRenameInfoPrefix)
            + len(str(parent / "target-😀.json").encode("utf-16-le")),
        )
    ]
    assert closed == [77]


@pytest.mark.parametrize(
    ("error", "is_collision"),
    [(80, True), (183, True), (5, False), (87, False)],
)
def test_mocked_windows_noreplace_only_suppresses_collision_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: int,
    is_collision: bool,
) -> None:
    """Only documented destination collisions return false after exact close."""
    expected = (7, 11, stat.S_IFREG)
    closed: list[int] = []
    monkeypatch.setattr(
        authority_io,
        "stat_child",
        lambda _directory, _name: authority_io.NodeInfo(
            expected,
            "file",
            stat.S_IFREG,
        ),
    )
    monkeypatch.setattr(
        authority_io,
        "_directory_path",
        lambda _directory: PureWindowsPath("C:/verified/authority"),
    )
    monkeypatch.setattr(authority_io, "_win_open_path", lambda *_args, **_kwargs: 77)
    monkeypatch.setattr(authority_io, "_win_identity", lambda _handle: (expected, "file"))
    monkeypatch.setattr(authority_io, "_win_close", closed.append)
    monkeypatch.setattr(
        authority_io,
        "_SetFileInformationByHandle",
        lambda *_args: False,
        raising=False,
    )
    monkeypatch.setattr(authority_io.ctypes, "get_last_error", lambda: error, raising=False)
    monkeypatch.setattr(
        authority_io.ctypes,
        "WinError",
        lambda code: OSError(code, f"injected Windows error {code}"),
        raising=False,
    )
    for name, value in {
        "_DELETE": 1,
        "_FILE_READ_ATTRIBUTES": 2,
        "_SYNCHRONIZE": 4,
        "_OPEN_EXISTING": 3,
        "_FILE_RENAME_INFO_CLASS": 3,
        "_ERROR_FILE_EXISTS": 80,
        "_ERROR_ALREADY_EXISTS": 183,
    }.items():
        monkeypatch.setattr(authority_io, name, value, raising=False)

    if is_collision:
        assert not authority_io._win_rename_noreplace(
            91,
            "source.json",
            "target.json",
            expected,
        )
    else:
        with pytest.raises(OSError) as raised:
            authority_io._win_rename_noreplace(
                91,
                "source.json",
                "target.json",
                expected,
            )
        assert raised.value.errno == error
    assert closed == [77]


def test_mocked_windows_lock_and_disposition_use_the_bound_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Win32 lock and reclamation APIs receive no reusable lexical handle."""
    class Overlapped(ctypes.Structure):
        _fields_: list[tuple[str, Any]] = []

    lock_calls: list[int] = []
    disposition_calls: list[tuple[int, int, int]] = []
    monkeypatch.setattr(authority_io, "_OVERLAPPED", Overlapped, raising=False)
    monkeypatch.setattr(authority_io, "_LOCKFILE_EXCLUSIVE_LOCK", 2, raising=False)
    monkeypatch.setattr(authority_io, "_LOCKFILE_FAIL_IMMEDIATELY", 1, raising=False)
    monkeypatch.setattr(
        authority_io,
        "_LockFileEx",
        lambda handle, *_args: lock_calls.append(handle) or True,
        raising=False,
    )
    monkeypatch.setattr(
        authority_io,
        "_FILE_DISPOSITION_DELETE",
        1,
        raising=False,
    )
    monkeypatch.setattr(
        authority_io,
        "_FILE_DISPOSITION_POSIX_SEMANTICS",
        2,
        raising=False,
    )
    monkeypatch.setattr(
        authority_io,
        "_FILE_DISPOSITION_IGNORE_READONLY_ATTRIBUTE",
        16,
        raising=False,
    )
    monkeypatch.setattr(
        authority_io,
        "_FILE_DISPOSITION_INFO_EX_CLASS",
        21,
        raising=False,
    )

    def set_information(
        handle: int,
        info_class: int,
        payload: Any,
        size: int,
    ) -> bool:
        flags = ctypes.cast(payload, ctypes.POINTER(ctypes.c_ulong)).contents.value
        disposition_calls.append((handle, info_class, flags))
        assert size == ctypes.sizeof(ctypes.c_ulong)
        return True

    monkeypatch.setattr(
        authority_io,
        "_SetFileInformationByHandle",
        set_information,
        raising=False,
    )

    assert authority_io._win_try_lock(55)
    authority_io._win_dispose(66, Path("ignored"))
    assert lock_calls == [55]
    assert disposition_calls == [(66, 21, 19)]


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse behavior")
def test_windows_backend_rejects_reparse_and_case_aliases(tmp_path: Path) -> None:
    """Windows public traversal rejects reparse and case-fold aliases."""
    directory = authority_io.open_bound_directory(tmp_path)
    try:
        _create_bound_file(directory, "Authority.json", b"DATA")
        with pytest.raises(ValueError, match="case-insensitive alias"):
            authority_io.stat_child(directory, "authority.JSON")
        with pytest.raises(ValueError, match="reserved"):
            authority_io.stat_child(directory, "CON")
        with pytest.raises(ValueError, match="space or dot"):
            authority_io.stat_child(directory, "authority. ")
        outside = tmp_path.parent / f"{tmp_path.name}-outside"
        outside.mkdir()
        reparse = tmp_path / "reparse"
        try:
            reparse.symlink_to(outside, target_is_directory=True)
        except OSError:
            pass
        else:
            with pytest.raises(ValueError, match="reparse"):
                authority_io.stat_child(directory, reparse.name)
    finally:
        directory.close()
