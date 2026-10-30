# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for chain loader: load_chain_factory."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from src.hephaestus.chains.loader import load_chain_factory
from src.hephaestus.loader import _load_module, released_loaded_modules


class TestLoadChainFactory:
    def test_load_chain_factory_success(self, tmp_path: Path) -> None:
        """Loads a build_chain function from a .py file."""
        chain_file = tmp_path / "my_chain.py"
        chain_file.write_text(
            """\
def build_chain(provider, config):
    return 'compiled_chain'
""",
            encoding="utf-8",
        )

        factory = load_chain_factory(str(chain_file))

        assert callable(factory)
        assert factory(None, {}) == "compiled_chain"

    def test_load_chain_factory_custom_fn_name(self, tmp_path: Path) -> None:
        """Loads a function with a non-default name."""
        chain_file = tmp_path / "my_chain.py"
        chain_file.write_text(
            """\
def create_graph(provider, config):
    return 'custom_chain'
""",
            encoding="utf-8",
        )

        factory = load_chain_factory(str(chain_file), fn_name="create_graph")

        assert callable(factory)
        assert factory(None, {}) == "custom_chain"

    def test_load_chain_factory_file_not_found(self) -> None:
        """Raises FileNotFoundError if the chain file does not exist."""
        with pytest.raises(FileNotFoundError):
            load_chain_factory("/nonexistent/path/chain.py")

    def test_load_chain_factory_fn_not_found(self, tmp_path: Path) -> None:
        """Raises ValueError if the named function is not in the module."""
        chain_file = tmp_path / "my_chain.py"
        chain_file.write_text(
            """\
def some_other_function(provider, config):
    return 'other'
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="build_chain"):
            load_chain_factory(str(chain_file))

    def test_load_chain_factory_fn_not_callable(self, tmp_path: Path) -> None:
        """Raises ValueError if the named attribute is not callable."""
        chain_file = tmp_path / "my_chain.py"
        chain_file.write_text(
            "build_chain = 42\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="not callable"):
            load_chain_factory(str(chain_file))

    def test_load_chain_factory_supports_relative_imports(self, tmp_path: Path) -> None:
        """Chain .py with relative imports from same package loads correctly."""
        pkg_dir = tmp_path / "chains_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        (pkg_dir / "helpers.py").write_text(
            """\
def get_label():
    return 'helper_label'
""",
            encoding="utf-8",
        )
        (pkg_dir / "chain.py").write_text(
            """\
from .helpers import get_label

def build_chain(provider, config):
    return get_label()
""",
            encoding="utf-8",
        )

        factory = load_chain_factory(str(pkg_dir / "chain.py"))

        assert callable(factory)
        assert factory(None, {}) == "helper_label"

    def test_load_chain_factory_isolates_namespaces(self, tmp_path: Path) -> None:
        """Two chains with same module names in different directories don't collide."""
        dir_a = tmp_path / "tenant_a"
        dir_a.mkdir()
        (dir_a / "chain.py").write_text(
            """\
def build_chain(provider, config):
    return 'chain_a'
""",
            encoding="utf-8",
        )

        dir_b = tmp_path / "tenant_b"
        dir_b.mkdir()
        (dir_b / "chain.py").write_text(
            """\
def build_chain(provider, config):
    return 'chain_b'
""",
            encoding="utf-8",
        )

        factory_a = load_chain_factory(str(dir_a / "chain.py"))
        factory_b = load_chain_factory(str(dir_b / "chain.py"))

        assert factory_a(None, {}) == "chain_a"
        assert factory_b(None, {}) == "chain_b"


class TestReleasedLoadedModules:
    def test_unregisters_modules_loaded_in_the_block(self, tmp_path: Path) -> None:
        """Modules loaded inside the block are removed from sys.modules when it exits."""
        module_file = tmp_path / "probe_module.py"
        module_file.write_text("VALUE = 1\n", encoding="utf-8")

        with released_loaded_modules():
            module = _load_module(module_file)
            assert sys.modules[module.__name__] is module

        assert module.__name__ not in sys.modules

    def test_keeps_modules_loaded_before_the_block(self, tmp_path: Path) -> None:
        """Modules that were loaded before the block stay registered."""
        module_file = tmp_path / "earlier_module.py"
        module_file.write_text("VALUE = 2\n", encoding="utf-8")
        module = _load_module(module_file)

        with released_loaded_modules():
            pass

        assert sys.modules.get(module.__name__) is module
        sys.modules.pop(module.__name__, None)
