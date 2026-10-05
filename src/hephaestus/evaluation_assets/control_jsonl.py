# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Strict, cycle-free JSONL parsing for durable control authority."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Literal, Mapping

from src.hephaestus import local_authority_io as authority_io
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
    directory_descriptor: authority_io.DirectoryLike,
) -> dict[str, tuple[int, int, int]]:
    """Capture every direct child's exact no-follow identity."""
    return {
        child: authority_io.stat_child(directory_descriptor, child).identity
        for child in authority_io.list_children(directory_descriptor)
    }


def create_and_open_local_directory_at(
    parent_descriptor: authority_io.DirectoryLike,
    name: str,
    *,
    final_mode: int,
    replacement_error: str,
) -> tuple[authority_io.BoundDirectory, tuple[int, int, int]]:
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
    with authority_io.exclusive_parent_namespace_lock(parent_descriptor):
        descriptor: authority_io.BoundDirectory | None = None
        owned_name = private_name
        identity: tuple[int, int, int] | None = None
        try:
            before_creation = _local_directory_inventory_at(parent_descriptor)
            if name in before_creation or private_name in before_creation:
                raise FileExistsError(name)
            descriptor = authority_io.create_child_directory(
                parent_descriptor,
                private_name,
                mode=private_mode,
            )
            identity = descriptor.identity
            after_creation = _local_directory_inventory_at(parent_descriptor)
            expected_names = {*before_creation, private_name}
            if set(after_creation) != expected_names or any(
                after_creation.get(child) != before_identity
                for child, before_identity in before_creation.items()
            ):
                raise ValueError(replacement_error)
            created = authority_io.stat_child(parent_descriptor, private_name)
            if (
                created.kind != "directory"
                or after_creation.get(private_name) != created.identity
                or descriptor.identity != created.identity
                or authority_io.list_children(descriptor)
            ):
                raise ValueError(replacement_error)
            if os.name != "nt":
                os.fchmod(descriptor.native, final_mode)
            rebound = authority_io.stat_child(parent_descriptor, private_name)
            if rebound.identity != identity:
                raise ValueError(replacement_error)
            authority_io.prepare_directory_source_rename(descriptor)
            if not rename_noreplace_at(
                parent_descriptor,
                private_name,
                name,
                expected_source=identity,
            ):
                raise ValueError(replacement_error)
            owned_name = name
            installed = authority_io.stat_child(parent_descriptor, name)
            if installed.identity != identity:
                raise ValueError(replacement_error)
            descriptor = authority_io.bind_renamed_directory(
                parent_descriptor,
                name,
                expected=identity,
                previous=descriptor,
            )
            after_install = _local_directory_inventory_at(parent_descriptor)
            expected_installed = dict(before_creation)
            expected_installed[name] = identity
            if after_install != expected_installed:
                raise ValueError(replacement_error)
            authority_io.sync_bound_directory(parent_descriptor)
            return descriptor, identity
        except BaseException:
            if descriptor is not None:
                descriptor.close()
            if identity is not None:
                try:
                    authority_io._reclaim_owned_tree_locked(
                        parent_descriptor,
                        authority_io.OwnedNode(
                            owned_name,
                            identity,
                            "directory",
                        ),
                    )
                except OSError:
                    pass
            raise


def _open_local_authority_root(
    lexical_root: Path,
    *,
    create: bool,
) -> authority_io.BoundDirectory:
    """Open, or safely bootstrap, one exact trusted-root directory."""
    try:
        return authority_io.open_bound_directory(lexical_root)
    except FileNotFoundError:
        if not create:
            raise ValueError("local authority root is missing or unsafe") from None
        root_name = lexical_root.name
        if not root_name or lexical_root.parent == lexical_root:
            raise ValueError("local authority root is missing or unsafe") from None
        parent_descriptor: authority_io.BoundDirectory | None = None
        try:
            parent_descriptor = authority_io.open_bound_directory(
                lexical_root.parent
            )
            if authority_io.optional_stat_child(parent_descriptor, root_name) is None:
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
                    pass
                else:
                    return root_descriptor
            return authority_io.open_child_directory(
                parent_descriptor,
                root_name,
            )
        except OSError as exc:
            raise ValueError("local authority root is missing or unsafe") from exc
        finally:
            if parent_descriptor is not None:
                parent_descriptor.close()


@contextmanager
def open_local_authority_directory(
    path: Path,
    trusted_root: Path,
    *,
    create: bool = False,
) -> Iterator[authority_io.BoundDirectory]:
    """Yield one stable no-follow directory descriptor beneath a trusted root."""
    lexical_root = Path(os.path.abspath(os.fspath(trusted_root)))
    lexical_path = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError("local authority directory escapes its trusted root") from exc
    current_descriptor = _open_local_authority_root(
        lexical_root,
        create=create,
    )
    try:
        for part in relative.parts:
            before = authority_io.optional_stat_child(current_descriptor, part)
            if before is None:
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
                    before = authority_io.stat_child(current_descriptor, part)
                else:
                    current_descriptor.close()
                    current_descriptor = next_descriptor
                    continue
            if before.kind != "directory":
                raise ValueError(
                    "local authority ancestor is not an exact directory"
                )
            try:
                next_descriptor = authority_io.open_child_directory(
                    current_descriptor,
                    part,
                    expected=before.identity,
                )
            except (OSError, ValueError) as exc:
                raise ValueError(
                    "local authority ancestor changed while opening"
                ) from exc
            current_descriptor.close()
            current_descriptor = next_descriptor
        yield current_descriptor
    finally:
        current_descriptor.close()


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
    file: authority_io.BoundFile | None = None
    with open_local_authority_directory(
        lexical_path.parent,
        trusted_root,
        create=True,
    ) as directory_descriptor:
        before = authority_io.optional_stat_child(directory_descriptor, leaf_name)
        if before is None:
            try:
                file = authority_io.open_child_file(
                    directory_descriptor,
                    leaf_name,
                    writable=True,
                    create_exclusive=True,
                    mode=0o600,
                )
            except FileExistsError:
                before = authority_io.stat_child(
                    directory_descriptor,
                    leaf_name,
                )
            else:
                before = authority_io.NodeInfo(file.identity, "file", stat.S_IFREG)
        if before.kind != "file":
            if file is not None:
                file.close()
            raise ValueError("local authority lock is not an exact regular file")
        if file is None:
            try:
                file = authority_io.open_child_file(
                    directory_descriptor,
                    leaf_name,
                    writable=True,
                )
            except OSError as exc:
                raise ValueError(
                    "local authority lock changed while opening"
                ) from exc
        if file.identity != before.identity:
            file.close()
            file = None
            raise ValueError("local authority lock changed while opening")
        try:
            with authority_io.exact_file_lock(file, timeout=timeout):
                locked_name = authority_io.stat_child(
                    directory_descriptor,
                    leaf_name,
                )
                if locked_name.identity != file.identity:
                    raise ValueError(
                        "local authority lock changed after acquisition"
                    )
                yield
        finally:
            file.close()


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
    current_descriptor = _open_local_authority_root(
        lexical_root,
        create=access == "write" and write_data is not None,
    )
    chunks: list[bytes] = []
    bound_identity: tuple[int, int, int] | None = None
    installed_identity: tuple[int, int, int] | None = None
    try:
        for part in relative.parts[:-1]:
            before = authority_io.optional_stat_child(current_descriptor, part)
            if before is None:
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
                    before = authority_io.stat_child(current_descriptor, part)
                else:
                    current_descriptor.close()
                    current_descriptor = next_descriptor
                    continue
            if before.kind != "directory":
                raise ValueError(
                    "local authority ancestor is not an exact directory"
                )
            try:
                next_descriptor = authority_io.open_child_directory(
                    current_descriptor,
                    part,
                    expected=before.identity,
                )
            except OSError as exc:
                raise ValueError(
                    "local authority ancestor changed while opening"
                ) from exc
            current_descriptor.close()
            current_descriptor = next_descriptor

        leaf_name = relative.parts[-1]
        before = authority_io.optional_stat_child(current_descriptor, leaf_name)
        if before is None:
            if access in {"write", "read_optional"} and write_data is None:
                return LocalAuthorityFile(
                    path=lexical_path,
                    data=None,
                    exists=False,
                )
            if access == "read":
                raise ValueError("local authority file is missing") from None
        if before is not None and before.kind != "file":
            raise ValueError("local authority node is not an exact regular file")

        if before is not None:
            try:
                file = authority_io.open_child_file(
                    current_descriptor,
                    leaf_name,
                )
            except (OSError, ValueError) as exc:
                raise ValueError(
                    "local authority file changed while opening"
                ) from exc
            try:
                if file.identity != before.identity:
                    raise ValueError("local authority file changed while opening")
                bound_identity = file.identity
                if access in {"read", "read_optional"} or (
                    check_expected_write_data and expected_write_data is not None
                ):
                    chunks.append(authority_io.read_bound_file(file))
            finally:
                file.close()
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
                expected_target=before.identity if before is not None else None,
                **target_content,
            )
    finally:
        current_descriptor.close()
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
    directory_descriptor: authority_io.DirectoryLike,
    filename: str,
) -> bytes:
    """Read one regular no-follow leaf through an already bound directory."""
    payload, _ = read_local_authority_file_with_identity_at(
        directory_descriptor,
        filename,
    )
    return payload


def read_local_authority_file_with_identity_at(
    directory_descriptor: authority_io.DirectoryLike,
    filename: str,
) -> tuple[bytes, tuple[int, int, int]]:
    """Read one bound leaf and return the identity supplying its bytes."""
    if not filename or Path(filename).name != filename:
        raise ValueError("descriptor-relative filename must be one path component")
    before = authority_io.stat_child(directory_descriptor, filename)
    if before.kind != "file":
        raise ValueError(
            "local authority node is a symlink or not an exact regular file"
        )
    file = authority_io.open_child_file(directory_descriptor, filename)
    try:
        if file.identity != before.identity:
            raise ValueError("local authority file changed while opening")
        return authority_io.read_bound_file(file), file.identity
    finally:
        file.close()


def capture_local_authority_tree(
    root: Path,
    trusted_root: Path,
) -> tuple[dict[Path, bytes], tuple[tuple[str, str, int, int], ...]]:
    """Capture one closed no-follow tree through stable directory descriptors."""
    lexical_root = Path(os.path.abspath(os.fspath(root)))
    files: dict[Path, bytes] = {}
    records: list[tuple[str, str, int, int]] = []
    def capture(
        directory_descriptor: authority_io.DirectoryLike,
        relative_parent: Path,
    ) -> None:
        names = authority_io.list_children(directory_descriptor)
        for name in names:
            details = authority_io.stat_child(directory_descriptor, name)
            relative = relative_parent / name
            if details.kind == "file":
                payload, opened_identity = read_local_authority_file_with_identity_at(
                    directory_descriptor,
                    name,
                )
                rebound = authority_io.stat_child(directory_descriptor, name)
                if opened_identity != details.identity or rebound != details:
                    raise ValueError("local authority file changed while capturing")
                files[lexical_root / relative] = payload
                records.append(
                    (
                        relative.as_posix(),
                        "file",
                        details.identity[0],
                        details.identity[1],
                    )
                )
                continue
            if details.kind != "directory":
                raise ValueError("local authority tree contains an unsafe node")
            child_descriptor = authority_io.open_child_directory(
                directory_descriptor,
                name,
                expected=details.identity,
            )
            try:
                records.append(
                    (
                        relative.as_posix(),
                        "directory",
                        details.identity[0],
                        details.identity[1],
                    )
                )
                capture(child_descriptor, relative)
            finally:
                child_descriptor.close()
        if authority_io.list_children(directory_descriptor) != names:
            raise ValueError("local authority directory inventory changed")

    with open_local_authority_directory(
        lexical_root,
        trusted_root,
    ) as root_descriptor:
        root_identity = authority_io.directory_identity(root_descriptor)
        records.append((".", "directory", root_identity[0], root_identity[1]))
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
        with (
            open_local_authority_directory(
                lexical_path.parent,
                lexical_root,
            ) as directory_descriptor,
            authority_io.exclusive_parent_namespace_lock(
                directory_descriptor
            ),
        ):
            leaf_name = relative.parts[-1]
            details = authority_io.optional_stat_child(
                directory_descriptor,
                leaf_name,
            )
            if details is None:
                return False
            if details.kind != "file":
                raise ValueError("local authority cleanup node has an unsafe type")
            expected = details.identity
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
            quarantined = authority_io.stat_child(
                directory_descriptor,
                quarantine_name,
            )
            if quarantined.identity != expected or quarantined.kind != "file":
                raise ValueError("local authority cleanup node changed before removal")
            authority_io.sync_bound_directory(directory_descriptor)
            if not authority_io.reclaim_owned_leaf(
                directory_descriptor,
                authority_io.OwnedNode(quarantine_name, expected, "file"),
            ):
                raise ValueError(
                    "local authority cleanup node changed before reclamation"
                )
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
