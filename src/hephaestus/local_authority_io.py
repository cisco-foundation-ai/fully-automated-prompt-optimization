# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Identity-bound native filesystem operations for local authority.

The public persistence layers use this module instead of assuming POSIX
``dir_fd`` support.  POSIX binds namespaces with directory descriptors;
Windows binds them with reparse-point-aware directory/file handles.  Missing
native lock or atomic-rename primitives fail with ``ENOTSUP`` rather than
selecting a soft-lock or check-then-replace fallback.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import stat
import sys
import threading
import time
import unicodedata
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, Mapping, TypeAlias

from filelock import BaseFileLock, Timeout

try:  # Never make the public package unimportable on Windows/minimal POSIX.
    import fcntl as _fcntl
except ModuleNotFoundError:  # pragma: no cover - exercised in an isolated import test
    _fcntl = None


NodeIdentity: TypeAlias = tuple[int, int, int]


@dataclass(frozen=True)
class NodeInfo:
    """One no-follow namespace observation."""

    identity: NodeIdentity
    kind: Literal["file", "directory", "symlink_or_reparse"]
    mode: int


@dataclass
class BoundDirectory:
    """An opened directory whose lexical binding is held for its lifetime."""

    path: Path
    native: int
    identity: NodeIdentity
    opening_pid: int = field(default_factory=os.getpid, repr=False)
    closed: bool = False
    ancestor_natives: tuple[int, ...] = field(default_factory=tuple, repr=False)

    def __index__(self) -> int:
        if os.name == "nt":
            raise TypeError("a Windows directory HANDLE is not a POSIX dir_fd")
        return self.native

    def __int__(self) -> int:
        return self.__index__()

    def close(self) -> None:
        if self.closed:
            return
        if os.name == "nt":
            error: BaseException | None = None
            for handle in (self.native, *reversed(self.ancestor_natives)):
                try:
                    _win_close(handle)
                except BaseException as exc:  # pragma: no cover - native cleanup
                    if error is None:
                        error = exc
            self.closed = True
            if error is not None:
                raise error
        else:
            os.close(self.native)
            self.closed = True


@dataclass
class BoundFile:
    """An opened exact regular file."""

    path: Path
    native: int
    identity: NodeIdentity
    opening_pid: int = field(default_factory=os.getpid, repr=False)
    closed: bool = False

    def close(self) -> None:
        if self.closed:
            return
        if os.name == "nt":
            _win_close(self.native)
        else:
            os.close(self.native)
        self.closed = True


@dataclass(frozen=True)
class OwnedNode:
    """Capability authorizing reclamation of one exact operation-owned node."""

    name: str
    identity: NodeIdentity
    kind: Literal["file", "directory"]
    children: Mapping[str, NodeIdentity] = field(default_factory=dict)


@dataclass
class _WindowsCreatedHandleState:
    """Report whether failed validation disposed an exact created handle."""

    handle_obtained: bool = False
    disposed: bool = False


DirectoryLike: TypeAlias = BoundDirectory | int


class _WindowsRenameInfoPrefix(ctypes.Structure):
    """Fixed-width FILE_RENAME_INFO prefix usable in platform-neutral tests."""

    _fields_ = [
        ("replace_if_exists", ctypes.c_ubyte),
        ("root_directory", ctypes.c_void_p),
        ("file_name_length", ctypes.c_uint32),
        ("file_name", ctypes.c_uint16 * 1),
    ]


def _windows_rename_info_buffer(
    destination: str,
) -> ctypes.Array[ctypes.c_char]:
    """Pack one aligned FILE_RENAME_INFO absolute-name payload."""
    encoded = destination.encode("utf-16-le")
    filename_offset = _WindowsRenameInfoPrefix.file_name.offset
    buffer = ctypes.create_string_buffer(
        ctypes.sizeof(_WindowsRenameInfoPrefix) + len(encoded)
    )
    prefix = ctypes.cast(
        buffer,
        ctypes.POINTER(_WindowsRenameInfoPrefix),
    ).contents
    prefix.replace_if_exists = 0
    prefix.root_directory = None
    prefix.file_name_length = len(encoded)
    ctypes.memmove(
        ctypes.addressof(buffer) + filename_offset,
        encoded,
        len(encoded),
    )
    return buffer


def _one_component(name: str) -> str:
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ValueError("local authority name must be one path component")
    if os.name == "nt":
        if name[-1:] in {" ", "."}:
            raise ValueError("Windows authority names cannot end in space or dot")
        stem = name.split(".", 1)[0].rstrip(" .").upper()
        reserved = {"CON", "PRN", "AUX", "NUL"} | {
            f"{prefix}{index}"
            for prefix in ("COM", "LPT")
            for index in range(1, 10)
        }
        if stem in reserved:
            raise ValueError("Windows reserved device name is not allowed")
    return name


def _authority_name_key(name: str) -> str:
    """Return the deterministic alias key used on case-insensitive platforms."""
    return unicodedata.normalize("NFC", name).casefold()


def _legacy_identity(details: os.stat_result) -> NodeIdentity:
    return (details.st_dev, details.st_ino, stat.S_IFMT(details.st_mode))


def _directory_native(directory: DirectoryLike) -> int:
    if isinstance(directory, BoundDirectory):
        if directory.closed:
            raise ValueError("bound directory is closed")
        if directory.opening_pid != os.getpid():
            raise ValueError("bound directory belongs to a different process")
        return directory.native
    if os.name == "nt":
        raise OSError(errno.ENOTSUP, "raw dir_fd authority is unsupported on Windows")
    return directory


def _directory_path(directory: DirectoryLike) -> Path:
    if not isinstance(directory, BoundDirectory):
        raise OSError(errno.ENOTSUP, "directory path is unavailable for this handle")
    if directory.closed:
        raise ValueError("bound directory is closed")
    if directory.opening_pid != os.getpid():
        raise ValueError("bound directory belongs to a different process")
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        rebound = _win_open_directory_chain(directory.path)
        try:
            if rebound.identity != directory.identity:
                raise ValueError("Windows authority directory path changed")
        finally:
            rebound.close()
    return directory.path


def directory_identity(directory: DirectoryLike) -> NodeIdentity:
    if isinstance(directory, BoundDirectory):
        if directory.closed:
            raise ValueError("bound directory is closed")
        if directory.opening_pid != os.getpid():
            raise ValueError("bound directory belongs to a different process")
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            live, kind = _win_identity(directory.native)
            if kind != "directory" or live != directory.identity:
                raise ValueError("bound directory identity changed")
            return live
        live = _legacy_identity(os.fstat(directory.native))
        if live != directory.identity:
            raise ValueError("bound directory identity changed")
        return live
    return _legacy_identity(os.fstat(directory))


def _bound_file_identity(file: BoundFile) -> NodeIdentity:
    """Recheck one open file handle against its captured identity."""
    if file.closed:
        raise ValueError("bound file is closed")
    if file.opening_pid != os.getpid():
        raise ValueError("bound file belongs to a different process")
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        live, kind = _win_identity(file.native)
        if kind != "file" or live != file.identity:
            raise ValueError("bound file identity changed")
        return live
    live = _legacy_identity(os.fstat(file.native))
    if live != file.identity:
        raise ValueError("bound file identity changed")
    return live


def close_directory(directory: DirectoryLike) -> None:
    if isinstance(directory, BoundDirectory):
        directory.close()
    else:
        os.close(directory)


def open_bound_directory(path: Path) -> BoundDirectory:
    """Open one exact directory and reject symlink/reparse traversal."""
    lexical = Path(os.path.abspath(os.fspath(path)))
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        return _win_open_directory_chain(lexical)
    before = os.lstat(lexical)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise ValueError("local authority node is not an exact directory")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    descriptor = os.open(lexical, flags)
    try:
        opened = os.fstat(descriptor)
        if _legacy_identity(opened) != _legacy_identity(before):
            raise ValueError("local authority directory changed while opening")
        return BoundDirectory(lexical, descriptor, _legacy_identity(opened))
    except BaseException:
        os.close(descriptor)
        raise


def validate_existing_directory_chain(base: Path, path: Path) -> None:
    """Bind every existing directory component beneath one lexical trust anchor."""
    lexical_base = Path(os.path.abspath(os.fspath(base)))
    lexical_path = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = lexical_path.relative_to(lexical_base)
    except ValueError as exc:
        raise ValueError("local authority path escapes its repository base") from exc
    try:
        current = open_bound_directory(lexical_base)
    except (OSError, ValueError) as exc:
        raise ValueError("local authority repository base is not exact") from exc
    try:
        for part in relative.parts:
            observed = optional_stat_child(current, part)
            if observed is None:
                return
            if observed.kind != "directory":
                raise ValueError(
                    "local authority repository path contains an unsafe ancestor"
                )
            child = open_child_directory(
                current,
                part,
                expected=observed.identity,
            )
            current.close()
            current = child
    finally:
        current.close()


def stat_child(directory: DirectoryLike, name: str) -> NodeInfo:
    """Return one no-follow child identity."""
    name = _one_component(name)
    if os.name == "nt" or sys.platform == "darwin":
        listed = os.listdir(
            _directory_path(directory)
            if os.name == "nt"
            else _directory_native(directory)
        )
        requested_key = _authority_name_key(name)
        aliases = tuple(
            child
            for child in listed
            if _authority_name_key(child) == requested_key
        )
        if any(child != name for child in aliases):
            raise ValueError("local authority name has a case-insensitive alias")
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        path = _directory_path(directory) / name
        handle = _win_open_path(
            path,
            access=_FILE_READ_ATTRIBUTES | _SYNCHRONIZE,
            creation=_OPEN_EXISTING,
            directory=None,
            share_delete=True,
        )
        try:
            identity, kind = _win_identity(handle)
            return NodeInfo(identity, kind, identity[2])
        finally:
            _win_close(handle)
    details = os.stat(
        name,
        dir_fd=_directory_native(directory),
        follow_symlinks=False,
    )
    kind: Literal["file", "directory", "symlink_or_reparse"]
    if stat.S_ISREG(details.st_mode):
        kind = "file"
    elif stat.S_ISDIR(details.st_mode):
        kind = "directory"
    else:
        kind = "symlink_or_reparse"
    return NodeInfo(_legacy_identity(details), kind, details.st_mode)


def optional_stat_child(directory: DirectoryLike, name: str) -> NodeInfo | None:
    try:
        return stat_child(directory, name)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) in {
            _ERROR_FILE_NOT_FOUND,
            _ERROR_PATH_NOT_FOUND,
        }:
            return None
        raise


def list_children(directory: DirectoryLike) -> tuple[str, ...]:
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        return tuple(sorted(os.listdir(_directory_path(directory))))
    return tuple(sorted(os.listdir(_directory_native(directory))))


def open_child_directory(
    parent: DirectoryLike,
    name: str,
    *,
    expected: NodeIdentity | None = None,
) -> BoundDirectory:
    name = _one_component(name)
    before = stat_child(parent, name)
    if before.kind != "directory" or (expected is not None and before.identity != expected):
        raise ValueError("local authority child is not the expected directory")
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        result = open_bound_directory(_directory_path(parent) / name)
    else:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_DIRECTORY", 0)
        )
        descriptor = os.open(name, flags, dir_fd=_directory_native(parent))
        try:
            opened = os.fstat(descriptor)
            result = BoundDirectory(
                (
                    _directory_path(parent) / name
                    if isinstance(parent, BoundDirectory)
                    else Path(name)
                ),
                descriptor,
                _legacy_identity(opened),
            )
        except BaseException:
            os.close(descriptor)
            raise
    if result.identity != before.identity:
        result.close()
        raise ValueError("local authority directory changed while opening")
    return result


def _discard_just_created_node_locked(
    parent: DirectoryLike,
    name: str,
    kind: Literal["file", "directory"],
) -> None:
    """Remove a no-replace creation before releasing its parent lock.

    Successful ``O_EXCL``/``mkdir`` is the ownership proof here.  This helper
    is only valid while the creating thread still holds the exact parent
    namespace lock, so no cooperating writer can replace the new name before
    cleanup when the first identity read itself fails.
    """
    name = _one_component(name)
    if kind == "file":
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            os.unlink(_directory_path(parent) / name)
        else:
            os.unlink(name, dir_fd=_directory_native(parent))
    elif os.name == "nt":  # pragma: no cover - exercised by Windows CI
        os.rmdir(_directory_path(parent) / name)
    else:
        os.rmdir(name, dir_fd=_directory_native(parent))
    sync_bound_directory(parent)


def create_child_directory(
    parent: DirectoryLike,
    name: str,
    *,
    mode: int,
) -> BoundDirectory:
    name = _one_component(name)
    with exclusive_parent_namespace_lock(parent):
        created_identity: NodeIdentity | None = None
        created_handle_state = _WindowsCreatedHandleState()
        result: BoundDirectory | None = None
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            path = _directory_path(parent) / name
            if not _CreateDirectoryW(str(path), None):
                _raise_last_winerror(path)
        else:
            os.mkdir(name, mode, dir_fd=_directory_native(parent))
        try:
            if os.name == "nt":  # pragma: no cover - exercised by Windows CI
                created_handle = _win_open_path(
                    path,
                    access=(
                        _FILE_LIST_DIRECTORY
                        | _FILE_READ_ATTRIBUTES
                        | _SYNCHRONIZE
                        | _DELETE
                    ),
                    creation=_OPEN_EXISTING,
                    directory=True,
                    share_delete=False,
                    dispose_on_error=True,
                    created_handle_state=created_handle_state,
                )
                try:
                    created_identity, created_kind = _win_identity(
                        created_handle
                    )
                    if created_kind != "directory":
                        raise ValueError(
                            "new local authority directory changed while opening"
                        )
                except BaseException:
                    try:
                        _win_dispose(created_handle, path)
                    except OSError:
                        pass
                    else:
                        created_handle_state.disposed = True
                    raise
                finally:
                    _win_close(created_handle)
            else:
                created = stat_child(parent, name)
                if created.kind != "directory":
                    raise ValueError(
                        "new local authority directory changed while opening"
                    )
                created_identity = created.identity
            result = open_child_directory(
                parent,
                name,
                expected=created_identity,
            )
            if os.name != "nt":
                os.fchmod(result.native, mode)
            rebound = stat_child(parent, name)
            if rebound.identity != result.identity or rebound.kind != "directory":
                raise ValueError(
                    "new local authority directory changed while opening"
                )
            return result
        except BaseException:
            if result is not None:
                try:
                    result.close()
                except OSError:
                    pass
            if created_identity is None and not created_handle_state.disposed:
                try:
                    created = stat_child(parent, name)
                except (OSError, ValueError):
                    created = None
                if created is not None and created.kind == "directory":
                    created_identity = created.identity
            if not created_handle_state.disposed:
                try:
                    if created_identity is None:
                        _discard_just_created_node_locked(
                            parent,
                            name,
                            "directory",
                        )
                    else:
                        _reclaim_owned_tree_locked(
                            parent,
                            OwnedNode(name, created_identity, "directory"),
                        )
                except OSError:
                    pass
            raise


def prepare_directory_source_rename(directory: BoundDirectory) -> None:
    """Release a Windows leaf guard before renaming its exact directory."""
    directory_identity(directory)
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        directory.close()


def bind_renamed_directory(
    parent: DirectoryLike,
    name: str,
    *,
    expected: NodeIdentity,
    previous: BoundDirectory,
) -> BoundDirectory:
    """Bind an installed directory name after its identity-checked rename."""
    name = _one_component(name)
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        return open_child_directory(parent, name, expected=expected)
    previous.path = (
        _directory_path(parent) / name
        if isinstance(parent, BoundDirectory)
        else previous.path
    )
    return previous


def prepare_file_source_replace(file: BoundFile) -> None:
    """Release a Windows source handle before path-based file replacement."""
    _bound_file_identity(file)
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        file.close()


def bind_replaced_file(
    parent: DirectoryLike,
    name: str,
    *,
    expected: NodeIdentity,
    previous: BoundFile,
) -> BoundFile:
    """Bind the installed file after an identity-checked path replacement."""
    name = _one_component(name)
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        if not previous.closed:
            raise ValueError("Windows replacement source handle is still open")
        rebound = open_child_file(
            parent,
            name,
            writable=True,
            delete_access=True,
        )
        if rebound.identity != expected:
            rebound.close()
            raise ValueError("installed file changed while binding replacement")
        return rebound
    if _bound_file_identity(previous) != expected:
        raise ValueError("installed file changed while binding replacement")
    previous.path = (
        _directory_path(parent) / name
        if isinstance(parent, BoundDirectory)
        else previous.path
    )
    return previous


def open_child_file(
    parent: DirectoryLike,
    name: str,
    *,
    writable: bool = False,
    create_exclusive: bool = False,
    mode: int = 0o600,
    delete_access: bool = False,
) -> BoundFile:
    name = _one_component(name)
    namespace_lock = (
        exclusive_parent_namespace_lock(parent)
        if create_exclusive
        else nullcontext()
    )
    with namespace_lock:
        path = (
            _directory_path(parent) / name
            if isinstance(parent, BoundDirectory)
            else Path(name)
        )
        before = None if create_exclusive else stat_child(parent, name)
        if before is not None and before.kind != "file":
            raise ValueError("local authority child is not an exact regular file")
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            access = _FILE_READ_ATTRIBUTES | _SYNCHRONIZE | _GENERIC_READ
            if writable:
                access |= _GENERIC_WRITE
            if delete_access or create_exclusive:
                access |= _DELETE
            created_handle_state = _WindowsCreatedHandleState()
            try:
                handle = _win_open_path(
                    path,
                    access=access,
                    creation=(
                        _CREATE_NEW if create_exclusive else _OPEN_EXISTING
                    ),
                    directory=False,
                    share_delete=delete_access,
                    created_handle_state=created_handle_state,
                )
            except BaseException:
                if (
                    create_exclusive
                    and created_handle_state.handle_obtained
                    and not created_handle_state.disposed
                ):
                    try:
                        _discard_just_created_node_locked(
                            parent,
                            name,
                            "file",
                        )
                    except OSError:
                        pass
                raise
            try:
                identity, kind = _win_identity(handle)
                if kind != "file":
                    raise ValueError(
                        "local authority child is not an exact regular file"
                    )
                result = BoundFile(path, handle, identity)
            except BaseException:
                disposed = False
                try:
                    if create_exclusive:
                        try:
                            _win_dispose(handle, path)
                        except OSError:
                            pass
                        else:
                            disposed = True
                finally:
                    _win_close(handle)
                if create_exclusive and not disposed:
                    try:
                        _discard_just_created_node_locked(
                            parent,
                            name,
                            "file",
                        )
                    except OSError:
                        pass
                raise
        else:
            flags = (
                (os.O_RDWR if writable else os.O_RDONLY)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            if create_exclusive:
                flags |= os.O_CREAT | os.O_EXCL
            descriptor = os.open(
                name,
                flags,
                mode,
                dir_fd=_directory_native(parent),
            )
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode):
                    raise ValueError(
                        "local authority child is not an exact regular file"
                    )
                result = BoundFile(path, descriptor, _legacy_identity(opened))
            except BaseException:
                try:
                    if create_exclusive:
                        try:
                            retry = os.fstat(descriptor)
                        except OSError:
                            retry = None
                        try:
                            if retry is not None and stat.S_ISREG(
                                retry.st_mode
                            ):
                                _reclaim_owned_leaf_locked(
                                    parent,
                                    OwnedNode(
                                        name,
                                        _legacy_identity(retry),
                                        "file",
                                    ),
                                )
                            else:
                                _discard_just_created_node_locked(
                                    parent,
                                    name,
                                    "file",
                                )
                        except OSError:
                            pass
                finally:
                    os.close(descriptor)
                raise
        try:
            if before is not None and result.identity != before.identity:
                raise ValueError("local authority file changed while opening")
            rebound = stat_child(parent, name)
            if rebound.identity != result.identity:
                raise ValueError("local authority file changed while opening")
            if os.name == "nt" and create_exclusive and not delete_access:
                created_identity = result.identity
                result.close()
                stable = open_child_file(
                    parent,
                    name,
                    writable=writable,
                    mode=mode,
                )
                if stable.identity != created_identity:
                    stable.close()
                    raise ValueError(
                        "local authority file changed stable identity"
                    )
                result = stable
            return result
        except BaseException:
            try:
                result.close()
            except OSError:
                pass
            if create_exclusive:
                try:
                    _reclaim_owned_leaf_locked(
                        parent,
                        OwnedNode(name, result.identity, "file"),
                    )
                except OSError:
                    pass
            raise


def read_bound_file(file: BoundFile) -> bytes:
    _bound_file_identity(file)
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        size = ctypes.c_longlong()
        if not _GetFileSizeEx(file.native, ctypes.byref(size)):
            _raise_last_winerror(file.path)
        if not _SetFilePointerEx(file.native, 0, None, _FILE_BEGIN):
            _raise_last_winerror(file.path)
        remaining = size.value
        chunks: list[bytes] = []
        while remaining:
            amount = min(remaining, 1024 * 1024)
            buffer = ctypes.create_string_buffer(amount)
            read = ctypes.c_ulong()
            if not _ReadFile(file.native, buffer, amount, ctypes.byref(read), None):
                _raise_last_winerror(file.path)
            if read.value == 0:
                break
            chunks.append(buffer.raw[: read.value])
            remaining -= read.value
        return b"".join(chunks)
    os.lseek(file.native, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(file.native, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def write_bound_file(file: BoundFile, content: bytes) -> None:
    _bound_file_identity(file)
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        if not _SetFilePointerEx(file.native, 0, None, _FILE_BEGIN):
            _raise_last_winerror(file.path)
        offset = 0
        while offset < len(content):
            chunk = content[offset : offset + 1024 * 1024]
            written = ctypes.c_ulong()
            if not _WriteFile(
                file.native,
                chunk,
                len(chunk),
                ctypes.byref(written),
                None,
            ):
                _raise_last_winerror(file.path)
            if written.value == 0:
                raise OSError("local authority write made no progress")
            offset += written.value
        if not _SetEndOfFile(file.native):
            _raise_last_winerror(file.path)
        return
    view = memoryview(content)
    offset = 0
    while offset < len(view):
        written = os.write(file.native, view[offset:])
        if written <= 0:
            raise OSError("local authority write made no progress")
        offset += written


def sync_bound_file(file: BoundFile) -> None:
    _bound_file_identity(file)
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        if not _FlushFileBuffers(file.native):
            _raise_last_winerror(file.path)
    else:
        os.fsync(file.native)


def sync_bound_directory(directory: DirectoryLike) -> None:
    if os.name != "nt":
        os.fsync(_directory_native(directory))


def _rename_with_flags_posix(
    directory: DirectoryLike,
    source: str,
    destination: str,
    *,
    darwin_flags: int,
    linux_flags: int,
) -> bool:
    library = ctypes.CDLL(None, use_errno=True)
    descriptor = _directory_native(directory)
    if sys.platform == "darwin" and hasattr(library, "renameatx_np"):
        rename = library.renameatx_np
        flags = darwin_flags
    elif sys.platform.startswith("linux") and hasattr(library, "renameat2"):
        rename = library.renameat2
        flags = linux_flags
    elif sys.platform.startswith("linux") and hasattr(library, "syscall"):
        machine = os.uname().machine.lower()
        syscall_number = {
            "x86_64": 316,
            "amd64": 316,
            "aarch64": 276,
            "arm64": 276,
            "i386": 353,
            "i686": 353,
            "armv7l": 382,
        }.get(machine)
        if syscall_number is None:
            raise OSError(errno.ENOTSUP, "atomic flagged rename is unsupported")
        result = library.syscall(
            ctypes.c_long(syscall_number),
            ctypes.c_int(descriptor),
            ctypes.c_char_p(os.fsencode(source)),
            ctypes.c_int(descriptor),
            ctypes.c_char_p(os.fsencode(destination)),
            ctypes.c_uint(linux_flags),
        )
        if result == 0:
            return True
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            return False
        raise OSError(error, os.strerror(error), destination)
    else:
        raise OSError(errno.ENOTSUP, "atomic flagged rename is unsupported")
    rename.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename.restype = ctypes.c_int
    result = rename(
        descriptor,
        os.fsencode(source),
        descriptor,
        os.fsencode(destination),
        flags,
    )
    if result == 0:
        return True
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        return False
    raise OSError(error, os.strerror(error), destination)


def rename_noreplace(
    directory: DirectoryLike,
    source: str,
    destination: str,
    *,
    expected_source: NodeIdentity | None = None,
    restore_source_on_mismatch: bool = False,
) -> bool:
    """Native atomic no-replace rename with post-operation identity recovery."""
    source = _one_component(source)
    destination = _one_component(destination)
    before = stat_child(directory, source)
    if expected_source is not None and before.identity != expected_source:
        raise ValueError("rename source is not the expected identity")
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        installed = _win_rename_noreplace(directory, source, destination, before.identity)
    else:
        installed = _rename_with_flags_posix(
            directory,
            source,
            destination,
            darwin_flags=0x00000004,
            linux_flags=1,
        )
    if not installed or expected_source is None:
        return installed
    destination_after = stat_child(directory, destination)
    if destination_after.identity == expected_source:
        return True
    if restore_source_on_mismatch:
        if not rename_noreplace(
            directory,
            destination,
            source,
            expected_source=destination_after.identity,
        ):
            raise OSError("raced rename source could not be restored")
        if optional_stat_child(directory, destination) is not None:
            raise OSError("raced rename source recovery could not be verified")
        sync_bound_directory(directory)
        raise ValueError("rename source changed during quarantine")
    rejected = f".{destination}.{uuid.uuid4().hex}.rejected"
    if not rename_noreplace(
        directory,
        destination,
        rejected,
        expected_source=destination_after.identity,
    ):
        raise OSError("raced rename source could not be quarantined")
    sync_bound_directory(directory)
    raise ValueError("rename source changed during installation")


def replace_with_backup(
    directory: DirectoryLike,
    source: str,
    destination: str,
    *,
    expected_source: NodeIdentity,
    expected_destination: NodeIdentity,
) -> OwnedNode:
    """Atomically replace destination and return exact displaced authority."""
    source_before = stat_child(directory, source)
    destination_before = stat_child(directory, destination)
    if source_before.identity != expected_source:
        raise ValueError("rename exchange node is not the expected identity")
    if destination_before.identity != expected_destination:
        raise ValueError("rename exchange node is not the expected identity")
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        backup = f".{destination}.{uuid.uuid4().hex}.tmp"
        try:
            _win_replace_file(directory, source, destination, backup)
        except OSError as exc:
            if getattr(exc, "winerror", None) not in {
                _ERROR_UNABLE_TO_REMOVE_REPLACED,
                _ERROR_UNABLE_TO_MOVE_REPLACEMENT,
                _ERROR_UNABLE_TO_MOVE_REPLACEMENT_2,
            }:
                raise
            if not _win_recover_partial_replace(
                directory,
                source,
                destination,
                backup,
                expected_source,
                expected_destination,
            ):
                raise
    else:
        backup = source
        if not _rename_with_flags_posix(
            directory,
            source,
            destination,
            darwin_flags=0x00000002,
            linux_flags=2,
        ):
            raise OSError("atomic exchange unexpectedly found a competing target")
    installed = stat_child(directory, destination)
    displaced = stat_child(directory, backup)
    if installed.identity == expected_source and displaced.identity == expected_destination:
        return OwnedNode(backup, expected_destination, "file")
    # Reverse only the exact tuple produced by this operation.
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        reversal_backup = f".{destination}.{uuid.uuid4().hex}.rejected"
        _win_replace_file(directory, backup, destination, reversal_backup)
        operation_source_name = reversal_backup
    else:
        if not _rename_with_flags_posix(
            directory,
            backup,
            destination,
            darwin_flags=0x00000002,
            linux_flags=2,
        ):
            raise OSError("raced rename exchange could not be reversed")
        operation_source_name = backup
    sync_bound_directory(directory)
    if installed.identity == expected_source:
        reclaim_owned_leaf(
            directory,
            OwnedNode(operation_source_name, expected_source, "file"),
        )
    if installed.identity != expected_source:
        raise ValueError("rename source changed during exchange")
    raise ValueError("rename destination changed during exchange")


def _reclaim_owned_leaf_locked(
    directory: DirectoryLike,
    owned: OwnedNode,
) -> bool:
    """Reclaim one leaf while the caller holds its parent namespace lock."""
    if owned.kind != "file":
        raise ValueError("owned-node capability is not a file")
    current = optional_stat_child(directory, owned.name)
    if current is None:
        return True
    if current.identity != owned.identity or current.kind != "file":
        return False
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        file = open_child_file(
            directory,
            owned.name,
            delete_access=True,
        )
        try:
            if file.identity != owned.identity:
                return False
            _win_dispose(file.native, file.path)
        finally:
            file.close()
    else:
        os.unlink(owned.name, dir_fd=_directory_native(directory))
    sync_bound_directory(directory)
    return True


def reclaim_owned_leaf(directory: DirectoryLike, owned: OwnedNode) -> bool:
    """Delete only the still-bound exact owned leaf; retain path replacements."""
    with exclusive_parent_namespace_lock(directory):
        return _reclaim_owned_leaf_locked(directory, owned)


def _reclaim_owned_tree_locked(
    directory: DirectoryLike,
    owned: OwnedNode,
) -> bool:
    """Reclaim one flat tree while the caller holds its parent namespace lock."""
    if owned.kind != "directory":
        raise ValueError("owned-node capability is not a directory")
    current = optional_stat_child(directory, owned.name)
    if current is None:
        return True
    if current.identity != owned.identity or current.kind != "directory":
        return False
    child = open_child_directory(directory, owned.name, expected=owned.identity)
    try:
        with exclusive_parent_namespace_lock(child):
            names = list_children(child)
            for name in names:
                expected = owned.children.get(name)
                if expected is None:
                    return False
                info = stat_child(child, name)
                if info.identity != expected or info.kind != "file":
                    return False
            for name in names:
                if not _reclaim_owned_leaf_locked(
                    child,
                    OwnedNode(name, owned.children[name], "file"),
                ):
                    return False
            if list_children(child):
                return False
    finally:
        child.close()
    rebound = stat_child(directory, owned.name)
    if rebound.identity != owned.identity:
        return False
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI
        child_handle = _win_open_path(
            _directory_path(directory) / owned.name,
            access=_DELETE | _FILE_READ_ATTRIBUTES | _SYNCHRONIZE,
            creation=_OPEN_EXISTING,
            directory=True,
            share_delete=True,
        )
        try:
            if _win_identity(child_handle)[0] != owned.identity:
                return False
            _win_dispose(child_handle, _directory_path(directory) / owned.name)
        finally:
            _win_close(child_handle)
    else:
        os.rmdir(owned.name, dir_fd=_directory_native(directory))
    sync_bound_directory(directory)
    return True


def reclaim_owned_tree(directory: DirectoryLike, owned: OwnedNode) -> bool:
    """Reclaim an exact flat owned tree without traversing foreign children."""
    with exclusive_parent_namespace_lock(directory):
        return _reclaim_owned_tree_locked(directory, owned)


@dataclass
class _NamespaceLockEntry:
    """One process-local owner/refcount for an exact native parent lock."""

    owner_thread: int
    depth: int = 1


_NAMESPACE_LOCK_CONDITION = threading.Condition()
_NAMESPACE_LOCK_REGISTRY: dict[tuple[int, NodeIdentity], _NamespaceLockEntry] = {}


@contextmanager
def exclusive_parent_namespace_lock(directory: DirectoryLike) -> Iterator[None]:
    """Serialize cooperating creators on one exact parent identity."""
    identity = directory_identity(directory)
    process_id = os.getpid()
    key = (process_id, identity)
    owner_thread = threading.get_ident()
    with _NAMESPACE_LOCK_CONDITION:
        while True:
            active = _NAMESPACE_LOCK_REGISTRY.get(key)
            if active is None:
                entry = _NamespaceLockEntry(owner_thread)
                _NAMESPACE_LOCK_REGISTRY[key] = entry
                nested = False
                break
            if active.owner_thread == owner_thread:
                if directory_identity(directory) != identity:
                    raise ValueError("local authority parent identity changed")
                active.depth += 1
                entry = active
                nested = True
                break
            _NAMESPACE_LOCK_CONDITION.wait()
    if nested:
        try:
            yield
        finally:
            if os.getpid() == process_id:
                with _NAMESPACE_LOCK_CONDITION:
                    entry.depth -= 1
        return

    mutex: int | None = None
    descriptor: int | None = None
    try:
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            name = "Global\\FAPO-" + hashlib.sha256(
                repr(identity).encode()
            ).hexdigest()
            mutex = _CreateMutexW(None, False, name)
            if not mutex:
                _raise_last_winerror(name)
            wait = _WaitForSingleObject(mutex, _INFINITE)
            if wait not in {_WAIT_OBJECT_0, _WAIT_ABANDONED}:
                _win_close(mutex)
                mutex = None
                raise OSError(
                    errno.ENOTSUP,
                    "Windows authority mutex is unavailable",
                )
        else:
            if _fcntl is None:
                raise OSError(
                    errno.ENOTSUP,
                    "native directory lock backend is unavailable",
                )
            descriptor = _directory_native(directory)
            _fcntl.flock(descriptor, _fcntl.LOCK_EX)
    except BaseException:
        with _NAMESPACE_LOCK_CONDITION:
            _NAMESPACE_LOCK_REGISTRY.pop(key, None)
            _NAMESPACE_LOCK_CONDITION.notify_all()
        raise
    try:
        yield
    finally:
        if os.getpid() == process_id:
            try:
                if os.name == "nt":  # pragma: no cover - exercised by Windows CI
                    assert mutex is not None
                    try:
                        if not _ReleaseMutex(mutex):
                            _raise_last_winerror("authority namespace mutex")
                    finally:
                        _win_close(mutex)
                else:
                    assert descriptor is not None
                    assert _fcntl is not None
                    _fcntl.flock(descriptor, _fcntl.LOCK_UN)
            finally:
                with _NAMESPACE_LOCK_CONDITION:
                    entry.depth -= 1
                    if entry.depth != 0:
                        raise RuntimeError(
                            "local authority namespace lock refcount is unbalanced"
                        )
                    _NAMESPACE_LOCK_REGISTRY.pop(key, None)
                    _NAMESPACE_LOCK_CONDITION.notify_all()


class _BoundFileLock(BaseFileLock):
    """filelock timeout/reentrancy orchestration over one already-bound handle."""

    def __init__(self, file: BoundFile, timeout: float) -> None:
        self._bound_file = file
        super().__init__(
            os.fspath(file.path),
            timeout=timeout,
            mode=0o600,
            thread_local=True,
        )

    def _register_context_descriptor(self) -> None:
        """Keep filelock from claiming the caller-owned bound descriptor."""

    def _unregister_released_descriptor(self) -> None:
        """The bound-file owner, not filelock, owns descriptor cleanup."""

    def _descriptors_for_fork(
        self,
    ) -> tuple[tuple[int, tuple[int, int] | None], ...]:
        """Exclude the caller-owned descriptor from filelock fork cleanup."""
        return ()

    def _acquire(self) -> None:
        if self._bound_file.opening_pid != os.getpid():
            raise ValueError("bound file belongs to a different process")
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            acquired = _win_try_lock(self._bound_file.native)
        else:
            if _fcntl is None:
                raise OSError(errno.ENOTSUP, "native hard-lock backend is unavailable")
            try:
                _fcntl.flock(
                    self._bound_file.native,
                    _fcntl.LOCK_EX | _fcntl.LOCK_NB,
                )
            except BlockingIOError:
                acquired = False
            else:
                acquired = True
        if acquired:
            self._context.lock_file_fd = self._bound_file.native

    def _release(self) -> None:
        if self._bound_file.opening_pid != os.getpid():
            self._context.lock_file_fd = None
            return
        if os.name == "nt":  # pragma: no cover - exercised by Windows CI
            _win_unlock(self._bound_file.native)
        elif _fcntl is not None:
            _fcntl.flock(self._bound_file.native, _fcntl.LOCK_UN)
        self._context.lock_file_fd = None


@dataclass
class _ExactFileLockEntry:
    """One process-local owner/refcount over an acquired exact file lock."""

    owner_thread: int
    lock: _BoundFileLock
    file: BoundFile
    depth: int = 1


_EXACT_FILE_LOCK_CONDITION = threading.Condition()
_EXACT_FILE_LOCK_REGISTRY: dict[tuple[int, NodeIdentity], _ExactFileLockEntry] = {}


def _remaining_timeout(deadline: float | None) -> float:
    if deadline is None:
        return -1
    return max(0.0, deadline - time.monotonic())


@contextmanager
def exact_file_lock(file: BoundFile, *, timeout: float) -> Iterator[None]:
    """Acquire one native hard lock without unlinking/truncating its name."""
    identity = _bound_file_identity(file)
    process_id = os.getpid()
    key = (process_id, identity)
    owner_thread = threading.get_ident()
    deadline = None if timeout < 0 else time.monotonic() + timeout
    path_key = os.path.normcase(os.path.abspath(os.fspath(file.path)))
    with _EXACT_FILE_LOCK_CONDITION:
        while True:
            for active_key, active in _EXACT_FILE_LOCK_REGISTRY.items():
                active_path = os.path.normcase(
                    os.path.abspath(os.fspath(active.file.path))
                )
                if active_path == path_key and active_key != key:
                    raise ValueError("local authority lock path identity changed")
            active = _EXACT_FILE_LOCK_REGISTRY.get(key)
            if active is None:
                lock = _BoundFileLock(file, timeout)
                entry = _ExactFileLockEntry(owner_thread, lock, file)
                _EXACT_FILE_LOCK_REGISTRY[key] = entry
                nested = False
                break
            if active.owner_thread == owner_thread:
                if _bound_file_identity(active.file) != identity:
                    raise ValueError("local authority lock handle identity changed")
                active.depth += 1
                entry = active
                nested = True
                break
            remaining = _remaining_timeout(deadline)
            if remaining == 0:
                raise TimeoutError("local authority lock is busy")
            _EXACT_FILE_LOCK_CONDITION.wait(
                timeout=None if remaining < 0 else remaining
            )
    if nested:
        try:
            entry.lock.acquire(timeout=0, poll_interval=0.01)
        except Timeout as exc:
            with _EXACT_FILE_LOCK_CONDITION:
                entry.depth -= 1
            raise TimeoutError("local authority lock is busy") from exc
        except BaseException:
            with _EXACT_FILE_LOCK_CONDITION:
                entry.depth -= 1
            raise
        try:
            yield
        finally:
            if os.getpid() == process_id:
                try:
                    entry.lock.release()
                finally:
                    with _EXACT_FILE_LOCK_CONDITION:
                        entry.depth -= 1
        return

    try:
        lock.acquire(
            timeout=_remaining_timeout(deadline),
            poll_interval=0.01,
        )
    except Timeout as exc:
        with _EXACT_FILE_LOCK_CONDITION:
            _EXACT_FILE_LOCK_REGISTRY.pop(key, None)
            _EXACT_FILE_LOCK_CONDITION.notify_all()
        raise TimeoutError("local authority lock is busy") from exc
    except BaseException:
        with _EXACT_FILE_LOCK_CONDITION:
            _EXACT_FILE_LOCK_REGISTRY.pop(key, None)
            _EXACT_FILE_LOCK_CONDITION.notify_all()
        raise
    try:
        yield
    finally:
        if os.getpid() == process_id:
            try:
                lock.release()
            finally:
                with _EXACT_FILE_LOCK_CONDITION:
                    entry.depth -= 1
                    if entry.depth != 0 or lock.is_locked:
                        raise RuntimeError(
                            "local authority file lock refcount is unbalanced"
                        )
                    _EXACT_FILE_LOCK_REGISTRY.pop(key, None)
                    _EXACT_FILE_LOCK_CONDITION.notify_all()


def _reset_process_lock_state_after_fork() -> None:
    """Discard copied process-local ownership state in a forked child."""
    global _NAMESPACE_LOCK_CONDITION, _NAMESPACE_LOCK_REGISTRY
    global _EXACT_FILE_LOCK_CONDITION, _EXACT_FILE_LOCK_REGISTRY
    _NAMESPACE_LOCK_CONDITION = threading.Condition()
    _NAMESPACE_LOCK_REGISTRY = {}
    _EXACT_FILE_LOCK_CONDITION = threading.Condition()
    _EXACT_FILE_LOCK_REGISTRY = {}


try:
    os.register_at_fork(after_in_child=_reset_process_lock_state_after_fork)
except AttributeError:  # pragma: no cover - Windows has no fork.
    pass


# -- Windows native bindings -------------------------------------------------

if os.name == "nt":  # pragma: no cover - definitions execute on Windows CI
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _DELETE = 0x00010000
    _SYNCHRONIZE = 0x00100000
    _FILE_LIST_DIRECTORY = 0x0001
    _FILE_READ_ATTRIBUTES = 0x0080
    _FILE_SHARE_READ = 0x1
    _FILE_SHARE_WRITE = 0x2
    _FILE_SHARE_DELETE = 0x4
    _CREATE_NEW = 1
    _OPEN_EXISTING = 3
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    _FILE_ATTRIBUTE_DIRECTORY = 0x10
    _FILE_BEGIN = 0
    _ERROR_FILE_NOT_FOUND = 2
    _ERROR_PATH_NOT_FOUND = 3
    _ERROR_FILE_EXISTS = 80
    _ERROR_ALREADY_EXISTS = 183
    _ERROR_LOCK_VIOLATION = 33
    _ERROR_UNABLE_TO_REMOVE_REPLACED = 1175
    _ERROR_UNABLE_TO_MOVE_REPLACEMENT = 1176
    _ERROR_UNABLE_TO_MOVE_REPLACEMENT_2 = 1177
    _LOCKFILE_EXCLUSIVE_LOCK = 0x2
    _LOCKFILE_FAIL_IMMEDIATELY = 0x1
    _WAIT_OBJECT_0 = 0
    _WAIT_ABANDONED = 0x80
    _INFINITE = 0xFFFFFFFF
    _FILE_RENAME_INFO_CLASS = 3
    _FILE_DISPOSITION_INFO_CLASS = 4
    _FILE_DISPOSITION_INFO_EX_CLASS = 21
    _FILE_DISPOSITION_DELETE = 0x1
    _FILE_DISPOSITION_POSIX_SEMANTICS = 0x2
    _FILE_DISPOSITION_IGNORE_READONLY_ATTRIBUTE = 0x10

    class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    class _OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ("Internal", ctypes.c_size_t),
            ("InternalHigh", ctypes.c_size_t),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE),
        ]

    class _FILE_ID_128(ctypes.Structure):
        _fields_ = [("identifier", ctypes.c_ubyte * 16)]

    class _FILE_ID_INFO(ctypes.Structure):
        _fields_ = [
            ("volume_serial_number", ctypes.c_ulonglong),
            ("file_id", _FILE_ID_128),
        ]

    class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
        _fields_ = [
            ("file_attributes", wintypes.DWORD),
            ("reparse_tag", wintypes.DWORD),
        ]

    _CreateFileW = _kernel32.CreateFileW
    _CreateFileW.restype = wintypes.HANDLE
    _CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _CreateDirectoryW = _kernel32.CreateDirectoryW
    _CreateDirectoryW.restype = wintypes.BOOL
    _CreateDirectoryW.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p]
    _CloseHandle = _kernel32.CloseHandle
    _CloseHandle.restype = wintypes.BOOL
    _CloseHandle.argtypes = [wintypes.HANDLE]
    _GetFileInformationByHandle = _kernel32.GetFileInformationByHandle
    _GetFileInformationByHandle.restype = wintypes.BOOL
    _GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION),
    ]
    _GetFileInformationByHandleEx = _kernel32.GetFileInformationByHandleEx
    _GetFileInformationByHandleEx.restype = wintypes.BOOL
    _GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _FlushFileBuffers = _kernel32.FlushFileBuffers
    _FlushFileBuffers.restype = wintypes.BOOL
    _FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _ReadFile = _kernel32.ReadFile
    _ReadFile.restype = wintypes.BOOL
    _ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    _WriteFile = _kernel32.WriteFile
    _WriteFile.restype = wintypes.BOOL
    _WriteFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    _SetEndOfFile = _kernel32.SetEndOfFile
    _SetEndOfFile.restype = wintypes.BOOL
    _SetEndOfFile.argtypes = [wintypes.HANDLE]
    _SetFilePointerEx = _kernel32.SetFilePointerEx
    _SetFilePointerEx.restype = wintypes.BOOL
    _SetFilePointerEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    ]
    _GetFileSizeEx = _kernel32.GetFileSizeEx
    _GetFileSizeEx.restype = wintypes.BOOL
    _GetFileSizeEx.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_longlong),
    ]
    _SetFileInformationByHandle = _kernel32.SetFileInformationByHandle
    _SetFileInformationByHandle.restype = wintypes.BOOL
    _SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _ReplaceFileW = _kernel32.ReplaceFileW
    _ReplaceFileW.restype = wintypes.BOOL
    _ReplaceFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    _LockFileEx = _kernel32.LockFileEx
    _LockFileEx.restype = wintypes.BOOL
    _LockFileEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_OVERLAPPED),
    ]
    _UnlockFileEx = _kernel32.UnlockFileEx
    _UnlockFileEx.restype = wintypes.BOOL
    _UnlockFileEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_OVERLAPPED),
    ]
    _CreateMutexW = _kernel32.CreateMutexW
    _CreateMutexW.restype = wintypes.HANDLE
    _CreateMutexW.argtypes = [
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    _WaitForSingleObject = _kernel32.WaitForSingleObject
    _WaitForSingleObject.restype = wintypes.DWORD
    _WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _ReleaseMutex = _kernel32.ReleaseMutex
    _ReleaseMutex.restype = wintypes.BOOL
    _ReleaseMutex.argtypes = [wintypes.HANDLE]


def _win_open_directory_chain(path: Path) -> BoundDirectory:  # pragma: no cover
    """Open every Windows ancestor without following a reparse component."""
    lexical = Path(os.path.abspath(os.fspath(path)))
    candidates = [
        candidate
        for candidate in (*reversed(lexical.parents), lexical)
        if candidate != Path(".")
    ]
    opened: list[int] = []
    try:
        for candidate in candidates:
            opened.append(
                _win_open_path(
                    candidate,
                    access=(
                        _FILE_LIST_DIRECTORY
                        | _FILE_READ_ATTRIBUTES
                        | _SYNCHRONIZE
                    ),
                    creation=_OPEN_EXISTING,
                    directory=True,
                    share_delete=False,
                )
            )
        handle = opened.pop()
        identity, kind = _win_identity(handle)
        if kind != "directory":
            raise ValueError("local authority node is not an exact directory")
        return BoundDirectory(
            lexical,
            handle,
            identity,
            ancestor_natives=tuple(opened),
        )
    except BaseException:
        if "handle" in locals():
            opened.append(handle)
        for handle in reversed(opened):
            _win_close(handle)
        raise


def _win_open_path(
    path: Path,
    *,
    access: int,
    creation: int,
    directory: bool | None,
    share_delete: bool,
    dispose_on_error: bool = False,
    created_handle_state: _WindowsCreatedHandleState | None = None,
) -> int:  # pragma: no cover - exercised by Windows CI
    reclaim_created = dispose_on_error or creation == globals().get("_CREATE_NEW")
    if reclaim_created:
        access |= _DELETE
    flags = _FILE_FLAG_OPEN_REPARSE_POINT
    if directory is not False:
        flags |= _FILE_FLAG_BACKUP_SEMANTICS
    share = _FILE_SHARE_READ | _FILE_SHARE_WRITE
    if share_delete:
        share |= _FILE_SHARE_DELETE
    handle = _CreateFileW(
        str(path),
        access,
        share,
        None,
        creation,
        flags,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        _raise_last_winerror(path)
    if created_handle_state is not None:
        created_handle_state.handle_obtained = True
    try:
        _identity, kind = _win_identity(handle)
        if kind == "symlink_or_reparse" or (
            directory is True and kind != "directory"
        ) or (directory is False and kind != "file"):
            raise ValueError(
                "Windows authority node is a reparse point or wrong type"
            )
        return int(handle)
    except BaseException:
        try:
            if reclaim_created:
                try:
                    _win_dispose(handle, path)
                except OSError:
                    pass
                else:
                    if created_handle_state is not None:
                        created_handle_state.disposed = True
        finally:
            _win_close(handle)
        raise


def _win_identity(handle: int) -> tuple[NodeIdentity, str]:  # pragma: no cover
    file_id = _FILE_ID_INFO()
    if not _GetFileInformationByHandleEx(
        handle,
        18,  # FileIdInfo
        ctypes.byref(file_id),
        ctypes.sizeof(file_id),
    ):
        _raise_last_winerror("authority handle")
    attributes = _FILE_ATTRIBUTE_TAG_INFO()
    if not _GetFileInformationByHandleEx(
        handle,
        9,  # FileAttributeTagInfo
        ctypes.byref(attributes),
        ctypes.sizeof(attributes),
    ):
        _raise_last_winerror("authority handle")
    identifier = int.from_bytes(bytes(file_id.file_id.identifier), "little")
    attribute_bits = attributes.file_attributes
    if attribute_bits & _FILE_ATTRIBUTE_REPARSE_POINT:
        kind = "symlink_or_reparse"
        mode = stat.S_IFLNK
    elif attribute_bits & _FILE_ATTRIBUTE_DIRECTORY:
        kind = "directory"
        mode = stat.S_IFDIR
    else:
        kind = "file"
        mode = stat.S_IFREG
    return (file_id.volume_serial_number, identifier, mode), kind


def _win_close(handle: int) -> None:  # pragma: no cover
    if not _CloseHandle(handle):
        _raise_last_winerror("authority handle")


def _win_rename_noreplace(
    directory: DirectoryLike,
    source: str,
    destination: str,
    expected: NodeIdentity,
) -> bool:  # pragma: no cover
    source_info = stat_child(directory, source)
    if source_info.identity != expected:
        raise ValueError("rename source changed before Windows rename")
    parent_path = _directory_path(directory)
    source_path = parent_path / source
    destination_path = parent_path / destination
    handle = _win_open_path(
        source_path,
        access=_DELETE | _FILE_READ_ATTRIBUTES | _SYNCHRONIZE,
        creation=_OPEN_EXISTING,
        directory=source_info.kind == "directory",
        share_delete=True,
    )
    try:
        if _win_identity(handle)[0] != expected:
            raise ValueError("rename source changed before Windows rename")
        buffer = _windows_rename_info_buffer(str(destination_path))
        if not _SetFileInformationByHandle(
            handle,
            _FILE_RENAME_INFO_CLASS,
            buffer,
            len(buffer),
        ):
            error = ctypes.get_last_error()
            if error in {_ERROR_FILE_EXISTS, _ERROR_ALREADY_EXISTS}:
                return False
            raise ctypes.WinError(error)
        return True
    finally:
        _win_close(handle)


def _win_replace_file(
    directory: DirectoryLike,
    source: str,
    destination: str,
    backup: str,
) -> None:  # pragma: no cover
    root = _directory_path(directory)
    if not _ReplaceFileW(
        str(root / destination),
        str(root / source),
        str(root / backup),
        0,
        None,
        None,
    ):
        _raise_last_winerror(root / destination)


def _win_recover_partial_replace(
    directory: DirectoryLike,
    source: str,
    destination: str,
    backup: str,
    expected_source: NodeIdentity,
    expected_destination: NodeIdentity,
) -> bool:  # pragma: no cover
    """Prove a partial ReplaceFileW outcome or restore its exact old tuple."""
    source_info = optional_stat_child(directory, source)
    destination_info = optional_stat_child(directory, destination)
    backup_info = optional_stat_child(directory, backup)
    source_identity = source_info.identity if source_info is not None else None
    destination_identity = (
        destination_info.identity if destination_info is not None else None
    )
    backup_identity = backup_info.identity if backup_info is not None else None

    if (
        source_identity is None
        and destination_identity == expected_source
        and backup_identity == expected_destination
    ):
        return True
    if (
        source_identity == expected_source
        and destination_identity == expected_destination
    ):
        return False
    if (
        source_identity == expected_source
        and destination_identity is None
        and backup_identity == expected_destination
    ):
        if not rename_noreplace(
            directory,
            backup,
            destination,
            expected_source=expected_destination,
        ):
            raise OSError("partial Windows CAS target could not be restored")
        return False
    raise OSError("partial Windows CAS outcome is ambiguous")


def _win_try_lock(handle: int) -> bool:  # pragma: no cover
    overlapped = _OVERLAPPED()
    if _LockFileEx(
        handle,
        _LOCKFILE_EXCLUSIVE_LOCK | _LOCKFILE_FAIL_IMMEDIATELY,
        0,
        1,
        0,
        ctypes.byref(overlapped),
    ):
        return True
    error = ctypes.get_last_error()
    if error == _ERROR_LOCK_VIOLATION:
        return False
    raise ctypes.WinError(error)


def _win_unlock(handle: int) -> None:  # pragma: no cover
    overlapped = _OVERLAPPED()
    if not _UnlockFileEx(handle, 0, 1, 0, ctypes.byref(overlapped)):
        _raise_last_winerror("authority lock")


def _win_dispose(handle: int, path: Path) -> None:  # pragma: no cover
    flags = ctypes.c_ulong(
        _FILE_DISPOSITION_DELETE
        | _FILE_DISPOSITION_POSIX_SEMANTICS
        | _FILE_DISPOSITION_IGNORE_READONLY_ATTRIBUTE
    )
    if _SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_EX_CLASS,
        ctypes.byref(flags),
        ctypes.sizeof(flags),
    ):
        return
    delete = wintypes.BOOLEAN(True)
    if not _SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(delete),
        ctypes.sizeof(delete),
    ):
        _raise_last_winerror(path)


def _raise_last_winerror(path: object) -> None:  # pragma: no cover
    error = ctypes.get_last_error()
    if error in {_ERROR_FILE_NOT_FOUND, _ERROR_PATH_NOT_FOUND}:
        raise FileNotFoundError(error, os.strerror(error), os.fspath(path))
    if error in {_ERROR_FILE_EXISTS, _ERROR_ALREADY_EXISTS}:
        raise FileExistsError(error, os.strerror(error), os.fspath(path))
    raise ctypes.WinError(error)
