# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import ast
import json
import multiprocessing
import shutil
import sys
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from src.hephaestus import artifact_io
from src.hephaestus.datasets import embedding_providers as embedding_provider_module
from src.hephaestus.datasets import rubric_providers as rubric_provider_module
from src.hephaestus.evaluation_assets import durability as durability_module
from src.hephaestus.evaluation_assets import models as evaluation_asset_models
from src.hephaestus.evaluation_assets import pipeline as pipeline_module
from src.hephaestus.evaluation_assets import provenance as provenance_module
from src.hephaestus.evaluation_assets import service as service_module
from src.hephaestus.evaluation_assets import stage_three_contract
from src.hephaestus.evaluation_assets import workspace as workspace_module
from src.hephaestus.evaluation_assets.durability import (
    LEGACY_UNAVAILABLE_PROVENANCE,
    STAGE_SPECIFICATIONS,
    EvaluationAssetBusyError,
    EvaluationAssetImmutableError,
    EvaluationAssetIntegrityError,
    EvaluationAssetLegacyError,
    canonical_sha256,
    file_sha256,
    released_parent_evidence,
    verify_release_candidate,
    verify_released_asset,
    verify_stage_receipt,
)
from src.hephaestus.evaluation_assets.models import (
    STATE_SCHEMA_VERSION,
    TOP_LEVEL_STATUSES,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.pipeline import (
    EvaluationAssetPipeline,
    ProviderCallError,
)
from src.hephaestus.evaluation_assets.service import EvaluationAssetRunManager
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


class _NeverCalledRubricProvider:
    provider_name = "fake"
    model = "never-called-rubric"

    def __init__(self) -> None:
        self.calls = 0

    def generate_json(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        raise AssertionError("busy pipeline reached the rubric provider")


def _studio_persistence_paths(source_root: Path) -> tuple[Path, ...]:
    """Return the complete declared Studio production persistence boundary."""
    paths = {
        source_root / "artifact_io.py",
        source_root / "datasets" / "evaluation_assets.py",
        source_root / "datasets" / "intent_assets.py",
        source_root / "cli.py",
        source_root / "webui" / "data.py",
        source_root / "webui" / "evaluation_assets_frontend.py",
        source_root / "webui" / "server.py",
        source_root / "webui" / "frontend.py",
        *(source_root / "evaluation_assets").rglob("*.py"),
    }
    return tuple(sorted(paths, key=lambda path: path.as_posix()))


def _assigned_ast_node(
    node: ast.AST,
    assignments: Mapping[str, ast.AST],
    *,
    seen: frozenset[str] = frozenset(),
) -> ast.AST:
    if isinstance(node, ast.NamedExpr):
        return _assigned_ast_node(node.value, assignments, seen=seen)
    if isinstance(node, ast.Name) and node.id in assignments and node.id not in seen:
        return _assigned_ast_node(
            assignments[node.id],
            assignments,
            seen=seen | {node.id},
        )
    return node


def _qualified_ast_name(
    node: ast.AST,
    aliases: Mapping[str, str],
    assignments: Mapping[str, ast.AST] | None = None,
) -> str:
    node = _assigned_ast_node(node, assignments or {})
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = _qualified_ast_name(node.value, aliases, assignments)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _literal_mode(
    node: ast.Call,
    *,
    positional_index: int,
    assignments: Mapping[str, ast.AST],
) -> str | None:
    if any(isinstance(argument, ast.Starred) for argument in node.args) or any(
        keyword.arg is None for keyword in node.keywords
    ):
        return None
    arguments = list(node.args[positional_index : positional_index + 1])
    arguments.extend(
        keyword.value for keyword in node.keywords if keyword.arg == "mode"
    )
    if not arguments:
        return "r"
    argument = _assigned_ast_node(arguments[0], assignments)
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value
    return None


def _os_write_flag_status(
    node: ast.AST,
    aliases: Mapping[str, str],
    assignments: Mapping[str, ast.AST],
) -> bool | None:
    node = _assigned_ast_node(node, assignments)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _os_write_flag_status(node.left, aliases, assignments)
        right = _os_write_flag_status(node.right, aliases, assignments)
        if left is True or right is True:
            return True
        return False if left is False and right is False else None
    qualified = _canonical_sink_name(
        _qualified_ast_name(node, aliases, assignments)
    )
    if qualified in {
        "os.O_WRONLY",
        "os.O_RDWR",
        "os.O_APPEND",
        "os.O_CREAT",
        "os.O_TRUNC",
        "os.O_EXCL",
    }:
        return True
    if qualified in {
        "os.O_RDONLY",
        "os.O_CLOEXEC",
        "os.O_DIRECTORY",
        "os.O_NOFOLLOW",
    }:
        return False
    if isinstance(node, ast.Constant) and node.value == 0:
        return False
    if (
        isinstance(node, ast.Call)
        and _qualified_ast_name(node.func, aliases, assignments) == "getattr"
        and len(node.args) == 3
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value in {"O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW"}
        and isinstance(node.args[2], ast.Constant)
        and node.args[2].value == 0
    ):
        return False
    return None


def _path_like_receiver(
    node: ast.AST,
    aliases: Mapping[str, str],
    assignments: Mapping[str, ast.AST],
) -> bool:
    node = _assigned_ast_node(node, assignments)
    if isinstance(node, ast.Name):
        name = node.id.lower()
        return name == "path" or name.endswith("_path") or name.endswith("path")
    if isinstance(node, ast.Attribute):
        return node.attr == "parent" or node.attr.lower().endswith(
            "path"
        ) or _path_like_receiver(node.value, aliases, assignments)
    if not isinstance(node, ast.Call):
        return False
    if _qualified_ast_name(node.func, aliases, assignments) in {
        "Path",
        "pathlib.Path",
    }:
        return True
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in {"absolute", "resolve"}
        and _path_like_receiver(
            node.func.value,
            aliases,
            assignments,
        )
    )


def _obvious_string_receiver(
    node: ast.AST,
    assignments: Mapping[str, ast.AST],
) -> bool:
    node = _assigned_ast_node(node, assignments)
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.Subscript):
        return _obvious_string_receiver(node.value, assignments)
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        in {
            "casefold",
            "lower",
            "lstrip",
            "removeprefix",
            "removesuffix",
            "rsplit",
            "rstrip",
            "split",
            "strip",
            "upper",
        }
    )


_PERSISTENCE_METHOD_SINKS = {
    "rename",
    "replace",
    "touch",
    "truncate",
    "write",
    "write_bytes",
    "write_text",
    "writeheader",
    "writerow",
    "writerows",
    "writelines",
}
_PERSISTENCE_COPY_SINKS = {
    "shutil.copy",
    "shutil.copy2",
    "shutil.copyfile",
    "shutil.copyfileobj",
    "shutil.copytree",
    "shutil.move",
}
_PERSISTENCE_LOW_LEVEL_SINKS = {
    "os.copy_file_range",
    "os.ftruncate",
    "os.pwrite",
    "os.pwritev",
    "os.rename",
    "os.replace",
    "os.sendfile",
    "os.splice",
    "os.truncate",
    "os.write",
    "os.writev",
}
_PERSISTENCE_DUMP_SINKS = {
    "json.dump",
    "pickle.dump",
    "toml.dump",
    "yaml.dump",
    "yaml.safe_dump",
}
_PERSISTENCE_CSV_FACTORIES = {"csv.DictWriter", "csv.writer"}
_CALLABLE_FACTORIES = {"functools.partial"}
_PERSISTENCE_MODULES = {
    "builtins",
    "csv",
    "io",
    "json",
    "nt",
    "os",
    "pickle",
    "posix",
    "shutil",
    "tempfile",
    "toml",
    "yaml",
}
_PERSISTENCE_NAMED_SINKS = {
    "builtins.open",
    "builtins.print",
    "io.open",
    "open",
    "os.fdopen",
    "os.open",
    "tempfile.NamedTemporaryFile",
}
_AUDITED_PIPELINE_PARTIAL_TARGETS = {
    "_normalize_feedback_evidence_response",
    "_normalize_guideline_response",
    "_normalize_inferred_rubric_response",
    "_normalize_synthetic_response",
    (
        "src.hephaestus.evaluation_assets.stage_three_contract."
        "normalize_guideline_response"
    ),
}


def _canonical_sink_name(name: str) -> str:
    """Project platform-native persistence aliases onto the os namespace."""
    for module in ("nt", "posix"):
        prefix = f"{module}."
        if name.startswith(prefix):
            return f"os.{name.removeprefix(prefix)}"
    return name


def _expanded_factory_call(
    node: ast.Call,
    aliases: Mapping[str, str],
    assignments: Mapping[str, ast.AST],
) -> tuple[ast.Call, bool]:
    """Expand a directly invoked callable factory into its bound sink call."""
    resolved_func = _assigned_ast_node(node.func, assignments)
    expanded = False
    while True:
        if isinstance(resolved_func, ast.Call) and (
            _qualified_ast_name(resolved_func.func, aliases, assignments)
            in _CALLABLE_FACTORIES
        ):
            factory_call = resolved_func
            invocation_args = node.args
            invocation_keywords = node.keywords
        elif (
            _qualified_ast_name(resolved_func, aliases, assignments)
            in _CALLABLE_FACTORIES
        ):
            factory_call = node
            invocation_args = []
            invocation_keywords = []
        else:
            break
        if not factory_call.args:
            break
        expanded = True
        invocation_names = {
            keyword.arg
            for keyword in invocation_keywords
            if keyword.arg is not None
        }
        node = ast.Call(
            func=_assigned_ast_node(factory_call.args[0], assignments),
            args=[*factory_call.args[1:], *invocation_args],
            keywords=[
                *invocation_keywords,
                *(
                    keyword
                    for keyword in factory_call.keywords
                    if keyword.arg not in invocation_names
                ),
            ],
        )
        resolved_func = _assigned_ast_node(node.func, assignments)
    return node, expanded


def _persistence_binding_score(
    node: ast.AST,
    aliases: Mapping[str, str],
    assignments: Mapping[str, ast.AST],
) -> int:
    """Score whether one possible binding exposes a persistence-capable call."""
    node = _assigned_ast_node(node, assignments)
    if isinstance(node, ast.IfExp):
        return max(
            _persistence_binding_score(candidate, aliases, assignments)
            for candidate in (node.body, node.orelse)
        )
    qualified = _canonical_sink_name(
        _qualified_ast_name(node, aliases, assignments)
    )
    attribute = node.attr if isinstance(node, ast.Attribute) else ""
    if (
        qualified in _PERSISTENCE_MODULES
        or qualified
        in _PERSISTENCE_DUMP_SINKS
        | _PERSISTENCE_COPY_SINKS
        | _PERSISTENCE_LOW_LEVEL_SINKS
        | _PERSISTENCE_CSV_FACTORIES
        | _CALLABLE_FACTORIES
        | _PERSISTENCE_NAMED_SINKS
        or attribute in _PERSISTENCE_METHOD_SINKS | {"dump", "open"}
    ):
        return 1
    if isinstance(node, ast.Call) and (
        _qualified_ast_name(node.func, aliases, assignments)
        in _CALLABLE_FACTORIES
    ):
        return 1
    return 0


def _explicit_persistence_reference(
    node: ast.AST,
    aliases: Mapping[str, str],
    assignments: Mapping[str, ast.AST],
) -> bool:
    """Return whether an expression visibly names a declared persistence sink."""
    node = _assigned_ast_node(node, assignments)
    if isinstance(node, ast.Call) and (
        _qualified_ast_name(node.func, aliases, assignments)
        in _CALLABLE_FACTORIES
    ):
        return bool(node.args) and _explicit_persistence_reference(
            node.args[0],
            aliases,
            assignments,
        )
    qualified = _canonical_sink_name(
        _qualified_ast_name(node, aliases, assignments)
    )
    attribute = node.attr if isinstance(node, ast.Attribute) else ""
    return (
        qualified
        in _PERSISTENCE_DUMP_SINKS
        | _PERSISTENCE_COPY_SINKS
        | _PERSISTENCE_LOW_LEVEL_SINKS
        | _PERSISTENCE_CSV_FACTORIES
        | _PERSISTENCE_NAMED_SINKS
        or attribute in _PERSISTENCE_METHOD_SINKS | {"dump", "open", "safe_dump"}
    )


def _visible_persistence_references(tree: ast.AST) -> list[tuple[int, str]]:
    """Return declared writer references that escape direct-call inspection."""
    aliases: dict[str, str] = {}
    imported_sinks: list[tuple[int, str]] = []
    for candidate in ast.walk(tree):
        if isinstance(candidate, ast.Import):
            for item in candidate.names:
                name = item.asname or item.name.split(".", 1)[0]
                if item.name.split(".", 1)[0] in _PERSISTENCE_MODULES:
                    aliases.setdefault(name, item.name)
        elif isinstance(candidate, ast.ImportFrom) and candidate.module:
            for item in candidate.names:
                name = item.asname or item.name
                qualified = _canonical_sink_name(
                    f"{candidate.module}.{item.name}"
                )
                aliases.setdefault(name, qualified)
                if qualified in (
                    _PERSISTENCE_DUMP_SINKS
                    | _PERSISTENCE_COPY_SINKS
                    | _PERSISTENCE_LOW_LEVEL_SINKS
                    | _PERSISTENCE_CSV_FACTORIES
                    | _PERSISTENCE_NAMED_SINKS
                ):
                    imported_sinks.append((candidate.lineno, qualified))

    # Escape analysis is deliberately conservative for the finite set of
    # persistence modules above.  Resolve ordinary module rebindings before
    # walking returns, containers, loop iterables, and callback arguments so a
    # second-hop alias cannot hide a declared sink or factory.
    module_alias_names = {
        name for name, qualified in aliases.items() if qualified in _PERSISTENCE_MODULES
    }
    changed = True
    while changed:
        changed = False
        for candidate in ast.walk(tree):
            target: ast.AST | None = None
            value: ast.AST | None = None
            if isinstance(candidate, (ast.Assign, ast.AnnAssign)):
                if isinstance(candidate, ast.Assign) and len(candidate.targets) == 1:
                    target = candidate.targets[0]
                elif isinstance(candidate, ast.AnnAssign):
                    target = candidate.target
                value = candidate.value
            elif isinstance(candidate, ast.NamedExpr):
                target = candidate.target
                value = candidate.value
            if not isinstance(target, ast.Name) or value is None:
                continue
            qualified = _qualified_ast_name(value, aliases)
            root = qualified.split(".", 1)[0]
            inherited_alias = (
                isinstance(value, ast.Name) and value.id in module_alias_names
            )
            if root not in _PERSISTENCE_MODULES and not inherited_alias:
                continue
            if target.id not in module_alias_names:
                module_alias_names.add(target.id)
                aliases.setdefault(
                    target.id,
                    aliases.get(value.id, qualified)
                    if isinstance(value, ast.Name)
                    else qualified,
                )
                changed = True

    parents = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    references = list(imported_sinks)
    for candidate in ast.walk(tree):
        if not isinstance(candidate, (ast.Name, ast.Attribute)):
            continue
        parent = parents.get(id(candidate))
        if isinstance(parent, ast.Call) and parent.func is candidate:
            continue
        qualified = _canonical_sink_name(
            _qualified_ast_name(candidate, aliases)
        )
        attribute = candidate.attr if isinstance(candidate, ast.Attribute) else ""
        receiver = candidate
        while isinstance(receiver, ast.Attribute):
            receiver = receiver.value
        module_alias_sink = (
            isinstance(candidate, ast.Attribute)
            and isinstance(receiver, ast.Name)
            and receiver.id in module_alias_names
            and attribute
            in {
                name.rsplit(".", 1)[-1]
                for name in (
                    _PERSISTENCE_DUMP_SINKS
                    | _PERSISTENCE_COPY_SINKS
                    | _PERSISTENCE_LOW_LEVEL_SINKS
                    | _PERSISTENCE_CSV_FACTORIES
                    | _PERSISTENCE_NAMED_SINKS
                )
            }
        )
        simple_module_alias = (
            isinstance(parent, ast.Assign)
            and len(parent.targets) == 1
            and isinstance(parent.targets[0], ast.Name)
            and parent.value is candidate
        ) or (
            isinstance(parent, ast.AnnAssign)
            and isinstance(parent.target, ast.Name)
            and parent.value is candidate
        ) or (
            isinstance(parent, ast.NamedExpr)
            and isinstance(parent.target, ast.Name)
            and parent.value is candidate
        )
        safe_module_introspection = (
            qualified in _PERSISTENCE_MODULES
            and isinstance(parent, ast.Call)
            and parent.args
            and parent.args[0] is candidate
            and _qualified_ast_name(parent.func, aliases)
            in {"getattr", "builtins.getattr"}
            and len(parent.args) >= 2
            and isinstance(parent.args[1], ast.Constant)
            and isinstance(parent.args[1].value, str)
            and _canonical_sink_name(
                f"{qualified}.{parent.args[1].value}"
            )
            not in (
                _PERSISTENCE_DUMP_SINKS
                | _PERSISTENCE_COPY_SINKS
                | _PERSISTENCE_LOW_LEVEL_SINKS
                | _PERSISTENCE_CSV_FACTORIES
                | _PERSISTENCE_NAMED_SINKS
            )
            and parent.args[1].value
            not in _PERSISTENCE_METHOD_SINKS | {"dump", "open", "safe_dump"}
        )
        module_escape = (
            qualified in _PERSISTENCE_MODULES
            or isinstance(candidate, ast.Name)
            and candidate.id in module_alias_names
        ) and not (
            isinstance(parent, ast.Attribute) and parent.value is candidate
        ) and not simple_module_alias and not safe_module_introspection
        if module_escape or module_alias_sink or qualified in (
            _PERSISTENCE_DUMP_SINKS
            | _PERSISTENCE_COPY_SINKS
            | _PERSISTENCE_LOW_LEVEL_SINKS
            | _PERSISTENCE_CSV_FACTORIES
            | _PERSISTENCE_NAMED_SINKS
        ) or attribute in _PERSISTENCE_METHOD_SINKS | {
            "dump",
            "safe_dump",
        }:
            references.append(
                (
                    candidate.lineno,
                    (
                        f"{qualified}.*"
                        if module_escape
                        else qualified or f"method.{attribute}"
                    ),
                )
            )
    return references


def _qualified_name_node(name: str) -> ast.AST:
    """Build an AST attribute chain that no longer depends on an import alias."""
    parts = name.split(".")
    node: ast.AST = ast.Name(id=parts[0], ctx=ast.Load())
    for part in parts[1:]:
        node = ast.Attribute(value=node, attr=part, ctx=ast.Load())
    return node


class _CallBindingCollector(ast.NodeVisitor):
    """Capture assignment bindings at each call without cross-scope rebinding."""

    def __init__(self) -> None:
        self.bindings: dict[str, ast.AST] = {}
        self.aliases: dict[str, str] = {}
        self.calls: dict[int, tuple[dict[str, ast.AST], dict[str, str]]] = {}
        self.sink_stores: list[int] = []

    def _bind(self, target: ast.AST, value: ast.AST) -> None:
        if isinstance(target, (ast.Attribute, ast.Subscript)):
            if _explicit_persistence_reference(
                value,
                self.aliases,
                self.bindings,
            ):
                self.sink_stores.append(target.lineno)
            return
        if isinstance(target, ast.Name):
            if isinstance(value, ast.IfExp):
                candidates = (value.body, value.orelse)
                persistence_candidates = [
                    candidate
                    for candidate in candidates
                    if _persistence_binding_score(
                        candidate,
                        self.aliases,
                        self.bindings,
                    )
                ]
                identities = {
                    _qualified_ast_name(
                        candidate,
                        self.aliases,
                        self.bindings,
                    )
                    or ast.dump(candidate, include_attributes=False)
                    for candidate in persistence_candidates
                }
                value = (
                    _qualified_name_node("os.write")
                    if len(identities) > 1
                    else max(
                        candidates,
                        key=lambda candidate: _persistence_binding_score(
                            candidate,
                            self.aliases,
                            self.bindings,
                        ),
                    )
                )
            elif (
                isinstance(value, ast.Call)
                and _qualified_ast_name(
                    value.func,
                    self.aliases,
                    self.bindings,
                )
                not in _CALLABLE_FACTORIES
                and any(
                _explicit_persistence_reference(
                    candidate,
                    self.aliases,
                    self.bindings,
                )
                for candidate in [
                    *value.args,
                    *(keyword.value for keyword in value.keywords),
                ]
                )
            ):
                value = _qualified_name_node("os.write")
            elif isinstance(
                value,
                (
                    ast.BoolOp,
                    ast.Dict,
                    ast.List,
                    ast.Set,
                    ast.Subscript,
                    ast.Tuple,
                ),
            ) and any(
                candidate is not value
                and _persistence_binding_score(
                    candidate,
                    self.aliases,
                    self.bindings,
                )
                for candidate in ast.walk(value)
            ):
                value = _qualified_name_node("os.write")
            self.bindings[target.id] = value
            self.aliases.pop(target.id, None)
        elif (
            isinstance(target, (ast.Tuple, ast.List))
            and isinstance(value, (ast.Tuple, ast.List))
            and len(target.elts) == len(value.elts)
        ):
            for item, item_value in zip(target.elts, value.elts):
                self._bind(item, item_value)

    def _snapshot(self) -> tuple[dict[str, ast.AST], dict[str, str]]:
        return dict(self.bindings), dict(self.aliases)

    def _restore(
        self,
        state: tuple[Mapping[str, ast.AST], Mapping[str, str]],
    ) -> None:
        self.bindings = dict(state[0])
        self.aliases = dict(state[1])

    def _run_statements(
        self,
        body: Sequence[ast.stmt],
        start: tuple[Mapping[str, ast.AST], Mapping[str, str]],
    ) -> tuple[dict[str, ast.AST], dict[str, str]]:
        self._restore(start)
        for statement in body:
            self.visit(statement)
        return self._snapshot()

    def _select_branch(
        self,
        states: Sequence[tuple[dict[str, ast.AST], dict[str, str]]],
    ) -> None:
        merged_bindings: dict[str, ast.AST] = {}
        merged_aliases: dict[str, str] = {}
        names = sorted(
            {
                name
                for bindings, aliases in states
                for name in set(bindings) | set(aliases)
            }
        )
        for name in names:
            candidates = [
                state
                for state in states
                if name in state[0] or name in state[1]
            ]
            persistence_candidates = [
                state
                for state in candidates
                if _persistence_binding_score(
                    ast.Name(id=name, ctx=ast.Load()),
                    state[1],
                    state[0],
                )
            ]
            persistence_identities = {
                (
                    _qualified_ast_name(
                        state[0][name],
                        state[1],
                        state[0],
                    )
                    or ast.dump(state[0][name], include_attributes=False)
                )
                if name in state[0]
                else state[1][name]
                for state in persistence_candidates
            }
            if len(persistence_identities) > 1:
                merged_bindings[name] = _qualified_name_node("os.write")
                continue
            selected = max(
                candidates,
                key=lambda state: _persistence_binding_score(
                    ast.Name(id=name, ctx=ast.Load()),
                    state[1],
                    state[0],
                ),
            )
            bindings, aliases = selected
            if name in bindings:
                value = bindings[name]
                qualified = _qualified_ast_name(value, aliases, bindings)
                merged_bindings[name] = (
                    _qualified_name_node(qualified) if qualified else value
                )
                for alias, target in aliases.items():
                    merged_aliases.setdefault(alias, target)
            else:
                merged_aliases[name] = aliases[name]
        self.bindings = merged_bindings
        self.aliases = merged_aliases

    def _visit_scoped_body(self, body: Sequence[ast.stmt]) -> None:
        outer_bindings = self.bindings
        outer_aliases = self.aliases
        self.bindings = dict(outer_bindings)
        self.aliases = dict(outer_aliases)
        try:
            for statement in body:
                self.visit(statement)
        finally:
            self.bindings = outer_bindings
            self.aliases = outer_aliases

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if default is not None:
                self.visit(default)
        if node.returns is not None:
            self.visit(node.returns)
        self._visit_scoped_body(node.body)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self._visit_scoped_body(node.body)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if default is not None:
                self.visit(default)
        outer_bindings = self.bindings
        outer_aliases = self.aliases
        self.bindings = dict(outer_bindings)
        self.aliases = dict(outer_aliases)
        try:
            self.visit(node.body)
        finally:
            self.bindings = outer_bindings
            self.aliases = outer_aliases

    def visit_Import(self, node: ast.Import) -> None:
        for item in node.names:
            name = item.asname or item.name.split(".", 1)[0]
            self.bindings.pop(name, None)
            self.aliases[name] = item.name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        for item in node.names:
            name = item.asname or item.name
            self.bindings.pop(name, None)
            self.aliases[name] = f"{node.module}.{item.name}"

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self.visit(target)
            self._bind(target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
            self.visit(node.target)
            self._bind(node.target, node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        self.visit(node.target)
        if isinstance(node.target, ast.Name):
            self._bind(
                node.target,
                ast.Name(id="__dynamic_assignment__", ctx=ast.Load()),
            )

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self._bind(node.target, node.value)

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        start = self._snapshot()
        body = self._run_statements(node.body, start)
        alternative = (
            self._run_statements(node.orelse, start) if node.orelse else start
        )
        self._select_branch([body, alternative])

    def visit_Try(self, node: ast.Try) -> None:
        start = self._snapshot()
        self._restore(start)
        prefixes = [start]
        for statement in node.body:
            self.visit(statement)
            prefixes.append(self._snapshot())
        success = prefixes[-1]
        if node.orelse:
            success = self._run_statements(node.orelse, success)
        alternatives = [success]
        for handler in node.handlers:
            for prefix in prefixes:
                self._restore(prefix)
                if handler.type is not None:
                    self.visit(handler.type)
                alternatives.append(
                    self._run_statements(handler.body, self._snapshot())
                )
        self._select_branch(alternatives)
        for statement in node.finalbody:
            self.visit(statement)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self.visit(node.target)
        start = self._snapshot()
        body = self._run_statements(node.body, start)
        alternatives = [start, body]
        if node.orelse:
            alternatives.extend(
                [
                    self._run_statements(node.orelse, start),
                    self._run_statements(node.orelse, body),
                ]
            )
        self._select_branch(alternatives)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        start = self._snapshot()
        body = self._run_statements(node.body, start)
        alternatives = [start, body]
        if node.orelse:
            alternatives.extend(
                [
                    self._run_statements(node.orelse, start),
                    self._run_statements(node.orelse, body),
                ]
            )
        self._select_branch(alternatives)

    def visit_Match(self, node: ast.Match) -> None:
        self.visit(node.subject)
        start = self._snapshot()
        alternatives = [start]
        for case in node.cases:
            self._restore(start)
            if case.guard is not None:
                self.visit(case.guard)
            alternatives.append(
                self._run_statements(case.body, self._snapshot())
            )
        self._select_branch(alternatives)

    def visit_Call(self, node: ast.Call) -> None:
        self.calls[id(node)] = (dict(self.bindings), dict(self.aliases))
        self.generic_visit(node)


def _call_binding_snapshots(
    tree: ast.AST,
) -> tuple[
    dict[int, tuple[dict[str, ast.AST], dict[str, str]]],
    list[int],
]:
    collector = _CallBindingCollector()
    collector.visit(tree)
    return collector.calls, collector.sink_stores


class _FunctionContextCollector(ast.NodeVisitor):
    """Record the exact class/function stack enclosing each call."""

    def __init__(self) -> None:
        self.stack: list[str] = []
        self.calls: dict[int, tuple[str, ...]] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        self.calls[id(node)] = tuple(self.stack)
        self.generic_visit(node)


def _call_function_contexts(tree: ast.AST) -> dict[int, tuple[str, ...]]:
    collector = _FunctionContextCollector()
    collector.visit(tree)
    return collector.calls


def _definition_context_at_line(tree: ast.AST, line: int) -> tuple[str, ...]:
    """Return the exact nested class/function identity containing one line."""
    parents = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    candidates = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.lineno <= line <= (node.end_lineno or line)
    ]
    if not candidates:
        return ()
    current: ast.AST | None = min(
        candidates,
        key=lambda node: (node.end_lineno or line) - node.lineno,
    )
    context: list[str] = []
    while current is not None:
        if isinstance(current, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            context.append(current.name)
        current = parents.get(id(current))
    return tuple(reversed(context))


def _studio_writer_violations(path: Path, source: str) -> list[str]:
    """Find direct persistence calls, resolving qualified and imported aliases."""
    tree = ast.parse(source, filename=str(path))
    call_bindings, sink_store_lines = _call_binding_snapshots(tree)
    function_contexts = _call_function_contexts(tree)

    path_text = path.as_posix()
    artifact_seam = path_text.endswith("src/hephaestus/artifact_io.py")
    publication_seam = path_text.endswith(
        "src/hephaestus/evaluation_assets/publication.py"
    )
    violations: list[str] = [
        f"{path.name}:{line}:os.write" for line in sink_store_lines
    ]
    for line, operation in _visible_persistence_references(tree):
        function_context = _definition_context_at_line(tree, line)
        if artifact_seam and function_context and function_context[0] in {
            "atomic_append_jsonl",
            "atomic_copy_file",
            "atomic_write_json",
            "atomic_write_jsonl",
            "atomic_write_text",
            "_atomic_write_binary",
            "_atomic_write_text",
            "sync_directory",
        }:
            continue
        if publication_seam and function_context and (
            function_context[0] == "install_generation"
        ):
            continue
        if path_text.endswith("src/hephaestus/webui/server.py") and (
            function_context
            in {
                ("_Handler", "_send_file"),
                ("_Handler", "_send_html"),
                ("_Handler", "_send_json"),
            }
        ):
            continue
        violations.append(f"{path.name}:{line}:{operation}")
    artifact_contexts = {
        "atomic_append_jsonl",
        "atomic_copy_file",
        "atomic_write_json",
        "atomic_write_jsonl",
        "atomic_write_text",
        "_atomic_write_binary",
        "_atomic_write_text",
        "sync_directory",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_context = function_contexts.get(id(node), ())
        artifact_function = (
            artifact_seam
            and bool(function_context)
            and function_context[0] in artifact_contexts
        )
        publication_function = (
            publication_seam
            and bool(function_context)
            and function_context[0] == "install_generation"
        )
        server_function = path_text.endswith(
            "src/hephaestus/webui/server.py"
        ) and function_context in {
            ("_Handler", "_send_file"),
            ("_Handler", "_send_html"),
            ("_Handler", "_send_json"),
        }
        assignments, aliases = call_bindings.get(id(node), ({}, {}))
        for argument in [
            *node.args,
            *(keyword.value for keyword in node.keywords),
        ]:
            if _explicit_persistence_reference(
                argument,
                aliases,
                assignments,
            ):
                visible = _canonical_sink_name(
                    _qualified_ast_name(argument, aliases, assignments)
                )
                violations.append(
                    f"{path.name}:{node.lineno}:{visible or 'os.write'}"
                )
        inspected_call, factory_expanded = _expanded_factory_call(
            node,
            aliases,
            assignments,
        )
        resolved_func = _assigned_ast_node(inspected_call.func, assignments)
        qualified = _canonical_sink_name(
            _qualified_ast_name(resolved_func, aliases, assignments)
        )
        attribute = (
            resolved_func.attr if isinstance(resolved_func, ast.Attribute) else ""
        )

        if (
            qualified in {"getattr", "builtins.getattr"}
            and len(node.args) >= 2
            and isinstance(
                method_node := _assigned_ast_node(node.args[1], assignments),
                ast.Constant,
            )
            and isinstance(method_node.value, str)
        ):
            receiver = _qualified_ast_name(
                node.args[0],
                aliases,
                assignments,
            )
            sink = _canonical_sink_name(
                f"{receiver}.{method_node.value}" if receiver else ""
            )
            recognized = (
                sink in _PERSISTENCE_DUMP_SINKS
                or sink in _PERSISTENCE_COPY_SINKS
                or sink in _PERSISTENCE_LOW_LEVEL_SINKS
                or sink in _PERSISTENCE_CSV_FACTORIES
                or sink
                in {
                    "builtins.print",
                    "builtins.open",
                    "io.open",
                    "os.fdopen",
                    "os.open",
                    "tempfile.NamedTemporaryFile",
                }
                or sink in _CALLABLE_FACTORIES
                or method_node.value
                in _PERSISTENCE_METHOD_SINKS | {"dump", "open"}
            )
            if recognized:
                allowed = (
                    artifact_function
                    and (
                        sink in _PERSISTENCE_DUMP_SINKS
                        or sink == "shutil.copyfileobj"
                        or sink == "tempfile.NamedTemporaryFile"
                        or sink == "os.replace"
                        or method_node.value in {"write", "writelines", "truncate"}
                    )
                ) or (publication_function and sink == "os.rename") or (
                    server_function
                    and receiver == "self.wfile"
                    and method_node.value == "write"
                )
                if not allowed:
                    operation = (
                        sink
                        if sink
                        in _PERSISTENCE_DUMP_SINKS
                        | _PERSISTENCE_COPY_SINKS
                        | _PERSISTENCE_LOW_LEVEL_SINKS
                        | _PERSISTENCE_CSV_FACTORIES
                        | {"builtins.print", "tempfile.NamedTemporaryFile"}
                        else (
                            "partial(dynamic)"
                            if sink in _CALLABLE_FACTORIES
                            else f"getattr({method_node.value})"
                        )
                    )
                    violations.append(f"{path.name}:{node.lineno}:{operation}")
                continue
        if attribute in {"write_text", "write_bytes", "touch"}:
            violations.append(f"{path.name}:{node.lineno}:{attribute}")
            continue
        if qualified in _PERSISTENCE_DUMP_SINKS or attribute in {
            "dump",
            "safe_dump",
        }:
            if not (artifact_function and qualified == "json.dump"):
                violations.append(f"{path.name}:{node.lineno}:{qualified or 'dump'}")
            continue
        if qualified in _PERSISTENCE_COPY_SINKS:
            if not (artifact_function and qualified == "shutil.copyfileobj"):
                violations.append(f"{path.name}:{node.lineno}:{qualified}")
            continue
        if qualified in _PERSISTENCE_CSV_FACTORIES:
            violations.append(f"{path.name}:{node.lineno}:{qualified}")
            continue
        if qualified in _PERSISTENCE_LOW_LEVEL_SINKS:
            allowed = (artifact_function and qualified == "os.replace") or (
                publication_function and qualified == "os.rename"
            )
            if not allowed:
                violations.append(f"{path.name}:{node.lineno}:{qualified}")
            continue
        if qualified == "tempfile.NamedTemporaryFile":
            if not artifact_function:
                violations.append(
                    f"{path.name}:{node.lineno}:tempfile.NamedTemporaryFile"
                )
            continue
        if qualified in {"builtins.print", "print"}:
            dynamic_destination = any(
                keyword.arg is None for keyword in inspected_call.keywords
            )
            destination = next(
                (
                    keyword.value
                    for keyword in inspected_call.keywords
                    if keyword.arg == "file"
                ),
                None,
            )
            if dynamic_destination or (
                destination is not None
                and _qualified_ast_name(
                    destination,
                    aliases,
                    assignments,
                )
                not in {"sys.stderr", "sys.stdout"}
            ):
                violations.append(f"{path.name}:{node.lineno}:print(file)")
            continue
        if qualified == "os.open":
            dynamic_arguments = any(
                isinstance(argument, ast.Starred)
                for argument in inspected_call.args
            ) or any(keyword.arg is None for keyword in inspected_call.keywords)
            flags = (
                None
                if dynamic_arguments
                else (
                    inspected_call.args[1]
                    if len(inspected_call.args) > 1
                    else next(
                        (
                            keyword.value
                            for keyword in inspected_call.keywords
                            if keyword.arg == "flags"
                        ),
                        None,
                    )
                )
            )
            status = (
                _os_write_flag_status(flags, aliases, assignments)
                if flags is not None
                else None
            )
            if status is not False:
                operation = "write" if status else "dynamic"
                violations.append(f"{path.name}:{node.lineno}:os.open({operation})")
            continue
        if qualified in {"builtins.open", "io.open", "os.fdopen"} or (
            qualified == "open" and isinstance(resolved_func, ast.Name)
        ):
            index = 1
        elif attribute == "open":
            index = 0
        else:
            index = -1
        if index >= 0:
            mode = _literal_mode(
                inspected_call,
                positional_index=index,
                assignments=assignments,
            )
            if mode is None or any(flag in mode for flag in "wax+"):
                violations.append(
                    f"{path.name}:{node.lineno}:open({mode or 'dynamic'})"
                )
            continue
        if attribute in {
            "write",
            "writeheader",
            "writerow",
            "writerows",
            "writelines",
            "truncate",
        }:
            allowed = (
                artifact_function
                and attribute in {"write", "writelines", "truncate"}
            ) or (
                server_function
                and attribute == "write"
                and isinstance(resolved_func, ast.Attribute)
                and _qualified_ast_name(
                    resolved_func.value,
                    aliases,
                    assignments,
                )
                == "self.wfile"
            )
            if not allowed:
                violations.append(f"{path.name}:{node.lineno}:{attribute}")
            continue
        if attribute in {"replace", "rename"}:
            receiver = resolved_func.value
            if not _obvious_string_receiver(receiver, assignments):
                violations.append(
                    f"{path.name}:{node.lineno}:path.{attribute}"
                )
            continue
        if factory_expanded:
            safe_target = _qualified_ast_name(
                resolved_func,
                aliases,
                assignments,
            )
            allowed = path_text.endswith(
                "src/hephaestus/evaluation_assets/pipeline.py"
            ) and safe_target in _AUDITED_PIPELINE_PARTIAL_TARGETS
            if not allowed:
                violations.append(f"{path.name}:{node.lineno}:partial(dynamic)")
    return violations


def test_studio_production_scope_has_no_direct_file_writers() -> None:
    """Studio production writes stay centralized in durable artifact primitives."""
    source_root = Path(__file__).resolve().parents[1] / "src" / "hephaestus"
    paths = _studio_persistence_paths(source_root)
    relative = {path.relative_to(source_root).as_posix() for path in paths}
    assert {
        "artifact_io.py",
        "datasets/evaluation_assets.py",
        "datasets/intent_assets.py",
        "cli.py",
        "webui/data.py",
        "webui/evaluation_assets_frontend.py",
        "webui/server.py",
        "webui/frontend.py",
    } <= relative
    assert {
        path.relative_to(source_root).as_posix()
        for path in (source_root / "evaluation_assets").rglob("*.py")
    } <= relative
    assert [
        violation
        for path in paths
        for violation in _studio_writer_violations(
            path,
            path.read_text(encoding="utf-8"),
        )
    ] == []


@pytest.mark.parametrize(
    ("source", "operation"),
    [
        ("Path('x').write_text('body')", "write_text"),
        ("Path('x').write_bytes(b'body')", "write_bytes"),
        ("from json import dump as emit\nemit({}, handle)", "json.dump"),
        ("open('x', 'a', encoding='utf-8')", "open(a)"),
        ("Path('x').open(mode='w')", "open(w)"),
        (
            "from builtins import open as file_open\nfile_open('x', 'x')",
            "open(x)",
        ),
        (
            "from pathlib import Path as P\nP('x').open('w')",
            "open(w)",
        ),
        (
            "from os import open as low_open, O_WRONLY as write_flag\n"
            "low_open('x', write_flag)",
            "os.open(write)",
        ),
        ("import shutil as sh\nsh.copy(source, target)", "shutil.copy"),
        (
            "from shutil import copyfileobj as stream\nstream(source, target)",
            "shutil.copyfileobj",
        ),
        ("import os as operating\noperating.write(fd, b'body')", "os.write"),
        ("from os import pwrite as emit\nemit(fd, b'body', 0)", "os.pwrite"),
        ("import os as operating\noperating.replace(a, b)", "os.replace"),
        ("from os import rename as swap\nswap(a, b)", "os.rename"),
        ("path.replace(target)", "path.replace"),
        ("Path('x').rename(target)", "path.rename"),
        ("mode = 'w'\nopen('x', mode)", "open(w)"),
        ("self.output_path.replace(target)", "path.replace"),
        ("emit = json.dump\nemit({}, handle)", "json.dump"),
        ("handle.write(b'body')", "write"),
        ("emit = Path('x').write_text\nemit('body')", "write_text"),
        ("emit = handle.write\nemit(b'body')", "write"),
        ("emit = Path('x').rename\nemit(target)", "path.rename"),
        ("Path('x').resolve().rename(target)", "path.rename"),
        ("Path('x').parent.replace(target)", "path.replace"),
        ("(Path('root') / 'x').replace(target)", "path.replace"),
        ("Path('x').with_suffix('.tmp').replace(target)", "path.replace"),
        ("Path('x').joinpath('y').rename(target)", "path.rename"),
        ("target.replace(destination)", "path.replace"),
        (
            "emit = (Path('root') / 'x').replace\nemit(target)",
            "path.replace",
        ),
        ("getattr(handle, 'write')(b'body')", "getattr(write)"),
        (
            "method = 'write'\ngetattr(handle, method)(b'body')",
            "getattr(write)",
        ),
        ("handle.writelines(lines)", "writelines"),
        ("handle.truncate(0)", "truncate"),
        ("import os\nos.writev(fd, buffers)", "os.writev"),
        ("import os\nos.pwritev(fd, buffers, 0)", "os.pwritev"),
        (
            "import os\nos.copy_file_range(source_fd, target_fd, count)",
            "os.copy_file_range",
        ),
        ("import os\nos.sendfile(target_fd, source_fd, 0, count)", "os.sendfile"),
        ("from posix import write as emit\nemit(fd, b'body')", "os.write"),
        (
            "from posix import open as emit, O_WRONLY\n"
            "emit('x', O_WRONLY)",
            "os.open(write)",
        ),
        ("from posix import pwrite as emit\nemit(fd, b'body', 0)", "os.pwrite"),
        (
            "import posix\nposix.copy_file_range(source_fd, target_fd, count)",
            "os.copy_file_range",
        ),
        (
            "from posix import sendfile as emit\n"
            "emit(target_fd, source_fd, 0, count)",
            "os.sendfile",
        ),
        (
            "from nt import open as emit, O_WRONLY\n"
            "emit('x', O_WRONLY)",
            "os.open(write)",
        ),
        ("import os\ngetattr(os, 'writev')(fd, buffers)", "os.writev"),
        (
            "import os\nmethod = 'sendfile'\n"
            "getattr(os, method)(target_fd, source_fd, 0, count)",
            "os.sendfile",
        ),
        (
            "import posix\n"
            "getattr(posix, 'copy_file_range')(source_fd, target_fd, count)",
            "os.copy_file_range",
        ),
        (
            "import shutil\ngetattr(shutil, 'copyfile')(source, target)",
            "shutil.copyfile",
        ),
        (
            "import tempfile\ngetattr(tempfile, 'NamedTemporaryFile')('w')",
            "tempfile.NamedTemporaryFile",
        ),
        (
            "from functools import partial\n"
            "emit = partial(open, 'x', 'w')\n"
            "emit()",
            "open(w)",
        ),
        (
            "import functools\n"
            "mode = choose_mode()\n"
            "emit = functools.partial(open, 'x', mode)\n"
            "emit()",
            "open(dynamic)",
        ),
        (
            "from functools import partial\n"
            "emit = partial(handle.writelines, lines)\n"
            "emit()",
            "writelines",
        ),
        (
            "from functools import partial\n"
            "emit = partial(open, 'x', mode='r')\n"
            "emit(mode='w')",
            "open(w)",
        ),
        (
            "from functools import partial\n"
            "partial(open, 'x', mode='r')(mode='w')",
            "open(w)",
        ),
        (
            "from functools import partial\n"
            "import os\n"
            "emit = partial(os.open, 'x', flags=os.O_RDONLY)\n"
            "emit(flags=os.O_WRONLY)",
            "os.open(write)",
        ),
        (
            "from functools import partial\n"
            "consumer(partial(open, 'x', 'w'))",
            "open(w)",
        ),
        (
            "from functools import partial\n"
            "emit = partial(open, 'x', 'w')\n"
            "consumer(emit)",
            "open(w)",
        ),
        (
            "from functools import partial\n"
            "import os\n"
            "consumer(partial(os.writev, fd, buffers))",
            "os.writev",
        ),
        (
            "from functools import partial\n"
            "emit = partial(select_sink(), target)\n"
            "emit(payload)",
            "partial(dynamic)",
        ),
        (
            "from functools import partial\n"
            "consumer(partial(select_sink(), target))",
            "partial(dynamic)",
        ),
        (
            "from functools import partial\n"
            "writer = writers[name]\n"
            "consumer(partial(writer, target))",
            "partial(dynamic)",
        ),
        ("emit, other = handle.write, noop\nemit(b'body')", "write"),
        ("(emit := handle.write)(b'body')", "write"),
        ("(emit := open)('x', 'w')", "open(w)"),
        (
            "import os\nemit = os.write\nemit(fd, b'body')\nemit = noop",
            "os.write",
        ),
        (
            "import os\n"
            "def bad():\n"
            "    emit = os.write\n"
            "    emit(fd, b'body')\n"
            "def good():\n"
            "    emit = noop\n",
            "os.write",
        ),
        (
            "import os\n"
            "emit = os.write\n"
            "def bad():\n"
            "    emit(fd, b'body')\n",
            "os.write",
        ),
        (
            "from os import write as emit\n"
            "emit(fd, b'body')\n"
            "from math import sin as emit\n",
            "os.write",
        ),
        (
            "def bad():\n"
            "    from os import write as emit\n"
            "    emit(fd, b'body')\n"
            "def good():\n"
            "    from math import sin as emit\n",
            "os.write",
        ),
        (
            "from os import open as emit, O_WRONLY\n"
            "emit('x', O_WRONLY)\n"
            "from builtins import len as emit\n",
            "os.open(write)",
        ),
        ("open('x', **{'mode': 'w'})", "open(dynamic)"),
        ("kwargs = {'mode': 'w'}\nopen('x', **kwargs)", "open(dynamic)"),
        ("Path('x').open(**{'mode': 'w'})", "open(dynamic)"),
        ("import os\nos.fdopen(fd, **{'mode': 'w'})", "open(dynamic)"),
        ("open(*('x', 'w'))", "open(dynamic)"),
        ("serializer.dump(payload, handle)", "serializer.dump"),
        ("toml.dump(payload, handle)", "toml.dump"),
        ("yaml.safe_dump(payload, handle)", "yaml.safe_dump"),
        (
            "from functools import partial\n"
            "partial(open, 'x', mode='r')(**{'mode': 'w'})",
            "open(dynamic)",
        ),
        (
            "from functools import partial\n"
            "import os\n"
            "partial(os.open, 'x', flags=os.O_RDONLY)"
            "(**{'flags': os.O_WRONLY})",
            "os.open(dynamic)",
        ),
        (
            "from functools import partial\n"
            "import os\n"
            "opts = {'flags': os.O_WRONLY}\n"
            "partial(os.open, 'x', flags=os.O_RDONLY)(**opts)",
            "os.open(dynamic)",
        ),
        (
            "if platform_ok:\n"
            "    from os import write as emit\n"
            "else:\n"
            "    from math import sin as emit\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "if platform_ok:\n"
            "    emit = os.write\n"
            "else:\n"
            "    emit = noop\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "try:\n"
            "    from os import write as emit\n"
            "except ImportError:\n"
            "    from math import sin as emit\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "emit = os.write\n"
            "for item in items:\n"
            "    emit = noop\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "emit = os.write\n"
            "while condition:\n"
            "    emit = noop\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "match platform_name:\n"
            "    case 'writer':\n"
            "        from os import write as emit\n"
            "    case _:\n"
            "        from math import sin as emit\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "emit = os.write if condition else noop\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "if condition:\n"
            "    emit = os.write\n"
            "else:\n"
            "    emit = noop\n"
            "    first = os.write\n"
            "    second = os.write\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "try:\n"
            "    emit = os.write\n"
            "    risky()\n"
            "    emit = noop\n"
            "except Exception:\n"
            "    pass\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        ("mode = 'r'\nmode += '+'\nopen('x', mode)", "open(dynamic)"),
        (
            "import os\n"
            "flags = os.O_RDONLY\n"
            "flags |= os.O_WRONLY\n"
            "os.open('x', flags)",
            "os.open(dynamic)",
        ),
        (
            "import os\n"
            "emit = condition and os.write or noop\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "emit = {'writer': os.write, 'safe': noop}[choice]\n"
            "emit(fd, b'body')",
            "os.write",
        ),
        ("import os\nconsumer(os.write)", "os.write"),
        (
            "import os\nself.emit = os.write\nself.emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "writers['emit'] = os.write\n"
            "writers['emit'](fd, b'body')",
            "os.write",
        ),
        (
            "import os\nemit = choose(os.write, noop)\nemit(fd, b'body')",
            "os.write",
        ),
        ("print('body', file=handle)", "print(file)"),
        ("print('body', **{'file': handle})", "print(file)"),
        ("options = {'file': handle}\nprint('body', **options)", "print(file)"),
        ("import csv\ncsv.writer(handle).writerow(row)", "csv.writer"),
        (
            "import csv\n"
            "csv.DictWriter(handle, fields).writerows(rows)",
            "csv.DictWriter",
        ),
        (
            "import csv\nconsumer(getattr(csv, 'writer')(handle))",
            "csv.writer",
        ),
        (
            "import builtins\n"
            "getattr(builtins, 'print')('body', file=handle)",
            "builtins.print",
        ),
        (
            "import os\nfor emit in (os.write,):\n    emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n"
            "async for emit in async_iter((os.write,)):\n"
            "    emit(fd, b'body')",
            "os.write",
        ),
        (
            "import os\n[emit(fd, b'body') for emit in (os.write,)]",
            "os.write",
        ),
        (
            "import os\n"
            "writers = (os.write,)\n"
            "for emit in writers:\n"
            "    emit(fd, b'body')",
            "os.write",
        ),
        ("import os\nconsumer([{'writers': (os.write,)}])", "os.write"),
        ("import os\ncallback = os.write", "os.write"),
        ("from os import write as callback", "os.write"),
        ("import os\ndef writer():\n    return os.write", "os.write"),
        (
            "import os\n"
            "def writer():\n"
            "    return {'writers': [(os.write,)]}",
            "os.write",
        ),
        (
            "import os\n"
            "def writer():\n"
            "    return os.write\n"
            "writer()(fd, b'body')",
            "os.write",
        ),
        (
            "import csv\nmodule = csv\ndef factory():\n    return module.writer",
            "csv.writer",
        ),
        (
            "import csv\nmodule = csv\n"
            "for factory in (module.writer,):\n    factory(handle)",
            "csv.writer",
        ),
        (
            "import csv\nmodule = csv\n"
            "async for factory in async_iter((module.DictWriter,)):\n"
            "    factory(handle, fields)",
            "csv.DictWriter",
        ),
        (
            "import csv\nmodule = csv\n"
            "[factory(handle) for factory in (module.writer,)]",
            "csv.writer",
        ),
        (
            "import csv\nmodule = csv\n"
            "consumer([{'factories': (module.writer,)}])",
            "csv.writer",
        ),
        (
            "import builtins\nconsumer([{'writers': (builtins.print,)}])",
            "builtins.print",
        ),
        (
            "import shutil\nmodule = shutil\ndef factory():\n"
            "    return module.copyfile",
            "shutil.copyfile",
        ),
        (
            "import tempfile\nmodule = tempfile\n"
            "for factory in (module.NamedTemporaryFile,):\n    factory('w')",
            "tempfile.NamedTemporaryFile",
        ),
        (
            "import shutil\n"
            "module = safe if condition else shutil\n"
            "module.copyfile(source, destination)",
            "shutil.copyfile",
        ),
        (
            "import tempfile\n"
            "if condition:\n    module = safe\n"
            "else:\n    module = tempfile\n"
            "module.NamedTemporaryFile('w')",
            "tempfile.NamedTemporaryFile",
        ),
        (
            "import csv\n"
            "module = safe if condition else csv\n"
            "consumer(module.writer)",
            "csv.writer",
        ),
        (
            "import shutil\n"
            "def get_module():\n    return shutil\n"
            "get_module().copyfile(source, destination)",
            "shutil",
        ),
        (
            "import shutil\n"
            "for module in (safe, shutil):\n"
            "    module.copyfile(source, destination)",
            "shutil",
        ),
        (
            "import shutil\n"
            "[module.copyfile(source, destination) "
            "for module in (safe, shutil)]",
            "shutil",
        ),
        (
            "import shutil\n"
            "modules = {'copy': shutil}\n"
            "modules['copy'].copyfile(source, destination)",
            "shutil",
        ),
        (
            "import shutil\n"
            "holder.module = shutil\n"
            "holder.module.copyfile(source, destination)",
            "shutil",
        ),
        (
            "import shutil\n"
            "holder['module'] = shutil\n"
            "holder['module'].copyfile(source, destination)",
            "shutil",
        ),
        (
            "import tempfile\n"
            "holder.module: object = tempfile\n"
            "holder.module.NamedTemporaryFile('w')",
            "tempfile",
        ),
    ],
)
def test_studio_writer_guard_rejects_qualified_and_aliased_forms(
    source: str,
    operation: str,
) -> None:
    """Imports and aliases cannot bypass the production persistence guard."""
    path = Path("src/hephaestus/evaluation_assets/example.py")
    assert any(
        operation in violation
        for violation in _studio_writer_violations(path, source)
    )


@pytest.mark.parametrize(
    ("source", "expected_lines"),
    [
        (
            "import os\n"
            "if condition:\n"
            "    first = os.write\n"
            "    second = noop\n"
            "else:\n"
            "    first = noop\n"
            "    second = os.write\n"
            "first(fd, b'body')\n"
            "second(fd, b'body')",
            {"8", "9"},
        ),
        (
            "if condition:\n"
            "    from os import write as first\n"
            "    from math import sin as second\n"
            "else:\n"
            "    from math import sin as first\n"
            "    from os import write as second\n"
            "first(fd, b'body')\n"
            "second(fd, b'body')",
            {"7", "8"},
        ),
    ],
)
def test_studio_writer_guard_joins_each_possible_branch_binding(
    source: str,
    expected_lines: set[str],
) -> None:
    """Every name retains a persistence-capable binding across branch joins."""
    violations = _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/example.py"),
        source,
    )
    assert {
        violation.split(":", 2)[1]
        for violation in violations
        if violation.endswith(":os.write")
    } >= expected_lines


@pytest.mark.parametrize(
    ("path", "source"),
    [
        (
            Path("src/hephaestus/artifact_io.py"),
            "import json, pickle\n"
            "if condition:\n"
            "    emit = json.dump\n"
            "else:\n"
            "    emit = pickle.dump\n"
            "emit(payload, handle)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "if condition:\n"
            "    emit = os.rename\n"
            "else:\n"
            "    emit = os.write\n"
            "emit(source, target)",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "if condition:\n"
            "    emit = self.wfile.write\n"
            "else:\n"
            "    emit = other_handle.write\n"
            "emit(body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import json, pickle\n"
            "emit = json.dump if condition else pickle.dump\n"
            "emit(payload, handle)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "emit = os.rename if condition else os.write\n"
            "emit(source, target)",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "emit = self.wfile.write if condition else other_handle.write\n"
            "emit(body)",
        ),
    ],
)
def test_studio_writer_guard_rejects_ambiguous_exact_seam_bindings(
    path: Path,
    source: str,
) -> None:
    """An allowed seam cannot mask another viable forbidden branch binding."""
    assert _studio_writer_violations(path, source)


@pytest.mark.parametrize(
    ("path", "source"),
    [
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\ndef unauthorized():\n    os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\ndef unauthorized():\n    os.rename(source, target)",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "class Handler:\n"
            "    def unauthorized(self):\n"
            "        self.wfile.write(body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "class Evil:\n"
            "    def atomic_write_json(self):\n"
            "        os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "class Evil:\n"
            "    def install_generation(self):\n"
            "        os.rename(source, target)",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "class Evil:\n"
            "    def _send_json(self):\n"
            "        self.wfile.write(body)",
        ),
    ],
)
def test_studio_writer_guard_rejects_writers_outside_exact_audited_functions(
    path: Path,
    source: str,
) -> None:
    """A trusted module path does not authorize a new writer function."""
    assert _studio_writer_violations(path, source)


@pytest.mark.parametrize(
    ("path", "source"),
    [
        (
            Path("src/hephaestus/artifact_io.py"),
            "import json, os, shutil, tempfile\n"
            "def atomic_write_json():\n"
            "    json.dump({}, handle)\n"
            "    handle.write('body')\n"
            "def atomic_copy_file():\n"
            "    shutil.copyfileobj(source, handle)\n"
            "def _atomic_write_binary():\n"
            "    tempfile.NamedTemporaryFile('wb')\n"
            "    os.replace(source, target)\n"
            "    getattr(os, 'replace')(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "def install_generation():\n"
            "    os.rename(temporary, target)\n"
            "    getattr(os, 'rename')(temporary, target)",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "class _Handler:\n"
            "    def _send_json(self):\n"
            "        self.wfile.write(body)",
        ),
        (
            Path("src/hephaestus/webui/data.py"),
            "import os\nopen(path, 'rb')\nPath(path).open('r')\n"
            "os.open(path, os.O_RDONLY)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/pipeline.py"),
            "from functools import partial\n"
            "partial(_normalize_feedback_evidence_response, batch=batch)\n"
            "partial(_normalize_guideline_response, route=route)\n"
            "partial(_normalize_inferred_rubric_response, batch=batch)\n"
            "partial(_normalize_synthetic_response, batch=batch)",
        ),
    ],
)
def test_studio_writer_guard_allows_only_audited_nonpersistent_seams(
    path: Path,
    source: str,
) -> None:
    """The allowlist is path-specific and does not suppress ordinary writers."""
    assert _studio_writer_violations(path, source) == []


class _NeverCalledEmbeddingProvider:
    provider_name = "fake"
    model = "never-called-embedding"

    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        raise AssertionError("busy pipeline reached the embedding provider")


class _SuccessfulEmbeddingProvider:
    provider_name = "fake"
    model = "fake-embedding"

    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


class _SuccessfulRubricProvider:
    provider_name = "fake"
    model = "fake-rubric"

    def __init__(self) -> None:
        self.calls = 0

    def generate_json(
        self,
        system_prompt: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls += 1
        if "records" in payload:
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "answer request",
                        "confidence": 0.9,
                        "observations": [
                            {
                                "claim": "Answer the stated request.",
                                "evidence_type": "explicit_feedback",
                                "evidence_pointer": "feedback.rationale",
                                "polarity": row["feedback"]["polarity"],
                            }
                        ],
                        "requested_corrections": [],
                        "uncertainties": [],
                    }
                    for row in payload["records"]
                ]
            }
        if "evidence" in payload:
            return {
                "guidelines": [
                    {
                        "intent_label": "answer request",
                        "description": "Answer requests within their stated scope.",
                        "route": payload["route"],
                        "source_record_ids": [
                            row["record_id"] for row in payload["evidence"]
                        ],
                        "confidence": 0.9,
                        "criteria": [
                            {
                                "kind": "required",
                                "statement": "Answer the stated request.",
                                "dimension": "task_success",
                                "severity": "critical",
                                "applicability": "always",
                                "scoring": "binary",
                                "evidence_required": False,
                                "evaluator": {
                                    "type": "llm_judge",
                                    "fallback": "human_review",
                                },
                            }
                        ],
                        "tool_expectations": {},
                        "reference_output": None,
                    }
                ]
            }
        if "synthetic evaluation input" in system_prompt:
            return {"cases": []}
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "answer request",
                    "confidence": 0.8,
                    "must": ["Answer the stated request."],
                    "must_not": [],
                    "should": [],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
                for row in payload["clusters"]
            ]
        }


class _SuccessfulDefaultRubricProvider(_SuccessfulRubricProvider):
    """Credential-free stand-in with the built-in OpenAI settings profile."""

    provider_name = "openai"

    def __init__(self, model: str, max_output_tokens: int = 16384) -> None:
        super().__init__()
        self.model = model
        self.timeout_seconds = 300
        self.max_retries = 3
        self.retry_backoff_seconds = 2
        self.max_output_tokens = max_output_tokens
        self.temperature = {
            "status": "not_applicable",
            "reason": "provider_does_not_use_sampling",
        }
        self.response_format = "json_object"
        self.seed = {
            "status": "not_applicable",
            "reason": "provider_does_not_use_sampling",
        }


class _SuccessfulDefaultEmbeddingProvider(_SuccessfulEmbeddingProvider):
    """Credential-free stand-in with the built-in OpenAI settings profile."""

    provider_name = "openai"

    def __init__(self, model: str) -> None:
        super().__init__()
        self.model = model
        self.timeout_seconds = 300
        self.max_retries = 3
        self.retry_backoff_seconds = 2
        self.batch_size = 128
        self.response_format = "dense_float_vectors"
        self.seed = {
            "status": "not_applicable",
            "reason": "provider_does_not_use_sampling",
        }


class _SuccessfulSyntheticRubricProvider(_SuccessfulRubricProvider):
    def __init__(self) -> None:
        super().__init__()
        self.synthetic_calls = 0

    def generate_json(
        self,
        system_prompt: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if "synthetic evaluation input" in system_prompt:
            self.calls += 1
            self.synthetic_calls += 1
            return {
                "cases": [
                    {
                        "cluster_id": row["cluster_id"],
                        "task_type": "generic",
                        "user_input": "Diagnose a novel lunar telemetry checksum divergence.",
                        "conversation_context": [],
                    }
                    for row in payload["clusters"]
                ]
            }
        return super().generate_json(system_prompt, payload)


def _hold_asset_lock(
    tenants_root: str,
    tenant_id: str,
    asset_id: str,
    ready: Any,
    release: Any,
) -> None:
    layout = EvaluationAssetLayout(Path(tenants_root), tenant_id, asset_id)
    with layout.asset_lock():
        ready.set()
        if not release.wait(10):
            raise RuntimeError("test lock holder timed out")


def test_state_round_trips_all_v2_lifecycle_statuses() -> None:
    """V2 accepts exactly the six lifecycle states and rejects completed."""
    timestamp = "2026-08-19T00:00:00+00:00"
    config = EvaluationAssetConfig(tenant_id="tenant_a")

    assert TOP_LEVEL_STATUSES == (
        "draft",
        "queued",
        "running",
        "awaiting_review",
        "released",
        "failed",
    )
    for status in TOP_LEVEL_STATUSES:
        state = PipelineState.new(config, timestamp)
        state.status = status
        restored = PipelineState.from_dict(state.to_dict())
        assert restored.schema_version == STATE_SCHEMA_VERSION
        assert restored.status == status

    invalid = PipelineState.new(config, timestamp).to_dict()
    invalid["status"] = "completed"
    with pytest.raises(ValueError, match="Unsupported evaluation asset status"):
        PipelineState.from_dict(invalid)


def test_pre_v2_completed_remains_an_explicit_legacy_sentinel() -> None:
    """Loading legacy completed never silently maps it to released."""
    raw = {
        "tenant_id": "tenant_a",
        "asset_id": "v1",
        "status": "completed",
        "created_at": "2026-08-19T00:00:00+00:00",
        "updated_at": "2026-08-19T01:00:00+00:00",
        "stages": [],
    }

    state = PipelineState.from_dict(raw)

    assert state.schema_version != STATE_SCHEMA_VERSION
    assert state.status == "completed"
    assert state.legacy_completed is True
    assert state.to_dict()["status"] == "completed"


def test_completed_is_rejected_for_an_explicit_future_state_schema() -> None:
    """Only the known pre-v2 representation may carry the legacy sentinel."""
    raw = {
        "schema_version": "fapo-evaluation-asset-state-v3",
        "tenant_id": "tenant_a",
        "asset_id": "v1",
        "status": "completed",
        "stages": [],
    }

    with pytest.raises(ValueError, match="Unsupported evaluation asset state schema"):
        PipelineState.from_dict(raw)


@pytest.mark.parametrize("schema_version", [None, "", 0, False, [], {}])
def test_explicit_falsey_or_non_string_state_schema_is_not_legacy(
    schema_version: Any,
) -> None:
    """Only an absent schema key denotes the historical pre-v2 representation."""
    raw = {
        "schema_version": schema_version,
        "tenant_id": "tenant_a",
        "asset_id": "v1",
        "status": "completed",
        "stages": [],
    }

    with pytest.raises(ValueError, match="Unsupported evaluation asset state schema"):
        PipelineState.from_dict(raw)


def test_new_pipeline_state_starts_draft() -> None:
    """Library and CLI initialization persist an inert draft workspace."""
    state = PipelineState.new(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        "2026-08-19T00:00:00+00:00",
    )

    assert state.status == "draft"
    assert state.schema_version == STATE_SCHEMA_VERSION
    assert state.mutation_sequence == 0


def test_filelock_is_a_bounded_core_dependency() -> None:
    """Every installed core caller receives the cross-process lock library."""
    pyproject = Path(__file__).parents[1] / "pyproject.toml"

    assert '"filelock>=3.13,<4"' in pyproject.read_text(encoding="utf-8")


def test_atomic_control_write_syncs_file_and_parent_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prepared journal rename is durable in file and directory metadata."""
    if artifact_io.os.name == "nt":
        pytest.skip("directory fsync is a POSIX durability primitive")
    synced: list[int] = []
    real_fsync = artifact_io.os.fsync

    def record_fsync(file_descriptor: int) -> None:
        synced.append(file_descriptor)
        real_fsync(file_descriptor)

    monkeypatch.setattr(artifact_io.os, "fsync", record_fsync)

    artifact_io.atomic_append_jsonl(
        tmp_path / "recovery_journal.jsonl",
        {"phase": "prepared"},
    )

    assert len(synced) >= 2


def test_spawned_process_holds_same_deterministic_asset_lock(tmp_path: Path) -> None:
    """A spawn-context holder excludes a direct library run without mutations."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            embedding_provider="tfidf",
            embedding_model="tfidf",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
    )
    rubric = _NeverCalledRubricProvider()
    embedding = _NeverCalledEmbeddingProvider()
    pipeline = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    before = _tree_bytes(layout.root)
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        with pytest.raises(
            EvaluationAssetBusyError,
            match="tenant_a/v1.*already being modified",
        ) as exc_info:
            pipeline.run()
        assert str(tmp_path) not in str(exc_info.value)
        assert layout.lock_path == (
            tenants_root.resolve()
            / "tenant_a"
            / "evaluation_assets"
            / ".locks"
            / "v1.lock"
        )
        assert rubric.calls == 0
        assert embedding.calls == 0
        assert _tree_bytes(layout.root) == before
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_spawned_lock_excludes_initialization_before_child_root_exists(
    tmp_path: Path,
) -> None:
    """Creation races use the collection-level lock before creating the asset root."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        with pytest.raises(EvaluationAssetBusyError):
            layout.initialize(
                EvaluationAssetConfig(tenant_id="tenant_a"),
                feedback,
                unlabeled,
            )
        assert not layout.root.exists()
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_revision_uses_same_asset_lock_and_preserves_bytes_when_busy(
    tmp_path: Path,
) -> None:
    """Direct config revision cannot bypass a lock owned by another process."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
    )
    before = _tree_bytes(layout.root)
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        with pytest.raises(EvaluationAssetBusyError):
            layout.revise_config({"cluster_count": 2})
        assert _tree_bytes(layout.root) == before
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_cli_and_service_resume_surface_library_lock_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI and service callers expose the core busy error without audit writes."""
    from src.hephaestus.cli import main

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            embedding_provider="tfidf",
            embedding_model="tfidf",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
    )
    before = _tree_bytes(layout.root)
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "hephaestus",
                "assets",
                "run",
                "--tenant",
                "tenant_a",
                "--asset-id",
                "v1",
                "--tenants-root",
                str(tenants_root),
            ],
        )
        with pytest.raises(EvaluationAssetBusyError):
            main()
        assert _tree_bytes(layout.root) == before

        manager = EvaluationAssetRunManager(tenants_root)
        with pytest.raises(EvaluationAssetBusyError):
            manager.resume("tenant_a", "v1")
        assert _tree_bytes(layout.root) == before
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_service_start_persists_queued_before_returning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service never returns a newly accepted job in draft state."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    entered = threading.Event()
    release = threading.Event()

    def pause_first_stage(
        pipeline: EvaluationAssetPipeline,
        stage: Any,
    ) -> dict[str, int]:
        entered.set()
        if not release.wait(5):
            raise RuntimeError("test stage timed out")
        raise RuntimeError("stop after service lifecycle assertion")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", pause_first_stage)
    manager = EvaluationAssetRunManager(tenants_root)
    try:
        response = manager.start(
            EvaluationAssetConfig(
                tenant_id="tenant_a",
                embedding_provider="tfidf",
                embedding_model="tfidf",
                cluster_count=1,
            ),
            feedback,
            unlabeled,
        )
        assert entered.wait(5)
        assert response["status"] in {"queued", "running"}
        assert response["status"] != "draft"
        persisted = EvaluationAssetLayout(
            tenants_root,
            "tenant_a",
            "v1",
        ).load_state()
        assert persisted.status in {"queued", "running"}
    finally:
        release.set()


def test_service_waits_for_live_slow_preflight_without_timeout_or_orphan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lock-owning worker remains the request's admitted preflight operation."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            embedding_provider="tfidf",
            embedding_model="tfidf",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        initial_status="queued",
    )
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    real_boundary = pipeline_module.mutable_rebuild_boundary

    real_event_type = threading.Event

    class DeterministicHandshakeEvent:
        def __init__(self) -> None:
            self._event = real_event_type()

        def set(self) -> None:
            self._event.set()

        def is_set(self) -> bool:
            return self._event.is_set()

        def wait(self, timeout: float | None = None) -> bool:
            if timeout is not None:
                return False
            return self._event.wait()

    def slow_boundary(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        if not release.wait(10):
            raise RuntimeError("test preflight timed out")
        return real_boundary(*args, **kwargs)

    def stop_before_provider(self: EvaluationAssetPipeline, stage: Any) -> Any:
        raise RuntimeError("stop after service admission")

    monkeypatch.setattr(pipeline_module, "mutable_rebuild_boundary", slow_boundary)
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", stop_before_provider)
    monkeypatch.setattr(service_module.threading, "Event", DeterministicHandshakeEvent)
    manager = EvaluationAssetRunManager(tenants_root)
    result: dict[str, Any] = {}

    def request() -> None:
        try:
            result["response"] = manager.resume("tenant_a", "v1")
        except Exception as exc:  # pragma: no cover - asserted below
            result["error"] = exc
        finally:
            finished.set()

    request_thread = threading.Thread(target=request)
    request_thread.start()
    try:
        assert entered.wait(5)
        assert not finished.is_set()
        assert manager.is_running("tenant_a", "v1")
        with pytest.raises(EvaluationAssetBusyError):
            layout.revise_config({"cluster_count": 2})
        release.set()
        assert finished.wait(5)
        assert "error" not in result
        assert result["response"]["status"] in {"running", "failed"}
    finally:
        release.set()
        request_thread.join(timeout=5)


@pytest.mark.parametrize("condition", ["released", "corrupt"])
def test_service_preflight_rejection_has_no_provider_or_stage_work_and_cleans_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition: str,
) -> None:
    """Immutable and corrupt releases reject synchronously with no orphan worker."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    if condition == "corrupt":
        receipt = layout.receipt_path(PipelineStage.DATASET_SPLITS)
        receipt.write_bytes(receipt.read_bytes() + b"\n")

    def reject_constructor(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("provider constructed during rejected preflight")

    def reject_stage(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("stage ran during rejected preflight")

    monkeypatch.setattr(pipeline_module, "OpenAIRubricProvider", reject_constructor)
    monkeypatch.setattr(pipeline_module, "OpenAIEmbeddingProvider", reject_constructor)
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", reject_stage)
    manager = EvaluationAssetRunManager(layout.tenants_root)
    expected = (
        EvaluationAssetImmutableError
        if condition == "released"
        else EvaluationAssetIntegrityError
    )

    with pytest.raises(expected):
        manager.resume(layout.tenant_id, layout.asset_id)

    assert not manager.is_running(layout.tenant_id, layout.asset_id)


def test_service_extension_persists_queued_before_worker_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service-created children enter queued, never draft, before execution."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    rubric = _SuccessfulRubricProvider()
    rubric.provider_name = "openai"
    parent_pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider="openai",
            rubric_model="fake-rubric",
            embedding_provider="tfidf",
            embedding_model="tfidf",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric,
    )
    parent_pipeline.run()
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    real_boundary = pipeline_module.mutable_rebuild_boundary

    def slow_boundary(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        if not release.wait(10):
            raise RuntimeError("test preflight timed out")
        return real_boundary(*args, **kwargs)

    def stop_before_provider(self: EvaluationAssetPipeline, stage: Any) -> Any:
        raise RuntimeError("stop after service extension admission")

    monkeypatch.setattr(pipeline_module, "mutable_rebuild_boundary", slow_boundary)
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", stop_before_provider)
    manager = EvaluationAssetRunManager(tenants_root)
    result: dict[str, Any] = {}

    def request() -> None:
        try:
            result["response"] = manager.extend(
                "tenant_a",
                "v1",
                "v2",
                additional_feedback=_write_additional_feedback(tenants_root),
                additional_unlabeled=None,
                clustering_mode="keep",
            )
        except Exception as exc:  # pragma: no cover - asserted below
            result["error"] = exc
        finally:
            finished.set()

    request_thread = threading.Thread(target=request)
    request_thread.start()
    try:
        assert entered.wait(5)
        child = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")
        assert child.load_state().status == "queued"
        assert not finished.is_set()
        release.set()
        assert finished.wait(5)
        assert "error" not in result
        assert result["response"]["status"] in {"running", "failed"}
    finally:
        release.set()
        request_thread.join(timeout=5)


def test_revised_rubric_model_constructs_only_the_new_default_after_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A resume cannot call the pre-revision default while claiming the new model."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    constructed: list[str] = []

    def rubric_factory(
        *,
        model: str,
        max_output_tokens: int,
        **_: Any,
    ) -> _SuccessfulRubricProvider:
        constructed.append(model)
        provider = _SuccessfulRubricProvider()
        provider.model = model
        provider.timeout_seconds = 300
        provider.max_retries = 3
        provider.retry_backoff_seconds = 2
        provider.max_output_tokens = max_output_tokens
        provider.temperature = 0.0
        provider.response_format = "json_object"
        provider.seed = {
            "status": "not_applicable",
            "reason": "provider_does_not_use_sampling",
        }
        return provider

    monkeypatch.setattr(pipeline_module, "OpenAIRubricProvider", rubric_factory)
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider="openai",
            rubric_model="old-rubric",
            embedding_provider="tfidf",
            embedding_model="tfidf",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
    )

    assert constructed == []
    released = pipeline.run(config_updates={"rubric_model": "new-rubric"})

    assert released.status == "released"
    assert constructed == ["new-rubric"]
    receipt = json.loads(
        pipeline.layout.receipt_path(PipelineStage.RUBRIC_EXTRACTION).read_text(
            encoding="utf-8"
        )
    )
    assert receipt["provider_identity"]["rubric"]["model"] == "new-rubric"


@pytest.mark.parametrize(
    ("initial_provider", "initial_model", "revised_model", "expected_models"),
    [
        ("tfidf", "tfidf", "new-embedding", ["new-embedding"]),
        ("openai", "old-embedding", "tfidf", []),
    ],
)
def test_embedding_revision_constructs_only_the_selected_default_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    initial_provider: str,
    initial_model: str,
    revised_model: str,
    expected_models: list[str],
) -> None:
    """Both local/remote revision directions use the reloaded configuration."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    constructed: list[str] = []

    def embedding_factory(*, model: str, **_: Any) -> _SuccessfulEmbeddingProvider:
        constructed.append(model)
        provider = _SuccessfulEmbeddingProvider()
        provider.model = model
        provider.timeout_seconds = 300
        provider.max_retries = 3
        provider.retry_backoff_seconds = 2
        provider.batch_size = 128
        provider.response_format = "dense_float_vectors"
        provider.seed = {
            "status": "not_applicable",
            "reason": "provider_does_not_use_sampling",
        }
        return provider

    monkeypatch.setattr(
        pipeline_module,
        "OpenAIEmbeddingProvider",
        embedding_factory,
    )
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider="fake",
            rubric_model="fake-rubric",
            embedding_provider=initial_provider,
            embedding_model=initial_model,
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=_SuccessfulRubricProvider(),
    )

    assert constructed == []
    released = pipeline.run(config_updates={"embedding_model": revised_model})

    assert released.status == "released"
    assert constructed == expected_models
    receipt = json.loads(
        pipeline.layout.receipt_path(PipelineStage.INTENT_CLUSTERING).read_text(
            encoding="utf-8"
        )
    )
    assert receipt["provider_identity"]["embedding"]["model"] == revised_model


def test_injected_provider_identity_is_receipted_and_manifested_as_actual(
    tmp_path: Path,
) -> None:
    """Injected provider evidence cannot silently repeat a stale configured model."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    rubric.model = "actual-rubric"
    rubric.provider_name = "injected-rubric"
    embedding.model = "actual-embedding"
    embedding.provider_name = "injected-embedding"

    pipeline.run()

    rubric_receipt = json.loads(
        pipeline.layout.receipt_path(PipelineStage.RUBRIC_EXTRACTION).read_text(
            encoding="utf-8"
        )
    )
    identity = rubric_receipt["provider_identity"]
    assert identity == {
        "rubric": provenance_module.provider_settings(
            rubric,
            role="rubric",
            identity={
                "model": "actual-rubric",
                "provider": "injected-rubric",
                "source": "injected",
            },
            pipeline_batch_size=3,
        )
    }
    assert rubric_receipt["provider_identity_sha256"] == canonical_sha256(identity)
    manifest = json.loads(pipeline.layout.manifest_path.read_text(encoding="utf-8"))
    assert manifest["providers"] == {
        "embedding_model": "actual-embedding",
        "embedding_provider": "injected-embedding",
        "rubric_model": "actual-rubric",
        "rubric_provider": "injected-rubric",
    }
    evidence = _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "feedback_evidence.jsonl",
        )
    )
    guidelines = _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
    )
    inferred = _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "inferred_unlabeled_cluster_rubrics.jsonl",
        )
    )
    assert {row["guideline_provider"] for row in evidence} == {"injected-rubric"}
    assert {row["guideline_provider"] for row in guidelines} == {"injected-rubric"}
    assert {row["rubric_provider"] for row in inferred} == {"injected-rubric"}


def test_mutable_resume_invalidates_from_changed_injected_provider_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request-affecting provider settings are receipt dependencies."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    rubric.timeout_seconds = 10
    original_run_stage = EvaluationAssetPipeline._run_stage

    def fail_at_clustering(
        instance: EvaluationAssetPipeline,
        stage: PipelineStage,
    ) -> dict[str, int]:
        if stage == PipelineStage.INTENT_CLUSTERING:
            raise RuntimeError("pause after rubric receipt")
        return original_run_stage(instance, stage)

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", fail_at_clustering)
    with pytest.raises(RuntimeError, match="pause after rubric receipt"):
        pipeline.run()
    old_receipt = pipeline.layout.receipt_path(
        PipelineStage.RUBRIC_EXTRACTION
    ).read_bytes()

    changed_rubric = _SuccessfulRubricProvider()
    changed_rubric.timeout_seconds = 11
    rerun_stages: list[PipelineStage] = []

    def record_stage(
        instance: EvaluationAssetPipeline,
        stage: PipelineStage,
    ) -> dict[str, int]:
        rerun_stages.append(stage)
        return original_run_stage(instance, stage)

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", record_stage)
    released = EvaluationAssetPipeline(
        pipeline.layout,
        rubric_provider=changed_rubric,
        embedding_provider=embedding,
    ).run()

    assert released.status == "released"
    assert rerun_stages[0] == PipelineStage.RUBRIC_EXTRACTION
    assert pipeline.layout.receipt_path(
        PipelineStage.RUBRIC_EXTRACTION
    ).read_bytes() != old_receipt
    assert changed_rubric.calls > 0


def test_released_verification_reaggregates_authenticated_provider_ledgers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release verification binds build calls to every receipt-backed ledger."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    seen: dict[str, list[dict[str, Any]]] = {}
    original = durability_module.validate_build_provenance_call_ledgers

    def capture(
        provenance: Mapping[str, Any],
        ledgers: Mapping[str, Sequence[Mapping[str, Any]]],
        *,
        profile: str,
    ) -> None:
        seen.update({stage: [dict(row) for row in rows] for stage, rows in ledgers.items()})
        original(provenance, ledgers, profile=profile)

    monkeypatch.setattr(
        durability_module,
        "validate_build_provenance_call_ledgers",
        capture,
    )

    verify_released_asset(pipeline.layout, released)

    assert set(seen) == {
        "rubric_extraction",
        "intent_clustering",
        "coverage_decisions",
        "label_inference",
        "synthetic_coverage",
    }


def test_injection_missing_required_provider_name_is_rejected_before_calls(
    tmp_path: Path,
) -> None:
    """The injection contract never substitutes config for required identity."""

    class ProtocolMinimalRubricProvider:
        model = "fake-rubric"

        def __init__(self) -> None:
            self.calls = 0

        def generate_json(
            self,
            system_prompt: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            self.calls += 1
            return _SuccessfulRubricProvider().generate_json(system_prompt, payload)

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    rubric = ProtocolMinimalRubricProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider="fake",
            rubric_model=rubric.model,
            embedding_provider="fake",
            embedding_model="fake-embedding",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    before = _authority_bytes(pipeline.layout)

    with pytest.raises(ValueError, match="injected rubric provider identity is unavailable"):
        pipeline.run()

    assert rubric.calls == 0
    assert _authority_bytes(pipeline.layout) == before


def test_injected_provider_mismatch_requires_explicit_extension_identity(
    tmp_path: Path,
) -> None:
    """A child cannot silently default to stale configured producer identities."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    rubric.provider_name = "actual-rubric-provider"
    rubric.model = "actual-rubric-model"
    embedding.provider_name = "actual-embedding-provider"
    embedding.model = "actual-embedding-model"
    pipeline.run()
    child = EvaluationAssetLayout(
        pipeline.layout.tenants_root,
        pipeline.layout.tenant_id,
        "v2",
    )
    additional = _write_additional_feedback(pipeline.layout.tenants_root)

    with pytest.raises(ValueError, match="explicit provider identity"):
        child.initialize_extension(
            pipeline.layout,
            additional_feedback=additional,
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()
    child.initialize_extension(
        pipeline.layout,
        additional_feedback=additional,
        additional_unlabeled=None,
        clustering_mode="keep",
        config_updates={
            "rubric_provider": "actual-rubric-provider",
            "rubric_model": "actual-rubric-model",
            "embedding_provider": "actual-embedding-provider",
            "embedding_model": "actual-embedding-model",
        },
    )
    child_config = child.load_config()
    assert (
        child_config.rubric_provider,
        child_config.rubric_model,
        child_config.embedding_provider,
        child_config.embedding_model,
    ) == (
        "actual-rubric-provider",
        "actual-rubric-model",
        "actual-embedding-provider",
        "actual-embedding-model",
    )


def test_refresh_extension_accepts_complete_new_embedding_identity(
    tmp_path: Path,
) -> None:
    """Refresh retains guideline provenance but may choose a new clusterer."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    rubric.provider_name = "actual-rubric-provider"
    rubric.model = "actual-rubric-model"
    embedding.provider_name = "actual-embedding-provider"
    embedding.model = "actual-embedding-model"
    pipeline.run()
    child = EvaluationAssetLayout(
        pipeline.layout.tenants_root,
        pipeline.layout.tenant_id,
        "v2",
    )
    child.initialize_extension(
        pipeline.layout,
        additional_feedback=_write_additional_feedback(
            pipeline.layout.tenants_root
        ),
        additional_unlabeled=None,
        clustering_mode="refresh",
        config_updates={
            "rubric_provider": "actual-rubric-provider",
            "rubric_model": "actual-rubric-model",
            "embedding_provider": "new-embedding-provider",
            "embedding_model": "new-embedding-model",
        },
    )
    new_embedding = _SuccessfulEmbeddingProvider()
    new_embedding.provider_name = "new-embedding-provider"
    new_embedding.model = "new-embedding-model"

    released = EvaluationAssetPipeline(
        child,
        rubric_provider=rubric,
        embedding_provider=new_embedding,
    ).run()

    assert released.status == "released"
    receipt = json.loads(
        child.receipt_path(PipelineStage.INTENT_CLUSTERING).read_text(
            encoding="utf-8"
        )
    )
    assert receipt["provider_identity"]["embedding"] == (
        provenance_module.provider_settings(
            new_embedding,
            role="embedding",
            identity={
                "provider": "new-embedding-provider",
                "model": "new-embedding-model",
                "source": "injected",
            },
            pipeline_batch_size=child.load_config().batch_size,
        )
    )


@pytest.mark.parametrize(
    "embedding_updates",
    [
        {},
        {"embedding_provider": "new-embedding-provider"},
        {"embedding_model": "new-embedding-model"},
    ],
)
def test_refresh_extension_rejects_implicit_or_partial_embedding_choice(
    tmp_path: Path,
    embedding_updates: dict[str, Any],
) -> None:
    """Stale configured defaults never fill a refresh embedding decision."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    rubric.provider_name = "actual-rubric-provider"
    rubric.model = "actual-rubric-model"
    embedding.provider_name = "actual-embedding-provider"
    embedding.model = "actual-embedding-model"
    pipeline.run()
    child = EvaluationAssetLayout(
        pipeline.layout.tenants_root,
        pipeline.layout.tenant_id,
        "v2",
    )
    updates = {
        "rubric_provider": "actual-rubric-provider",
        "rubric_model": "actual-rubric-model",
        **embedding_updates,
    }

    with pytest.raises(ValueError, match="explicit provider identity"):
        child.initialize_extension(
            pipeline.layout,
            additional_feedback=_write_additional_feedback(
                pipeline.layout.tenants_root
            ),
            additional_unlabeled=None,
            clustering_mode="refresh",
            config_updates=updates,
        )

    assert not child.root.exists()


def test_keep_extension_rejects_complete_new_embedding_identity(
    tmp_path: Path,
) -> None:
    """Keep mode remains anchored to the verified producing clusterer."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    rubric.provider_name = "actual-rubric-provider"
    rubric.model = "actual-rubric-model"
    embedding.provider_name = "actual-embedding-provider"
    embedding.model = "actual-embedding-model"
    pipeline.run()
    child = EvaluationAssetLayout(
        pipeline.layout.tenants_root,
        pipeline.layout.tenant_id,
        "v2",
    )

    with pytest.raises(ValueError, match="released parent embedding evidence"):
        child.initialize_extension(
            pipeline.layout,
            additional_feedback=_write_additional_feedback(
                pipeline.layout.tenants_root
            ),
            additional_unlabeled=None,
            clustering_mode="keep",
            config_updates={
                "rubric_provider": "actual-rubric-provider",
                "rubric_model": "actual-rubric-model",
                "embedding_provider": "new-embedding-provider",
                "embedding_model": "new-embedding-model",
            },
        )

    assert not child.root.exists()


def test_unavailable_parent_provider_identity_accepts_explicit_child_choice(
    tmp_path: Path,
) -> None:
    """An adopted parent can extend only with a complete explicit identity."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    _downgrade_to_legacy_completed(pipeline.layout)
    pipeline.layout.adopt_legacy()
    child = EvaluationAssetLayout(
        pipeline.layout.tenants_root,
        pipeline.layout.tenant_id,
        "v2",
    )
    additional = _write_additional_feedback(pipeline.layout.tenants_root)

    child.initialize_extension(
        pipeline.layout,
        additional_feedback=additional,
        additional_unlabeled=None,
        clustering_mode="keep",
        config_updates={
            "rubric_provider": "chosen-rubric-provider",
            "rubric_model": "chosen-rubric-model",
            "embedding_provider": "chosen-embedding-provider",
            "embedding_model": "chosen-embedding-model",
        },
    )

    child_config = child.load_config()
    assert (
        child_config.rubric_provider,
        child_config.rubric_model,
        child_config.embedding_provider,
        child_config.embedding_model,
    ) == (
        "chosen-rubric-provider",
        "chosen-rubric-model",
        "chosen-embedding-provider",
        "chosen-embedding-model",
    )


@pytest.mark.parametrize("explicit_embedding", [True, False])
def test_adopted_parent_refresh_requires_complete_provider_choices(
    tmp_path: Path,
    explicit_embedding: bool,
) -> None:
    """Historically unavailable identities are replaced only explicitly."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    _downgrade_to_legacy_completed(pipeline.layout)
    pipeline.layout.adopt_legacy()
    child = EvaluationAssetLayout(
        pipeline.layout.tenants_root,
        pipeline.layout.tenant_id,
        "v2",
    )
    updates = {
        "rubric_provider": "chosen-rubric-provider",
        "rubric_model": "chosen-rubric-model",
    }
    if explicit_embedding:
        updates.update(
            {
                "embedding_provider": "chosen-embedding-provider",
                "embedding_model": "chosen-embedding-model",
            }
        )

    if explicit_embedding:
        child.initialize_extension(
            pipeline.layout,
            additional_feedback=_write_additional_feedback(
                pipeline.layout.tenants_root
            ),
            additional_unlabeled=None,
            clustering_mode="refresh",
            config_updates=updates,
        )
        assert (
            child.load_config().embedding_provider,
            child.load_config().embedding_model,
        ) == ("chosen-embedding-provider", "chosen-embedding-model")
    else:
        with pytest.raises(ValueError, match="parent embedding identity is unavailable"):
            child.initialize_extension(
                pipeline.layout,
                additional_feedback=_write_additional_feedback(
                    pipeline.layout.tenants_root
                ),
                additional_unlabeled=None,
                clustering_mode="refresh",
                config_updates=updates,
            )
        assert not child.root.exists()


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_raw_snapshot_floor_rejects_before_revision_or_default_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    """Raw-floor integrity precedes revision WAL and credential-bearing defaults."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider="openai",
            rubric_model="initial-rubric",
            embedding_provider="openai",
            embedding_model="initial-embedding",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    if damage == "missing":
        layout.feedback_path.unlink()
    else:
        layout.feedback_path.write_bytes(layout.feedback_path.read_bytes() + b" \n")
    before = _authority_bytes(layout)
    constructed: list[tuple[str, str]] = []

    def rubric_factory(*, model: str, **_: Any) -> _SuccessfulRubricProvider:
        constructed.append(("rubric", model))
        provider = _SuccessfulRubricProvider()
        provider.model = model
        return provider

    def embedding_factory(*, model: str, **_: Any) -> _SuccessfulEmbeddingProvider:
        constructed.append(("embedding", model))
        provider = _SuccessfulEmbeddingProvider()
        provider.model = model
        return provider

    monkeypatch.setattr(pipeline_module, "OpenAIRubricProvider", rubric_factory)
    monkeypatch.setattr(pipeline_module, "OpenAIEmbeddingProvider", embedding_factory)

    with pytest.raises(EvaluationAssetIntegrityError, match="raw input snapshot"):
        EvaluationAssetPipeline(layout).run(
            config_updates={"rubric_model": "revised-rubric"}
        )

    assert constructed == []
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
@pytest.mark.parametrize("updates", [{}, {"match_threshold": 0.2}])
def test_direct_revision_rejects_invalid_raw_snapshot_without_authority_write(
    tmp_path: Path,
    damage: str,
    updates: dict[str, Any],
) -> None:
    """The library revision seam authenticates its immutable rebuild floor."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    if damage == "missing":
        layout.feedback_path.unlink()
    else:
        layout.feedback_path.write_bytes(layout.feedback_path.read_bytes() + b" \n")
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="raw input snapshot"):
        layout.revise_config(updates)

    assert _authority_bytes(layout) == before


def test_direct_noop_revision_accepts_valid_raw_snapshot_without_write(
    tmp_path: Path,
) -> None:
    """A valid immutable floor keeps the direct no-op result side-effect free."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    before = _authority_bytes(layout)

    result = layout.revise_config({})

    assert result == {
        "changed_fields": {},
        "invalidated_from_stage": None,
        "resume_from_stage": None,
    }
    assert _authority_bytes(layout) == before


def test_pending_never_receipted_stage_one_keeps_presence_only_revision_path(
    tmp_path: Path,
) -> None:
    """A fresh pending workspace may revise before Stage 1 creates authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    result = pipeline.layout.revise_config({"match_threshold": 0.2})

    stage_one = pipeline.layout.load_state().stages[0]
    assert result["invalidated_from_stage"] == PipelineStage.COVERAGE_DECISIONS.value
    assert stage_one.status == "pending"
    assert stage_one.receipt_sha256 is None
    assert not pipeline.layout.receipt_path(PipelineStage.RAW_INPUTS).exists()


def test_running_never_receipted_stage_one_keeps_presence_only_revision_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A process death before the Stage 1 receipt leaves a resumable floor."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def interrupt_before_stage_one(stage: PipelineStage) -> dict[str, int]:
        assert stage == PipelineStage.RAW_INPUTS
        raise KeyboardInterrupt

    monkeypatch.setattr(pipeline, "_run_stage", interrupt_before_stage_one)
    with pytest.raises(KeyboardInterrupt):
        pipeline.run()

    stage_one = pipeline.layout.load_state().stages[0]
    assert stage_one.status == "running"
    assert stage_one.receipt_sha256 is None
    assert not pipeline.layout.receipt_path(PipelineStage.RAW_INPUTS).exists()

    result = pipeline.layout.revise_config({"match_threshold": 0.2})

    assert result["invalidated_from_stage"] == PipelineStage.COVERAGE_DECISIONS.value


def test_completed_stage_one_cannot_be_relabeled_as_never_receipted(
    tmp_path: Path,
) -> None:
    """A retained completion event prevents a failed-state receipt bypass."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = _make_released_checkpoint_mutable(layout)
    state.stages[0].status = "failed"
    state.stages[0].receipt_sha256 = None
    layout.save_state(state)
    layout.receipt_path(PipelineStage.RAW_INPUTS).unlink()
    before = _authority_bytes(layout)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="raw input snapshot receipt authority",
    ):
        layout.revise_config({"match_threshold": 0.2})

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "receipt_damage",
    ["missing", "malformed", "incomplete_inputs", "rewritten_with_stale_state"],
)
@pytest.mark.parametrize("revision_path", ["direct_changed", "direct_noop", "pipeline"])
def test_claimed_raw_snapshot_floor_requires_complete_receipt_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt_damage: str,
    revision_path: str,
) -> None:
    """A completed Stage 1 never falls back to presence-only raw validation."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    receipt_path = layout.receipt_path(PipelineStage.RAW_INPUTS)

    if receipt_damage == "missing":
        receipt_path.unlink()
    elif receipt_damage == "malformed":
        artifact_io.atomic_write_text(receipt_path, "{not-json\n")
        state = layout.load_state()
        state.stages[0].receipt_sha256 = file_sha256(receipt_path)
        artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    else:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt_damage == "incomplete_inputs":
            receipt["inputs"] = receipt["inputs"][:1]
            artifact_io.atomic_write_json(receipt_path, receipt)
            state = layout.load_state()
            state.stages[0].receipt_sha256 = file_sha256(receipt_path)
            artifact_io.atomic_write_json(layout.state_path, state.to_dict())
        else:
            layout.feedback_path.write_bytes(
                layout.feedback_path.read_bytes() + b" \n"
            )
            relative = layout.feedback_path.relative_to(layout.root).as_posix()
            feedback_record = next(
                item for item in receipt["inputs"] if item["path"] == relative
            )
            feedback_record["bytes"] = layout.feedback_path.stat().st_size
            feedback_record["sha256"] = file_sha256(layout.feedback_path)
            artifact_io.atomic_write_json(receipt_path, receipt)

    configured: list[bool] = []

    def forbidden_configuration(*_: Any, **__: Any) -> None:
        configured.append(True)
        raise AssertionError("provider configuration preceded raw-floor rejection")

    monkeypatch.setattr(
        pipeline_module.EvaluationAssetPipeline,
        "_configure_providers",
        forbidden_configuration,
    )
    before = _authority_bytes(layout)
    updates = {} if revision_path == "direct_noop" else {"match_threshold": 0.2}

    with pytest.raises(EvaluationAssetIntegrityError, match="raw input snapshot"):
        if revision_path == "pipeline":
            EvaluationAssetPipeline(layout).run(config_updates=updates)
        else:
            layout.revise_config(updates)

    assert configured == []
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("rejection", ["busy", "released", "corrupt"])
def test_default_provider_constructors_are_not_called_on_rejected_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rejection: str,
) -> None:
    """Busy, immutable, and corrupt release preflight reject before defaults exist."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider="openai",
            rubric_model="configured-rubric",
            embedding_provider="openai",
            embedding_model="configured-embedding",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    pipeline.run()
    layout = pipeline.layout
    if rejection == "busy":
        _make_released_checkpoint_mutable(layout)
    elif rejection == "corrupt":
        target = layout.artifact_path(
            PipelineStage.INTENT_CLUSTERING,
            "intent_inventory.jsonl",
        )
        target.write_bytes(target.read_bytes() + b" \n")

    def forbidden_constructor(**_: Any) -> Any:
        raise AssertionError("default provider constructed before preflight rejection")

    monkeypatch.setattr(
        pipeline_module,
        "OpenAIRubricProvider",
        forbidden_constructor,
    )
    monkeypatch.setattr(
        pipeline_module,
        "OpenAIEmbeddingProvider",
        forbidden_constructor,
    )
    candidate = EvaluationAssetPipeline(layout)

    if rejection == "busy":
        with layout.asset_lock():
            with pytest.raises(EvaluationAssetBusyError):
                candidate.run()
    elif rejection == "released":
        with pytest.raises(EvaluationAssetImmutableError):
            candidate.run()
    else:
        with pytest.raises(EvaluationAssetIntegrityError):
            candidate.run()


def test_stage_specification_exhaustively_declares_required_artifacts() -> None:
    """One declarative map covers every current stage-owned release artifact."""
    expected = {
        PipelineStage.RAW_INPUTS: {"input_manifest.json"},
        PipelineStage.PREPARED_INPUTS: {
            "normalized_feedback.jsonl",
            "intent_records.jsonl",
        },
        PipelineStage.RUBRIC_EXTRACTION: {
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
        },
        PipelineStage.INTENT_CLUSTERING: {"intent_inventory.jsonl"},
        PipelineStage.COVERAGE_DECISIONS: {
            "intent_matches.jsonl",
            "coverage_report.md",
            "review_queue/labeling_queue.jsonl",
        },
        PipelineStage.LABEL_INFERENCE: {
            "inferred_unlabeled_cluster_rubrics.jsonl",
            "inferred_unlabeled_labels.jsonl",
            "missing_labeled_feedback_clusters.jsonl",
            "missing_labeled_feedback_report.md",
            "inferred_cases.jsonl",
        },
        PipelineStage.SYNTHETIC_COVERAGE: {
            "synthetic_candidates.jsonl",
            "rejected_synthetic.jsonl",
            "synthetic_filter_issues.jsonl",
            "synthetic_cases.jsonl",
        },
        PipelineStage.DATASET_SPLITS: {
            "train_trusted.jsonl",
            "train_inferred.jsonl",
            "train_synthetic.jsonl",
            "train.jsonl",
            "validation_trusted.jsonl",
            "validation_inferred.jsonl",
            "validation_synthetic.jsonl",
            "validation.jsonl",
            "test_trusted.jsonl",
            "test_inferred.jsonl",
            "test_synthetic.jsonl",
            "test.jsonl",
            "regression_trusted.jsonl",
            "triage_hold.jsonl",
            "dataset_manifest.json",
            "generation_manifest.json",
        },
    }

    assert set(STAGE_SPECIFICATIONS) == set(PipelineStage)
    for stage, required_outputs in expected.items():
        assert set(STAGE_SPECIFICATIONS[stage].required_outputs) == required_outputs
        assert STAGE_SPECIFICATIONS[stage].required_evidence_outputs == (
            "provenance.json",
        )
    assert STAGE_SPECIFICATIONS[PipelineStage.DATASET_SPLITS].required_asset_outputs == (
        "asset_manifest.json",
        "build_provenance.json",
    )
    assert STAGE_SPECIFICATIONS[PipelineStage.DATASET_SPLITS].required_catalog_outputs == ()


def test_pipeline_writes_receipt_commit_markers_and_releases(tmp_path: Path) -> None:
    """A new build releases only after all stage receipts exist and are referenced."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)

    state = pipeline.run()

    assert state.status == "released"
    assert state.schema_version == STATE_SCHEMA_VERSION
    assert all(stage.status == "completed" for stage in state.stages)
    assert rubric.calls > 0
    assert embedding.calls > 0
    for index, stage in enumerate(PipelineStage, start=1):
        stage_state = next(item for item in state.stages if item.stage == stage.value)
        receipt_path = pipeline.layout.receipt_path(stage)
        assert receipt_path.name == f"{index:02d}_{stage.value}.json"
        assert receipt_path.is_file()
        assert stage_state.receipt_sha256 == file_sha256(receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["schema_version"] == (
            durability_module.STAGE_RECEIPT_SCHEMA_VERSION
        )
        assert receipt["stage"] == stage.value
        assert receipt["stage_index"] == index
        assert receipt["resolved_config_sha256"]
        assert receipt["dependency_config_sha256"]
        assert receipt["prompt_set_sha256"]
        assert receipt["provider_identity_sha256"]
        assert receipt["provider_calls_sha256"]
        assert receipt["code_sha256"]
        if stage == PipelineStage.DATASET_SPLITS:
            assert receipt["build_provenance_sha256"] == file_sha256(
                pipeline.layout.build_provenance_path
            )
            assert receipt["generation_manifest_sha256"] == file_sha256(
                pipeline.layout.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "generation_manifest.json",
                )
            )
        assert {item["path"] for item in receipt["outputs"]} >= {
            pipeline.layout.artifact_path(stage, name)
            .relative_to(pipeline.layout.root)
            .as_posix()
            for name in STAGE_SPECIFICATIONS[stage].required_outputs
        }
    ledger_rows = []
    provider_stages = tuple(PipelineStage)[2:7]
    for stage in provider_stages:
        ledger_path = pipeline.layout.artifact_path(stage, "provider_calls.jsonl")
        assert ledger_path.is_file()
        rows = _read_jsonl(ledger_path)
        assert [row["ordinal"] for row in rows] == list(range(1, len(rows) + 1))
        assert all(
            row["transport_identity"]
            == {
                "status": "unavailable",
                "reason": "optional_metadata_protocol_absent",
            }
            for row in rows
        )
        stage_provenance = json.loads(
            pipeline.layout.artifact_path(stage, "provenance.json").read_text(
                encoding="utf-8"
            )
        )
        assert stage_provenance["calls"] == rows
        ledger_rows.extend(rows)
    assert _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "provider_calls.jsonl",
        )
    ) == []
    build_provenance = json.loads(
        pipeline.layout.build_provenance_path.read_text(encoding="utf-8")
    )
    assert len(build_provenance["identity"]["calls"]) == len(ledger_rows)
    assert len(build_provenance["audit"]["calls"]) == len(ledger_rows)


_STAGE_MUTATION_TARGETS = {
    PipelineStage.RAW_INPUTS: "input_manifest.json",
    PipelineStage.PREPARED_INPUTS: "normalized_feedback.jsonl",
    PipelineStage.RUBRIC_EXTRACTION: "feedback_evidence.jsonl",
    PipelineStage.INTENT_CLUSTERING: "intent_inventory.jsonl",
    PipelineStage.COVERAGE_DECISIONS: "coverage_report.md",
    PipelineStage.LABEL_INFERENCE: "inferred_cases.jsonl",
    PipelineStage.SYNTHETIC_COVERAGE: "synthetic_cases.jsonl",
    PipelineStage.DATASET_SPLITS: "train.jsonl",
}


@pytest.mark.parametrize("stage", list(PipelineStage))
def test_mutable_resume_rebuilds_from_first_missing_output(
    tmp_path: Path,
    stage: PipelineStage,
) -> None:
    """A missing committed output invalidates that mutable stage and its suffix."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    boundary = list(PipelineStage).index(stage)
    prefix_receipts = {
        prior: layout.receipt_path(prior).read_bytes()
        for prior in list(PipelineStage)[:boundary]
    }
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    target.unlink()
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    ).run()

    assert resumed.status == "released"
    assert target.is_file()
    assert all(
        layout.receipt_path(prior).read_bytes() == receipt_bytes
        for prior, receipt_bytes in prefix_receipts.items()
    )


@pytest.mark.parametrize("stage", list(PipelineStage))
def test_mutable_resume_rebuilds_from_first_corrupt_output(
    tmp_path: Path,
    stage: PipelineStage,
) -> None:
    """A parseable byte change still invalidates a mutable receipt boundary."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    boundary = list(PipelineStage).index(stage)
    prefix_receipts = {
        prior: layout.receipt_path(prior).read_bytes()
        for prior in list(PipelineStage)[:boundary]
    }
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    corrupt_bytes = target.read_bytes() + b" \n"
    target.write_bytes(corrupt_bytes)

    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    assert resumed.status == "released"
    assert target.read_bytes() != corrupt_bytes
    assert all(
        layout.receipt_path(prior).read_bytes() == receipt_bytes
        for prior, receipt_bytes in prefix_receipts.items()
    )


@pytest.mark.parametrize("stage", list(PipelineStage))
@pytest.mark.parametrize("mutation", ["missing", "corrupt"])
def test_released_asset_fails_closed_for_stage_output_damage(
    tmp_path: Path,
    stage: PipelineStage,
    mutation: str,
) -> None:
    """Released verification detects every stage boundary without repair."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    if mutation == "missing":
        target.unlink()
    else:
        target.write_bytes(target.read_bytes() + b" \n")
    before = _authority_bytes(layout)
    rubric = _NeverCalledRubricProvider()
    embedding = _NeverCalledEmbeddingProvider()

    with pytest.raises(EvaluationAssetIntegrityError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


def test_released_revision_and_run_fail_before_any_mutation(tmp_path: Path) -> None:
    """Changed, unchanged, and run requests cannot write a released asset."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    before = _authority_bytes(layout)

    for updates in ({}, {"match_threshold": 0.2}):
        with pytest.raises(
            EvaluationAssetImmutableError,
            match=r"assets extend --parent-asset-id v1 --asset-id <new-id>",
        ):
            layout.revise_config(updates)
        assert _authority_bytes(layout) == before

    rubric = _NeverCalledRubricProvider()
    embedding = _NeverCalledEmbeddingProvider()
    with pytest.raises(EvaluationAssetImmutableError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()
    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


def test_legacy_completed_rejects_revision_before_any_mutation(tmp_path: Path) -> None:
    """Adoption is the legacy completion's only permitted mutation path."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    before = _authority_bytes(layout)

    for updates in ({}, {"match_threshold": 0.2}):
        with pytest.raises(EvaluationAssetLegacyError, match="Run assets adopt"):
            layout.revise_config(updates)
        assert _authority_bytes(layout) == before


def test_legacy_completed_run_requires_adoption_without_mutation(tmp_path: Path) -> None:
    """The strict native selector preserves the pre-v2 adoption sentinel."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    before = _authority_bytes(layout)

    with pytest.raises(
        EvaluationAssetLegacyError,
        match="explicit verification and adoption are required",
    ):
        EvaluationAssetPipeline(layout).run()

    assert _authority_bytes(layout) == before


def test_downstream_revision_keeps_projected_receipt_prefix_valid(
    tmp_path: Path,
) -> None:
    """Audit-only full config changes do not invalidate unrelated stages."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    prefix = {
        stage: layout.receipt_path(stage).read_bytes()
        for stage in list(PipelineStage)[:7]
    }

    revision = layout.revise_config({"split_seed": 73})
    rubric = _NeverCalledRubricProvider()
    rubric.model = "fake-rubric"
    embedding = _NeverCalledEmbeddingProvider()
    embedding.model = "fake-embedding"
    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    ).run()

    assert revision["invalidated_from_stage"] == "dataset_splits"
    assert resumed.status == "released"
    assert all(
        layout.receipt_path(stage).read_bytes() == receipt
        for stage, receipt in prefix.items()
    )


def test_released_verification_does_not_require_current_code_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Historical code hashes remain evidence after the checkout changes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    monkeypatch.setattr(
        durability_module,
        "_code_identity",
        lambda: {"fingerprint": "new-code", "members": []},
    )

    verify_released_asset(pipeline.layout, released)
    with pytest.raises(EvaluationAssetImmutableError):
        EvaluationAssetPipeline(
            pipeline.layout,
            rubric_provider=_NeverCalledRubricProvider(),
            embedding_provider=_NeverCalledEmbeddingProvider(),
        ).run()


def test_interim_v2_release_without_pointer_fails_closed_with_repair_guidance(
    tmp_path: Path,
) -> None:
    """Task 3 releases without a publication pointer are not auto-adopted."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    pipeline.layout.release_pointer_path.unlink()

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match=(
            "this interim v2 release has no release.json publication pointer; "
            "repair it from a verified backup or rebuild it as a new asset version"
        ),
    ):
        verify_released_asset(pipeline.layout, released)


@pytest.mark.parametrize(
    "corruption",
    [
        "config_value",
        "config_tenant",
        "config_asset",
        "state_schema",
        "state_tenant",
        "state_asset",
        "stage_status",
        "stage_order",
        "duplicate_stage",
        "current_stage",
        "terminal_error",
        "missing_count",
        "extra_count",
        "negative_count",
    ],
)
def test_released_verification_authenticates_config_and_terminal_state(
    tmp_path: Path,
    corruption: str,
) -> None:
    """A release binds its persisted config, identity, stage set, and count shape."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    layout = pipeline.layout
    if corruption.startswith("config_"):
        payload = json.loads(layout.config_path.read_text(encoding="utf-8"))
        if corruption == "config_value":
            payload["rubric_model"] = "tampered-model"
        elif corruption == "config_tenant":
            payload["tenant_id"] = "other_tenant"
        else:
            payload["asset_id"] = "other_asset"
        artifact_io.atomic_write_json(layout.config_path, payload)
    else:
        payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
        if corruption == "state_schema":
            payload["schema_version"] = "fapo-evaluation-asset-state-v1"
        elif corruption == "state_tenant":
            payload["tenant_id"] = "other_tenant"
        elif corruption == "state_asset":
            payload["asset_id"] = "other_asset"
        elif corruption == "stage_status":
            payload["stages"][3]["status"] = "pending"
        elif corruption == "stage_order":
            payload["stages"][2], payload["stages"][3] = (
                payload["stages"][3],
                payload["stages"][2],
            )
        elif corruption == "duplicate_stage":
            payload["stages"][-1] = dict(payload["stages"][0])
        elif corruption == "current_stage":
            payload["current_stage"] = PipelineStage.DATASET_SPLITS.value
        elif corruption == "terminal_error":
            payload["error"] = "stale error"
        elif corruption == "missing_count":
            payload["counts"].pop("dataset_cases")
        elif corruption == "extra_count":
            payload["counts"]["untrusted_extra"] = 1
        else:
            payload["counts"]["dataset_cases"] = -1
        artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(layout, released)

    assert _authority_bytes(layout) == before


def test_released_verification_replays_receipt_config_history(
    tmp_path: Path,
) -> None:
    """Retained prefix receipts may use older audited configs, never unknown ones."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    revised = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    ).run(config_updates={"match_threshold": 0.2})

    verify_released_asset(layout, revised)
    history = _read_jsonl(layout.config_history_path)
    history[1]["changed_fields"]["match_threshold"]["previous"] = 0.123
    artifact_io.atomic_write_jsonl(layout.config_history_path, history)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(layout, layout.load_state())

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "damage",
    [
        "missing_journal",
        "missing_all_prepares",
        "missing_commit",
        "duplicate_prepare",
        "duplicate_commit",
        "unmatched_pair",
        "reordered_pairs",
    ],
)
def test_native_release_requires_ordered_history_journal_bijection(
    tmp_path: Path,
    damage: str,
) -> None:
    """Every native configuration update has one ordered WAL prepare and commit."""
    layout = _release_with_config_revisions(
        tmp_path,
        revision_count=2 if damage == "reordered_pairs" else 1,
    )
    _damage_revision_journal(layout, damage)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(layout, layout.load_state())

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("control_name", ["recovery_journal", "config_history"])
@pytest.mark.parametrize("corruption", ["blank_row", "duplicate_key"])
def test_standalone_release_verification_requires_strict_control_jsonl(
    tmp_path: Path,
    control_name: str,
    corruption: str,
) -> None:
    """Released verification applies recovery's strict JSONL boundary itself."""
    layout = _release_with_config_revisions(tmp_path, revision_count=1)
    path = (
        layout.recovery_journal_path
        if control_name == "recovery_journal"
        else layout.config_history_path
    )
    raw = path.read_text(encoding="utf-8")
    if corruption == "blank_row":
        raw = "\n" + raw
    elif control_name == "recovery_journal":
        raw = raw.replace(
            '"phase": "prepared"',
            '"phase": "prepared", "phase": "prepared"',
            1,
        )
    else:
        raw = raw.replace(
            '"event": "configuration_created"',
            '"event": "configuration_created", '
            '"event": "configuration_created"',
            1,
        )
    artifact_io.atomic_write_text(path, raw)
    if control_name == "config_history":
        receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["config_history_sha256"] = file_sha256(path)
        artifact_io.atomic_write_json(receipt_path, receipt)
        state = layout.load_state()
        next(
            item
            for item in state.stages
            if item.stage == PipelineStage.DATASET_SPLITS.value
        ).receipt_sha256 = file_sha256(receipt_path)
        artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(layout, layout.load_state())

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("verification_boundary", ["candidate", "persisted"])
@pytest.mark.parametrize(
    "ledger_damage",
    [
        "v1_row",
        "nonrevision_v2_row",
        "mixed_v1_v2",
        "audit_descriptor",
        "reanchored_history",
        "relabeled_origins_without_wal",
    ],
)
def test_standalone_release_verification_uses_complete_journal_authority(
    tmp_path: Path,
    verification_boundary: str,
    ledger_damage: str,
) -> None:
    """Candidate and persisted verification share recovery's complete ledger grammar."""
    layout = (
        _release_with_config_revisions(tmp_path, revision_count=1)
        if ledger_damage
        in {"mixed_v1_v2", "audit_descriptor", "reanchored_history"}
        else _create_pipeline(tmp_path)[0].layout
    )
    if not layout.state_path.exists():
        raise AssertionError("test setup did not initialize the asset")
    if layout.load_state().status != "released":
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()

    if ledger_damage == "relabeled_origins_without_wal":
        state = layout.load_state()
        for stage in PipelineStage:
            path = layout.receipt_path(stage)
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["origin"] = "legacy_adoption"
            receipt["upstream_receipts"] = [
                {
                    "stage": dependency.value,
                    "sha256": file_sha256(layout.receipt_path(dependency)),
                }
                for dependency in STAGE_SPECIFICATIONS[stage].upstream_stages
            ]
            artifact_io.atomic_write_json(path, receipt)
            next(
                item for item in state.stages if item.stage == stage.value
            ).receipt_sha256 = file_sha256(path)
        artifact_io.atomic_write_json(layout.state_path, state.to_dict())
        if layout.recovery_journal_path.exists():
            layout.recovery_journal_path.unlink()
    elif ledger_damage in {"v1_row", "nonrevision_v2_row", "mixed_v1_v2"}:
        rows = (
            _read_jsonl(layout.recovery_journal_path)
            if layout.recovery_journal_path.exists()
            else []
        )
        rows.append(
            {
                "schema_version": (
                    "fapo-recovery-journal-v1"
                    if ledger_damage != "nonrevision_v2_row"
                    else "fapo-recovery-journal-v2"
                ),
                "kind": "checkpoint_rebuild",
                "phase": "prepared",
                "operation_id": "f" * 32,
            }
        )
        artifact_io.atomic_write_jsonl(layout.recovery_journal_path, rows)
    elif ledger_damage == "audit_descriptor":
        rows = _read_jsonl(layout.recovery_journal_path)
        rows[0]["audit"]["events"]["target"]["sha256"] = "f" * 64
        artifact_io.atomic_write_jsonl(layout.recovery_journal_path, rows)
    else:
        history_rows = _read_jsonl(layout.config_history_path)
        artifact_io.atomic_write_text(
            layout.config_history_path,
            "".join(
                json.dumps(row, sort_keys=False, separators=(",", ":")) + "\n"
                for row in history_rows
            ),
        )
        receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["config_history_sha256"] = file_sha256(layout.config_history_path)
        artifact_io.atomic_write_json(receipt_path, receipt)
        state = layout.load_state()
        next(
            item
            for item in state.stages
            if item.stage == PipelineStage.DATASET_SPLITS.value
        ).receipt_sha256 = file_sha256(receipt_path)
        artifact_io.atomic_write_json(layout.state_path, state.to_dict())

    state = layout.load_state()
    before = _authority_bytes(layout)
    with pytest.raises(EvaluationAssetIntegrityError):
        if verification_boundary == "candidate":
            verify_release_candidate(layout, state)
        else:
            verify_released_asset(layout, state)
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("verification_boundary", ["candidate", "persisted"])
def test_standalone_adopted_verification_replays_legacy_semantics(
    tmp_path: Path,
    verification_boundary: str,
) -> None:
    """A matching WAL and rehashed receipts cannot bless invalid legacy bytes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    layout.adopt_legacy()
    candidate_path = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "candidate_guidelines.jsonl",
    )
    candidates = _read_jsonl(candidate_path)
    candidates.append(json.loads(json.dumps(candidates[0])))
    artifact_io.atomic_write_jsonl(candidate_path, candidates)
    _rehash_committed_adoption_authority(layout)
    state = layout.load_state()
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        if verification_boundary == "candidate":
            verify_release_candidate(layout, state)
        else:
            verify_released_asset(layout, state)

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "damage",
    ["missing_journal", "missing_all_prepares", "missing_commit"],
)
def test_native_terminal_candidate_requires_revision_journal_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    """Terminal verification rejects missing WAL evidence before release writes."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    pipeline.run()
    _make_released_checkpoint_mutable(pipeline.layout)
    resumed = EvaluationAssetPipeline(
        pipeline.layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    real_builder = pipeline_module.build_stage_receipt

    def damage_journal_after_final_receipt(
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        receipt = real_builder(*args, **kwargs)
        if args[1] == PipelineStage.DATASET_SPLITS:
            _damage_revision_journal(pipeline.layout, damage)
        return receipt

    before_verification: dict[str, dict[str, bytes]] = {}
    real_verify = pipeline_module.verify_completed_release_candidate

    def capture_candidate_authority(
        layout: EvaluationAssetLayout,
        candidate: PipelineState,
    ) -> Any:
        before_verification["authority"] = _authority_bytes(layout)
        return real_verify(layout, candidate)

    monkeypatch.setattr(
        pipeline_module,
        "build_stage_receipt",
        damage_journal_after_final_receipt,
    )
    monkeypatch.setattr(
        pipeline_module,
        "verify_completed_release_candidate",
        capture_candidate_authority,
    )

    with pytest.raises(EvaluationAssetIntegrityError):
        resumed.run(config_updates={"match_threshold": 0.2})

    assert pipeline.layout.load_state().status != "released"
    assert _authority_bytes(pipeline.layout) == before_verification["authority"]


def test_released_verification_requires_config_history_authority(
    tmp_path: Path,
) -> None:
    """Receipt config hashes must be backed by the persisted revision history."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    pipeline.layout.config_history_path.unlink()
    before = _authority_bytes(pipeline.layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(pipeline.layout, released)

    assert _authority_bytes(pipeline.layout) == before


@pytest.mark.parametrize("damage", ["missing", "malformed"])
def test_native_release_authenticates_history_before_persisting_released(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    """A run never reports release for a terminal candidate lacking audit evidence."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    real_builder = pipeline_module.build_stage_receipt

    def damage_history_after_final_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        receipt = real_builder(*args, **kwargs)
        stage = args[1]
        if stage == PipelineStage.DATASET_SPLITS:
            if damage == "missing":
                pipeline.layout.config_history_path.unlink()
            else:
                pipeline.layout.config_history_path.write_text(
                    "{not-json\n",
                    encoding="utf-8",
                )
        return receipt

    monkeypatch.setattr(
        pipeline_module,
        "build_stage_receipt",
        damage_history_after_final_receipt,
    )

    with pytest.raises(EvaluationAssetIntegrityError):
        pipeline.run()

    assert pipeline.layout.load_state().status != "released"


def test_native_release_verifies_the_persisted_terminal_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The successful return follows verification of exact persisted authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    persisted_statuses: list[str] = []
    real_verify = workspace_module.verify_released_asset

    def record_persisted_verification(
        layout: EvaluationAssetLayout,
        state: PipelineState,
    ) -> None:
        persisted_statuses.append(
            json.loads(layout.state_path.read_text(encoding="utf-8"))["status"]
        )
        real_verify(layout, state)

    monkeypatch.setattr(
        workspace_module,
        "verify_released_asset",
        record_persisted_verification,
    )

    released = pipeline.run()

    assert released.status == "released"
    assert persisted_statuses
    assert set(persisted_statuses) == {"released"}


@pytest.mark.parametrize(
    "corruption",
    [
        "created_timestamp",
        "created_timestamp_missing",
        "created_extra",
        "created_revision_bool",
        "created_configuration_extra",
        "updated_timestamp",
        "updated_timestamp_missing",
        "updated_extra",
        "updated_operation",
        "updated_operation_missing",
        "updated_invalidated_boundary",
        "updated_resume_boundary",
    ],
)
def test_released_verification_authenticates_exact_config_history_records(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Every created/updated audit field and exact row schema is release evidence."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    pipeline.run()
    _make_released_checkpoint_mutable(pipeline.layout)
    EvaluationAssetPipeline(
        pipeline.layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    ).run(config_updates={"match_threshold": 0.2})
    rows = _read_jsonl(pipeline.layout.config_history_path)
    if corruption == "created_timestamp":
        rows[0]["timestamp"] = "2026-08-19T00:00:00+00:00"
    elif corruption == "created_timestamp_missing":
        rows[0].pop("timestamp")
    elif corruption == "created_extra":
        rows[0]["untrusted_extra"] = "value"
    elif corruption == "created_revision_bool":
        rows[0]["revision"] = True
    elif corruption == "created_configuration_extra":
        rows[0]["configuration"]["untrusted_extra"] = "value"
    elif corruption == "updated_timestamp":
        rows[1]["timestamp"] = "2026-08-19T00:00:00+00:00"
    elif corruption == "updated_timestamp_missing":
        rows[1].pop("timestamp")
    elif corruption == "updated_extra":
        rows[1]["untrusted_extra"] = "value"
    elif corruption == "updated_operation":
        rows[1]["operation_id"] = "f" * 32
    elif corruption == "updated_operation_missing":
        rows[1].pop("operation_id")
    elif corruption == "updated_invalidated_boundary":
        rows[1]["invalidated_from_stage"] = PipelineStage.LABEL_INFERENCE.value
    elif corruption == "updated_resume_boundary":
        rows[1]["resume_from_stage"] = PipelineStage.LABEL_INFERENCE.value
    else:
        raise AssertionError(corruption)
    artifact_io.atomic_write_jsonl(pipeline.layout.config_history_path, rows)
    before = _authority_bytes(pipeline.layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(pipeline.layout, pipeline.layout.load_state())

    assert _authority_bytes(pipeline.layout) == before


@pytest.mark.parametrize(
    "corruption",
    ["parent_asset", "missing_parent_asset", "extra_field"],
)
def test_released_verification_authenticates_exact_inherited_history_record(
    tmp_path: Path,
    corruption: str,
) -> None:
    """An extension release binds every inherited-origin history field."""
    parent, _, _ = _create_pipeline(tmp_path)
    parent.run()
    child = EvaluationAssetLayout(
        parent.layout.tenants_root,
        parent.layout.tenant_id,
        "v2",
    )
    child.initialize_extension(
        parent.layout,
        additional_feedback=_write_additional_feedback(parent.layout.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    released = EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()
    rows = _read_jsonl(child.config_history_path)
    if corruption == "parent_asset":
        rows[0]["parent_asset_id"] = "different-parent"
    elif corruption == "missing_parent_asset":
        rows[0].pop("parent_asset_id")
    else:
        rows[0]["untrusted_extra"] = "value"
    artifact_io.atomic_write_jsonl(child.config_history_path, rows)
    before = _authority_bytes(child)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(child, released)

    assert _authority_bytes(child) == before


def test_legacy_adoption_authenticates_terminal_history_before_wal(
    tmp_path: Path,
) -> None:
    """Invalid terminal audit evidence cannot prepare adoption authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    rows = _read_jsonl(layout.config_history_path)
    rows[0]["untrusted_extra"] = "value"
    artifact_io.atomic_write_jsonl(layout.config_history_path, rows)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


@pytest.mark.parametrize(
    "corruption",
    [
        "schema",
        "empty_operation",
        "phase",
        "kind",
        "before_config_hash",
        "before_state_hash",
        "target_config_hash",
        "target_state_hash",
        "state_tenant",
        "state_asset",
        "state_operation",
        "config_tenant",
        "config_asset",
        "history_operation",
        "event_tenant",
        "invalidated_order",
        "result_boundary",
        "duplicate_prepared",
        "orphan_committed",
    ],
)
def test_recovery_journal_corruption_fails_closed_before_any_roll_forward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    """Every WAL schema, identity, and hash field is authenticated before writes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    rows = _read_jsonl(layout.recovery_journal_path)
    prepared = rows[0]
    prepared.setdefault(
        "target",
        {
            "config_sha256": durability_module.persisted_json_sha256(
                prepared["target_config"]
            ),
            "state_sha256": durability_module.persisted_json_sha256(
                prepared["target_state"]
            ),
        },
    )
    if corruption == "schema":
        prepared["schema_version"] = "unknown"
    elif corruption == "empty_operation":
        prepared["operation_id"] = ""
    elif corruption == "phase":
        prepared["phase"] = "unknown"
    elif corruption == "kind":
        prepared["kind"] = "unknown"
    elif corruption == "before_config_hash":
        prepared["before"]["config_sha256"] = "0" * 64
    elif corruption == "before_state_hash":
        prepared["before"]["state_sha256"] = "0" * 64
    elif corruption == "target_config_hash":
        prepared["target"]["config_sha256"] = "0" * 64
    elif corruption == "target_state_hash":
        prepared["target"]["state_sha256"] = "0" * 64
    elif corruption == "state_tenant":
        prepared["target_state"]["tenant_id"] = "other_tenant"
    elif corruption == "state_asset":
        prepared["target_state"]["asset_id"] = "other_asset"
    elif corruption == "state_operation":
        prepared["target_state"]["last_operation_id"] = "other-operation"
    elif corruption == "config_tenant":
        prepared["target_config"]["tenant_id"] = "other_tenant"
    elif corruption == "config_asset":
        prepared["target_config"]["asset_id"] = "other_asset"
    elif corruption == "history_operation":
        prepared["history_entry"]["operation_id"] = "other-operation"
    elif corruption == "event_tenant":
        prepared["event_entry"]["tenant_id"] = "other_tenant"
    elif corruption == "invalidated_order":
        prepared["invalidated_stages"].reverse()
    elif corruption == "result_boundary":
        prepared["result"]["invalidated_from_stage"] = "raw_inputs"
    elif corruption == "duplicate_prepared":
        rows.append(dict(prepared))
    elif corruption == "orphan_committed":
        rows = [
            {
                "schema_version": "fapo-recovery-journal-v1",
                "operation_id": prepared["operation_id"],
                "kind": prepared["kind"],
                "phase": "committed",
                "committed_at": "2026-08-19T00:00:00+00:00",
            }
        ]
    else:
        raise AssertionError(corruption)
    if corruption not in {"duplicate_prepared", "orphan_committed"}:
        rows[0] = prepared
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, rows)
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "corruption",
    [
        "unknown_current_stage",
        "duplicate_stage",
        "unknown_stage",
        "impossible_prefix",
        "invalid_prefix_status",
        "invalidated_message",
        "invalidated_started_at",
        "history_extra",
        "result_extra",
        "changed_field_previous",
        "changed_field_unchanged",
        "dependency_boundary",
        "event_extra",
    ],
)
def test_rehashed_revision_journal_semantic_corruption_fails_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    """Rehashing cannot turn an operation-impossible revision into authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    rows = _read_jsonl(layout.recovery_journal_path)
    prepared = rows[0]
    target_state = prepared["target_state"]
    history = prepared["history_entry"]
    result = prepared["result"]
    event_details = prepared["event_entry"]["details"]
    if corruption == "unknown_current_stage":
        for payload in (history, result, event_details):
            payload["resume_from_stage"] = "not_a_stage"
        target_state["current_stage"] = "not_a_stage"
    elif corruption == "duplicate_stage":
        target_state["stages"].append(dict(target_state["stages"][0]))
    elif corruption == "unknown_stage":
        target_state["stages"].append(
            {
                "stage": "not_a_stage",
                "label": "Unknown stage",
                "status": "pending",
                "message": "",
                "started_at": None,
                "completed_at": None,
                "receipt_sha256": None,
            }
        )
    elif corruption == "impossible_prefix":
        target_state["stages"][0].update(
            {
                "status": "pending",
                "message": "",
                "started_at": None,
                "completed_at": None,
                "receipt_sha256": None,
            }
        )
    elif corruption == "invalid_prefix_status":
        target_state["stages"][0]["status"] = "not_a_status"
    elif corruption == "invalidated_message":
        target_state["stages"][4]["message"] = "stale authority"
    elif corruption == "invalidated_started_at":
        target_state["stages"][4]["started_at"] = target_state["updated_at"]
    elif corruption == "history_extra":
        history["untrusted_extra"] = "value"
    elif corruption == "result_extra":
        result["untrusted_extra"] = "value"
    elif corruption == "changed_field_previous":
        for payload in (history, result, event_details):
            payload["changed_fields"]["match_threshold"]["previous"] = 0.123
    elif corruption == "changed_field_unchanged":
        unchanged = {"previous": 3, "new": 3}
        for payload in (history, result, event_details):
            payload["changed_fields"]["batch_size"] = unchanged
    elif corruption == "dependency_boundary":
        prior = json.loads(layout.state_path.read_text(encoding="utf-8"))
        target_state["stages"][4] = prior["stages"][4]
        target_state["current_stage"] = PipelineStage.LABEL_INFERENCE.value
        prepared["invalidated_stages"] = [
            stage.value
            for stage in list(PipelineStage)[
                list(PipelineStage).index(PipelineStage.LABEL_INFERENCE) :
            ]
        ]
        for payload in (history, result, event_details):
            payload["invalidated_from_stage"] = PipelineStage.LABEL_INFERENCE.value
            payload["resume_from_stage"] = PipelineStage.LABEL_INFERENCE.value
    elif corruption == "event_extra":
        prepared["event_entry"]["untrusted_extra"] = "value"
    else:
        raise AssertionError(corruption)
    prepared["target"]["state_sha256"] = durability_module.persisted_json_sha256(
        target_state
    )
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, [prepared])
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_revision_journal_rejects_impossible_state_before_config_intermediate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only before/before, target/before, and target/target control pairs exist."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    artifact_io.atomic_write_json(layout.state_path, prepared["target_state"])
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    ("failed_stage", "updates", "expected_resume"),
    [
        (
            PipelineStage.RUBRIC_EXTRACTION,
            {"match_threshold": 0.2},
            PipelineStage.RUBRIC_EXTRACTION,
        ),
        (
            PipelineStage.LABEL_INFERENCE,
            {"cluster_count": 2},
            PipelineStage.INTENT_CLUSTERING,
        ),
    ],
)
def test_revision_resume_is_earliest_of_existing_failure_and_dependency_boundary(
    tmp_path: Path,
    failed_stage: PipelineStage,
    updates: dict[str, Any],
    expected_resume: PipelineStage,
) -> None:
    """Revision resume always names the derived target's first incomplete stage."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    state = _failed_prefix_state(layout.load_state(), failed_stage)
    artifact_io.atomic_write_json(layout.state_path, state.to_dict())

    result = layout.revise_config(updates)

    revised = layout.load_state()
    assert result["resume_from_stage"] == expected_resume.value
    assert revised.current_stage == expected_resume.value
    assert next(
        item for item in revised.stages if item.stage == expected_resume.value
    ).status != "completed"


@pytest.mark.parametrize("phase", ["prepared", "state_installed"])
@pytest.mark.parametrize(
    "corruption",
    [
        "outside_suffix_message",
        "outside_count_change",
        "created_at_change",
        "mutation_sequence_jump",
    ],
)
def test_rehashed_revision_target_must_be_exactly_derived_from_before_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    corruption: str,
) -> None:
    """An authenticated before snapshot proves the target after every crash phase."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    fault_name = (
        "after_prepared_journal"
        if phase == "prepared"
        else "after_state_replace"
    )

    def stop_at_phase(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_at_phase)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    target = prepared["target_state"]
    if corruption == "outside_suffix_message":
        target["stages"][0]["message"] = "substituted completed message"
    elif corruption == "outside_count_change":
        target["counts"]["feedback_records"] += 1
    elif corruption == "created_at_change":
        target["created_at"] = target["updated_at"]
    elif corruption == "mutation_sequence_jump":
        target["mutation_sequence"] += 1
    else:
        raise AssertionError(corruption)
    prepared["target"]["state_sha256"] = durability_module.persisted_json_sha256(
        target
    )
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, [prepared])
    if phase == "state_installed":
        artifact_io.atomic_write_json(layout.state_path, target)
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_recovery_journal_rejects_interleaved_committed_operations(
    tmp_path: Path,
) -> None:
    """The global ledger grammar is contiguous prepare then matching commit."""
    layout = _release_with_config_revisions(tmp_path, revision_count=2)
    rows = _read_jsonl(layout.recovery_journal_path)
    prepares = [row for row in rows if row["phase"] == "prepared"]
    commits = [row for row in rows if row["phase"] == "committed"]
    artifact_io.atomic_write_jsonl(
        layout.recovery_journal_path,
        [prepares[0], prepares[1], commits[0], commits[1]],
    )
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_recovery_journal_rejects_cross_kind_interleaving(
    tmp_path: Path,
) -> None:
    """The one-active-operation grammar applies across every journal kind."""
    layout = _release_with_config_revisions(tmp_path, revision_count=2)
    rows = _read_jsonl(layout.recovery_journal_path)
    rows[2]["kind"] = "checkpoint_rebuild"
    rows[3]["kind"] = "checkpoint_rebuild"
    artifact_io.atomic_write_jsonl(
        layout.recovery_journal_path,
        [rows[0], rows[2], rows[1], rows[3]],
    )
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_recovery_journal_rejects_swapped_complete_revision_pairs(
    tmp_path: Path,
) -> None:
    """Locally complete revision pairs remain chained in writer chronology."""
    layout = _release_with_config_revisions(tmp_path, revision_count=2)
    rows = _read_jsonl(layout.recovery_journal_path)
    first_pair = rows[:2]
    second_pair = rows[2:4]
    artifact_io.atomic_write_jsonl(
        layout.recovery_journal_path,
        [*second_pair, *first_pair],
    )
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_ordered_complete_revision_pairs_remain_exact_recovery_noop(
    tmp_path: Path,
) -> None:
    """Writer-ordered committed revisions remain a stable terminal ledger."""
    layout = _release_with_config_revisions(tmp_path, revision_count=2)
    prepared = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["phase"] == "prepared"
    ]
    assert (
        prepared[0]["audit"]["events"]["target"]["row_count"]
        < prepared[1]["audit"]["events"]["before"]["row_count"]
    )
    before = _authority_bytes(layout)

    assert layout.recover() == []
    verify_released_asset(layout, layout.load_state())
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "operation_kind",
    ["configuration_revision", "checkpoint_rebuild"],
)
@pytest.mark.parametrize(
    "damage",
    ["config_tamper", "unjournaled_history_suffix"],
)
def test_final_committed_mutation_recovery_rejects_unjournaled_config_authority(
    tmp_path: Path,
    operation_kind: str,
    damage: str,
) -> None:
    """Final revision/rebuild recovery binds exact config and history authority."""
    layout = _layout_after_final_committed_mutation(
        tmp_path,
        operation_kind=operation_kind,
        lifecycle="released",
    )
    if damage == "config_tamper":
        config = json.loads(layout.config_path.read_text(encoding="utf-8"))
        config["batch_size"] += 1
        artifact_io.atomic_write_json(layout.config_path, config)
    else:
        history = _read_jsonl(layout.config_history_path)
        extra = json.loads(json.dumps(history[-1]))
        extra["operation_id"] = "f" * 32
        extra["revision"] = len(history) + 1
        history.append(extra)
        artifact_io.atomic_write_jsonl(layout.config_history_path, history)
        receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["config_history_sha256"] = file_sha256(
            layout.config_history_path
        )
        artifact_io.atomic_write_json(receipt_path, receipt)
        state = layout.load_state()
        next(
            item
            for item in state.stages
            if item.stage == PipelineStage.DATASET_SPLITS.value
        ).receipt_sha256 = file_sha256(receipt_path)
        artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "operation_kind",
    ["configuration_revision", "checkpoint_rebuild"],
)
@pytest.mark.parametrize("lifecycle", ["running", "failed", "released"])
def test_final_committed_mutation_recovery_allows_pipeline_advancement(
    tmp_path: Path,
    operation_kind: str,
    lifecycle: str,
) -> None:
    """Current state and ordinary events may advance after mutation commit."""
    layout = _layout_after_final_committed_mutation(
        tmp_path,
        operation_kind=operation_kind,
        lifecycle=lifecycle,
    )
    prepared = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["phase"] == "prepared" and row["kind"] == operation_kind
    ][-1]
    assert (
        prepared["audit"]["events"]["target"]["row_count"]
        < len(_read_jsonl(layout.events_path))
    )
    assert layout.load_state().status == lifecycle
    before = _authority_bytes(layout)

    assert layout.recover() == []
    assert layout.recover() == []
    assert _authority_bytes(layout) == before


def test_committed_revision_prefix_with_outstanding_prepare_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A final outstanding prepare governs current controls after a valid prefix."""
    layout = _release_with_config_revisions(tmp_path, revision_count=1)
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"split_seed": 73})
    prepared = _read_jsonl(layout.recovery_journal_path)[-1]
    assert prepared["phase"] == "prepared"
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    assert layout.recover() == [prepared["operation_id"]]
    after = _authority_bytes(layout)
    assert layout.recover() == []
    assert _authority_bytes(layout) == after


def test_recovery_rejects_reordered_committed_prefix_before_outstanding_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An outstanding operation cannot hide a reordered committed prefix."""
    layout = _release_with_config_revisions(tmp_path, revision_count=2)
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"synthetic_coverage_enabled": True})
    rows = _read_jsonl(layout.recovery_journal_path)
    artifact_io.atomic_write_jsonl(
        layout.recovery_journal_path,
        [*rows[2:4], *rows[:2], rows[4]],
    )
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_recovery_rejects_committed_adoption_reverted_to_before_state(
    tmp_path: Path,
) -> None:
    """A committed terminal adoption requires its exact released controls."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    layout.adopt_legacy()
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    artifact_io.atomic_write_json(layout.state_path, prepared["before_state"])
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_committed_adoption_terminal_recovery_is_exact_and_idempotent(
    tmp_path: Path,
) -> None:
    """The exact committed adoption terminal remains a stable no-op on recovery."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    adopted = layout.adopt_legacy()
    before = _authority_bytes(layout)

    assert adopted.status == "released"
    assert layout.recover() == []
    assert layout.recover() == []
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    ("fault_name", "audit_name"),
    [
        ("after_prepared_journal", "config_history"),
        ("after_prepared_journal", "events"),
        ("after_history_append", "config_history"),
        ("after_event_append", "events"),
    ],
)
def test_recovery_authenticates_complete_prior_audit_prefixes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
    audit_name: str,
) -> None:
    """Recovery rejects a rewritten append-only prefix at every audit phase."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)

    def stop_at_phase(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_at_phase)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    audit_path = (
        layout.config_history_path
        if audit_name == "config_history"
        else layout.events_path
    )
    rows = _read_jsonl(audit_path)
    rows[0]["timestamp"] = "2026-01-01T00:00:00+00:00"
    artifact_io.atomic_write_jsonl(audit_path, rows)
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("corruption", ["blank_row", "duplicate_key"])
def test_recovery_journal_requires_strict_jsonl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    """Blank rows and duplicate JSON keys never enter durable authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    raw = layout.recovery_journal_path.read_text(encoding="utf-8")
    if corruption == "blank_row":
        raw = "\n" + raw
    else:
        raw = raw.replace(
            '"phase": "prepared"',
            '"phase": "prepared", "phase": "prepared"',
            1,
        )
    artifact_io.atomic_write_text(layout.recovery_journal_path, raw)
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("journal_form", ["unfinished_v1", "mixed_v1_v2"])
def test_recovery_journal_v1_authority_requires_explicit_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    journal_form: str,
) -> None:
    """Runtime recovery never infers missing v2 before-state evidence."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    rows = _read_jsonl(layout.recovery_journal_path)
    rows[0]["schema_version"] = "fapo-recovery-journal-v1"
    if journal_form == "mixed_v1_v2":
        rows.append(
            {
                "schema_version": "fapo-recovery-journal-v2",
                "operation_id": rows[0]["operation_id"],
                "kind": rows[0]["kind"],
                "phase": "committed",
                "committed_at": rows[0]["prepared_at"],
            }
        )
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, rows)
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("installed_count", range(9))
def test_adoption_recovery_accepts_every_receipt_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    installed_count: int,
) -> None:
    """Crash recovery accepts exactly Stage 1 through Stage k intermediates."""
    layout, prepared = _prepared_adoption(tmp_path, monkeypatch)
    _install_adoption_target_manifests(layout, prepared)
    for stage in list(PipelineStage)[:installed_count]:
        artifact_io.atomic_write_json(
            layout.receipt_path(stage),
            prepared["target_receipts"][stage.value],
        )
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    recovered = layout.recover()

    assert recovered == [prepared["operation_id"]]
    assert layout.load_state().status == "released"


@pytest.mark.parametrize(
    "installed_stages",
    [
        [PipelineStage.DATASET_SPLITS],
        [PipelineStage.PREPARED_INPUTS, PipelineStage.RUBRIC_EXTRACTION],
        [PipelineStage.RAW_INPUTS, PipelineStage.RUBRIC_EXTRACTION],
    ],
)
def test_adoption_recovery_rejects_nonprefix_receipt_intermediates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    installed_stages: list[PipelineStage],
) -> None:
    """Middle, suffix, and gapped adoption receipt sets are never authoritative."""
    layout, prepared = _prepared_adoption(tmp_path, monkeypatch)
    _install_adoption_target_manifests(layout, prepared)
    for stage in installed_stages:
        artifact_io.atomic_write_json(
            layout.receipt_path(stage),
            prepared["target_receipts"][stage.value],
        )
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_recovery_journal_rejects_commit_that_precedes_its_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching commit is authoritative only after its prepare record."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    committed = {
        "schema_version": prepared["schema_version"],
        "operation_id": prepared["operation_id"],
        "kind": prepared["kind"],
        "phase": "committed",
        "committed_at": prepared["prepared_at"],
    }
    artifact_io.atomic_write_jsonl(
        layout.recovery_journal_path,
        [committed, prepared],
    )
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("corruption", ["unknown_current_stage", "stale_suffix"])
def test_rehashed_checkpoint_journal_semantics_fail_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    """Checkpoint recovery authenticates its exact resumable target state."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    target = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )
    target.write_bytes(target.read_bytes() + b" \n")

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    if corruption == "unknown_current_stage":
        prepared["target_state"]["current_stage"] = "not_a_stage"
        prepared["result"]["resume_from_stage"] = "not_a_stage"
    else:
        prepared["target_state"]["stages"][4]["completed_at"] = prepared[
            "prepared_at"
        ]
    prepared["target"]["state_sha256"] = durability_module.persisted_json_sha256(
        prepared["target_state"]
    )
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, [prepared])
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "corruption",
    [
        "stage_status",
        "stage_order",
        "negative_count",
        "receipt_schema",
        "receipt_output_hash",
        "receipt_upstream",
    ],
)
def test_rehashed_adoption_journal_semantics_fail_before_receipt_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    """Adoption WAL validates terminal authority before installing receipts."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.adopt_legacy()
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    if corruption == "stage_status":
        prepared["target_state"]["stages"][0]["status"] = "pending"
    elif corruption == "stage_order":
        prepared["target_state"]["stages"][0:2] = reversed(
            prepared["target_state"]["stages"][0:2]
        )
    elif corruption == "negative_count":
        prepared["target_state"]["counts"]["dataset_cases"] = -1
    else:
        stage = (
            PipelineStage.RAW_INPUTS
            if corruption != "receipt_upstream"
            else PipelineStage.PREPARED_INPUTS
        )
        receipt = prepared["target_receipts"][stage.value]
        if corruption == "receipt_schema":
            receipt["schema_version"] = "not-a-receipt-schema"
        elif corruption == "receipt_output_hash":
            receipt["outputs"][0]["sha256"] = "0" * 64
        else:
            receipt["upstream_receipts"] = []
        receipt_sha256 = durability_module.persisted_json_sha256(receipt)
        prepared["target"]["receipt_sha256"][stage.value] = receipt_sha256
        next(
            item
            for item in prepared["target_state"]["stages"]
            if item["stage"] == stage.value
        )["receipt_sha256"] = receipt_sha256
    prepared["target"]["state_sha256"] = durability_module.persisted_json_sha256(
        prepared["target_state"]
    )
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, [prepared])
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_outstanding_adoption_semantic_failure_is_integrity_and_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery translates deep adoption replay failure before roll-forward."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.adopt_legacy()
    candidate_path = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "candidate_guidelines.jsonl",
    )
    candidates = _read_jsonl(candidate_path)
    candidates.append(json.loads(json.dumps(candidates[0])))
    artifact_io.atomic_write_jsonl(candidate_path, candidates)
    _rehash_prepared_adoption_authority(layout)
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before
    assert not any(layout.receipts_root.glob("*.json"))


def test_missing_raw_snapshot_is_not_rebuildable(tmp_path: Path) -> None:
    """Mutable recovery never fabricates a missing immutable raw snapshot."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    layout.feedback_path.unlink()
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="raw input snapshot"):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_NeverCalledRubricProvider(),
            embedding_provider=_NeverCalledEmbeddingProvider(),
        ).run()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "fault_name",
    [
        "after_prepared_journal",
        "after_config_replace",
        "after_state_replace",
        "after_history_append",
        "after_event_append",
        "before_cleanup",
    ],
)
def test_revision_recovery_rolls_forward_after_each_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Every interrupted revision recovers one target state and one audit row."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = _make_released_checkpoint_mutable(layout)
    prefix_receipts = {
        stage: layout.receipt_path(stage).read_bytes()
        for stage in list(PipelineStage)[:4]
    }
    stale_stage_five = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )

    def inject_fault(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault, match=fault_name):
        layout.revise_config({"match_threshold": 0.2})

    journal_after_fault = _read_jsonl(layout.recovery_journal_path)
    prepared = [row for row in journal_after_fault if row["phase"] == "prepared"]
    assert len(prepared) == 1
    operation_id = prepared[0]["operation_id"]
    if fault_name == "before_cleanup":
        interrupted_state = layout.load_state()
        assert interrupted_state.stages[4].status == "pending"
        assert interrupted_state.stages[4].receipt_sha256 is None
        assert stale_stage_five.is_file()

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    recovered = layout.recover()

    assert recovered == [operation_id]
    assert layout.load_config().match_threshold == 0.2
    recovered_state = layout.load_state()
    assert recovered_state.status == "queued"
    assert recovered_state.current_stage == PipelineStage.COVERAGE_DECISIONS.value
    assert recovered_state.mutation_sequence == state.mutation_sequence + 1
    assert recovered_state.last_operation_id == operation_id
    assert [item.status for item in recovered_state.stages[:4]] == [
        "completed"
    ] * 4
    assert [item.status for item in recovered_state.stages[4:]] == ["pending"] * 4
    assert all(
        layout.receipt_path(stage).read_bytes() == receipt_bytes
        for stage, receipt_bytes in prefix_receipts.items()
    )
    assert not stale_stage_five.exists()
    history = [
        row
        for row in _read_jsonl(layout.config_history_path)
        if row.get("operation_id") == operation_id
    ]
    events = [
        row
        for row in _read_jsonl(layout.events_path)
        if row.get("operation_id") == operation_id
    ]
    assert len(history) == 1
    assert len(events) == 1
    phases = [
        row["phase"]
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["operation_id"] == operation_id
    ]
    assert phases == ["prepared", "committed"]


def test_revision_prepares_journal_before_changing_control_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The prepared WAL record is durable while prior control bytes remain exact."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    before = {
        path.name: path.read_bytes()
        for path in (
            layout.config_path,
            layout.state_path,
            layout.config_history_path,
            layout.events_path,
        )
    }

    def inject_fault(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})

    assert {
        path.name: path.read_bytes()
        for path in (
            layout.config_path,
            layout.state_path,
            layout.config_history_path,
            layout.events_path,
        )
    } == before
    journal = _read_jsonl(layout.recovery_journal_path)
    assert len(journal) == 1
    assert journal[0]["kind"] == "configuration_revision"
    assert journal[0]["phase"] == "prepared"


@pytest.mark.parametrize(
    "fault_name",
    [
        "after_prepared_journal",
        "after_state_replace",
        "after_event_append",
        "before_cleanup",
    ],
)
def test_checkpoint_rebuild_recovery_marks_stale_suffix_nonauthoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Interrupted receipt repair rolls forward before a resumed stage runs."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    target = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )
    target.write_bytes(target.read_bytes() + b" \n")
    prior_state = layout.state_path.read_bytes()

    def inject_fault(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault, match=fault_name):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()

    journal = _read_jsonl(layout.recovery_journal_path)
    prepared = [
        row
        for row in journal
        if row.get("kind") == "checkpoint_rebuild" and row["phase"] == "prepared"
    ]
    assert len(prepared) == 1
    operation_id = prepared[0]["operation_id"]
    if fault_name == "after_prepared_journal":
        assert layout.state_path.read_bytes() == prior_state
    else:
        interrupted = layout.load_state()
        assert interrupted.status == "queued"
        assert interrupted.stages[4].status == "pending"
        assert interrupted.stages[4].receipt_sha256 is None
    if fault_name == "before_cleanup":
        assert target.is_file()

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    assert resumed.status == "released"
    phases = [
        row["phase"]
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["operation_id"] == operation_id
    ]
    assert phases == ["prepared", "committed"]
    rebuild_events = [
        row
        for row in _read_jsonl(layout.events_path)
        if row.get("operation_id") == operation_id
    ]
    assert len(rebuild_events) == 1
    assert rebuild_events[0]["event"] == "checkpoint_rebuild_started"


def test_legacy_adoption_builds_honest_receipts_then_releases(tmp_path: Path) -> None:
    """Explicit adoption converts only a fully validated legacy completion."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    adopted = layout.adopt_legacy()

    assert adopted.status == "released"
    assert adopted.schema_version == STATE_SCHEMA_VERSION
    assert adopted.current_stage is None
    unavailable_hash = canonical_sha256(LEGACY_UNAVAILABLE_PROVENANCE)
    for stage in PipelineStage:
        stage_state = next(item for item in adopted.stages if item.stage == stage.value)
        receipt_path = layout.receipt_path(stage)
        assert stage_state.receipt_sha256 == file_sha256(receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["origin"] == "legacy_adoption"
        assert receipt["code"] == LEGACY_UNAVAILABLE_PROVENANCE
        assert receipt["code_sha256"] == unavailable_hash
        assert receipt["provider_calls_sha256"] == unavailable_hash
    verify_released_asset(layout, adopted)
    adoption_rows = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row.get("kind") == "legacy_adoption"
    ]
    assert [row["phase"] for row in adoption_rows] == ["prepared", "committed"]


def test_legacy_adoption_accepts_declared_rubric_compatibility_profile(
    tmp_path: Path,
) -> None:
    """Pre-guideline artifacts are adopted without inventing native provenance."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _convert_to_legacy_rubric_profile(layout)
    _downgrade_to_legacy_completed(layout)

    adopted = layout.adopt_legacy()

    stage_three = json.loads(
        layout.receipt_path(PipelineStage.RUBRIC_EXTRACTION).read_text(
            encoding="utf-8"
        )
    )
    stage_six = json.loads(
        layout.receipt_path(PipelineStage.LABEL_INFERENCE).read_text(
            encoding="utf-8"
        )
    )
    assert adopted.status == "released"
    assert stage_three["artifact_profile"] == "legacy"
    assert stage_six["artifact_profile"] == "legacy"
    assert any(
        item["path"].endswith("feedback_rubrics.jsonl")
        for item in stage_three["outputs"]
    )
    verify_released_asset(layout, adopted)


@pytest.mark.parametrize(
    "corruption",
    [
        "prepared_identity",
        "duplicate_intent_record",
        "evidence_source",
        "guideline_source",
        "trusted_intent_link",
        "trusted_case_shape",
        "cluster_shape",
        "cluster_partition",
        "match_cluster",
        "match_score",
        "queue_member",
        "inferred_label_ref",
        "inferred_case_ref",
        "synthetic_case_trust",
        "synthetic_filter_partition",
        "split_component",
        "split_group_leakage",
        "combined_mismatch",
        "regression_untrusted",
        "regression_duplicate",
    ],
)
def test_legacy_adoption_rejects_parseable_semantic_corruption_without_writes(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Parseable stage and cross-artifact corruption never becomes authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    _apply_semantic_corruption(layout, corruption)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


@pytest.mark.parametrize(
    ("profile", "corruption"),
    [
        ("native", "native_evidence_confidence_nan"),
        ("native", "native_evidence_confidence_positive_infinity"),
        ("native", "native_evidence_confidence_negative_infinity"),
        ("native", "native_evidence_confidence_bool"),
        ("native", "native_evidence_confidence_out_of_domain"),
        ("native", "native_evidence_observations_object"),
        ("native", "native_candidate_confidence_bool"),
        ("native", "native_guideline_support_bool"),
        ("native", "native_criterion_evidence_required_integer"),
        ("native", "native_duplicate_evidence"),
        ("native", "native_candidate_kind_unknown"),
        ("native", "native_candidate_severity_unknown"),
        ("native", "native_candidate_evaluator_unknown"),
        ("native", "native_candidate_statement_mismatch"),
        ("native", "native_evidence_provider_mismatch"),
        ("native", "native_compiled_kind_unknown"),
        ("native", "native_compiled_policy_mismatch"),
        ("native", "native_candidate_missing_scoring"),
        ("native", "native_candidate_extra_field"),
        ("native", "native_candidate_evaluator_extra_field"),
        ("native", "native_candidate_applicability_empty"),
        ("native", "native_candidate_applicability_wrong_type"),
        ("native", "native_candidate_tool_expectations_wrong_type"),
        ("native", "native_compiled_extra_field"),
        ("legacy", "legacy_rubric_confidence_nan"),
        ("legacy", "legacy_rubric_confidence_positive_infinity"),
        ("legacy", "legacy_rubric_confidence_negative_infinity"),
        ("legacy", "legacy_rubric_confidence_bool"),
        ("legacy", "legacy_rubric_nested_nonfinite"),
        ("legacy", "legacy_duplicate_rubric"),
        ("legacy", "legacy_rubric_empty_check"),
        ("legacy", "legacy_expected_empty_check"),
        ("legacy", "legacy_rubric_scoreable_mismatch"),
        ("legacy", "legacy_trusted_intent_text_mismatch"),
        ("legacy", "legacy_rubric_extra_field"),
        ("legacy", "legacy_rubric_missing_field"),
        ("legacy", "legacy_rubric_tool_expectations_wrong_type"),
        ("legacy", "legacy_rubric_check_wrong_type"),
    ],
)
def test_legacy_adoption_rejects_strict_stage_three_schema_corruption(
    tmp_path: Path,
    profile: str,
    corruption: str,
) -> None:
    """Native and compatibility rows reject non-JSON and coerced field values."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    if profile == "legacy":
        _convert_to_legacy_rubric_profile(layout)
    _downgrade_to_legacy_completed(layout)
    _apply_semantic_corruption(layout, corruption)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", "mandatory"),
        ("severity", "fatal"),
        ("evaluator.type", "arbitrary_code"),
        ("evaluator.fallback", "silent_accept"),
    ],
)
def test_native_writer_rejects_unsupported_candidate_domains_before_persistence(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    """Live Stage 3 and adoption enforce the same declared criterion domains."""

    class InvalidGuidelineProvider(_SuccessfulRubricProvider):
        def generate_json(
            self,
            system_prompt: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            response = super().generate_json(system_prompt, payload)
            if "evidence" in payload:
                criterion = response["guidelines"][0]["criteria"][0]
                if field.startswith("evaluator."):
                    criterion["evaluator"][field.split(".", 1)[1]] = value
                else:
                    criterion[field] = value
            return response

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    provider = InvalidGuidelineProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider=provider.provider_name,
            rubric_model=provider.model,
            embedding_provider="fake",
            embedding_model="fake-embedding",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=provider,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )

    with pytest.raises(ProviderCallError, match="invalid response"):
        pipeline.run()

    assert not pipeline.layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "candidate_guidelines.jsonl",
    ).exists()


@pytest.mark.parametrize(
    "duplicate_shape",
    ["exact_candidate", "criterion_identity", "derived_id_collision"],
)
def test_native_writer_rejects_duplicate_stage_three_identities_before_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    duplicate_shape: str,
) -> None:
    """Ambiguous Stage 3 canonical identities fail before derivative authority."""

    class DuplicateIdentityProvider(_SuccessfulRubricProvider):
        def generate_json(
            self,
            system_prompt: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            response = super().generate_json(system_prompt, payload)
            if "evidence" not in payload:
                return response
            first = response["guidelines"][0]
            if duplicate_shape == "exact_candidate":
                response["guidelines"].append(json.loads(json.dumps(first)))
            elif duplicate_shape == "criterion_identity":
                duplicate = json.loads(json.dumps(first["criteria"][0]))
                duplicate["dimension"] = "colliding_secondary_dimension"
                first["criteria"].append(duplicate)
            else:
                second = json.loads(json.dumps(first))
                second["intent_label"] = "distinct candidate"
                second["description"] = "A distinct canonical candidate."
                second["criteria"][0]["statement"] = "A distinct criterion."
                response["guidelines"].append(second)
            return response

    if duplicate_shape == "derived_id_collision":
        class CollidingHashlib:
            @staticmethod
            def sha256(_: bytes) -> Any:
                return type("Digest", (), {"hexdigest": lambda self: "0" * 64})()

        monkeypatch.setattr(stage_three_contract, "hashlib", CollidingHashlib)

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    provider = DuplicateIdentityProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider=provider.provider_name,
            rubric_model=provider.model,
            embedding_provider="fake",
            embedding_model="fake-embedding",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=provider,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )

    with pytest.raises(ProviderCallError, match="invalid response"):
        pipeline.run()

    stage = PipelineStage.RUBRIC_EXTRACTION
    assert not any(
        pipeline.layout.artifact_path(stage, name).exists()
        for name in STAGE_SPECIFICATIONS[stage].required_outputs
    )
    assert not any(
        pipeline.layout.receipt_path(later).exists()
        for later in list(PipelineStage)[2:]
    )
    assert not pipeline.layout.manifest_path.exists()
    assert not pipeline.layout.published_datasets.exists()
    assert pipeline.layout.load_state().status != "released"


def test_legacy_adoption_rejects_duplicate_native_candidates_without_writes(
    tmp_path: Path,
) -> None:
    """Adoption applies the same exact-candidate uniqueness contract as live Stage 3."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    path = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "candidate_guidelines.jsonl",
    )
    candidates = _read_jsonl(path)
    candidates.append(json.loads(json.dumps(candidates[0])))
    artifact_io.atomic_write_jsonl(path, candidates)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


def test_native_stage_three_accepts_all_declared_domains_and_open_structures(
    tmp_path: Path,
) -> None:
    """Closed enums stay strict while scoring and structured contracts stay open."""

    class DomainMatrixProvider(_SuccessfulRubricProvider):
        def generate_json(
            self,
            system_prompt: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            response = super().generate_json(system_prompt, payload)
            if "evidence" in payload:
                kinds = ["required", "prohibited", "preferred"]
                severities = ["critical", "major", "minor"]
                evaluators = [
                    "state_check",
                    "deterministic_check",
                    "semantic_trajectory",
                    "llm_judge",
                    "human_review",
                ]
                response["guidelines"][0]["criteria"] = [
                    {
                        "kind": kinds[index % len(kinds)],
                        "statement": f"Criterion {index} must remain authentic.",
                        "dimension": "task_success",
                        "severity": severities[index % len(severities)],
                        "applicability": (
                            "always"
                            if index == 0
                            else {"route": payload["route"], "minimum": index}
                        ),
                        "scoring": f"tenant_scale_{index}",
                        "evidence_required": bool(index % 2),
                        "evaluator": {
                            "type": evaluator,
                            "fallback": evaluators[-index - 1],
                        },
                    }
                    for index, evaluator in enumerate(evaluators)
                ]
                response["guidelines"][0]["tool_expectations"] = {
                    "allowed_paths": ["primary", "fallback"],
                    "policy": {"mode": "tenant_defined"},
                }
            return response

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    provider = DomainMatrixProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider=provider.provider_name,
            rubric_model=provider.model,
            embedding_provider="fake",
            embedding_model="fake-embedding",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=provider,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    pipeline.run()
    _downgrade_to_legacy_completed(pipeline.layout)

    adopted = pipeline.layout.adopt_legacy()

    assert adopted.status == "released"
    verify_released_asset(pipeline.layout, adopted)


@pytest.mark.parametrize(
    "corruption",
    [
        "zero_candidates_with_accepted",
        "accepted_payload_differs_from_candidate",
        "accepted_order_differs_from_filter",
    ],
)
def test_legacy_adoption_rejects_nonreproducible_stage_seven_authority(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Accepted synthetic authority must exactly reproduce ordered filtering."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    first = _synthetic_case_fixture(
        layout,
        case_id="synthetic-first",
        user_input="Diagnose a novel lunar telemetry checksum divergence.",
    )
    second = _synthetic_case_fixture(
        layout,
        case_id="synthetic-second",
        user_input="Classify an unusual botanical spectral absorption anomaly.",
    )
    if corruption == "zero_candidates_with_accepted":
        candidates: list[dict[str, Any]] = []
        accepted = [first]
    elif corruption == "accepted_payload_differs_from_candidate":
        candidates = [first]
        accepted = json.loads(json.dumps(candidates))
        accepted[0]["context"]["messages_json"] = json.dumps(
            [{"role": "user", "content": "A substituted accepted payload."}]
        )
    else:
        candidates = [first, second]
        accepted = [second, first]
    _install_synthetic_fixture(
        layout,
        candidates=candidates,
        rejected=[],
        issues=[],
        accepted=accepted,
    )
    _downgrade_to_legacy_completed(layout)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


def test_legacy_adoption_accepts_exact_native_synthetic_filter_outputs(
    tmp_path: Path,
) -> None:
    """A genuine enabled Stage 7 output remains adoptable."""
    pipeline, provider = _create_synthetic_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    assert provider.synthetic_calls == 1
    assert len(
        _read_jsonl(
            layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_candidates.jsonl",
            )
        )
    ) == 1
    _downgrade_to_legacy_completed(layout)

    adopted = layout.adopt_legacy()

    assert adopted.status == "released"
    verify_released_asset(layout, adopted)


def test_legacy_adoption_reconstructs_exact_keep_mode_inherited_synthetic_output(
    tmp_path: Path,
) -> None:
    """Keep-mode adoption retains only the self-contained unchanged parent case."""
    pipeline, _ = _create_synthetic_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    provider = _SuccessfulSyntheticRubricProvider()
    EvaluationAssetPipeline(
        child,
        rubric_provider=provider,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()
    inherited = _read_jsonl(
        child.artifact_path(PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl")
    )
    assert provider.synthetic_calls == 0
    assert len(inherited) == 1
    assert inherited[0]["metadata"]["dataset_version"] == "v2"
    assert not _read_jsonl(
        child.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_candidates.jsonl",
        )
    )
    _downgrade_to_legacy_completed(child)

    adopted = child.adopt_legacy()

    assert adopted.status == "released"
    verify_released_asset(child, adopted)


@pytest.mark.parametrize("layout_kind", ["old_staged", "pre_stage_layout"])
def test_legacy_adoption_accepts_real_legacy_layout_alternatives(
    tmp_path: Path,
    layout_kind: str,
) -> None:
    """Compatibility validation follows actual historical directory layouts."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _convert_to_legacy_rubric_profile(layout)
    _downgrade_to_legacy_completed(layout)
    if layout_kind == "old_staged":
        layout.stage_directory(PipelineStage.RUBRIC_EXTRACTION).rename(
            layout.stages_root / "03_rubric_extraction"
        )
    else:
        _move_to_pre_stage_layout(layout)

    adopted = layout.adopt_legacy()

    assert adopted.status == "released"
    verify_released_asset(layout, adopted)


def test_pre_stage_legacy_adoption_rejects_external_provenance_symlink_without_writes(
    tmp_path: Path,
) -> None:
    """Historical provenance materialization cannot escape the asset root."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _convert_to_legacy_rubric_profile(layout)
    _downgrade_to_legacy_completed(layout)
    _move_to_pre_stage_layout(layout)
    outside = tmp_path / "outside-provenance"
    outside.mkdir()
    provenance_directory = layout.root / "stage_provenance"
    provenance_directory.symlink_to(outside, target_is_directory=True)
    before_asset = _tree_bytes(layout.root)
    before_outside = _tree_bytes(outside)

    with pytest.raises(EvaluationAssetLegacyError, match="verification"):
        layout.adopt_legacy()

    assert provenance_directory.is_symlink()
    assert _tree_bytes(layout.root) == before_asset
    assert _tree_bytes(outside) == before_outside == {}
    assert not layout.recovery_journal_path.exists()


@pytest.mark.parametrize("invalid_target", ["build_provenance", "stage_provenance"])
def test_pre_stage_legacy_adoption_preflights_every_provenance_target(
    tmp_path: Path,
    invalid_target: str,
) -> None:
    """A later invalid provenance target cannot leave earlier provenance writes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _convert_to_legacy_rubric_profile(layout)
    _downgrade_to_legacy_completed(layout)
    _move_to_pre_stage_layout(layout)
    if invalid_target == "build_provenance":
        layout.build_provenance_path.mkdir()
    else:
        final_target = layout.stage_provenance_path(PipelineStage.DATASET_SPLITS)
        final_target.parent.mkdir()
        final_target.mkdir()
    before = _tree_bytes(layout.root)

    with pytest.raises(EvaluationAssetLegacyError, match="verification"):
        layout.adopt_legacy()

    assert _tree_bytes(layout.root) == before
    assert not layout.recovery_journal_path.exists()


def test_pre_stage_legacy_adoption_rejects_external_receipt_symlink_without_writes(
    tmp_path: Path,
) -> None:
    """Adoption cannot install authoritative receipts through an external symlink."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _convert_to_legacy_rubric_profile(layout)
    _downgrade_to_legacy_completed(layout)
    _move_to_pre_stage_layout(layout)
    shutil.rmtree(layout.receipts_root)
    outside = tmp_path / "outside-receipts"
    outside.mkdir()
    layout.receipts_root.symlink_to(outside, target_is_directory=True)
    before_asset = _tree_bytes(layout.root)

    with pytest.raises(EvaluationAssetLegacyError, match="verification"):
        layout.adopt_legacy()

    assert layout.receipts_root.is_symlink()
    assert _tree_bytes(layout.root) == before_asset
    assert _tree_bytes(outside) == {}
    assert not layout.recovery_journal_path.exists()


def test_legacy_adoption_rejects_ambiguous_complete_stage_three_profiles(
    tmp_path: Path,
) -> None:
    """Canonical and historical Stage 3 trees cannot compete for authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    old_directory = layout.stages_root / "03_rubric_extraction"
    old_directory.mkdir()
    artifact_io.atomic_write_jsonl(
        old_directory / "feedback_rubrics.jsonl",
        [{"record_id": "feedback-1", "must": ["Answer the request."]}],
    )
    for name in ("trusted_intents.jsonl", "trusted_cases.jsonl"):
        artifact_io.atomic_copy_file(
            layout.artifact_path(PipelineStage.RUBRIC_EXTRACTION, name),
            old_directory / name,
        )
    _downgrade_to_legacy_completed(layout)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("manifest_name", ["input", "asset"])
def test_legacy_adoption_rejects_inconsistent_manifest_without_writes(
    tmp_path: Path,
    manifest_name: str,
) -> None:
    """Source and asset manifest claims must agree with the persisted files."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    if manifest_name == "input":
        path = layout.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["inputs"]["labeled_feedback"]["sha256"] = "0" * 64
    else:
        path = layout.manifest_path
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["asset_id"] = "wrong"
    workspace_module.atomic_write_json(path, manifest)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()


@pytest.mark.parametrize("stage", list(PipelineStage))
@pytest.mark.parametrize("mutation", ["missing", "corrupt"])
def test_legacy_adoption_rejects_invalid_required_artifact_without_authority_change(
    tmp_path: Path,
    stage: PipelineStage,
    mutation: str,
) -> None:
    """Every stage must validate before adoption writes receipts or a journal."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    if mutation == "missing":
        target.unlink()
    elif target.suffix == ".md":
        target.write_text("", encoding="utf-8")
    else:
        target.write_text("{not-json\n", encoding="utf-8")
    before = _authority_bytes(layout)

    with pytest.raises(
        EvaluationAssetLegacyError,
        match=r"Run assets adopt after repair, or create a new asset version",
    ):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


@pytest.mark.parametrize(
    "catalog_name",
    ["train.jsonl", "validation.jsonl", "test.jsonl", "regression_trusted.jsonl"],
)
def test_legacy_adoption_rejects_catalog_copy_mismatch_without_authority_change(
    tmp_path: Path,
    catalog_name: str,
) -> None:
    """The four current catalog copies must match the legacy Stage 8 outputs."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    catalog_path = layout.published_datasets / catalog_name
    catalog_path.write_bytes(catalog_path.read_bytes() + b" \n")
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


def test_legacy_adoption_recovers_installed_nonauthoritative_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery completes adoption without rerunning any pipeline stage."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def inject_fault(name: str) -> None:
        if name == "after_receipts_install":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault, match="after_receipts_install"):
        layout.adopt_legacy()

    assert layout.load_state().legacy_completed
    assert len(list(layout.receipts_root.glob("*.json"))) == len(PipelineStage)
    prepared = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row.get("kind") == "legacy_adoption" and row["phase"] == "prepared"
    ]
    assert len(prepared) == 1
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    assert layout.recover() == [prepared[0]["operation_id"]]
    adopted = layout.load_state()
    assert adopted.status == "released"
    verify_released_asset(layout, adopted)
    phases = [
        row["phase"]
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["operation_id"] == prepared[0]["operation_id"]
    ]
    assert phases == ["prepared", "committed"]


@pytest.mark.parametrize(
    "fault_name",
    [
        "after_generation_install",
        "after_prepared_journal",
        "after_adoption_asset_manifest_replace",
        "after_adoption_dataset_manifest_replace",
        "after_adoption_generation_manifest_replace",
        "after_receipts_install",
        "after_adoption_pointer_replace",
        "after_state_replace",
        "after_event_append",
    ],
)
def test_legacy_adoption_fault_phases_recover_as_one_terminal_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Pre-v2 adoption retries or recovers without chaining publication WAL."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def inject(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match=fault_name):
        layout.adopt_legacy()

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    if fault_name == "after_generation_install":
        assert layout.load_state().legacy_completed
        assert not layout.recovery_journal_path.exists()
        adopted = layout.adopt_legacy()
    else:
        prepared = [
            row
            for row in _read_jsonl(layout.recovery_journal_path)
            if row.get("kind") == "legacy_adoption"
            and row.get("phase") == "prepared"
        ]
        assert len(prepared) == 1
        assert layout.recover() == [prepared[0]["operation_id"]]
        adopted = layout.load_state()

    assert adopted.status == "released"
    verify_released_asset(layout, adopted)
    journal = _read_jsonl(layout.recovery_journal_path)
    assert [row["kind"] for row in journal] == [
        "legacy_adoption",
        "legacy_adoption",
    ]
    assert [row["phase"] for row in journal] == ["prepared", "committed"]
    assert adopted.last_operation_id == journal[0]["operation_id"]


def test_adoption_recovery_rejects_impossible_manifest_prefix_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dataset-manifest target cannot precede the asset-manifest target."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.adopt_legacy()
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    artifact_io.atomic_write_json(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "dataset_manifest.json",
        ),
        prepared["target_manifests"]["dataset_manifest"],
    )
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "unreachable_phase",
    ["receipt", "pointer", "state"],
)
def test_adoption_recovery_rejects_authority_before_manifests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unreachable_phase: str,
) -> None:
    """Receipts, pointer, and state cannot precede all adoption manifests."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.adopt_legacy()
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    stages = list(PipelineStage)
    install_count = 1 if unreachable_phase == "receipt" else len(stages)
    for stage in stages[:install_count]:
        artifact_io.atomic_write_json(
            layout.receipt_path(stage),
            prepared["target_receipts"][stage.value],
        )
    if unreachable_phase in {"pointer", "state"}:
        artifact_io.atomic_write_json(
            layout.release_pointer_path,
            prepared["request"]["release_pointer"],
        )
    if unreachable_phase == "state":
        artifact_io.atomic_write_json(layout.state_path, prepared["target_state"])
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


def test_adopted_legacy_catalog_copies_are_nonauthoritative(tmp_path: Path) -> None:
    """Historical top-level copies no longer influence an adopted release."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    adopted = layout.adopt_legacy()

    for split in ("train", "validation", "test", "regression_trusted"):
        top_level = layout.published_datasets / f"{split}.jsonl"
        top_level.write_text("nonauthoritative legacy bytes\n", encoding="utf-8")

    verify_released_asset(layout, adopted)


def test_relative_tenants_root_runs_and_adopts_with_repo_relative_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI-style default relative tenants root has one canonical base."""
    monkeypatch.chdir(tmp_path)
    tenants_root = Path("tenants")
    feedback, unlabeled = _write_input_pair(tenants_root)
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id="v1",
            rubric_provider="fake",
            rubric_model="fake-rubric",
            embedding_provider="fake",
            embedding_model="fake-embedding",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    released = pipeline.run()
    assert released.status == "released"
    _downgrade_to_legacy_completed(pipeline.layout)

    adopted = pipeline.layout.adopt_legacy()

    assert adopted.status == "released"
    assert pipeline.layout.tenants_root == (tmp_path / "tenants").resolve()
    verify_released_asset(pipeline.layout, adopted)


def test_service_adopt_is_a_thin_locked_core_api(tmp_path: Path) -> None:
    """Service callers use the same adoption transaction as library callers."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    response = EvaluationAssetRunManager(layout.tenants_root).adopt(
        layout.tenant_id,
        layout.asset_id,
    )

    assert response["status"] == "released"
    verify_released_asset(layout, layout.load_state())


@pytest.mark.parametrize(
    "damage",
    ["receipt", "source", "manifest", "catalog"],
)
def test_extension_rejects_corrupt_parent_before_child_creation(
    tmp_path: Path,
    damage: str,
) -> None:
    """A child root stays absent unless the released parent verifies fully."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    if damage == "receipt":
        target = parent.receipt_path(PipelineStage.DATASET_SPLITS)
    elif damage == "source":
        target = parent.feedback_path
    elif damage == "manifest":
        target = parent.manifest_path
    else:
        pointer = json.loads(parent.release_pointer_path.read_text(encoding="utf-8"))
        target = (
            parent.generations_root
            / pointer["generation_id"]
            / "train.jsonl"
        )
    target.write_bytes(target.read_bytes() + b" \n")
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    additional = _write_additional_feedback(parent.tenants_root)

    with pytest.raises(EvaluationAssetIntegrityError):
        child.initialize_extension(
            parent,
            additional_feedback=additional,
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()


def test_extension_points_legacy_parent_to_adoption_without_child_creation(
    tmp_path: Path,
) -> None:
    """Legacy completed is never accepted as a released parent alias."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    _downgrade_to_legacy_completed(parent)
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")

    with pytest.raises(EvaluationAssetLegacyError, match="Run assets adopt"):
        child.initialize_extension(
            parent,
            additional_feedback=_write_additional_feedback(parent.tenants_root),
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()


def test_extension_records_verified_parent_evidence_and_is_self_contained(
    tmp_path: Path,
) -> None:
    """Verified release/source identities are copied into a runnable child."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    parent_state = pipeline.run()
    parent = pipeline.layout
    expected_evidence = released_parent_evidence(parent, parent_state)
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")

    state = child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )

    assert state.status == "draft"
    assert all(stage.status == "pending" for stage in state.stages)
    lineage = json.loads(child.lineage_path.read_text(encoding="utf-8"))
    assert lineage["parent_release"] == expected_evidence
    assert json.loads(child.reuse_manifest_path.read_text(encoding="utf-8"))[
        "parent_release"
    ] == expected_evidence
    shutil.rmtree(parent.root)

    released = EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    assert released.status == "released"
    verify_released_asset(child, released)


def test_extension_receipts_anchor_lineage_and_every_parent_snapshot_input(
    tmp_path: Path,
) -> None:
    """Incremental receipts bind the self-contained parent evidence they consume."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    expected_snapshots = {
        PipelineStage.RUBRIC_EXTRACTION: {
            "parent_feedback_evidence.jsonl",
            "parent_candidate_guidelines.jsonl",
            "parent_evaluation_guidelines.jsonl",
            "parent_trusted_intents.jsonl",
            "parent_trusted_cases.jsonl",
        },
        PipelineStage.INTENT_CLUSTERING: {"parent_intent_inventory.jsonl"},
        PipelineStage.COVERAGE_DECISIONS: {"parent_intent_matches.jsonl"},
        PipelineStage.LABEL_INFERENCE: {
            "parent_intent_matches.jsonl",
            "parent_inferred_cluster_rubrics.jsonl",
        },
        PipelineStage.SYNTHETIC_COVERAGE: {
            "parent_intent_matches.jsonl",
            "parent_synthetic_cases.jsonl",
        },
        PipelineStage.DATASET_SPLITS: {
            "parent_train.jsonl",
            "parent_validation.jsonl",
            "parent_test.jsonl",
            "parent_regression_trusted.jsonl",
        },
    }
    snapshot_prefix = child.parent_snapshot.relative_to(child.root).as_posix()
    for stage, names in expected_snapshots.items():
        receipt = json.loads(child.receipt_path(stage).read_text(encoding="utf-8"))
        paths = {str(item["path"]) for item in receipt["inputs"]}
        assert "lineage.json" in paths
        assert "reuse_manifest.json" in paths
        assert {
            f"{snapshot_prefix}/{name}" for name in names
        } <= paths
    stage_eight = json.loads(
        child.receipt_path(PipelineStage.DATASET_SPLITS).read_text(encoding="utf-8")
    )
    assert {"lineage.json", "reuse_manifest.json"} <= {
        str(item["path"])
        for item in stage_eight["outputs"]
        if item.get("required") is True
    }


@pytest.mark.parametrize(
    "damage",
    [
        "creation_mode",
        "clustering_mode",
        "created_at",
        "added_labeled_record_ids",
        "added_unlabeled_record_ids",
        "parent_input_counts",
        "extended_input_counts",
        "parent_release.stage_8_receipt_sha256",
        "parent_release.released_state_sha256",
        "parent_release.source_lineage_sha256",
        "seeded_stage",
        "seeded_artifacts",
        "seeded_operation",
        "reused_stages",
        "snapshot_missing_row",
        "snapshot_extra_row",
    ],
)
def test_extension_rejects_each_corrupt_lineage_field_before_grandchild_creation(
    tmp_path: Path,
    damage: str,
) -> None:
    """Every lineage and reuse claim is schema-bound to released receipts."""
    parent = _released_extension_parent(tmp_path)
    lineage = json.loads(parent.lineage_path.read_text(encoding="utf-8"))
    reuse = json.loads(parent.reuse_manifest_path.read_text(encoding="utf-8"))
    if damage.startswith("parent_release."):
        field = damage.split(".", 1)[1]
        lineage["parent_release"][field] = "not-a-sha256"
        reuse["parent_release"][field] = "not-a-sha256"
    elif damage == "creation_mode":
        lineage[damage] = "unknown"
    elif damage == "clustering_mode":
        lineage[damage] = "unknown"
    elif damage == "created_at":
        lineage[damage] = 0
    elif damage == "added_labeled_record_ids":
        lineage[damage] = ["feedback-2", "feedback-2"]
    elif damage == "added_unlabeled_record_ids":
        lineage[damage] = "none"
    elif damage in {"parent_input_counts", "extended_input_counts"}:
        lineage[damage] = {"labeled": -1, "unlabeled": 1}
    elif damage == "seeded_stage":
        reuse["seeded_incremental_stage"]["stage"] = "unknown"
    elif damage == "seeded_artifacts":
        reuse["seeded_incremental_stage"]["artifacts"] = ["trusted_cases.jsonl"]
    elif damage == "seeded_operation":
        reuse["seeded_incremental_stage"]["operation"] = "unknown"
    elif damage == "reused_stages":
        reuse["reused_stages"] = []
    elif damage == "snapshot_missing_row":
        reuse["parent_snapshot"]["artifacts"].pop()
    elif damage == "snapshot_extra_row":
        extra = parent.parent_snapshot / "unexpected.jsonl"
        artifact_io.atomic_write_jsonl(extra, [])
        reuse["parent_snapshot"]["artifacts"].append(
            {
                "file": extra.name,
                "sha256": file_sha256(extra),
                "bytes": extra.stat().st_size,
            }
        )
    else:
        raise AssertionError(damage)
    artifact_io.atomic_write_json(parent.lineage_path, lineage)
    artifact_io.atomic_write_json(parent.reuse_manifest_path, reuse)
    manifest = json.loads(parent.manifest_path.read_text(encoding="utf-8"))
    manifest["lineage"] = lineage
    artifact_io.atomic_write_json(parent.manifest_path, manifest)
    artifact_io.atomic_write_json(
        parent.artifact_path(PipelineStage.DATASET_SPLITS, "dataset_manifest.json"),
        manifest,
    )
    grandchild = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v3")

    with pytest.raises(EvaluationAssetIntegrityError):
        grandchild.initialize_extension(
            parent,
            additional_feedback=_write_additional_feedback_v3(parent.tenants_root),
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not grandchild.root.exists()


@pytest.mark.parametrize(
    "snapshot_name",
    [
        "parent_feedback_evidence.jsonl",
        "parent_candidate_guidelines.jsonl",
        "parent_evaluation_guidelines.jsonl",
        "parent_trusted_intents.jsonl",
        "parent_trusted_cases.jsonl",
        "parent_intent_inventory.jsonl",
        "parent_intent_matches.jsonl",
        "parent_inferred_cluster_rubrics.jsonl",
        "parent_synthetic_cases.jsonl",
        "parent_train.jsonl",
        "parent_validation.jsonl",
        "parent_test.jsonl",
        "parent_regression_trusted.jsonl",
    ],
)
def test_extension_rejects_each_rehashed_corrupt_parent_snapshot_before_child(
    tmp_path: Path,
    snapshot_name: str,
) -> None:
    """Rehashing corrupt snapshot bytes cannot rewrite released lineage history."""
    parent = _released_extension_parent(tmp_path)
    target = parent.parent_snapshot / snapshot_name
    target.write_bytes(target.read_bytes() + b"\n")
    reuse = json.loads(parent.reuse_manifest_path.read_text(encoding="utf-8"))
    row = next(
        item
        for item in reuse["parent_snapshot"]["artifacts"]
        if item["file"] == snapshot_name
    )
    row["sha256"] = file_sha256(target)
    row["bytes"] = target.stat().st_size
    artifact_io.atomic_write_json(parent.reuse_manifest_path, reuse)
    grandchild = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v3")

    with pytest.raises(EvaluationAssetIntegrityError):
        grandchild.initialize_extension(
            parent,
            additional_feedback=_write_additional_feedback_v3(parent.tenants_root),
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not grandchild.root.exists()


@pytest.mark.parametrize(
    "failure_stage",
    [
        PipelineStage.RAW_INPUTS,
        PipelineStage.PREPARED_INPUTS,
        PipelineStage.RUBRIC_EXTRACTION,
    ],
)
def test_keep_extension_restores_snapshot_after_each_preclustering_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: PipelineStage,
) -> None:
    """Keep mode restores exact parent clusters and never invokes reclustering."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    expected = (
        child.parent_snapshot / "parent_intent_inventory.jsonl"
    ).read_bytes()
    shutil.rmtree(parent.root)
    first = EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    real_run_stage = first._run_stage

    def fail_once(stage: PipelineStage) -> dict[str, int]:
        if stage == failure_stage:
            raise RuntimeError("injected pre-clustering failure")
        return real_run_stage(stage)

    monkeypatch.setattr(first, "_run_stage", fail_once)
    with pytest.raises(RuntimeError, match="injected pre-clustering failure"):
        first.run()

    def reject_recluster(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("keep-mode extension attempted to recluster")

    monkeypatch.setattr(pipeline_module, "cluster_records_fixed_count", reject_recluster)
    resumed = EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    assert resumed.status == "released"
    assert child.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    ).read_bytes() == expected
    lineage_rows = _read_jsonl(
        child.artifact_path(PipelineStage.INTENT_CLUSTERING, "cluster_lineage.jsonl")
    )
    assert all(
        row["previous_cluster_id"] == row["new_cluster_id"]
        and row["relationship"] == "reused"
        for row in lineage_rows
    )


def test_extension_acquires_parent_and_child_locks_in_absolute_sorted_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock ordering is independent of caller parent/child argument order."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    acquired: list[str] = []

    class RecordingLock:
        def __init__(self, path: str, timeout: float) -> None:
            self.path = path

        def acquire(self) -> None:
            acquired.append(self.path)

        def release(self) -> None:
            pass

    monkeypatch.setattr(workspace_module, "FileLock", RecordingLock)

    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )

    expected = sorted(
        [str(parent.lock_path.absolute()), str(child.lock_path.absolute())]
    )
    assert acquired == expected


class _InjectedFault(RuntimeError):
    pass


@pytest.mark.parametrize("stage", list(PipelineStage), ids=lambda stage: stage.value)
def test_each_stage_provenance_rejects_self_consistent_secret_rehash_without_writes(
    tmp_path: Path,
    stage: PipelineStage,
) -> None:
    """A receipt hash authenticates only strict body-free provenance semantics."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    provenance_path = layout.stage_provenance_path(stage)
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    payload["request_body"] = {
        "authorization": "Bearer stage-provenance-canary",
        "protected_response": "sk-stage-provenance-canary",
    }
    _replace_stage_provenance_and_rehash_receipt(layout, state, stage, payload)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="provenance"):
        verify_stage_receipt(
            layout,
            state,
            stage,
            layout.load_config(),
            prompt_values={},
            compare_current_dependencies=False,
        )

    assert _authority_bytes(layout) == before


def test_stage_provenance_receipt_rejects_self_consistent_duplicate_key_json(
    tmp_path: Path,
) -> None:
    """Duplicate keys cannot collapse into an apparently valid stage record."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    stage = PipelineStage.RAW_INPUTS
    provenance_path = layout.artifact_path(stage, "provenance.json")
    original = provenance_path.read_text(encoding="utf-8").rstrip()
    raw = (original[:-1] + ',"stage":"raw_inputs"}\n').encode("utf-8")
    _replace_stage_provenance_and_rehash_receipt(layout, state, stage, raw)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="provenance"):
        verify_stage_receipt(
            layout,
            state,
            stage,
            layout.load_config(),
            prompt_values={},
            compare_current_dependencies=False,
        )

    assert _authority_bytes(layout) == before


def test_mutable_receipt_rejects_rehashed_undeclared_origin_without_writes(
    tmp_path: Path,
) -> None:
    """Mutable verification admits only exact native or adoption profiles."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    stage = PipelineStage.RAW_INPUTS
    receipt_path = layout.receipt_path(stage)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["origin"] = "fabricated"
    artifact_io.atomic_write_json(receipt_path, receipt)
    next(item for item in state.stages if item.stage == stage.value).receipt_sha256 = (
        file_sha256(receipt_path)
    )
    artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="profile|origin"):
        verify_stage_receipt(
            layout,
            state,
            stage,
            layout.load_config(),
            prompt_values={},
            compare_current_dependencies=True,
        )

    assert _authority_bytes(layout) == before


def test_mutable_receipt_rejects_native_legacy_hybrid_without_writes(
    tmp_path: Path,
) -> None:
    """Legacy provenance cannot be paired with retained native receipt evidence."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    stage = PipelineStage.RAW_INPUTS
    _replace_stage_provenance_and_rehash_receipt(
        layout,
        state,
        stage,
        workspace_module.build_legacy_stage_provenance(stage.value),
    )
    receipt_path = layout.receipt_path(stage)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["origin"] = "legacy_adoption"
    receipt["provider_calls_sha256"] = canonical_sha256(
        LEGACY_UNAVAILABLE_PROVENANCE
    )
    artifact_io.atomic_write_json(receipt_path, receipt)
    next(item for item in state.stages if item.stage == stage.value).receipt_sha256 = (
        file_sha256(receipt_path)
    )
    artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="profile|origin"):
        verify_stage_receipt(
            layout,
            state,
            stage,
            layout.load_config(),
            prompt_values={},
            compare_current_dependencies=True,
        )

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "corruption",
    [
        "counts_extra",
        "output_extra",
        "input_extra",
        "upstream_extra",
        "stage_index_bool",
        "completed_at_secret",
        "output_bytes_float",
    ],
)
def test_stage_receipt_rejects_rehashed_nested_secret_extras_without_writes(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Receipt subtrees are closed, body-free authentication records."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    stage = PipelineStage.PREPARED_INPUTS
    receipt_path = layout.receipt_path(stage)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if corruption == "counts_extra":
        receipt["counts"]["secret_extra"] = "sk-receipt-canary"
    elif corruption == "output_extra":
        receipt["outputs"][0]["secret_extra"] = "sk-receipt-canary"
    elif corruption == "input_extra":
        receipt["inputs"][0]["secret_extra"] = "sk-receipt-canary"
    elif corruption == "upstream_extra":
        receipt["upstream_receipts"][0]["secret_extra"] = "sk-receipt-canary"
    elif corruption == "stage_index_bool":
        receipt["stage_index"] = True
    elif corruption == "completed_at_secret":
        receipt["completed_at"] = "sk-receipt-timestamp"
    else:
        receipt["outputs"][0]["bytes"] = float(receipt["outputs"][0]["bytes"])
    artifact_io.atomic_write_json(receipt_path, receipt)
    next(item for item in state.stages if item.stage == stage.value).receipt_sha256 = (
        file_sha256(receipt_path)
    )
    artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_stage_receipt(
            layout,
            state,
            stage,
            layout.load_config(),
            prompt_values={},
            compare_current_dependencies=False,
        )

    assert _authority_bytes(layout) == before


def test_stage_receipt_rejects_rehashed_duplicate_key_secret_without_writes(
    tmp_path: Path,
) -> None:
    """Strict receipt parsing rejects hidden duplicate-key body content."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    stage = PipelineStage.PREPARED_INPUTS
    receipt_path = layout.receipt_path(stage)
    original = receipt_path.read_text(encoding="utf-8")
    artifact_io.atomic_write_text(
        receipt_path,
        original.replace(
            "{\n",
            '{\n  "counts": {"secret": "sk-duplicate-receipt"},\n',
            1,
        ),
    )
    next(item for item in state.stages if item.stage == stage.value).receipt_sha256 = (
        file_sha256(receipt_path)
    )
    artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="JSON|receipt"):
        verify_stage_receipt(
            layout,
            state,
            stage,
            layout.load_config(),
            prompt_values={},
            compare_current_dependencies=False,
        )

    assert _authority_bytes(layout) == before


def test_final_release_verification_validates_every_stage_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Final release verification rechecks all captured stage evidence."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    calls: list[tuple[str, str]] = []
    original = durability_module.validate_stage_provenance

    def record(payload: Mapping[str, Any], **expected: Any) -> dict[str, Any]:
        calls.append((expected["expected_stage"], expected["profile"]))
        return original(payload, **expected)

    monkeypatch.setattr(durability_module, "validate_stage_provenance", record)
    verify_released_asset(pipeline.layout, released)

    assert {
        stage
        for stage, profile in calls
        if profile == provenance_module.HISTORICAL_PROVENANCE_PROFILE_V2
    } == {
        stage.value for stage in PipelineStage
    }


def test_legacy_adoption_candidate_validates_every_stage_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prospective adoption rejects provenance before installing release authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    calls: list[tuple[str, str]] = []
    original = durability_module.validate_stage_provenance

    def record(payload: Mapping[str, Any], **expected: Any) -> dict[str, Any]:
        calls.append((expected["expected_stage"], expected["profile"]))
        return original(payload, **expected)

    monkeypatch.setattr(durability_module, "validate_stage_provenance", record)
    adopted = layout.adopt_legacy()

    assert adopted.status == "released"
    assert {
        stage
        for stage, profile in calls
        if profile
        == provenance_module.HISTORICAL_LEGACY_PROVENANCE_PROFILE_V2
    } == {
        stage.value for stage in PipelineStage
    }


_PRE_RECEIPT_PUBLICATION_FAULTS = (
    "after_generation_temp_created",
    "after_generation_split_train",
    "after_generation_split_validation",
    "after_generation_split_test",
    "after_generation_split_regression_trusted",
    "after_generation_manifest_write",
    "after_generation_temp_sync",
    "after_generation_install",
    "after_stage_8_outputs_validated",
)
_RECEIPT_AUTHORITY_PUBLICATION_FAULTS = (
    "after_stage_8_receipt_state_complete",
    "after_release_publication_prepared",
    "before_release_pointer_replace",
    "after_release_pointer_replace",
    "after_release_pointer_verify",
    "after_released_state_replace",
    "after_release_event_append",
    "after_release_publication_commit",
)


def _exercise_native_publication_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
    *,
    expected_stage_eight_runs: int,
) -> None:
    """Exercise one generation/publication fault and its exact recovery contract."""
    stage_eight_runs = 0
    original_run_stage = EvaluationAssetPipeline._run_stage

    def count_stage_eight(
        instance: EvaluationAssetPipeline,
        stage: PipelineStage,
    ) -> dict[str, int]:
        nonlocal stage_eight_runs
        if stage == PipelineStage.DATASET_SPLITS:
            stage_eight_runs += 1
        return original_run_stage(instance, stage)

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", count_stage_eight)
    pipeline, rubric, embedding = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match=fault_name):
        pipeline.run()

    calls_before_resume = (rubric.calls, embedding.calls)
    state_after_fault = pipeline.layout.load_state()
    receipt_before = None
    generation_before = None
    generation_id = None
    if expected_stage_eight_runs == 1:
        receipt_before = pipeline.layout.receipt_path(
            PipelineStage.DATASET_SPLITS
        ).read_bytes()
        manifest = json.loads(
            pipeline.layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "generation_manifest.json",
            ).read_text(encoding="utf-8")
        )
        generation_id = manifest["generation_id"]
        generation_before = _tree_bytes(
            pipeline.layout.generations_root / generation_id
        )
    if fault_name in {
        "after_released_state_replace",
        "after_release_event_append",
        "after_release_publication_commit",
    }:
        assert state_after_fault.status == "released"
    else:
        assert state_after_fault.status != "released"

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("publication recovery reran a provider")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    resumed = EvaluationAssetPipeline(
        pipeline.layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    if fault_name == "after_release_publication_commit":
        assert pipeline.layout.recover() == []
        recovered = pipeline.layout.load_state()
    else:
        recovered = resumed.run()

    assert recovered.status == "released"
    assert (rubric.calls, embedding.calls) == calls_before_resume
    assert stage_eight_runs == expected_stage_eight_runs
    if receipt_before is not None and generation_before is not None:
        assert pipeline.layout.receipt_path(
            PipelineStage.DATASET_SPLITS
        ).read_bytes() == receipt_before
        assert _tree_bytes(
            pipeline.layout.generations_root / str(generation_id)
        ) == generation_before
    verify_released_asset(pipeline.layout, recovered)
    release_rows = [
        row
        for row in _read_jsonl(pipeline.layout.recovery_journal_path)
        if row.get("kind") == "release_publication"
    ]
    assert [row["phase"] for row in release_rows] == ["prepared", "committed"]
    assert recovered.last_operation_id == release_rows[0]["operation_id"]
    release_events = [
        row
        for row in _read_jsonl(pipeline.layout.events_path)
        if row.get("event") == "pipeline_released"
    ]
    assert len(release_events) == 1
    assert release_events[0]["operation_id"] == release_rows[0]["operation_id"]
    assert release_rows[1]["operation_id"] == release_rows[0]["operation_id"]


@pytest.mark.parametrize("fault_name", _PRE_RECEIPT_PUBLICATION_FAULTS)
def test_native_pre_receipt_faults_recompute_stage_eight_without_provider_rerun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Pre-receipt generation failures recompute only deterministic Stage 8."""
    _exercise_native_publication_fault(
        tmp_path,
        monkeypatch,
        fault_name,
        expected_stage_eight_runs=2,
    )


@pytest.mark.parametrize("fault_name", _RECEIPT_AUTHORITY_PUBLICATION_FAULTS)
def test_native_receipt_and_wal_faults_reuse_stage_eight_and_provider_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Receipt/WAL authority recovers without rerunning a stage or provider."""
    _exercise_native_publication_fault(
        tmp_path,
        monkeypatch,
        fault_name,
        expected_stage_eight_runs=1,
    )


def test_corrupt_completed_stage_eight_handoff_fails_closed_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A corrupt completed release candidate is never silently recomputed."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match="after_stage_8_receipt_state_complete"):
        pipeline.run()
    assert (
        pipeline.layout.load_state().current_stage
        == PipelineStage.DATASET_SPLITS.value
    )
    receipt_path = pipeline.layout.receipt_path(PipelineStage.DATASET_SPLITS)
    receipt_path.write_bytes(receipt_path.read_bytes() + b"\n")
    before = _authority_bytes(pipeline.layout)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("corrupt release candidate reran work")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate",
    ):
        EvaluationAssetPipeline(
            pipeline.layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(pipeline.layout) == before


def test_reanchored_build_handoff_corruption_fails_before_any_resume_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A self-consistent receipt rehash cannot bypass the completed handoff preflight."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match="after_stage_8_receipt_state_complete"):
        pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    provenance = json.loads(layout.build_provenance_path.read_text(encoding="utf-8"))
    provenance["identity"]["algorithms"]["raw_inputs"] = "substituted-v1"
    provenance["identity_sha256"] = canonical_sha256(provenance["identity"])
    artifact_io.atomic_write_json(layout.build_provenance_path, provenance)
    receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    relative = layout.build_provenance_path.relative_to(layout.root).as_posix()
    build_row = next(item for item in receipt["outputs"] if item["path"] == relative)
    build_row["sha256"] = file_sha256(layout.build_provenance_path)
    build_row["bytes"] = layout.build_provenance_path.stat().st_size
    receipt["build_provenance_sha256"] = file_sha256(
        layout.build_provenance_path
    )
    artifact_io.atomic_write_json(receipt_path, receipt)
    stage_state = next(
        item
        for item in state.stages
        if item.stage == PipelineStage.DATASET_SPLITS.value
    )
    stage_state.receipt_sha256 = file_sha256(receipt_path)
    artifact_io.atomic_write_json(layout.state_path, state.to_dict())
    before = _authority_bytes(layout)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("corrupt completed handoff reran work")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("receipt_fact", ["provider", "source"])
def test_historical_stage_receipt_facts_are_bound_to_build_provenance(
    tmp_path: Path,
    receipt_fact: str,
) -> None:
    """A self-consistent receipt cannot contradict captured build/stage facts."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    stage = PipelineStage.RUBRIC_EXTRACTION
    receipt = json.loads(layout.receipt_path(stage).read_text(encoding="utf-8"))
    if receipt_fact == "provider":
        receipt["provider_identity"]["rubric"]["model"] = "substituted-model"
        receipt["provider_identity_sha256"] = canonical_sha256(
            receipt["provider_identity"]
        )
    else:
        receipt["code"]["members"][0]["sha256"] = "0" * 64
        receipt["code"]["fingerprint"] = canonical_sha256(
            receipt["code"]["members"]
        )
        receipt["code_sha256"] = canonical_sha256(receipt["code"])
    provenance = json.loads(
        layout.build_provenance_path.read_text(encoding="utf-8")
    )

    with pytest.raises(ValueError, match="receipt.*build"):
        durability_module._validate_stage_provenance_evidence(
            layout,
            stage,
            receipt,
            layout.load_config(),
            release_provenance=provenance,
            historical_evidence=True,
        )


def test_stage_and_build_historical_profiles_cannot_be_hybridized(
    tmp_path: Path,
) -> None:
    """Every native stage record uses the release build's schema generation."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    stage = PipelineStage.RAW_INPUTS
    receipt = json.loads(layout.receipt_path(stage).read_text(encoding="utf-8"))
    provenance = json.loads(
        layout.build_provenance_path.read_text(encoding="utf-8")
    )
    stage_payload = json.loads(
        layout.stage_provenance_path(stage).read_text(encoding="utf-8")
    )
    stage_payload["schema_version"] = "fapo-stage-provenance-v1"

    with pytest.raises(ValueError, match="provenance profiles differ"):
        durability_module._validate_stage_provenance_evidence(
            layout,
            stage,
            receipt,
            layout.load_config(),
            artifact_overrides={
                layout.stage_provenance_path(stage): json.dumps(
                    stage_payload
                ).encode("utf-8")
            },
            release_provenance=provenance,
            historical_evidence=True,
        )


def test_receipt_and_stage_historical_profiles_cannot_be_hybridized(
    tmp_path: Path,
) -> None:
    """A release cannot combine a v1 receipt with v2 stage evidence."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    layout = pipeline.layout
    stage = PipelineStage.RUBRIC_EXTRACTION
    receipt = json.loads(layout.receipt_path(stage).read_text(encoding="utf-8"))
    receipt["schema_version"] = "fapo-stage-receipt-v1"
    artifact_io.atomic_write_json(layout.receipt_path(stage), receipt)
    next(
        item for item in released.stages if item.stage == stage.value
    ).receipt_sha256 = file_sha256(layout.receipt_path(stage))

    with pytest.raises(EvaluationAssetIntegrityError, match="stage provenance"):
        verify_stage_receipt(
            layout,
            released,
            stage,
            layout.load_config(),
            prompt_values={},
            compare_current_dependencies=False,
        )


def _write_ambiguous_build_provenance(
    layout: EvaluationAssetLayout,
    corruption: str,
) -> None:
    path = layout.build_provenance_path
    payload = path.read_text(encoding="utf-8")
    if corruption == "duplicate":
        payload = payload.replace(
            '"schema_version":',
            '"schema_version":"sk-build-canary","schema_version":',
            1,
        )
    else:
        assert corruption == "nonfinite"
        payload = payload.replace(
            '"audit":',
            '"audit":{"secret":NaN},"audit":',
            1,
        )
    artifact_io.atomic_write_text(path, payload)


@pytest.mark.parametrize("corruption", ["duplicate", "nonfinite"])
def test_completed_candidate_strictly_parses_build_provenance_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    """Ambiguous build bytes cannot pass a completed-handoff preflight."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(pipeline_module, "_publication_fault_point", inject)
    with pytest.raises(_InjectedFault):
        pipeline.run()
    layout = pipeline.layout
    _write_ambiguous_build_provenance(layout, corruption)
    receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    build_hash = file_sha256(layout.build_provenance_path)
    build_relative = layout.build_provenance_path.relative_to(layout.root).as_posix()
    output = next(row for row in receipt["outputs"] if row["path"] == build_relative)
    output["sha256"] = build_hash
    output["bytes"] = layout.build_provenance_path.stat().st_size
    receipt["build_provenance_sha256"] = build_hash
    artifact_io.atomic_write_json(receipt_path, receipt)
    state = layout.load_state()
    next(
        item
        for item in state.stages
        if item.stage == PipelineStage.DATASET_SPLITS.value
    ).receipt_sha256 = file_sha256(receipt_path)
    layout.save_state(state)
    before = _authority_bytes(layout)
    monkeypatch.setattr(pipeline_module, "_publication_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError) as caught:
        EvaluationAssetPipeline(layout).run()

    assert caught.value.__cause__ is not None
    assert "control JSON" in str(caught.value.__cause__)
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("corruption", ["duplicate", "nonfinite"])
def test_final_publication_links_strictly_parse_build_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    """Final release verification rejects ambiguous authenticated build bytes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    layout = pipeline.layout
    receipts = durability_module.verify_receipt_chain(layout, released)
    journal = durability_module.validate_recovery_journal(
        layout,
        _read_jsonl(layout.recovery_journal_path),
    )
    snapshot = durability_module.resolve_evaluation_asset_release(
        layout.published_datasets,
        expected_tenant_id=layout.tenant_id,
        expected_asset_id=layout.asset_id,
        trusted_root=layout.tenant_root,
    )
    _write_ambiguous_build_provenance(layout, corruption)
    monkeypatch.setattr(
        durability_module,
        "resolve_evaluation_asset_release",
        lambda *args, **kwargs: replace(
            snapshot,
            build_provenance_sha256=file_sha256(layout.build_provenance_path),
        ),
    )
    before = _authority_bytes(layout)

    with pytest.raises(ValueError, match="control JSON"):
        durability_module._verify_release_publication_links(
            layout,
            released,
            receipts,
            journal,
            layout.load_config(),
        )

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("build_fact", ["configuration", "input"])
def test_build_provenance_is_bound_to_persisted_release_inputs(
    tmp_path: Path,
    build_fact: str,
) -> None:
    """Self-rehashed build claims must equal config and Stage 1 authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    layout = pipeline.layout
    receipts = durability_module.verify_receipt_chain(layout, released)
    provenance = json.loads(
        layout.build_provenance_path.read_text(encoding="utf-8")
    )
    if build_fact == "configuration":
        values = provenance["identity"]["resolved_configuration"]["values"]
        values["cluster_count"] += 1
        provenance["identity"]["resolved_configuration"]["sha256"] = (
            canonical_sha256(values)
        )
    else:
        provenance["identity"]["inputs"]["labeled_feedback"]["rows"] += 1
    provenance["identity_sha256"] = canonical_sha256(provenance["identity"])

    with pytest.raises(ValueError, match="build provenance.*authority"):
        durability_module._verify_build_provenance_authority_links(
            layout,
            provenance,
            receipts,
            layout.load_config(),
        )


def test_build_input_rows_are_derived_from_strict_source_jsonl(
    tmp_path: Path,
) -> None:
    """Matching manifest/build claims cannot overstate actual source rows."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    layout = pipeline.layout
    receipts = durability_module.verify_receipt_chain(layout, released)
    input_manifest_path = layout.artifact_path(
        PipelineStage.RAW_INPUTS,
        "input_manifest.json",
    )
    input_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    input_manifest["inputs"]["labeled_feedback"]["rows"] = 8
    artifact_io.atomic_write_json(input_manifest_path, input_manifest)
    provenance = json.loads(
        layout.build_provenance_path.read_text(encoding="utf-8")
    )
    provenance["identity"]["inputs"]["labeled_feedback"]["rows"] = 8
    provenance["identity_sha256"] = canonical_sha256(provenance["identity"])

    with pytest.raises(ValueError, match="build provenance.*authority"):
        durability_module._verify_build_provenance_authority_links(
            layout,
            provenance,
            receipts,
            layout.load_config(),
        )


@pytest.mark.parametrize("blank_position", ["leading", "interior"])
def test_release_input_row_authority_preserves_contract_blank_line_semantics(
    tmp_path: Path,
    blank_position: str,
) -> None:
    """Release row cross-links ignore blank physical input lines like Stage 1."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    if blank_position == "leading":
        artifact_io.atomic_write_text(
            layout.feedback_path,
            "\n" + layout.feedback_path.read_text(encoding="utf-8"),
        )
    else:
        first = json.loads(layout.unlabeled_path.read_text(encoding="utf-8"))
        second = {**first, "record_id": "unlabeled-2", "group_id": "group-2"}
        artifact_io.atomic_write_text(
            layout.unlabeled_path,
            json.dumps(first) + "\n\n" + json.dumps(second) + "\n",
        )

    released = pipeline.run()

    assert released.status == "released"
    verify_released_asset(layout, released)


def test_extension_build_lineage_is_bound_to_local_lineage_authority(
    tmp_path: Path,
) -> None:
    """Extension build hashes cannot contradict validated local lineage files."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    released = EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()
    receipts = durability_module.verify_receipt_chain(child, released)
    provenance = json.loads(
        child.build_provenance_path.read_text(encoding="utf-8")
    )
    dependencies = provenance["identity"]["lineage"]["file_dependencies"]
    dependencies["reuse_manifest_sha256"] = "0" * 64
    provenance["audit"]["lineage_files"]["reuse_manifest_sha256"] = "0" * 64
    provenance["identity_sha256"] = canonical_sha256(provenance["identity"])

    with pytest.raises(ValueError, match="build provenance.*authority"):
        durability_module._verify_build_provenance_authority_links(
            child,
            provenance,
            receipts,
            child.load_config(),
        )


@pytest.mark.parametrize("lineage_path", ["lineage", "reuse"])
def test_native_release_rejects_dangling_lineage_authority_symlinks(
    tmp_path: Path,
    lineage_path: str,
) -> None:
    """A dangling local lineage marker cannot change meaning after release."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    path = (
        pipeline.layout.lineage_path
        if lineage_path == "lineage"
        else pipeline.layout.reuse_manifest_path
    )
    path.symlink_to(tmp_path / "absent-lineage-target.json")

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="released control evidence",
    ):
        verify_released_asset(pipeline.layout, released)


_COMPLETED_STATE_INTEGER_FIELDS = (
    "mutation_sequence",
    "candidate_guidelines",
    "dataset_cases",
    "evaluation_guidelines",
    "feedback_evidence",
    "feedback_records",
    "inferred_cases",
    "intent_clusters",
    "labeling_queue_clusters",
    "labeling_queue_traces",
    "matched_clusters",
    "missing_label_clusters",
    "needs_more_feedback_clusters",
    "prepared_feedback",
    "prepared_intents",
    "regression_trusted_cases",
    "rejected_synthetic_cases",
    "review_clusters",
    "synthetic_cases",
    "test_cases",
    "train_cases",
    "triage_hold_cases",
    "trusted_cases",
    "unlabeled_records",
    "validation_cases",
)
_COMPLETED_CONFIG_INTEGER_FIELDS = (
    "batch_size",
    "cluster_count",
    "min_trusted_examples",
    "min_trusted_groups",
    "split_seed",
    "synthetic_cases_per_cluster",
)
_COMPLETED_CONTROL_TYPE_SUBSTITUTIONS = (
    *(f"state:{field}:float" for field in _COMPLETED_STATE_INTEGER_FIELDS),
    *(f"config:{field}:float" for field in _COMPLETED_CONFIG_INTEGER_FIELDS),
    "state:mutation_sequence:bool",
    "state:intent_clusters:bool",
    "config:synthetic_coverage_enabled:int",
    "config:max_unlabeled_to_trusted_ratio:int",
)


@pytest.fixture(scope="module")
def completed_handoff_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Create one immutable Stage 8 handoff copied by scalar-schema probes."""
    template_root = tmp_path_factory.mktemp("completed-handoff")
    pipeline, _, _ = _create_pipeline(template_root)
    original_fault_point = workspace_module._fault_point

    def inject(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    workspace_module._fault_point = inject
    try:
        with pytest.raises(
            _InjectedFault,
            match="after_stage_8_receipt_state_complete",
        ):
            pipeline.run()
    finally:
        workspace_module._fault_point = original_fault_point
    return pipeline.layout.tenants_root


@pytest.fixture(scope="module")
def default_provider_completed_handoff_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Create a credential-free handoff recorded as built-in default providers."""
    template_root = tmp_path_factory.mktemp("default-provider-handoff")
    tenants_root = template_root / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    patch = pytest.MonkeyPatch()
    patch.setattr(
        pipeline_module,
        "OpenAIRubricProvider",
        _SuccessfulDefaultRubricProvider,
    )
    patch.setattr(
        pipeline_module,
        "OpenAIEmbeddingProvider",
        _SuccessfulDefaultEmbeddingProvider,
    )
    patch.setattr(
        rubric_provider_module,
        "OpenAIRubricProvider",
        _SuccessfulDefaultRubricProvider,
    )
    patch.setattr(
        embedding_provider_module,
        "OpenAIEmbeddingProvider",
        _SuccessfulDefaultEmbeddingProvider,
    )
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
    )
    original_fault_point = workspace_module._fault_point

    def inject(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    workspace_module._fault_point = inject
    try:
        with pytest.raises(
            _InjectedFault,
            match="after_stage_8_receipt_state_complete",
        ):
            pipeline.run()
    finally:
        workspace_module._fault_point = original_fault_point
        patch.undo()
    return pipeline.layout.tenants_root


@pytest.mark.parametrize(
    "current_stage",
    [PipelineStage.DATASET_SPLITS.value, None],
    ids=["stage-8-handoff", "post-stage-event-handoff"],
)
@pytest.mark.parametrize(
    "substitution",
    _COMPLETED_CONTROL_TYPE_SUBSTITUTIONS,
)
def test_completed_control_scalar_substitution_fails_without_authority_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    current_stage: str | None,
    substitution: str,
) -> None:
    """Equal-valued JSON scalar substitutions cannot be normalized into release."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state_payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    state_payload["current_stage"] = current_stage
    target, field, replacement_type = substitution.split(":")
    if target == "state":
        container = (
            state_payload
            if field == "mutation_sequence"
            else state_payload["counts"]
        )
    else:
        container = json.loads(layout.config_path.read_text(encoding="utf-8"))
    original = container[field]
    if replacement_type == "float":
        container[field] = float(original)
    elif replacement_type == "bool":
        assert original in {0, 1}
        container[field] = bool(original)
    else:
        assert replacement_type == "int"
        container[field] = int(original)
    artifact_io.atomic_write_json(layout.state_path, state_payload)
    if target == "config":
        artifact_io.atomic_write_json(layout.config_path, container)
    before = _authority_bytes(layout)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("invalid completed control reran pipeline work")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


@pytest.mark.parametrize(
    ("status", "current_stage", "error"),
    [
        ("running", PipelineStage.RUBRIC_EXTRACTION.value, None),
        ("running", PipelineStage.DATASET_SPLITS.value, "unexpected error"),
    ],
)
def test_all_receipted_handoff_rejects_invalid_lifecycle_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    status: str,
    current_stage: str,
    error: str | None,
) -> None:
    """An unreachable running receipt chain enters strict handoff verification."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    payload.update(status=status, current_stage=current_stage, error=error)
    artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("invalid completed lifecycle reran pipeline work")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


def test_receipt_bound_stage_status_corruption_fails_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
) -> None:
    """A retained receipt hash cannot be treated as an incomplete mutable stage."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    payload["stages"][-1]["status"] = True
    artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("receipt-bound status corruption reran pipeline work")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


@pytest.mark.parametrize(
    "damage",
    [
        "null_receipt",
        "missing_receipt",
        "deleted_stage",
        "deleted_stage_and_count",
        "nonmapping",
        "extra",
    ],
)
def test_completed_stage_authority_downgrade_fails_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    damage: str,
) -> None:
    """Completed authority cannot downgrade through receipt or stage damage."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    if damage == "null_receipt":
        payload["stages"][-1]["receipt_sha256"] = None
    elif damage == "missing_receipt":
        del payload["stages"][-1]["receipt_sha256"]
    elif damage == "deleted_stage":
        del payload["stages"][-1]
    elif damage == "deleted_stage_and_count":
        del payload["stages"][-1]
        del payload["counts"]["dataset_cases"]
    elif damage == "nonmapping":
        payload["stages"][-1] = "not-a-stage-row"
    else:
        assert damage == "extra"
        payload["stages"].append(dict(payload["stages"][-1]))
    artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("damaged completed authority reran pipeline work")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate control",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "current_stage",
    [PipelineStage.DATASET_SPLITS.value, None],
    ids=["stage-8-handoff", "post-stage-event-handoff"],
)
@pytest.mark.parametrize(
    "schema_damage",
    ["removed", "explicit-v1"],
)
@pytest.mark.parametrize("missing_stage_receipt", [False, True])
@pytest.mark.parametrize("downgraded_status", ["running", "completed"])
@pytest.mark.parametrize(
    "config_updates",
    [None, {}, {"match_threshold": 0.2}],
    ids=["no-update", "empty-update", "nonempty-update"],
)
def test_native_handoff_schema_downgrade_fails_without_writes_or_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    current_stage: str | None,
    schema_damage: str,
    missing_stage_receipt: bool,
    downgraded_status: str,
    config_updates: dict[str, Any] | None,
) -> None:
    """Non-v2 control cannot reclassify receipt-backed native authority."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    payload["current_stage"] = current_stage
    payload["status"] = downgraded_status
    if schema_damage == "removed":
        del payload["schema_version"]
    else:
        assert schema_damage == "explicit-v1"
        payload["schema_version"] = "fapo-evaluation-asset-state-v1"
    if missing_stage_receipt:
        del payload["stages"][-1]["receipt_sha256"]
    artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("downgraded native authority reran pipeline work")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate control",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run(config_updates=config_updates)

    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


@pytest.mark.parametrize("schema_mode", ["removed", "explicit-v1"])
@pytest.mark.parametrize(
    "legacy_event",
    [None, "stage_completed", "pipeline_completed"],
    ids=["no-event", "historical-stage-event", "historical-completion-event"],
)
def test_receipt_free_legacy_status_checkpoint_remains_mutable(
    tmp_path: Path,
    schema_mode: str,
    legacy_event: str | None,
) -> None:
    """A genuine receipt-free legacy prefix may still resume into v2."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    layout = pipeline.layout
    payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    payload.update(
        status="running",
        current_stage=PipelineStage.RAW_INPUTS.value,
        error=None,
    )
    if schema_mode == "removed":
        del payload["schema_version"]
    else:
        payload["schema_version"] = "fapo-evaluation-asset-state-v1"
    artifact_io.atomic_write_json(layout.state_path, payload)
    if legacy_event is not None:
        artifact_io.atomic_append_jsonl(
            layout.events_path,
            {"event": legacy_event},
        )

    released = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    ).run()

    assert released.status == "released"
    assert released.schema_version == STATE_SCHEMA_VERSION


@pytest.mark.parametrize(
    "evidence",
    ["stage-provenance", "provider-ledger", "release-event", "event-node"],
)
def test_legacy_completed_sentinel_rejects_task4_native_evidence(
    tmp_path: Path,
    evidence: str,
) -> None:
    """Task 4 evidence cannot hide behind the pre-v2 completed sentinel."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    if evidence == "stage-provenance":
        artifact_io.atomic_write_json(
            layout.stage_provenance_path(PipelineStage.RAW_INPUTS),
            {},
        )
    elif evidence == "provider-ledger":
        artifact_io.atomic_write_jsonl(
            layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "provider_calls.jsonl",
            ),
            [],
        )
    elif evidence == "release-event":
        artifact_io.atomic_append_jsonl(
            layout.events_path,
            {"event": "pipeline_released"},
        )
    else:
        assert evidence == "event-node"
        layout.events_path.unlink()
        layout.events_path.mkdir()
    before = _authority_bytes(layout)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate control",
    ):
        durability_module.load_completed_release_handoff_control(layout)

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "evidence",
    [
        "state-receipt",
        "receipt-file",
        "stage-provenance",
        "provider-ledger",
        "build-provenance",
        "journal",
        "pointer",
        "generation-manifest",
        "dataset-manifest",
        "asset-manifest",
        "generations-directory",
        "publication-event",
        "event-node",
    ],
)
def test_non_v2_native_authority_detector_is_read_only_and_complete(
    tmp_path: Path,
    evidence: str,
) -> None:
    """Every native authority family prevents a non-v2 mutable fallback."""
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    layout.root.mkdir(parents=True)
    raw_state: dict[str, Any] = {"stages": []}
    if evidence == "state-receipt":
        raw_state["stages"] = [{"receipt_sha256": "0" * 64}]
    elif evidence == "receipt-file":
        artifact_io.atomic_write_json(
            layout.receipt_path(PipelineStage.RAW_INPUTS),
            {},
        )
    elif evidence == "stage-provenance":
        artifact_io.atomic_write_json(
            layout.stage_provenance_path(PipelineStage.RAW_INPUTS),
            {},
        )
    elif evidence == "provider-ledger":
        artifact_io.atomic_write_jsonl(
            layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "provider_calls.jsonl",
            ),
            [],
        )
    elif evidence == "build-provenance":
        artifact_io.atomic_write_json(layout.build_provenance_path, {})
    elif evidence == "journal":
        artifact_io.atomic_write_jsonl(layout.recovery_journal_path, [{}])
    elif evidence == "pointer":
        artifact_io.atomic_write_json(layout.release_pointer_path, {})
    elif evidence == "generation-manifest":
        artifact_io.atomic_write_json(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "generation_manifest.json",
            ),
            {},
        )
    elif evidence == "dataset-manifest":
        artifact_io.atomic_write_json(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "dataset_manifest.json",
            ),
            {},
        )
    elif evidence == "asset-manifest":
        artifact_io.atomic_write_json(layout.manifest_path, {})
    elif evidence == "generations-directory":
        layout.generations_root.mkdir(parents=True)
    elif evidence == "publication-event":
        assert evidence == "publication-event"
        artifact_io.atomic_write_jsonl(
            layout.events_path,
            [{"event": "pipeline_released"}],
        )
    else:
        assert evidence == "event-node"
        layout.events_path.mkdir()
    before = _tree_bytes(layout.tenant_root)

    assert durability_module._has_native_authority_evidence(layout, raw_state)
    assert _tree_bytes(layout.tenant_root) == before


def test_non_v2_provider_ledger_detection_uses_frozen_stage_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Current provider-role drift cannot hide a historical Task 4 ledger."""
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "provider_calls.jsonl",
        ),
        [],
    )
    monkeypatch.setattr(
        durability_module,
        "STAGE_SPECIFICATIONS",
        {
            stage: replace(specification, provider_roles=())
            for stage, specification in STAGE_SPECIFICATIONS.items()
        },
    )

    assert durability_module._has_native_authority_evidence(
        layout,
        {"stages": []},
    )


@pytest.mark.parametrize("replacement", [True, 1.0])
def test_failed_all_receipted_config_coercion_fails_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    replacement: bool | float,
) -> None:
    """Mutable failed compatibility still authenticates raw control types first."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state_payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    state_payload.update(
        status="failed",
        current_stage=None,
        error="interrupted test checkpoint",
    )
    artifact_io.atomic_write_json(layout.state_path, state_payload)
    config_payload = json.loads(layout.config_path.read_text(encoding="utf-8"))
    config_payload["cluster_count"] = replacement
    artifact_io.atomic_write_json(layout.config_path, config_payload)
    before = _authority_bytes(layout)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("invalid failed control reran pipeline work")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate control",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("field", ["tenant_id", "asset_id"])
def test_completed_handoff_state_identity_mismatch_fails_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    field: str,
) -> None:
    """Completed state identity is bound to the selected asset before publication."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    payload[field] = f"substituted-{field}"
    artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("identity-mismatched handoff reran pipeline work")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate control",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("current_stage", "not_a_stage"),
        ("last_operation_id", "not_an_operation"),
    ],
)
def test_failed_all_receipted_state_domain_fails_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    field: str,
    replacement: str,
) -> None:
    """Failed compatibility accepts only closed cursor and operation domains."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    payload.update(
        status="failed",
        current_stage=None,
        error="interrupted test checkpoint",
    )
    payload[field] = replacement
    artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("invalid failed state reran pipeline work")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate control",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("updates", [{}, {"match_threshold": 0.2}])
@pytest.mark.parametrize("damage", ["state_type", "state_identity", "config_type"])
def test_completed_control_updates_cannot_bypass_raw_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    updates: dict[str, Any],
    damage: str,
) -> None:
    """Even explicit revision requests authenticate completed raw control first."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    if damage == "config_type":
        payload = json.loads(layout.config_path.read_text(encoding="utf-8"))
        payload["cluster_count"] = True
        artifact_io.atomic_write_json(layout.config_path, payload)
    else:
        payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
        if damage == "state_type":
            payload["mutation_sequence"] = True
        else:
            assert damage == "state_identity"
            payload["tenant_id"] = "substituted-tenant"
        artifact_io.atomic_write_json(layout.state_path, payload)
    before = _authority_bytes(layout)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("invalid revised control reran pipeline work")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="completed release candidate control",
    ):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run(config_updates=updates)

    assert _authority_bytes(layout) == before


@pytest.fixture(scope="module")
def released_control_template(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Create one released authority tree copied by final-control probes."""
    template_root = tmp_path_factory.mktemp("released-control")
    pipeline, _, _ = _create_pipeline(template_root)
    pipeline.run()
    return pipeline.layout.tenants_root


@pytest.mark.parametrize("control", ["completed_handoff", "released"])
def test_invalid_terminal_config_rejects_before_config_model_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    released_control_template: Path,
    control: str,
) -> None:
    """Strict terminal control rejects config types before coercive construction."""
    tenants_root = tmp_path / "tenants"
    template = (
        completed_handoff_template
        if control == "completed_handoff"
        else released_control_template
    )
    shutil.copytree(template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    payload = json.loads(layout.config_path.read_text(encoding="utf-8"))
    payload["cluster_count"] = True
    artifact_io.atomic_write_json(layout.config_path, payload)
    before = _authority_bytes(layout)
    model_calls = 0

    def forbidden_model(
        cls: type[EvaluationAssetConfig],
        raw: Mapping[str, Any],
    ) -> EvaluationAssetConfig:
        del cls, raw
        nonlocal model_calls
        model_calls += 1
        raise AssertionError("invalid terminal config reached coercive model")

    monkeypatch.setattr(
        EvaluationAssetConfig,
        "from_dict",
        classmethod(forbidden_model),
    )

    with pytest.raises(EvaluationAssetIntegrityError):
        EvaluationAssetPipeline(layout).run()

    assert model_calls == 0
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "substitution",
    [
        "state:mutation_sequence:float",
        "state:intent_clusters:float",
        "config:cluster_count:float",
        "config:synthetic_coverage_enabled:int",
        "config:max_unlabeled_to_trusted_ratio:int",
    ],
)
def test_released_control_scalar_substitution_fails_without_writes(
    tmp_path: Path,
    released_control_template: Path,
    substitution: str,
) -> None:
    """Final verification rejects type-coerced state and config authority."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(released_control_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    target, field, replacement_type = substitution.split(":")
    path = layout.state_path if target == "state" else layout.config_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    container = (
        payload["counts"]
        if target == "state" and field != "mutation_sequence"
        else payload
    )
    original = container[field]
    container[field] = (
        float(original) if replacement_type == "float" else int(original)
    )
    artifact_io.atomic_write_json(path, payload)
    before = _authority_bytes(layout)

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        durability_module._validate_released_control_state(
            layout,
            layout.load_state(),
            require_persisted_state=True,
        )

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "current_stage",
    [PipelineStage.DATASET_SPLITS.value, None],
    ids=["stage-8-handoff", "post-stage-event-handoff"],
)
@pytest.mark.parametrize("dependency_drift", ["source", "prompt", "provider"])
@pytest.mark.parametrize(
    "config_updates",
    [None, {}],
    ids=["no-update-argument", "empty-update-map"],
)
def test_completed_handoff_publishes_captured_generation_after_dependency_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    current_stage: str | None,
    dependency_drift: str,
    config_updates: dict[str, Any] | None,
) -> None:
    """Current dependencies cannot strand authenticated historical handoff evidence."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state_payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    state_payload["current_stage"] = current_stage
    artifact_io.atomic_write_json(layout.state_path, state_payload)
    receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
    receipt_before = receipt_path.read_bytes()
    manifest = json.loads(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        ).read_text(encoding="utf-8")
    )
    generation_id = manifest["generation_id"]
    generation_before = _tree_bytes(layout.generations_root / generation_id)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    if dependency_drift == "source":
        source_identity = durability_module._code_identity()
        source_identity["members"][0]["sha256"] = "0" * 64
        source_identity["fingerprint"] = canonical_sha256(
            source_identity["members"]
        )
        monkeypatch.setattr(
            durability_module,
            "_code_identity",
            lambda: source_identity,
        )
    elif dependency_drift == "prompt":
        prompt_values = {
            stage: dict(values)
            for stage, values in pipeline_module.STAGE_PROMPTS.items()
        }
        prompt_values[PipelineStage.RUBRIC_EXTRACTION][
            "evidence_extraction"
        ] += "\nCurrent deployment prompt drift."
        monkeypatch.setattr(pipeline_module, "STAGE_PROMPTS", prompt_values)
    else:
        assert dependency_drift == "provider"
        rubric.model = "current-rubric-model"
        embedding.model = "current-embedding-model"

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("completed handoff reran a stage or provider")

    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]
    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    released = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    ).run(config_updates=config_updates)

    assert released.status == "released"
    assert rubric.calls == 0
    assert embedding.calls == 0
    assert receipt_path.read_bytes() == receipt_before
    assert _tree_bytes(layout.generations_root / generation_id) == generation_before
    release_rows = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row.get("kind") == "release_publication"
    ]
    assert [row["phase"] for row in release_rows] == ["prepared", "committed"]
    release_events = [
        row
        for row in _read_jsonl(layout.events_path)
        if row.get("event") == "pipeline_released"
    ]
    assert len(release_events) == 1
    assert released.last_operation_id == release_rows[0]["operation_id"]
    assert release_events[0]["operation_id"] == released.last_operation_id
    verify_released_asset(layout, released)


@pytest.mark.parametrize("release_kind", ["native", "adopted"])
def test_released_restart_uses_only_frozen_state_profiles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release_kind: str,
) -> None:
    """Current labels cannot strand native or adopted persisted releases."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    if release_kind == "adopted":
        _downgrade_to_legacy_completed(layout)
        layout.adopt_legacy()
    labels = dict(evaluation_asset_models.STAGE_LABELS)
    labels[PipelineStage.RAW_INPUTS] = "Current deployment label"
    monkeypatch.setattr(evaluation_asset_models, "STAGE_LABELS", labels)
    fresh_layout = EvaluationAssetLayout(
        layout.tenants_root,
        layout.tenant_id,
        layout.asset_id,
    )

    released = fresh_layout.load_state()

    assert next(
        item
        for item in released.stages
        if item.stage == PipelineStage.RAW_INPUTS.value
    ).label == "Validate raw inputs"
    verify_released_asset(fresh_layout, released)
    with pytest.raises(EvaluationAssetImmutableError):
        EvaluationAssetPipeline(fresh_layout).run()


@pytest.mark.parametrize(
    "current_stage",
    [PipelineStage.DATASET_SPLITS.value, None],
    ids=["stage-8-handoff", "post-stage-event-handoff"],
)
@pytest.mark.parametrize(
    "registry_drift",
    [
        "prompt-and-revision",
        "source-inventory",
        "algorithm-revision",
        "default-provider-absent",
        "default-provider-settings",
        "stage-specification",
        "state-registry",
        "receipt-schema",
        "provenance-schema",
    ],
)
@pytest.mark.parametrize(
    "config_updates",
    [None, {}],
    ids=["no-update-argument", "empty-update-map"],
)
def test_default_provider_handoff_uses_only_versioned_historical_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    default_provider_completed_handoff_template: Path,
    current_stage: str | None,
    registry_drift: str,
    config_updates: dict[str, Any] | None,
) -> None:
    """Current registries/providers cannot strand captured v1 provenance."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(default_provider_completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state_payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    state_payload["current_stage"] = current_stage
    artifact_io.atomic_write_json(layout.state_path, state_payload)
    receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
    receipt_before = receipt_path.read_bytes()
    generation_manifest = json.loads(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        ).read_text(encoding="utf-8")
    )
    generation_id = generation_manifest["generation_id"]
    generation_before = _tree_bytes(layout.generations_root / generation_id)
    constructor_calls = {"rubric": 0, "embedding": 0}

    def current_rubric(
        model: str,
        max_output_tokens: int = 16384,
    ) -> _SuccessfulDefaultRubricProvider:
        constructor_calls["rubric"] += 1
        if registry_drift == "default-provider-absent":
            raise RuntimeError("current rubric provider is unavailable")
        provider = _SuccessfulDefaultRubricProvider(model, max_output_tokens)
        if registry_drift == "default-provider-settings":
            provider.timeout_seconds += 1
        return provider

    def current_embedding(model: str) -> _SuccessfulDefaultEmbeddingProvider:
        constructor_calls["embedding"] += 1
        if registry_drift == "default-provider-absent":
            raise RuntimeError("current embedding provider is unavailable")
        provider = _SuccessfulDefaultEmbeddingProvider(model)
        if registry_drift == "default-provider-settings":
            provider.batch_size += 1
        return provider

    for module in (pipeline_module, rubric_provider_module):
        monkeypatch.setattr(module, "OpenAIRubricProvider", current_rubric)
    for module in (pipeline_module, embedding_provider_module):
        monkeypatch.setattr(module, "OpenAIEmbeddingProvider", current_embedding)

    if registry_drift == "prompt-and-revision":
        revisions = dict(provenance_module.PROMPT_REVISIONS)
        revisions["evidence_extraction"] = "v2"
        monkeypatch.setattr(provenance_module, "PROMPT_REVISIONS", revisions)
        monkeypatch.setattr(durability_module, "PROMPT_REVISIONS", revisions)
        prompts = {
            stage: dict(values)
            for stage, values in pipeline_module.STAGE_PROMPTS.items()
        }
        prompts[PipelineStage.RUBRIC_EXTRACTION][
            "evidence_extraction"
        ] += "\nCurrent deployment prompt revision."
        monkeypatch.setattr(pipeline_module, "STAGE_PROMPTS", prompts)
    elif registry_drift == "source-inventory":
        monkeypatch.setattr(
            provenance_module,
            "SOURCE_FIXED_MEMBERS",
            (*provenance_module.SOURCE_FIXED_MEMBERS, "new-source-member.py"),
        )
    elif registry_drift == "algorithm-revision":
        current_inventory = provenance_module.build_algorithm_inventory

        def drifted_inventory(
            config: Mapping[str, Any],
            *,
            extension: bool,
        ) -> dict[str, Any]:
            inventory = current_inventory(config, extension=extension)
            inventory["raw_inputs"] = "fapo-evaluation-input-v2"
            return inventory

        monkeypatch.setattr(
            provenance_module,
            "build_algorithm_inventory",
            drifted_inventory,
        )
        monkeypatch.setattr(
            durability_module,
            "build_algorithm_inventory",
            drifted_inventory,
        )
    elif registry_drift == "stage-specification":
        current_specifications = dict(durability_module.STAGE_SPECIFICATIONS)
        current_specifications[PipelineStage.RUBRIC_EXTRACTION] = replace(
            current_specifications[PipelineStage.RUBRIC_EXTRACTION],
            provider_roles=(),
        )
        monkeypatch.setattr(
            durability_module,
            "STAGE_SPECIFICATIONS",
            current_specifications,
        )
    elif registry_drift == "state-registry":
        labels = dict(evaluation_asset_models.STAGE_LABELS)
        labels[PipelineStage.RAW_INPUTS] = "Current deployment label"
        count_keys = dict(durability_module.STAGE_COUNT_KEYS)
        count_keys[PipelineStage.RAW_INPUTS] = (
            *count_keys[PipelineStage.RAW_INPUTS],
            "future_count",
        )
        monkeypatch.setattr(evaluation_asset_models, "STAGE_LABELS", labels)
        monkeypatch.setattr(durability_module, "STAGE_COUNT_KEYS", count_keys)
    elif registry_drift == "receipt-schema":
        monkeypatch.setattr(
            durability_module,
            "STAGE_RECEIPT_SCHEMA_VERSION",
            "fapo-stage-receipt-v3",
        )
        monkeypatch.setattr(
            durability_module,
            "_STAGE_RECEIPT_FIELDS",
            {*durability_module._STAGE_RECEIPT_FIELDS, "future_field"},
        )
    elif registry_drift == "provenance-schema":
        monkeypatch.setattr(
            provenance_module,
            "PROVIDER_CALL_SCHEMA_VERSION",
            "fapo-provider-call-v3",
        )
        monkeypatch.setattr(
            provenance_module,
            "STAGE_PROVENANCE_SCHEMA_VERSION",
            "fapo-stage-provenance-v3",
        )
        monkeypatch.setattr(
            provenance_module,
            "BUILD_PROVENANCE_SCHEMA_VERSION",
            "fapo-evaluation-build-provenance-v3",
        )
        monkeypatch.setattr(
            provenance_module,
            "BUILD_IDENTITY_SCHEMA_VERSION",
            "fapo-evaluation-build-identity-v3",
        )

    def forbidden_stage(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("historical handoff reran a completed stage")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden_stage)

    released = EvaluationAssetPipeline(layout).run(
        config_updates=config_updates
    )

    assert released.status == "released"
    assert constructor_calls == {"rubric": 0, "embedding": 0}
    assert receipt_path.read_bytes() == receipt_before
    assert _tree_bytes(layout.generations_root / generation_id) == generation_before
    release_rows = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row.get("kind") == "release_publication"
    ]
    assert [row["phase"] for row in release_rows] == ["prepared", "committed"]
    release_events = [
        row
        for row in _read_jsonl(layout.events_path)
        if row.get("event") == "pipeline_released"
    ]
    assert len(release_events) == 1
    assert released.last_operation_id == release_rows[0]["operation_id"]
    assert release_events[0]["operation_id"] == released.last_operation_id
    verify_released_asset(layout, released)


@pytest.mark.parametrize(
    "current_stage",
    [PipelineStage.DATASET_SPLITS.value, None],
    ids=["stage-8-handoff", "post-stage-event-handoff"],
)
def test_completed_custom_provider_handoff_publishes_without_current_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    current_stage: str | None,
) -> None:
    """Historical provider evidence is sufficient after a provider is removed."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state_payload = json.loads(layout.state_path.read_text(encoding="utf-8"))
    state_payload["current_stage"] = current_stage
    artifact_io.atomic_write_json(layout.state_path, state_payload)
    receipt_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
    receipt_before = receipt_path.read_bytes()
    manifest = json.loads(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        ).read_text(encoding="utf-8")
    )
    generation_id = manifest["generation_id"]
    generation_before = _tree_bytes(layout.generations_root / generation_id)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("completed provider handoff reran a stage")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)

    released = EvaluationAssetPipeline(layout).run()

    assert released.status == "released"
    assert receipt_path.read_bytes() == receipt_before
    assert _tree_bytes(layout.generations_root / generation_id) == generation_before
    verify_released_asset(layout, released)


def test_generation_temp_created_fault_removes_owned_temporary_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The earliest generation fault cannot strand a hidden temporary tree."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == "after_generation_temp_created":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match="after_generation_temp_created"):
        pipeline.run()

    generations_root = pipeline.layout.generations_root
    assert not list(generations_root.glob(".*.tmp"))


def test_recovery_rejects_corrupt_prepared_release_before_pointer_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepared evidence is semantically verified before pointer authority moves."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == "after_release_publication_prepared":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match="after_release_publication_prepared"):
        pipeline.run()
    layout = pipeline.layout
    assert not layout.release_pointer_path.exists()
    provenance = json.loads(layout.build_provenance_path.read_text(encoding="utf-8"))
    provenance["created_at"] = "2026-08-20T00:00:00+00:00"
    artifact_io.atomic_write_json(layout.build_provenance_path, provenance)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert not layout.release_pointer_path.exists()


@pytest.mark.parametrize(
    "corruption",
    [
        "pointer_generation",
        "pointer_provenance",
        "pointer_receipt",
        "generation_manifest",
        "build_provenance",
        "stage_8_receipt",
    ],
)
def test_release_cross_link_corruption_fails_closed_without_repair_writes(
    tmp_path: Path,
    corruption: str,
) -> None:
    """Pointer, generation, provenance, and receipt links are one authority DAG."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    layout = pipeline.layout
    pointer = json.loads(layout.release_pointer_path.read_text(encoding="utf-8"))
    generation_manifest = (
        layout.generations_root
        / pointer["generation_id"]
        / "generation_manifest.json"
    )
    if corruption == "pointer_generation":
        pointer["generation_id"] = f"sha256-{'0' * 64}"
        artifact_io.atomic_write_json(layout.release_pointer_path, pointer)
    elif corruption == "pointer_provenance":
        pointer["build_provenance_sha256"] = "0" * 64
        artifact_io.atomic_write_json(layout.release_pointer_path, pointer)
    elif corruption == "pointer_receipt":
        pointer["stage_8_receipt_sha256"] = "0" * 64
        artifact_io.atomic_write_json(layout.release_pointer_path, pointer)
    elif corruption == "generation_manifest":
        artifact_io.atomic_write_text(
            generation_manifest,
            generation_manifest.read_text(encoding="utf-8") + " ",
        )
    elif corruption == "build_provenance":
        provenance = json.loads(layout.build_provenance_path.read_text(encoding="utf-8"))
        provenance["created_at"] = "2026-08-20T00:00:00+00:00"
        artifact_io.atomic_write_json(layout.build_provenance_path, provenance)
    elif corruption == "stage_8_receipt":
        receipt = json.loads(
            layout.receipt_path(PipelineStage.DATASET_SPLITS).read_text(
                encoding="utf-8"
            )
        )
        receipt["build_provenance_sha256"] = "0" * 64
        artifact_io.atomic_write_json(
            layout.receipt_path(PipelineStage.DATASET_SPLITS),
            receipt,
        )
    else:  # pragma: no cover - parameter list is exhaustive
        raise AssertionError(corruption)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before
    assert released.status == "released"


def _create_pipeline(
    tmp_path: Path,
    *,
    asset_id: str = "v1",
) -> tuple[
    EvaluationAssetPipeline,
    _SuccessfulRubricProvider,
    _SuccessfulEmbeddingProvider,
]:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id=asset_id,
            rubric_provider="fake",
            rubric_model=rubric.model,
            embedding_provider="fake",
            embedding_model=embedding.model,
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    return pipeline, rubric, embedding


def _create_synthetic_pipeline(
    tmp_path: Path,
) -> tuple[EvaluationAssetPipeline, _SuccessfulSyntheticRubricProvider]:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    rubric = _SuccessfulSyntheticRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            rubric_provider="fake",
            rubric_model=rubric.model,
            embedding_provider="fake",
            embedding_model=embedding.model,
            cluster_count=1,
            synthetic_coverage_enabled=True,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    return pipeline, rubric


def _write_input_pair(tenants_root: Path) -> tuple[Path, Path]:
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    common = {
        "schema_version": "fapo-evaluation-input-v1",
        "group_id": "group-1",
        "task_type": "generic",
        "user_input": "Process the supplied input.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }
    feedback.write_text(
        json.dumps(
            {
                **common,
                "record_id": "feedback-1",
                "assistant_output": "A previous response.",
                "feedback": {
                    "polarity": "positive",
                    "rationale": "The response satisfied the request.",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        json.dumps({**common, "record_id": "unlabeled-1"}) + "\n",
        encoding="utf-8",
    )
    return feedback, unlabeled


def _write_additional_feedback(tenants_root: Path) -> Path:
    path = tenants_root / "tenant_a" / "source_artifacts" / "additional.jsonl"
    payload = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "feedback-2",
        "group_id": "group-2",
        "task_type": "generic",
        "user_input": "Process another supplied input.",
        "assistant_output": "Another previous response.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "feedback": {
            "polarity": "positive",
            "rationale": "The other response satisfied the request.",
        },
        "metadata": {},
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _write_additional_feedback_v3(tenants_root: Path) -> Path:
    path = tenants_root / "tenant_a" / "source_artifacts" / "additional-v3.jsonl"
    payload = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "feedback-3",
        "group_id": "group-3",
        "task_type": "generic",
        "user_input": "Process a third supplied input.",
        "assistant_output": "A third previous response.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "feedback": {
            "polarity": "positive",
            "rationale": "The third response satisfied the request.",
        },
        "metadata": {},
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _released_extension_parent(tmp_path: Path) -> EvaluationAssetLayout:
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()
    return child


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _authority_bytes(layout: EvaluationAssetLayout) -> dict[str, bytes]:
    authority = {
        f"asset/{name}": contents
        for name, contents in _tree_bytes(layout.root).items()
    }
    if layout.published_datasets.is_dir():
        authority.update(
            {
                f"catalog/{name}": contents
                for name, contents in _tree_bytes(layout.published_datasets).items()
            }
        )
    return authority


def _replace_stage_provenance_and_rehash_receipt(
    layout: EvaluationAssetLayout,
    state: PipelineState,
    stage: PipelineStage,
    payload: Mapping[str, Any] | bytes,
) -> None:
    """Install test-only provenance bytes and re-anchor its immediate receipt/state."""
    provenance_path = layout.stage_provenance_path(stage)
    if isinstance(payload, bytes):
        artifact_io.atomic_write_text(provenance_path, payload.decode("utf-8"))
    else:
        artifact_io.atomic_write_json(provenance_path, payload)
    receipt_path = layout.receipt_path(stage)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    relative = provenance_path.relative_to(layout.root).as_posix()
    row = next(item for item in receipt["outputs"] if item["path"] == relative)
    row["sha256"] = file_sha256(provenance_path)
    row["bytes"] = provenance_path.stat().st_size
    artifact_io.atomic_write_json(receipt_path, receipt)
    stage_state = next(item for item in state.stages if item.stage == stage.value)
    stage_state.receipt_sha256 = file_sha256(receipt_path)


def _rehash_committed_adoption_authority(layout: EvaluationAssetLayout) -> None:
    """Re-anchor a committed adoption after a Stage 3 artifact rewrite."""
    candidate_path = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "candidate_guidelines.jsonl",
    )
    candidate_relative = candidate_path.relative_to(layout.root).as_posix()
    receipts: dict[PipelineStage, dict[str, Any]] = {}
    for stage in PipelineStage:
        receipt_path = layout.receipt_path(stage)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if stage == PipelineStage.RUBRIC_EXTRACTION:
            output = next(
                item
                for item in receipt["outputs"]
                if item["path"] == candidate_relative
            )
            output["sha256"] = file_sha256(candidate_path)
            output["bytes"] = candidate_path.stat().st_size
        receipt["upstream_receipts"] = [
            {
                "stage": dependency.value,
                "sha256": durability_module.persisted_json_sha256(
                    receipts[dependency]
                ),
            }
            for dependency in STAGE_SPECIFICATIONS[stage].upstream_stages
        ]
        artifact_io.atomic_write_json(receipt_path, receipt)
        receipts[stage] = receipt

    rows = _read_jsonl(layout.recovery_journal_path)
    prepared = rows[0]
    state = layout.load_state()
    receipt_hashes = {
        stage.value: file_sha256(layout.receipt_path(stage))
        for stage in PipelineStage
    }
    for stage_state in state.stages:
        stage_state.receipt_sha256 = receipt_hashes[stage_state.stage]
    prepared["target_receipts"] = {
        stage.value: receipts[stage] for stage in PipelineStage
    }
    prepared["target"]["receipt_sha256"] = receipt_hashes
    prepared["target_state"] = state.to_dict()
    prepared["target"]["state_sha256"] = durability_module.persisted_json_sha256(
        prepared["target_state"]
    )
    artifact_io.atomic_write_json(layout.state_path, prepared["target_state"])
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, rows)


def _rehash_prepared_adoption_authority(layout: EvaluationAssetLayout) -> None:
    """Re-anchor one outstanding adoption after a Stage 3 artifact rewrite."""
    rows = _read_jsonl(layout.recovery_journal_path)
    prepared = rows[0]
    candidate_path = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "candidate_guidelines.jsonl",
    )
    candidate_relative = candidate_path.relative_to(layout.root).as_posix()
    receipts: dict[PipelineStage, dict[str, Any]] = {}
    for stage in PipelineStage:
        receipt = prepared["target_receipts"][stage.value]
        if stage == PipelineStage.RUBRIC_EXTRACTION:
            output = next(
                item
                for item in receipt["outputs"]
                if item["path"] == candidate_relative
            )
            output["sha256"] = file_sha256(candidate_path)
            output["bytes"] = candidate_path.stat().st_size
        receipt["upstream_receipts"] = [
            {
                "stage": dependency.value,
                "sha256": durability_module.persisted_json_sha256(
                    receipts[dependency]
                ),
            }
            for dependency in STAGE_SPECIFICATIONS[stage].upstream_stages
        ]
        receipts[stage] = receipt
    receipt_hashes = {
        stage.value: durability_module.persisted_json_sha256(receipts[stage])
        for stage in PipelineStage
    }
    for stage_state in prepared["target_state"]["stages"]:
        stage_state["receipt_sha256"] = receipt_hashes[stage_state["stage"]]
    prepared["target"]["receipt_sha256"] = receipt_hashes
    prepared["target"]["state_sha256"] = durability_module.persisted_json_sha256(
        prepared["target_state"]
    )
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, rows)


def _release_with_config_revisions(
    tmp_path: Path,
    *,
    revision_count: int,
) -> EvaluationAssetLayout:
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    pipeline.run()
    updates = (
        {"match_threshold": 0.2},
        {"split_seed": 73},
    )
    for revision_updates in updates[:revision_count]:
        _make_released_checkpoint_mutable(pipeline.layout)
        EvaluationAssetPipeline(
            pipeline.layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run(config_updates=revision_updates)
    return pipeline.layout


def _layout_after_final_committed_mutation(
    tmp_path: Path,
    *,
    operation_kind: str,
    lifecycle: str,
) -> EvaluationAssetLayout:
    """Build a writer-reachable post-commit state for revision/rebuild recovery."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    _make_released_checkpoint_mutable(pipeline.layout)
    config_updates: dict[str, Any] | None
    if operation_kind == "configuration_revision":
        config_updates = {"match_threshold": 0.2}
    elif operation_kind == "checkpoint_rebuild":
        config_updates = None
        target = pipeline.layout.artifact_path(
            PipelineStage.COVERAGE_DECISIONS,
            "intent_matches.jsonl",
        )
        target.write_bytes(target.read_bytes() + b" \n")
    else:
        raise AssertionError(operation_kind)

    if lifecycle == "running":
        def stop_after_pipeline_started() -> None:
            raise _InjectedFault("after_pipeline_started")

        with pytest.raises(_InjectedFault, match="after_pipeline_started"):
            pipeline.run(
                config_updates=config_updates,
                _preflight_accepted_callback=stop_after_pipeline_started,
            )
    elif lifecycle == "failed":
        def fail_stage(stage: PipelineStage) -> dict[str, int]:
            raise _InjectedFault(f"failed_{stage.value}")

        pipeline._run_stage = fail_stage  # type: ignore[method-assign]
        with pytest.raises(_InjectedFault, match="failed_"):
            pipeline.run(config_updates=config_updates)
    elif lifecycle == "released":
        pipeline.run(config_updates=config_updates)
    else:
        raise AssertionError(lifecycle)

    prepared = [
        row
        for row in _read_jsonl(pipeline.layout.recovery_journal_path)
        if row["phase"] == "prepared" and row["kind"] == operation_kind
    ]
    assert prepared
    return pipeline.layout


def _damage_revision_journal(
    layout: EvaluationAssetLayout,
    damage: str,
) -> None:
    if damage == "missing_journal":
        layout.recovery_journal_path.unlink()
        return
    rows = _read_jsonl(layout.recovery_journal_path)
    prepares = [
        row
        for row in rows
        if row.get("kind") == "configuration_revision"
        and row.get("phase") == "prepared"
    ]
    commits = [
        row
        for row in rows
        if row.get("kind") == "configuration_revision"
        and row.get("phase") == "committed"
    ]
    if damage == "missing_all_prepares":
        rows = [row for row in rows if row not in prepares]
    elif damage == "missing_commit":
        rows.remove(commits[-1])
    elif damage == "duplicate_prepare":
        index = rows.index(prepares[0])
        rows.insert(index + 1, json.loads(json.dumps(prepares[0])))
    elif damage == "duplicate_commit":
        index = rows.index(commits[0])
        rows.insert(index + 1, json.loads(json.dumps(commits[0])))
    elif damage == "unmatched_pair":
        extra_prepare = json.loads(json.dumps(prepares[0]))
        extra_commit = json.loads(json.dumps(commits[0]))
        operation_id = "e" * 32
        extra_prepare["operation_id"] = operation_id
        extra_prepare["history_entry"]["operation_id"] = operation_id
        extra_commit["operation_id"] = operation_id
        rows.extend((extra_prepare, extra_commit))
    elif damage == "reordered_pairs":
        assert len(prepares) == len(commits) == 2
        rows = [prepares[1], commits[1], prepares[0], commits[0]]
    else:
        raise AssertionError(damage)
    artifact_io.atomic_write_jsonl(layout.recovery_journal_path, rows)


def _failed_prefix_state(
    state: PipelineState,
    failed_stage: PipelineStage,
) -> PipelineState:
    target = PipelineState.from_dict(state.to_dict())
    boundary = list(PipelineStage).index(failed_stage)
    for index, stage_state in enumerate(target.stages):
        if index < boundary:
            continue
        if index == boundary:
            stage_state.status = "failed"
            stage_state.message = "injected prior failure"
            stage_state.completed_at = None
            stage_state.receipt_sha256 = None
        else:
            stage_state.status = "pending"
            stage_state.message = ""
            stage_state.started_at = None
            stage_state.completed_at = None
            stage_state.receipt_sha256 = None
    invalid_counts = {
        key
        for stage in list(PipelineStage)[boundary:]
        for key in durability_module.STAGE_COUNT_KEYS[stage]
    }
    target.counts = {
        key: value
        for key, value in target.counts.items()
        if key not in invalid_counts
    }
    target.status = "failed"
    target.current_stage = failed_stage.value
    target.error = "injected prior failure"
    return target


def _prepared_adoption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[EvaluationAssetLayout, dict[str, Any]]:
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.adopt_legacy()
    return layout, _read_jsonl(layout.recovery_journal_path)[0]


def _install_adoption_target_manifests(
    layout: EvaluationAssetLayout,
    prepared: dict[str, Any],
) -> None:
    targets = prepared["target_manifests"]
    artifact_io.atomic_write_json(layout.manifest_path, targets["asset_manifest"])
    artifact_io.atomic_write_json(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "dataset_manifest.json",
        ),
        targets["dataset_manifest"],
    )
    artifact_io.atomic_write_json(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        ),
        targets["generation_manifest"],
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _convert_to_legacy_rubric_profile(layout: EvaluationAssetLayout) -> None:
    normalized = _read_jsonl(
        layout.artifact_path(
            PipelineStage.PREPARED_INPUTS,
            "normalized_feedback.jsonl",
        )
    )[0]
    native_case = _read_jsonl(
        layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "trusted_cases.jsonl",
        )
    )[0]
    rubric = {
        "record_id": "feedback-1",
        "intent_label": "answer request",
        "confidence": 0.9,
        "must": ["Answer the stated request."],
        "must_not": [],
        "should": [],
        "deterministic_checks": [
            {"type": "required_field", "field": "answer"}
        ],
        "tool_expectations": {"required_tool": "tool_a"},
        "reference_output": None,
        "label_source": "human_feedback",
        "rubric_provider": "openai",
        "rubric_model": "fake-rubric",
        "oracle_version": "fapo-evaluation-asset-v1",
    }
    trusted_intent = {
        "intent_id": "feedback-1",
        "label": rubric["intent_label"],
        "texts": [
            normalized["user_input"],
            " ".join([*rubric["must"], *rubric["must_not"]]),
        ],
        "route": normalized["route"],
        "metadata": {
            "trusted_example_count": 1,
            "trusted_group_count": 1,
            "feedback_polarity": normalized["feedback"]["polarity"],
        },
    }
    trusted_case = {
        "case_id": "feedback-feedback-1",
        "task_type": normalized["task_type"],
        "context": native_case["context"],
        "expected": {
            "label_source": rubric["label_source"],
            "confidence": rubric["confidence"],
            "rubric": {
                "must": rubric["must"],
                "must_not": rubric["must_not"],
                "should": rubric["should"],
            },
            "deterministic_checks": rubric["deterministic_checks"],
            "tool_expectations": rubric["tool_expectations"],
            "reference_output": rubric["reference_output"],
            "feedback_polarity": normalized["feedback"]["polarity"],
        },
        "metadata": native_case["metadata"],
    }
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "feedback_rubrics.jsonl",
        ),
        [rubric],
    )
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "trusted_intents.jsonl",
        ),
        [trusted_intent],
    )
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "trusted_cases.jsonl",
        ),
        [trusted_case],
    )
    matches_path = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )
    matches = _read_jsonl(matches_path)
    for row in matches:
        if row.get("matched_intent_id"):
            row["matched_intent_id"] = "feedback-1"
    artifact_io.atomic_write_jsonl(matches_path, matches)
    labels_path = layout.artifact_path(
        PipelineStage.LABEL_INFERENCE,
        "inferred_unlabeled_labels.jsonl",
    )
    labels = _read_jsonl(labels_path)
    for row in labels:
        if row.get("matched_intent_id"):
            row["matched_intent_id"] = "feedback-1"
    artifact_io.atomic_write_jsonl(labels_path, labels)
    inferred_path = layout.artifact_path(
        PipelineStage.LABEL_INFERENCE,
        "inferred_cases.jsonl",
    )
    inferred = _read_jsonl(inferred_path)
    for row in inferred:
        if row["metadata"].get("matched_intent_id"):
            row["metadata"]["matched_intent_id"] = "feedback-1"
    artifact_io.atomic_write_jsonl(inferred_path, inferred)
    case_by_id = {
        trusted_case["case_id"]: trusted_case,
        **{row["case_id"]: row for row in inferred},
    }
    for name in (
        "train.jsonl",
        "validation.jsonl",
        "test.jsonl",
        "train_trusted.jsonl",
        "validation_trusted.jsonl",
        "test_trusted.jsonl",
        "train_inferred.jsonl",
        "validation_inferred.jsonl",
        "test_inferred.jsonl",
        "regression_trusted.jsonl",
        "triage_hold.jsonl",
    ):
        split_path = layout.artifact_path(PipelineStage.DATASET_SPLITS, name)
        split_rows = _read_jsonl(split_path)
        artifact_io.atomic_write_jsonl(
            split_path,
            [case_by_id.get(row["case_id"], row) for row in split_rows],
        )
    for name in (
        "train.jsonl",
        "validation.jsonl",
        "test.jsonl",
        "regression_trusted.jsonl",
    ):
        artifact_io.atomic_copy_file(
            layout.artifact_path(PipelineStage.DATASET_SPLITS, name),
            layout.published_datasets / name,
        )
    for name in (
        "feedback_evidence.jsonl",
        "candidate_guidelines.jsonl",
        "evaluation_guidelines.jsonl",
    ):
        layout.artifact_path(PipelineStage.RUBRIC_EXTRACTION, name).unlink()
    manifest = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    manifest["evaluation_guidelines"] = {
        "schema_version": "legacy-feedback-rubric-v1",
        "count": 0,
        "activation_status": "legacy_compatibility",
        "calibration_status": "unavailable",
    }
    artifact_io.atomic_write_json(layout.manifest_path, manifest)
    artifact_io.atomic_write_json(
        layout.artifact_path(PipelineStage.DATASET_SPLITS, "dataset_manifest.json"),
        manifest,
    )


def _move_to_pre_stage_layout(layout: EvaluationAssetLayout) -> None:
    moves: list[tuple[Path, Path]] = []
    for stage in PipelineStage:
        directory = layout.stage_directory(stage)
        for source in directory.rglob("*"):
            if source.is_file():
                relative = source.relative_to(directory).as_posix()
                moves.append(
                    (
                        source,
                        layout.root
                        / workspace_module._legacy_artifact_path(
                            stage.value,
                            relative,
                        ),
                    )
                )
    for source, destination in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
    shutil.rmtree(layout.stages_root)


def _apply_semantic_corruption(
    layout: EvaluationAssetLayout,
    corruption: str,
) -> None:
    def path(stage: PipelineStage, name: str) -> Path:
        return layout.artifact_path(stage, name)

    def rows(stage: PipelineStage, name: str) -> list[dict[str, Any]]:
        return _read_jsonl(path(stage, name))

    def write(stage: PipelineStage, name: str, payload: list[dict[str, Any]]) -> None:
        artifact_io.atomic_write_jsonl(path(stage, name), payload)

    def write_historical_nonfinite(
        stage: PipelineStage,
        name: str,
        payload: list[dict[str, Any]],
    ) -> None:
        """Bypass strict current writers to model already-persisted legacy bytes."""
        path(stage, name).write_text(
            "".join(
                json.dumps(row, sort_keys=True, allow_nan=True) + "\n"
                for row in payload
            ),
            encoding="utf-8",
        )

    def sync_case_to_splits(case: dict[str, Any]) -> None:
        for name in (
            "train.jsonl",
            "validation.jsonl",
            "test.jsonl",
            "train_trusted.jsonl",
            "validation_trusted.jsonl",
            "test_trusted.jsonl",
            "regression_trusted.jsonl",
            "triage_hold.jsonl",
        ):
            split_rows = rows(PipelineStage.DATASET_SPLITS, name)
            changed = False
            for index, row in enumerate(split_rows):
                if row.get("case_id") == case.get("case_id"):
                    split_rows[index] = json.loads(json.dumps(case))
                    changed = True
            if changed:
                write(PipelineStage.DATASET_SPLITS, name, split_rows)

    if corruption == "prepared_identity":
        payload = rows(PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl")
        payload[0]["record_id"] = "unknown-feedback"
        write(PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl", payload)
    elif corruption == "duplicate_intent_record":
        payload = rows(PipelineStage.PREPARED_INPUTS, "intent_records.jsonl")
        payload.append(dict(payload[0]))
        write(PipelineStage.PREPARED_INPUTS, "intent_records.jsonl", payload)
    elif corruption == "evidence_source":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl")
        payload[0]["record_id"] = "unknown-feedback"
        write(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl", payload)
    elif corruption.startswith("native_evidence_confidence_"):
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl")
        value_by_suffix = {
            "nan": float("nan"),
            "positive_infinity": float("inf"),
            "negative_infinity": float("-inf"),
            "bool": True,
            "out_of_domain": 1.5,
        }
        payload[0]["confidence"] = value_by_suffix[
            corruption.removeprefix("native_evidence_confidence_")
        ]
        if corruption.endswith(("nan", "infinity")):
            write_historical_nonfinite(
                PipelineStage.RUBRIC_EXTRACTION,
                "feedback_evidence.jsonl",
                payload,
            )
        else:
            write(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl", payload)
    elif corruption == "native_evidence_observations_object":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl")
        payload[0]["observations"] = {"claim": "not an array"}
        write(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl", payload)
    elif corruption == "native_candidate_confidence_bool":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "candidate_guidelines.jsonl")
        payload[0]["confidence"] = True
        write(PipelineStage.RUBRIC_EXTRACTION, "candidate_guidelines.jsonl", payload)
    elif corruption == "native_guideline_support_bool":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl")
        payload[0]["support"]["trusted_example_count"] = True
        write(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl", payload)
    elif corruption == "native_criterion_evidence_required_integer":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl")
        payload[0]["criteria"][0]["evidence_required"] = 1
        write(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl", payload)
    elif corruption == "native_duplicate_evidence":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl")
        payload.append(json.loads(json.dumps(payload[0])))
        write(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl", payload)
    elif corruption.startswith("native_candidate_"):
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "candidate_guidelines.jsonl")
        criterion = payload[0]["criteria"][0]
        if corruption == "native_candidate_kind_unknown":
            criterion["kind"] = "mandatory"
        elif corruption == "native_candidate_severity_unknown":
            criterion["severity"] = "fatal"
        elif corruption == "native_candidate_evaluator_unknown":
            criterion["evaluator"]["type"] = "arbitrary_code"
        elif corruption == "native_candidate_statement_mismatch":
            criterion["statement"] = "A substituted candidate statement."
        elif corruption == "native_candidate_missing_scoring":
            criterion.pop("scoring")
        elif corruption == "native_candidate_extra_field":
            payload[0]["untrusted_extra"] = "value"
        elif corruption == "native_candidate_evaluator_extra_field":
            criterion["evaluator"]["untrusted_extra"] = "value"
        elif corruption == "native_candidate_applicability_empty":
            criterion["applicability"] = ""
        elif corruption == "native_candidate_applicability_wrong_type":
            criterion["applicability"] = ["always"]
        elif corruption == "native_candidate_tool_expectations_wrong_type":
            payload[0]["tool_expectations"] = ["required-tool"]
        else:
            raise AssertionError(corruption)
        write(PipelineStage.RUBRIC_EXTRACTION, "candidate_guidelines.jsonl", payload)
    elif corruption == "native_evidence_provider_mismatch":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl")
        payload[0]["guideline_provider"] = "different-provider"
        write(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl", payload)
    elif corruption.startswith("native_compiled_"):
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl")
        if corruption == "native_compiled_kind_unknown":
            payload[0]["criteria"][0]["kind"] = "mandatory"
        elif corruption == "native_compiled_policy_mismatch":
            payload[0]["unknown_policy"] = "silently_accept"
        elif corruption == "native_compiled_extra_field":
            payload[0]["untrusted_extra"] = "value"
        else:
            raise AssertionError(corruption)
        write(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl", payload)
        trusted = rows(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl")
        trusted[0]["expected"]["evaluation_guidelines"] = json.loads(
            json.dumps(payload)
        )
        write(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl", trusted)
        sync_case_to_splits(trusted[0])
    elif corruption.startswith("legacy_rubric_confidence_"):
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl")
        value_by_suffix = {
            "nan": float("nan"),
            "positive_infinity": float("inf"),
            "negative_infinity": float("-inf"),
            "bool": True,
        }
        payload[0]["confidence"] = value_by_suffix[
            corruption.removeprefix("legacy_rubric_confidence_")
        ]
        if corruption.endswith(("nan", "infinity")):
            write_historical_nonfinite(
                PipelineStage.RUBRIC_EXTRACTION,
                "feedback_rubrics.jsonl",
                payload,
            )
        else:
            write(PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl", payload)
    elif corruption == "legacy_rubric_nested_nonfinite":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl")
        payload[0]["deterministic_checks"] = [{"threshold": float("nan")}]
        write_historical_nonfinite(
            PipelineStage.RUBRIC_EXTRACTION,
            "feedback_rubrics.jsonl",
            payload,
        )
    elif corruption == "legacy_duplicate_rubric":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl")
        payload.append(json.loads(json.dumps(payload[0])))
        write(PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl", payload)
    elif corruption.startswith("legacy_rubric_"):
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl")
        if corruption == "legacy_rubric_empty_check":
            payload[0]["deterministic_checks"] = [{}]
        elif corruption == "legacy_rubric_scoreable_mismatch":
            payload[0]["must"] = ["A substituted scoreable requirement."]
        elif corruption == "legacy_rubric_extra_field":
            payload[0]["untrusted_extra"] = "value"
        elif corruption == "legacy_rubric_missing_field":
            payload[0].pop("oracle_version")
        elif corruption == "legacy_rubric_tool_expectations_wrong_type":
            payload[0]["tool_expectations"] = ["required-tool"]
        elif corruption == "legacy_rubric_check_wrong_type":
            payload[0]["deterministic_checks"] = ["not-an-object"]
        else:
            raise AssertionError(corruption)
        write(PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl", payload)
    elif corruption == "legacy_expected_empty_check":
        trusted = rows(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl")
        trusted[0]["expected"]["deterministic_checks"] = [{}]
        write(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl", trusted)
        sync_case_to_splits(trusted[0])
    elif corruption == "legacy_trusted_intent_text_mismatch":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "trusted_intents.jsonl")
        payload[0]["texts"][1] = "A substituted rubric summary."
        write(PipelineStage.RUBRIC_EXTRACTION, "trusted_intents.jsonl", payload)
    elif corruption == "guideline_source":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl")
        payload[0]["source_record_ids"] = ["unknown-feedback"]
        write(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl", payload)
    elif corruption == "trusted_intent_link":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "trusted_intents.jsonl")
        payload[0]["intent_id"] = "unknown-guideline"
        write(PipelineStage.RUBRIC_EXTRACTION, "trusted_intents.jsonl", payload)
    elif corruption == "trusted_case_shape":
        payload = rows(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl")
        payload[0].pop("expected")
        write(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl", payload)
    elif corruption == "cluster_shape":
        write(PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl", [{}])
    elif corruption == "cluster_partition":
        payload = rows(PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl")
        payload[0]["record_ids"] = ["unknown-record"]
        payload[0]["representative_ids"] = ["unknown-record"]
        write(PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl", payload)
    elif corruption in {"match_cluster", "match_score"}:
        payload = rows(PipelineStage.COVERAGE_DECISIONS, "intent_matches.jsonl")
        if corruption == "match_cluster":
            payload[0]["cluster_id"] = "unknown-cluster"
        else:
            payload[0]["score"] = "not-a-score"
        write(PipelineStage.COVERAGE_DECISIONS, "intent_matches.jsonl", payload)
    elif corruption == "queue_member":
        write(
            PipelineStage.COVERAGE_DECISIONS,
            "review_queue/labeling_queue.jsonl",
            [
                {
                    "cluster_id": "generic-001",
                    "record_id": "unknown-record",
                    "route": "generic",
                    "user_input": "Unknown input",
                }
            ],
        )
    elif corruption == "inferred_label_ref":
        payload = rows(
            PipelineStage.LABEL_INFERENCE,
            "inferred_unlabeled_labels.jsonl",
        )
        payload[0]["record_id"] = "unknown-record"
        write(
            PipelineStage.LABEL_INFERENCE,
            "inferred_unlabeled_labels.jsonl",
            payload,
        )
    elif corruption == "inferred_case_ref":
        payload = rows(PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl")
        payload[0]["metadata"]["source_cluster"] = "unknown-cluster"
        write(PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl", payload)
    elif corruption == "synthetic_case_trust":
        payload = rows(PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl")
        payload[0]["case_id"] = "synthetic-invalid"
        payload[0]["metadata"]["source"] = "synthetic_generation"
        write(PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl", payload)
    elif corruption == "synthetic_filter_partition":
        payload = rows(PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl")
        payload[0]["case_id"] = "synthetic-invalid"
        payload[0]["metadata"].update(
            {
                "source": "synthetic_generation",
                "trust_tier": "synthetic",
            }
        )
        write(PipelineStage.SYNTHETIC_COVERAGE, "synthetic_candidates.jsonl", payload)
        write(PipelineStage.SYNTHETIC_COVERAGE, "rejected_synthetic.jsonl", payload)
        write(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_filter_issues.jsonl",
            [
                {
                    "case_id": "synthetic-invalid",
                    "code": "invented",
                    "message": "Invented rejection.",
                }
            ],
        )
    elif corruption == "split_component":
        inferred = rows(PipelineStage.DATASET_SPLITS, "train_inferred.jsonl")[0]
        trusted = rows(PipelineStage.DATASET_SPLITS, "train_trusted.jsonl")
        trusted.append(inferred)
        write(PipelineStage.DATASET_SPLITS, "train_trusted.jsonl", trusted)
        _set_manifest_split_count(layout, "train_trusted", len(trusted))
    elif corruption == "split_group_leakage":
        case = rows(PipelineStage.DATASET_SPLITS, "train_trusted.jsonl")[0]
        write(PipelineStage.DATASET_SPLITS, "validation_trusted.jsonl", [case])
        write(PipelineStage.DATASET_SPLITS, "validation.jsonl", [case])
        artifact_io.atomic_copy_file(
            path(PipelineStage.DATASET_SPLITS, "validation.jsonl"),
            layout.published_datasets / "validation.jsonl",
        )
        _set_manifest_split_count(layout, "validation_trusted", 1)
        _set_manifest_split_count(layout, "validation", 1)
    elif corruption == "combined_mismatch":
        trusted = rows(PipelineStage.DATASET_SPLITS, "train_trusted.jsonl")
        write(PipelineStage.DATASET_SPLITS, "train.jsonl", trusted)
        artifact_io.atomic_copy_file(
            path(PipelineStage.DATASET_SPLITS, "train.jsonl"),
            layout.published_datasets / "train.jsonl",
        )
        _set_manifest_split_count(layout, "train", len(trusted))
    elif corruption == "regression_untrusted":
        inferred = rows(PipelineStage.DATASET_SPLITS, "train_inferred.jsonl")[0]
        write(PipelineStage.DATASET_SPLITS, "regression_trusted.jsonl", [inferred])
        artifact_io.atomic_copy_file(
            path(PipelineStage.DATASET_SPLITS, "regression_trusted.jsonl"),
            layout.published_datasets / "regression_trusted.jsonl",
        )
        _set_manifest_split_count(layout, "regression_trusted", 1)
    elif corruption == "regression_duplicate":
        trusted = rows(PipelineStage.DATASET_SPLITS, "train_trusted.jsonl")[0]
        write(PipelineStage.DATASET_SPLITS, "regression_trusted.jsonl", [trusted])
        artifact_io.atomic_copy_file(
            path(PipelineStage.DATASET_SPLITS, "regression_trusted.jsonl"),
            layout.published_datasets / "regression_trusted.jsonl",
        )
        _set_manifest_split_count(layout, "regression_trusted", 1)
    else:
        raise AssertionError(f"unknown semantic corruption: {corruption}")


def _synthetic_case_fixture(
    layout: EvaluationAssetLayout,
    *,
    case_id: str,
    user_input: str,
) -> dict[str, Any]:
    expected = _read_jsonl(
        layout.artifact_path(PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl")
    )[0]["expected"]
    expected = json.loads(json.dumps(expected))
    expected["label_source"] = "synthetic_from_trusted_rubric"
    return {
        "case_id": case_id,
        "task_type": "generic",
        "context": {
            "messages_json": json.dumps([{"role": "user", "content": user_input}]),
            "runtime_json": "{}",
            "tool_context_json": "[]",
        },
        "expected": expected,
        "metadata": {
            "source": "synthetic_generation",
            "source_cluster": "generic-001",
            "dataset_version": layout.asset_id,
            "group_id": case_id,
            "request_id": case_id,
            "trust_tier": "synthetic",
            "review_status": "review_required",
        },
    }


def _install_synthetic_fixture(
    layout: EvaluationAssetLayout,
    *,
    candidates: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    accepted: list[dict[str, Any]],
) -> None:
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_candidates.jsonl",
        ),
        candidates,
    )
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "rejected_synthetic.jsonl",
        ),
        rejected,
    )
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_filter_issues.jsonl",
        ),
        issues,
    )
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl"),
        accepted,
    )
    train_synthetic = layout.artifact_path(
        PipelineStage.DATASET_SPLITS,
        "train_synthetic.jsonl",
    )
    train = layout.artifact_path(PipelineStage.DATASET_SPLITS, "train.jsonl")
    existing_train = _read_jsonl(train)
    artifact_io.atomic_write_jsonl(train_synthetic, accepted)
    artifact_io.atomic_write_jsonl(train, [*existing_train, *accepted])
    artifact_io.atomic_copy_file(train, layout.published_datasets / "train.jsonl")
    _set_manifest_split_count(layout, "train_synthetic", len(accepted))
    _set_manifest_split_count(layout, "train", len(existing_train) + len(accepted))


def _set_manifest_split_count(
    layout: EvaluationAssetLayout,
    split: str,
    count: int,
) -> None:
    manifest = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    manifest["split_counts"][split] = count
    artifact_io.atomic_write_json(layout.manifest_path, manifest)
    artifact_io.atomic_write_json(
        layout.artifact_path(PipelineStage.DATASET_SPLITS, "dataset_manifest.json"),
        manifest,
    )


def _downgrade_to_legacy_completed(layout: EvaluationAssetLayout) -> None:
    state = layout.load_state().to_dict()
    state.pop("schema_version", None)
    state.pop("mutation_sequence", None)
    state.pop("last_operation_id", None)
    state["status"] = "completed"
    for stage_state in state["stages"]:
        stage_state.pop("receipt_sha256", None)
    workspace_module.atomic_write_json(layout.state_path, state)
    for stage in PipelineStage:
        layout.receipt_path(stage).unlink()
        layout.stage_provenance_path(stage).unlink(missing_ok=True)
        layout.artifact_path(stage, "provider_calls.jsonl").unlink(missing_ok=True)
    layout.recovery_journal_path.unlink(missing_ok=True)
    layout.release_pointer_path.unlink(missing_ok=True)
    layout.build_provenance_path.unlink(missing_ok=True)
    layout.artifact_path(
        PipelineStage.DATASET_SPLITS,
        "generation_manifest.json",
    ).unlink(missing_ok=True)
    artifact_io.atomic_write_jsonl(
        layout.events_path,
        [
            event
            for event in _read_jsonl(layout.events_path)
            if event.get("event") != "pipeline_released"
        ],
    )
    if layout.generations_root.exists():
        shutil.rmtree(layout.generations_root)
    published_files = {}
    for split in ("train", "validation", "test", "regression_trusted"):
        destination = layout.published_datasets / f"{split}.jsonl"
        artifact_io.atomic_copy_file(
            layout.artifact_path(PipelineStage.DATASET_SPLITS, f"{split}.jsonl"),
            destination,
        )
        published_files[split] = destination.relative_to(
            layout.tenant_root
        ).as_posix()
    manifest = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    manifest["published_datasets"] = {
        "directory": layout.published_datasets.relative_to(
            layout.tenant_root
        ).as_posix(),
        "files": published_files,
    }
    artifact_io.atomic_write_json(layout.manifest_path, manifest)
    artifact_io.atomic_write_json(
        layout.artifact_path(PipelineStage.DATASET_SPLITS, "dataset_manifest.json"),
        manifest,
    )


def _make_released_checkpoint_mutable(
    layout: EvaluationAssetLayout,
) -> PipelineState:
    """Remove only the terminal publication authority for mutable-resume fixtures."""
    entries = _read_jsonl(layout.recovery_journal_path)
    publication = next(
        (
            row
            for row in reversed(entries)
            if row.get("kind") == "release_publication"
            and row.get("phase") == "prepared"
        ),
        None,
    )
    if publication is None:
        state = layout.load_state()
    else:
        operation_id = publication["operation_id"]
        retained = [
            row for row in entries if row.get("operation_id") != operation_id
        ]
        if retained:
            artifact_io.atomic_write_jsonl(layout.recovery_journal_path, retained)
        else:
            layout.recovery_journal_path.unlink(missing_ok=True)
        event_before = publication["audit"]["events"]["before"]
        prefix = layout.events_path.read_bytes()[: event_before["byte_length"]]
        if event_before["present"]:
            artifact_io.atomic_write_text(
                layout.events_path,
                prefix.decode("utf-8"),
            )
        else:
            layout.events_path.unlink(missing_ok=True)
        layout.release_pointer_path.unlink(missing_ok=True)
        state = PipelineState.from_dict(publication["before_state"])
    state.status = "failed"
    state.current_stage = None
    state.error = "interrupted test checkpoint"
    layout.save_state(state)
    return state
