# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Strict, cycle-free JSONL parsing for durable control authority."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Literal, Mapping

from src.hephaestus.artifact_io import atomic_write_bytes_at, rename_noreplace_at


@dataclass(frozen=True)
class LocalAuthorityFile:
    """One lexically bound local authority file and its optional read bytes."""

    path: Path
    data: bytes | None
    exists: bool
    identity: tuple[int, int, int] | None = None


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """Return whether two stat results identify the same exact node kind."""
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
    )


def _local_directory_inventory_at(
    directory_descriptor: int,
) -> dict[str, tuple[int, int, int]]:
    """Capture every direct child's exact no-follow identity."""
    inventory: dict[str, tuple[int, int, int]] = {}
    for child in os.listdir(directory_descriptor):
        details = os.stat(
            child,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        inventory[child] = (
            details.st_dev,
            details.st_ino,
            stat.S_IFMT(details.st_mode),
        )
    return inventory


def create_and_open_local_directory_at(
    parent_descriptor: int,
    name: str,
    *,
    final_mode: int,
    replacement_error: str,
) -> tuple[int, tuple[int, int, int]]:
    """Privately build and install one directory under the writer lock.

    Cooperating creators serialize on the already-bound parent descriptor.
    The parent inventory detects unaccounted namespace changes before the new
    private entry is opened or mutated, and the opened identity is rechecked
    through no-replace installation.  This is defense in depth, not an atomic
    ``mkdir`` ownership proof: POSIX returns no descriptor from ``mkdirat``.
    The supported boundary therefore requires every same-identity Studio
    writer to honor this lock; arbitrary noncooperating same-UID mutation in
    the ``mkdir``-to-``open`` interval is outside that boundary.
    """
    if not name or Path(name).name != name:
        raise ValueError("local authority directory must be one path component")
    private_mode = 0o500
    name_tag = hashlib.sha256(os.fsencode(name)).hexdigest()[:16]
    private_name = (
        f".{name[:24]}.{name_tag}.{uuid.uuid4().hex}.directory"
    )
    fcntl.flock(parent_descriptor, fcntl.LOCK_EX)
    try:
        before_creation = _local_directory_inventory_at(parent_descriptor)
        if name in before_creation or private_name in before_creation:
            raise FileExistsError(name)
        os.mkdir(private_name, private_mode, dir_fd=parent_descriptor)
        after_creation = _local_directory_inventory_at(parent_descriptor)
        expected_names = {*before_creation, private_name}
        if set(after_creation) != expected_names or any(
            after_creation.get(child) != identity
            for child, identity in before_creation.items()
        ):
            raise ValueError(replacement_error)
        created = os.stat(
            private_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            stat.S_ISLNK(created.st_mode)
            or not stat.S_ISDIR(created.st_mode)
            or stat.S_IMODE(created.st_mode) != private_mode
            or after_creation.get(private_name)
            != (
                created.st_dev,
                created.st_ino,
                stat.S_IFMT(created.st_mode),
            )
        ):
            raise ValueError(replacement_error)
        directory_flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            descriptor = os.open(
                private_name,
                directory_flags,
                dir_fd=parent_descriptor,
            )
        except OSError as exc:
            raise ValueError(replacement_error) from exc
        opened = os.fstat(descriptor)
        if not _same_file_identity(opened, created) or os.listdir(descriptor):
            os.close(descriptor)
            raise ValueError(replacement_error)
        identity = (
            opened.st_dev,
            opened.st_ino,
            stat.S_IFMT(opened.st_mode),
        )
        os.fchmod(descriptor, final_mode)
        rebound = os.stat(
            private_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            rebound.st_dev,
            rebound.st_ino,
            stat.S_IFMT(rebound.st_mode),
        ) != identity:
            os.close(descriptor)
            raise ValueError(replacement_error)
        if not rename_noreplace_at(
            parent_descriptor,
            private_name,
            name,
            expected_source=identity,
        ):
            os.close(descriptor)
            raise ValueError(replacement_error)
        installed = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            installed.st_dev,
            installed.st_ino,
            stat.S_IFMT(installed.st_mode),
        ) != identity:
            os.close(descriptor)
            raise ValueError(replacement_error)
        after_install = _local_directory_inventory_at(parent_descriptor)
        expected_installed = dict(before_creation)
        expected_installed[name] = identity
        if after_install != expected_installed:
            os.close(descriptor)
            raise ValueError(replacement_error)
        os.fsync(parent_descriptor)
        return descriptor, identity
    finally:
        fcntl.flock(parent_descriptor, fcntl.LOCK_UN)


def _open_local_authority_root(
    lexical_root: Path,
    *,
    create: bool,
) -> int:
    """Open, or safely bootstrap, one exact trusted-root directory."""
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    try:
        root_before = os.lstat(lexical_root)
    except FileNotFoundError:
        if not create:
            raise ValueError("local authority root is missing or unsafe") from None
        root_name = lexical_root.name
        if not root_name or lexical_root.parent == lexical_root:
            raise ValueError("local authority root is missing or unsafe") from None
        parent_descriptor: int | None = None
        try:
            parent_before = os.lstat(lexical_root.parent)
            if stat.S_ISLNK(parent_before.st_mode) or not stat.S_ISDIR(
                parent_before.st_mode
            ):
                raise ValueError(
                    "local authority root parent is not an exact directory"
                )
            parent_descriptor = os.open(lexical_root.parent, directory_flags)
            parent_opened = os.fstat(parent_descriptor)
            if not _same_file_identity(parent_opened, parent_before):
                raise ValueError(
                    "local authority root parent changed while opening"
                )
            try:
                root_before = os.stat(
                    root_name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                try:
                    root_descriptor, _ = create_and_open_local_directory_at(
                        parent_descriptor,
                        root_name,
                        final_mode=0o755,
                        replacement_error=(
                            "new local authority root was replaced before opening"
                        ),
                    )
                except FileExistsError:
                    root_before = os.stat(
                        root_name,
                        dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                else:
                    return root_descriptor
            if stat.S_ISLNK(root_before.st_mode) or not stat.S_ISDIR(
                root_before.st_mode
            ):
                raise ValueError("local authority root is not an exact directory")
            try:
                root_descriptor = os.open(
                    root_name,
                    directory_flags,
                    dir_fd=parent_descriptor,
                )
            except OSError as exc:
                raise ValueError(
                    "local authority root changed while opening"
                ) from exc
            root_opened = os.fstat(root_descriptor)
            if not _same_file_identity(root_opened, root_before):
                os.close(root_descriptor)
                raise ValueError("local authority root changed while opening")
            return root_descriptor
        except OSError as exc:
            raise ValueError("local authority root is missing or unsafe") from exc
        finally:
            if parent_descriptor is not None:
                os.close(parent_descriptor)
    if stat.S_ISLNK(root_before.st_mode) or not stat.S_ISDIR(root_before.st_mode):
        raise ValueError("local authority root is not an exact directory")
    try:
        root_descriptor = os.open(lexical_root, directory_flags)
    except OSError as exc:
        raise ValueError("local authority root is missing or unsafe") from exc
    root_opened = os.fstat(root_descriptor)
    if not _same_file_identity(root_opened, root_before):
        os.close(root_descriptor)
        raise ValueError("local authority root changed while opening")
    return root_descriptor


@contextmanager
def open_local_authority_directory(
    path: Path,
    trusted_root: Path,
    *,
    create: bool = False,
) -> Iterator[int]:
    """Yield one stable no-follow directory descriptor beneath a trusted root."""
    lexical_root = Path(os.path.abspath(os.fspath(trusted_root)))
    lexical_path = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError("local authority directory escapes its trusted root") from exc
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    current_descriptor = _open_local_authority_root(
        lexical_root,
        create=create,
    )
    try:
        for part in relative.parts:
            try:
                before = os.stat(
                    part,
                    dir_fd=current_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                if not create:
                    raise ValueError(
                        "local authority directory is missing"
                    ) from None
                try:
                    next_descriptor, _ = create_and_open_local_directory_at(
                        current_descriptor,
                        part,
                        final_mode=0o755,
                        replacement_error=(
                            "new local authority directory was replaced before opening"
                        ),
                    )
                except FileExistsError:
                    before = os.stat(
                        part,
                        dir_fd=current_descriptor,
                        follow_symlinks=False,
                    )
                else:
                    os.close(current_descriptor)
                    current_descriptor = next_descriptor
                    continue
            if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
                raise ValueError(
                    "local authority ancestor is not an exact directory"
                )
            try:
                next_descriptor = os.open(
                    part,
                    directory_flags,
                    dir_fd=current_descriptor,
                )
            except OSError as exc:
                raise ValueError(
                    "local authority ancestor changed while opening"
                ) from exc
            opened = os.fstat(next_descriptor)
            if not _same_file_identity(opened, before):
                os.close(next_descriptor)
                raise ValueError("local authority ancestor changed while opening")
            os.close(current_descriptor)
            current_descriptor = next_descriptor
        yield current_descriptor
    finally:
        os.close(current_descriptor)


@contextmanager
def acquire_local_authority_lock(
    path: Path,
    trusted_root: Path,
    *,
    timeout: float,
) -> Iterator[None]:
    """Hold one no-follow regular-file lock beneath a trusted root."""
    lexical_path = Path(os.path.abspath(os.fspath(path)))
    leaf_name = lexical_path.name
    if not leaf_name or leaf_name != os.fspath(path.name):
        raise ValueError("local authority lock must name one leaf")
    descriptor: int | None = None
    lock_flags = (
        os.O_RDWR
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    with open_local_authority_directory(
        lexical_path.parent,
        trusted_root,
        create=True,
    ) as directory_descriptor:
        try:
            before = os.stat(
                leaf_name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            try:
                descriptor = os.open(
                    leaf_name,
                    lock_flags | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=directory_descriptor,
                )
            except FileExistsError:
                before = os.stat(
                    leaf_name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            else:
                before = os.fstat(descriptor)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            if descriptor is not None:
                os.close(descriptor)
            raise ValueError("local authority lock is not an exact regular file")
        if descriptor is None:
            try:
                descriptor = os.open(
                    leaf_name,
                    lock_flags,
                    dir_fd=directory_descriptor,
                )
            except OSError as exc:
                raise ValueError(
                    "local authority lock changed while opening"
                ) from exc
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
            or stat.S_IFMT(opened.st_mode) != stat.S_IFMT(before.st_mode)
        ):
            os.close(descriptor)
            descriptor = None
            raise ValueError("local authority lock changed while opening")
        deadline = None if timeout < 0 else time.monotonic() + timeout
        try:
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked_name = os.stat(
                        leaf_name,
                        dir_fd=directory_descriptor,
                        follow_symlinks=False,
                    )
                    if (
                        locked_name.st_dev != opened.st_dev
                        or locked_name.st_ino != opened.st_ino
                        or stat.S_IFMT(locked_name.st_mode)
                        != stat.S_IFMT(opened.st_mode)
                    ):
                        raise ValueError(
                            "local authority lock changed after acquisition"
                        )
                    break
                except BlockingIOError:
                    if deadline is not None and time.monotonic() >= deadline:
                        raise TimeoutError("local authority lock is busy") from None
                    time.sleep(0.01)
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def resolve_local_authority_file(
    path: Path,
    trusted_root: Path,
    *,
    access: Literal["read", "read_optional", "write"],
    write_data: bytes | None = None,
    expected_write_data: bytes | None = None,
    check_expected_write_data: bool = False,
    write_precondition: Callable[[], None] | None = None,
) -> LocalAuthorityFile:
    """Validate/read one file through stable no-follow directory handles."""
    if access != "write" and write_data is not None:
        raise ValueError("local authority read cannot include write bytes")
    if write_data is not None and not isinstance(write_data, bytes):
        raise TypeError("local authority write data must be bytes")
    if check_expected_write_data and access != "write":
        raise ValueError("only local authority writes can bind expected bytes")
    if check_expected_write_data and expected_write_data is not None and not isinstance(
        expected_write_data,
        bytes,
    ):
        raise TypeError("expected local authority write data must be bytes")
    if write_precondition is not None and access != "write":
        raise ValueError("only local authority writes can have a precondition")
    lexical_root = Path(os.path.abspath(os.fspath(trusted_root)))
    lexical_path = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError("local authority path escapes its trusted root") from exc
    if not relative.parts:
        raise ValueError("local authority path must name a file beneath its root")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    try:
        root_before = os.lstat(lexical_root)
        if stat.S_ISLNK(root_before.st_mode) or not stat.S_ISDIR(
            root_before.st_mode
        ):
            raise ValueError("local authority root is not an exact directory")
        current_descriptor = os.open(lexical_root, directory_flags)
    except OSError as exc:
        raise ValueError("local authority root is missing or unsafe") from exc
    try:
        root_opened = os.fstat(current_descriptor)
        if (
            root_opened.st_dev != root_before.st_dev
            or root_opened.st_ino != root_before.st_ino
            or stat.S_IFMT(root_opened.st_mode)
            != stat.S_IFMT(root_before.st_mode)
        ):
            raise ValueError("local authority root changed while opening")
        for part in relative.parts[:-1]:
            try:
                before = os.stat(
                    part,
                    dir_fd=current_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                if access in {"write", "read_optional"} and write_data is None:
                    return LocalAuthorityFile(
                        path=lexical_path,
                        data=None,
                        exists=False,
                    )
                if access == "read":
                    raise ValueError("local authority ancestor is missing") from None
                try:
                    next_descriptor, _ = create_and_open_local_directory_at(
                        current_descriptor,
                        part,
                        final_mode=0o755,
                        replacement_error=(
                            "new local authority directory was replaced before opening"
                        ),
                    )
                except FileExistsError:
                    before = os.stat(
                        part,
                        dir_fd=current_descriptor,
                        follow_symlinks=False,
                    )
                else:
                    os.close(current_descriptor)
                    current_descriptor = next_descriptor
                    continue
            if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
                raise ValueError(
                    "local authority ancestor is not an exact directory"
                )
            try:
                next_descriptor = os.open(
                    part,
                    directory_flags,
                    dir_fd=current_descriptor,
                )
            except OSError as exc:
                raise ValueError(
                    "local authority ancestor changed while opening"
                ) from exc
            opened = os.fstat(next_descriptor)
            if (
                opened.st_dev != before.st_dev
                or opened.st_ino != before.st_ino
                or stat.S_IFMT(opened.st_mode) != stat.S_IFMT(before.st_mode)
            ):
                os.close(next_descriptor)
                raise ValueError("local authority ancestor changed while opening")
            os.close(current_descriptor)
            current_descriptor = next_descriptor

        leaf_name = relative.parts[-1]
        try:
            before = os.stat(
                leaf_name,
                dir_fd=current_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            if access in {"write", "read_optional"} and write_data is None:
                return LocalAuthorityFile(
                    path=lexical_path,
                    data=None,
                    exists=False,
                )
            if access == "read":
                raise ValueError("local authority file is missing") from None
            before = None
        if before is not None and (
            stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode)
        ):
            raise ValueError("local authority node is not an exact regular file")

        chunks: list[bytes] = []
        bound_identity: tuple[int, int, int] | None = None
        installed_identity: tuple[int, int, int] | None = None
        if before is not None:
            file_flags = (
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            try:
                descriptor = os.open(
                    leaf_name,
                    file_flags,
                    dir_fd=current_descriptor,
                )
            except OSError as exc:
                raise ValueError(
                    "local authority file changed while opening"
                ) from exc
            try:
                opened = os.fstat(descriptor)
                if (
                    opened.st_dev != before.st_dev
                    or opened.st_ino != before.st_ino
                    or stat.S_IFMT(opened.st_mode) != stat.S_IFMT(before.st_mode)
                ):
                    raise ValueError("local authority file changed while opening")
                bound_identity = (
                    opened.st_dev,
                    opened.st_ino,
                    stat.S_IFMT(opened.st_mode),
                )
                if access in {"read", "read_optional"} or (
                    check_expected_write_data and expected_write_data is not None
                ):
                    while True:
                        chunk = os.read(descriptor, 1024 * 1024)
                        if not chunk:
                            break
                        chunks.append(chunk)
            finally:
                os.close(descriptor)
        if access == "write" and write_data is not None:
            if check_expected_write_data:
                if expected_write_data is None and before is not None:
                    raise ValueError("local authority target appeared before writing")
                if expected_write_data is not None and before is None:
                    raise ValueError("local authority target disappeared before writing")
                if (
                    expected_write_data is not None
                    and b"".join(chunks) != expected_write_data
                ):
                    raise ValueError("local authority target bytes changed before writing")
            if write_precondition is not None:
                write_precondition()
            target_content = (
                {"expected_target_content": expected_write_data}
                if check_expected_write_data
                else {}
            )
            installed_identity = atomic_write_bytes_at(
                current_descriptor,
                leaf_name,
                write_data,
                expected_target=(
                    (
                        before.st_dev,
                        before.st_ino,
                        stat.S_IFMT(before.st_mode),
                    )
                    if before is not None
                    else None
                ),
                **target_content,
            )
    finally:
        os.close(current_descriptor)
    if write_data is not None:
        rebound = resolve_local_authority_file(
            lexical_path,
            lexical_root,
            access="read",
        )
        if rebound.data != write_data or rebound.identity != installed_identity:
            raise ValueError("local authority file changed after writing")
        return rebound
    return LocalAuthorityFile(
        path=lexical_path,
        data=b"".join(chunks) if access in {"read", "read_optional"} else None,
        exists=True,
        identity=bound_identity,
    )


def read_local_authority_file_at(
    directory_descriptor: int,
    filename: str,
) -> bytes:
    """Read one regular no-follow leaf through an already bound directory."""
    payload, _ = read_local_authority_file_with_identity_at(
        directory_descriptor,
        filename,
    )
    return payload


def read_local_authority_file_with_identity_at(
    directory_descriptor: int,
    filename: str,
) -> tuple[bytes, tuple[int, int, int]]:
    """Read one bound leaf and return the identity supplying its bytes."""
    if not filename or Path(filename).name != filename:
        raise ValueError("descriptor-relative filename must be one path component")
    before = os.stat(
        filename,
        dir_fd=directory_descriptor,
        follow_symlinks=False,
    )
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError(
            "local authority node is a symlink or not an exact regular file"
        )
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(filename, flags, dir_fd=directory_descriptor)
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
            or stat.S_IFMT(opened.st_mode) != stat.S_IFMT(before.st_mode)
        ):
            raise ValueError("local authority file changed while opening")
        opened_identity = (
            opened.st_dev,
            opened.st_ino,
            stat.S_IFMT(opened.st_mode),
        )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks), opened_identity
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def capture_local_authority_tree(
    root: Path,
    trusted_root: Path,
) -> tuple[dict[Path, bytes], tuple[tuple[str, str, int, int], ...]]:
    """Capture one closed no-follow tree through stable directory descriptors."""
    lexical_root = Path(os.path.abspath(os.fspath(root)))
    files: dict[Path, bytes] = {}
    records: list[tuple[str, str, int, int]] = []
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )

    def capture(directory_descriptor: int, relative_parent: Path) -> None:
        names = tuple(sorted(os.listdir(directory_descriptor)))
        for name in names:
            details = os.stat(
                name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            relative = relative_parent / name
            if stat.S_ISREG(details.st_mode):
                payload, opened_identity = read_local_authority_file_with_identity_at(
                    directory_descriptor,
                    name,
                )
                rebound = os.stat(
                    name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
                if (
                    opened_identity
                    != (
                        details.st_dev,
                        details.st_ino,
                        stat.S_IFMT(details.st_mode),
                    )
                    or
                    rebound.st_dev != details.st_dev
                    or rebound.st_ino != details.st_ino
                    or stat.S_IFMT(rebound.st_mode) != stat.S_IFMT(details.st_mode)
                ):
                    raise ValueError("local authority file changed while capturing")
                files[lexical_root / relative] = payload
                records.append((relative.as_posix(), "file", details.st_dev, details.st_ino))
                continue
            if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
                raise ValueError("local authority tree contains an unsafe node")
            child_descriptor = os.open(
                name,
                directory_flags,
                dir_fd=directory_descriptor,
            )
            try:
                opened = os.fstat(child_descriptor)
                if opened.st_dev != details.st_dev or opened.st_ino != details.st_ino:
                    raise ValueError("local authority directory changed while opening")
                records.append(
                    (relative.as_posix(), "directory", details.st_dev, details.st_ino)
                )
                capture(child_descriptor, relative)
            finally:
                os.close(child_descriptor)
        if tuple(sorted(os.listdir(directory_descriptor))) != names:
            raise ValueError("local authority directory inventory changed")

    with open_local_authority_directory(
        lexical_root,
        trusted_root,
    ) as root_descriptor:
        root_details = os.fstat(root_descriptor)
        records.append((".", "directory", root_details.st_dev, root_details.st_ino))
        capture(root_descriptor, Path())
    return files, tuple(records)


def remove_local_authority_file(
    path: Path,
    trusted_root: Path,
    *,
    expected_identity: tuple[int, int, int] | None = None,
) -> bool:
    """Quarantine one exact leaf without deleting a raced replacement node."""
    lexical_path = Path(os.path.abspath(os.fspath(path)))
    lexical_root = Path(os.path.abspath(os.fspath(trusted_root)))
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError("local authority path escapes its trusted root") from exc
    if not relative.parts:
        raise ValueError("local authority path must name a file beneath its root")
    try:
        with open_local_authority_directory(
            lexical_path.parent,
            lexical_root,
        ) as directory_descriptor:
            leaf_name = relative.parts[-1]
            try:
                details = os.stat(
                    leaf_name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return False
            if not stat.S_ISLNK(details.st_mode) and not stat.S_ISREG(
                details.st_mode
            ):
                raise ValueError("local authority cleanup node has an unsafe type")
            expected = (
                details.st_dev,
                details.st_ino,
                stat.S_IFMT(details.st_mode),
            )
            if expected_identity is not None and expected != expected_identity:
                raise ValueError(
                    "local authority cleanup node is not the expected identity"
                )
            quarantine_name = f".{leaf_name}.{uuid.uuid4().hex}.removed"
            if not rename_noreplace_at(
                directory_descriptor,
                leaf_name,
                quarantine_name,
                expected_source=expected,
                restore_source_on_mismatch=True,
            ):
                raise ValueError("local authority cleanup quarantine collided")
            quarantined = os.stat(
                quarantine_name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            quarantined_identity = (
                quarantined.st_dev,
                quarantined.st_ino,
                stat.S_IFMT(quarantined.st_mode),
            )
            if quarantined_identity != expected:
                raise ValueError("local authority cleanup node changed before removal")
            os.fsync(directory_descriptor)
    except ValueError as exc:
        if str(exc) == "local authority directory is missing":
            return False
        raise
    return True


def read_strict_jsonl_objects(
    path: Path,
    *,
    trusted_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Read strict standard-JSON object rows without skipping blank authority."""
    if trusted_root is not None:
        authority = resolve_local_authority_file(
            path,
            trusted_root,
            access="read_optional",
        )
        if not authority.exists:
            return []
        if authority.data is None:
            raise ValueError("local authority read did not return bytes")
        return parse_strict_jsonl_objects(authority.data)
    if not path.is_file():
        return []
    return parse_strict_jsonl_objects(path.read_bytes())


def write_local_authority_json(
    path: Path,
    trusted_root: Path,
    payload: Mapping[str, Any],
    *,
    precondition: Callable[[], None] | None = None,
    expected_current: bytes | None = None,
    check_expected_current: bool = False,
) -> None:
    """Persist one JSON object through the descriptor-bound authority writer."""
    data = (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    resolve_local_authority_file(
        path,
        trusted_root,
        access="write",
        write_data=data,
        expected_write_data=expected_current,
        check_expected_write_data=check_expected_current,
        write_precondition=precondition,
    )


def write_local_authority_jsonl(
    path: Path,
    trusted_root: Path,
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_current: bytes | None = None,
    check_expected_current: bool = False,
) -> None:
    """Persist JSONL rows through the descriptor-bound authority writer."""
    data = "".join(
        json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n"
        for row in rows
    ).encode("utf-8")
    resolve_local_authority_file(
        path,
        trusted_root,
        access="write",
        write_data=data,
        expected_write_data=expected_current,
        check_expected_write_data=check_expected_current,
    )


def write_local_authority_text(
    path: Path,
    trusted_root: Path,
    content: str,
    *,
    expected_current: bytes | None = None,
    check_expected_current: bool = False,
) -> None:
    """Persist UTF-8 text through the descriptor-bound authority writer."""
    resolve_local_authority_file(
        path,
        trusted_root,
        access="write",
        write_data=content.encode("utf-8"),
        expected_write_data=expected_current,
        check_expected_write_data=check_expected_current,
    )


def read_strict_json_object(
    path: Path,
    *,
    trusted_root: Path | None = None,
) -> dict[str, Any]:
    """Read one strict standard-JSON object without duplicate-key collapse."""
    if trusted_root is not None:
        authority = resolve_local_authority_file(
            path,
            trusted_root,
            access="read",
        )
        if authority.data is None:
            raise ValueError("local authority read did not return bytes")
        return parse_strict_json_object(authority.data)
    return parse_strict_json_object(path.read_bytes())


def parse_strict_json_object(raw: bytes) -> dict[str, Any]:
    """Parse exact UTF-8 JSON, rejecting duplicates and non-standard numbers."""
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("control JSON is invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("control JSON is not an object")
    return value


def parse_strict_jsonl_objects(raw: bytes) -> list[dict[str, Any]]:
    """Parse exact UTF-8 JSONL, rejecting blanks, duplicates, and constants."""
    text = raw.decode("utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            raise ValueError("control log contains a blank row")
        value = json.loads(
            line,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("control log row is not an object")
        rows.append(value)
    return rows


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("control JSON contains a duplicate key")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> Any:
    del value
    raise ValueError("control JSON contains a non-standard numeric constant")
