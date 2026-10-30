# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterator

# Prefixes of the module names `_load_module` registers in `sys.modules`.
_LOADED_MODULE_PREFIXES = ("_hephaestus_tenant_pkg_", "hephaestus_tenant_module_")


@contextlib.contextmanager
def released_loaded_modules() -> Iterator[None]:
    """Unregister the modules `_load_module` registers inside the block.

    An eval loads its chain and scorer from a fresh snapshot, so each eval
    registers new module names. Without this, every eval's modules, and any
    large data they hold at module level, stay alive for the whole process.
    """
    before = set(sys.modules)
    try:
        yield
    finally:
        for name in [name for name in sys.modules if name not in before]:
            if name.startswith(_LOADED_MODULE_PREFIXES):
                sys.modules.pop(name, None)


def _infer_module_name(module_path: Path) -> tuple[str, Path | None, list[str], str | None]:
    stem = module_path.stem
    module_digest = hashlib.sha1(str(module_path).encode("utf-8")).hexdigest()[:12]

    package_parts: list[str] = []
    cursor = module_path.parent
    while (cursor / "__init__.py").exists():
        package_parts.append(cursor.name)
        cursor = cursor.parent

    if package_parts:
        import_root = cursor
        package_name = ".".join(reversed(package_parts))
        root_digest = hashlib.sha1(str(import_root).encode("utf-8")).hexdigest()[:12]
        unique_root = f"_hephaestus_tenant_pkg_{root_digest}"
        unique_package_name = f"{unique_root}.{package_name}"
        if stem == "__init__":
            return unique_package_name, import_root, list(reversed(package_parts)), unique_root
        return (
            f"{unique_package_name}._hephaestus_tenant_module_{module_digest}",
            import_root,
            list(reversed(package_parts)),
            unique_root,
        )

    return f"hephaestus_tenant_module_{stem}_{module_digest}", None, [], None


def _ensure_module_package(name: str, search_locations: list[str]) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        sys.modules[name] = module
    if getattr(module, "__path__", None) is None:
        module.__path__ = search_locations


def _load_package_module(name: str, package_dir: Path) -> None:
    package_init = package_dir / "__init__.py"
    existing = sys.modules.get(name)
    if existing is not None:
        if getattr(existing, "__file__", None) == str(package_init):
            return
        sys.modules.pop(name, None)

    spec = importlib.util.spec_from_file_location(
        name,
        package_init,
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"Unable to load package module from {package_init}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise


def _ensure_package_chain(import_root: Path, package_parts: list[str], unique_root: str) -> None:
    _ensure_module_package(unique_root, [str(import_root)])
    current_name = unique_root
    current_path = import_root
    for package_part in package_parts:
        current_name = f"{current_name}.{package_part}"
        current_path = current_path / package_part
        _load_package_module(current_name, current_path)


@contextlib.contextmanager
def _prepend_sys_path(path: Path | None) -> Iterator[None]:
    if path is None:
        yield
        return
    path_str = str(path)
    sys.path.insert(0, path_str)
    try:
        yield
    finally:
        try:
            sys.path.remove(path_str)
        except ValueError:
            pass


def _load_module(module_path: Path) -> ModuleType:
    module_path = module_path.resolve()
    if not module_path.exists():
        raise FileNotFoundError(f"Module path not found: {module_path}")
    module_name, import_root, package_parts, unique_root = _infer_module_name(module_path)
    is_package_init = module_path.name == "__init__.py"

    with _prepend_sys_path(import_root):
        if import_root is not None and unique_root is not None:
            _ensure_package_chain(import_root, package_parts, unique_root)
            if is_package_init:
                package_module = sys.modules.get(module_name)
                if package_module is not None:
                    return package_module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Unable to load module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        return module
