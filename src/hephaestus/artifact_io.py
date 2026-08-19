# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Failure-safe single-file artifact persistence primitives."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable, Mapping, TextIO, Union

TextContent = Union[str, Iterable[str]]


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically replace one JSON file after durable serialization."""

    def produce(handle: TextIO) -> None:
        json.dump(dict(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")

    _atomic_write_text(path, produce)


def atomic_write_jsonl(
    path: Path,
    rows: Iterable[Mapping[str, Any]],
) -> None:
    """Atomically replace one JSONL file, including iterable failures."""

    def produce(handle: TextIO) -> None:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")

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
        serialized = json.dumps(dict(payload), sort_keys=True) + "\n"
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
        _sync_parent_directory(path.parent)
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
        _sync_parent_directory(path.parent)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _sync_parent_directory(directory: Path) -> None:
    """Persist a successful rename in directory metadata on POSIX systems."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
