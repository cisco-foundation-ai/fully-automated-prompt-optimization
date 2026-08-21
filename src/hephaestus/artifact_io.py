# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Failure-safe single-file artifact persistence primitives."""

from __future__ import annotations

import ctypes
import errno
import json
import os
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable, Mapping, TextIO, Union

TextContent = Union[str, Iterable[str]]
_UNSPECIFIED_TARGET = object()
_UNSPECIFIED_TARGET_CONTENT = object()


def _descriptor_bytes(descriptor: int) -> bytes:
    """Read an opened regular file from its stable descriptor identity."""
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _rename_with_flags_at(
    directory_descriptor: int,
    source: str,
    destination: str,
    *,
    darwin_flags: int,
    linux_flags: int,
) -> bool:
    """Rename through one directory descriptor with native atomic flags."""
    library = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin":
        rename = library.renameatx_np
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(
            directory_descriptor,
            source_bytes,
            directory_descriptor,
            destination_bytes,
            darwin_flags,
        )
    elif sys.platform.startswith("linux") and hasattr(library, "renameat2"):
        rename = library.renameat2
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(
            directory_descriptor,
            source_bytes,
            directory_descriptor,
            destination_bytes,
            linux_flags,
        )
    else:
        raise OSError("atomic flagged rename is unsupported")
    if result == 0:
        return True
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        return False
    raise OSError(error, os.strerror(error), destination)


def rename_noreplace_at(
    directory_descriptor: int,
    source: str,
    destination: str,
    *,
    expected_source: tuple[int, int, int] | None = None,
) -> bool:
    """Atomically rename only when the destination name is absent."""
    if expected_source is not None:
        source_details = os.stat(
            source,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if (
            source_details.st_dev,
            source_details.st_ino,
            stat.S_IFMT(source_details.st_mode),
        ) != expected_source:
            raise ValueError("rename source is not the expected identity")
    return _rename_with_flags_at(
        directory_descriptor,
        source,
        destination,
        darwin_flags=0x00000004,
        linux_flags=1,
    )


def rename_exchange_at(
    directory_descriptor: int,
    source: str,
    destination: str,
    *,
    expected_source: tuple[int, int, int] | None = None,
    expected_destination: tuple[int, int, int] | None = None,
) -> None:
    """Atomically exchange two names beneath one stable directory descriptor."""
    for name, expected in (
        (source, expected_source),
        (destination, expected_destination),
    ):
        if expected is None:
            continue
        details = os.stat(
            name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if (
            details.st_dev,
            details.st_ino,
            stat.S_IFMT(details.st_mode),
        ) != expected:
            raise ValueError("rename exchange node is not the expected identity")
    if not _rename_with_flags_at(
        directory_descriptor,
        source,
        destination,
        darwin_flags=0x00000002,
        linux_flags=2,
    ):
        raise OSError("atomic exchange unexpectedly found a competing target")


def atomic_write_bytes_at(
    directory_descriptor: int,
    filename: str,
    content: bytes,
    *,
    expected_target: tuple[int, int, int] | None | object = _UNSPECIFIED_TARGET,
    expected_target_content: bytes | object = _UNSPECIFIED_TARGET_CONTENT,
) -> tuple[int, int, int]:
    """Atomically replace one file relative to an already verified directory."""
    if not filename or Path(filename).name != filename:
        raise ValueError("descriptor-relative filename must be one path component")
    temporary_name = f".{filename}.{uuid.uuid4().hex}.tmp"
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    temporary_descriptor: int | None = None
    try:
        if expected_target is _UNSPECIFIED_TARGET:
            try:
                current = os.stat(
                    filename,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                expected_target = None
            else:
                expected_target = (
                    current.st_dev,
                    current.st_ino,
                    stat.S_IFMT(current.st_mode),
                )
        temporary_descriptor = os.open(
            temporary_name,
            flags,
            0o600,
            dir_fd=directory_descriptor,
        )
        view = memoryview(content)
        offset = 0
        while offset < len(view):
            written = os.write(temporary_descriptor, view[offset:])
            if written <= 0:
                raise OSError("descriptor-relative authority write made no progress")
            offset += written
        os.fsync(temporary_descriptor)
        temporary_stat = os.fstat(temporary_descriptor)
        temporary_identity = (
            temporary_stat.st_dev,
            temporary_stat.st_ino,
            stat.S_IFMT(temporary_stat.st_mode),
        )
        named_temporary = os.stat(
            temporary_name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if (
            named_temporary.st_dev,
            named_temporary.st_ino,
            stat.S_IFMT(named_temporary.st_mode),
        ) != temporary_identity:
            raise ValueError("authority temporary source changed before installation")
        if _descriptor_bytes(temporary_descriptor) != content:
            raise ValueError("authority temporary source content changed before installation")
        if expected_target is None:
            if not rename_noreplace_at(
                directory_descriptor,
                temporary_name,
                filename,
                expected_source=temporary_identity,
            ):
                raise ValueError("authority target appeared before installation")
            installed = os.stat(
                filename,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            installed_identity = (
                installed.st_dev,
                installed.st_ino,
                stat.S_IFMT(installed.st_mode),
            )
            if installed_identity != temporary_identity:
                raise ValueError("authority temporary source changed during installation")
            if _descriptor_bytes(temporary_descriptor) != content:
                rejected_name = f".{filename}.{uuid.uuid4().hex}.rejected"
                if not rename_noreplace_at(
                    directory_descriptor,
                    filename,
                    rejected_name,
                    expected_source=temporary_identity,
                ):
                    raise OSError(
                        "raced authority installation could not be quarantined"
                    )
                raise ValueError(
                    "authority temporary source content changed during installation"
                )
        else:
            current = os.stat(
                filename,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            current_identity = (
                current.st_dev,
                current.st_ino,
                stat.S_IFMT(current.st_mode),
            )
            if current_identity != expected_target:
                raise ValueError("authority target changed before replacement")
            rename_exchange_at(
                directory_descriptor,
                temporary_name,
                filename,
                expected_source=temporary_identity,
                expected_destination=expected_target,
            )
            installed = os.stat(
                filename,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            installed_identity = (
                installed.st_dev,
                installed.st_ino,
                stat.S_IFMT(installed.st_mode),
            )
            displaced = os.stat(
                temporary_name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            displaced_identity = (
                displaced.st_dev,
                displaced.st_ino,
                stat.S_IFMT(displaced.st_mode),
            )
            if (
                installed_identity != temporary_identity
                or displaced_identity != expected_target
            ):
                if installed_identity != temporary_identity:
                    raise ValueError(
                        "authority temporary source changed during replacement"
                    )
                raise ValueError("authority target changed during replacement")
            if expected_target_content is not _UNSPECIFIED_TARGET_CONTENT:
                displaced_flags = (
                    os.O_RDONLY
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0)
                )
                displaced_descriptor = os.open(
                    temporary_name,
                    displaced_flags,
                    dir_fd=directory_descriptor,
                )
                try:
                    displaced_opened = os.fstat(displaced_descriptor)
                    if (
                        displaced_opened.st_dev,
                        displaced_opened.st_ino,
                        stat.S_IFMT(displaced_opened.st_mode),
                    ) != expected_target:
                        raise ValueError(
                            "authority target changed during replacement"
                        )
                    if _descriptor_bytes(displaced_descriptor) != expected_target_content:
                        rename_exchange_at(
                            directory_descriptor,
                            temporary_name,
                            filename,
                            expected_source=expected_target,
                            expected_destination=temporary_identity,
                        )
                        raise ValueError(
                            "authority target bytes changed during replacement"
                        )
                finally:
                    os.close(displaced_descriptor)
            if _descriptor_bytes(temporary_descriptor) != content:
                rename_exchange_at(
                    directory_descriptor,
                    temporary_name,
                    filename,
                    expected_source=expected_target,
                    expected_destination=temporary_identity,
                )
                raise ValueError(
                    "authority temporary source content changed during replacement"
                )
        os.fsync(directory_descriptor)
        return temporary_identity
    finally:
        if temporary_descriptor is not None:
            os.close(temporary_descriptor)
        # A descriptor does not provide an identity-bound unlink primitive.
        # If replacement failed, retain the uniquely named file rather than
        # deleting a different node raced into the reusable lexical name.


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically replace one JSON file after durable serialization."""

    def produce(handle: TextIO) -> None:
        json.dump(
            dict(payload),
            handle,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.write("\n")

    _atomic_write_text(path, produce)


def atomic_write_jsonl(
    path: Path,
    rows: Iterable[Mapping[str, Any]],
) -> None:
    """Atomically replace one JSONL file, including iterable failures."""

    def produce(handle: TextIO) -> None:
        for row in rows:
            handle.write(
                json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n"
            )

    _atomic_write_text(path, produce)


def atomic_write_text(path: Path, content: TextContent) -> None:
    """Atomically replace one UTF-8 text file from text or generated chunks."""

    def produce(handle: TextIO) -> None:
        if isinstance(content, str):
            handle.write(content)
            return
        for chunk in content:
            if not isinstance(chunk, str):
                raise TypeError("atomic text chunks must be strings")
            handle.write(chunk)

    _atomic_write_text(path, produce)


def atomic_copy_file(source: Path, destination: Path) -> None:
    """Atomically replace one file with a byte-for-byte copy."""
    source = source.resolve()

    def produce(handle: BinaryIO) -> None:
        with source.open("rb") as source_handle:
            shutil.copyfileobj(source_handle, handle)

    _atomic_write_binary(destination, produce)


def atomic_append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    """Append one JSONL row by atomically replacing a copied prior file."""

    def produce(handle: BinaryIO) -> None:
        needs_newline = False
        if path.is_file():
            with path.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, handle)
                if source_handle.tell() > 0:
                    source_handle.seek(-1, os.SEEK_END)
                    needs_newline = source_handle.read(1) != b"\n"
        if needs_newline:
            handle.write(b"\n")
        serialized = json.dumps(dict(payload), sort_keys=True, allow_nan=False) + "\n"
        handle.write(serialized.encode("utf-8"))

    _atomic_write_binary(path, produce)


def _atomic_write_text(
    path: Path,
    producer: Callable[[TextIO], None],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            producer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        sync_directory(path.parent)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _atomic_write_binary(
    path: Path,
    producer: Callable[[BinaryIO], None],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            producer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        sync_directory(path.parent)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def sync_directory(directory: Path) -> None:
    """Persist a successful rename in directory metadata on POSIX systems."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
