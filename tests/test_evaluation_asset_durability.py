# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import ast
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pytest

from src.hephaestus import artifact_io, local_authority_io
from src.hephaestus.datasets import embedding_providers as embedding_provider_module
from src.hephaestus.datasets import rubric_providers as rubric_provider_module
from src.hephaestus.datasets.evaluation_assets import filter_synthetic_cases
from src.hephaestus.datasets.jsonl_loader import load_cases
from src.hephaestus.evaluation_assets import control_jsonl as control_jsonl_module
from src.hephaestus.evaluation_assets import durability as durability_module
from src.hephaestus.evaluation_assets import journal_transitions as journal_transitions_module
from src.hephaestus.evaluation_assets import journal_validation as journal_validation_module
from src.hephaestus.evaluation_assets import lineage_validation as lineage_validation_module
from src.hephaestus.evaluation_assets import models as evaluation_asset_models
from src.hephaestus.evaluation_assets import pipeline as pipeline_module
from src.hephaestus.evaluation_assets import provenance as provenance_module
from src.hephaestus.evaluation_assets import publication as publication_module
from src.hephaestus.evaluation_assets import review as review_module
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


class _DriftedPipelineStage(str, Enum):
    """A simulated future registry with changed membership and order."""

    FUTURE_STAGE = "future_stage"
    DATASET_SPLITS = "dataset_splits"
    RAW_INPUTS = "raw_inputs"
    PREPARED_INPUTS = "prepared_inputs"
    RUBRIC_EXTRACTION = "rubric_extraction"
    INTENT_CLUSTERING = "intent_clustering"
    COVERAGE_DECISIONS = "coverage_decisions"
    LABEL_INFERENCE = "label_inference"
    SYNTHETIC_COVERAGE = "synthetic_coverage"


class _RemovedHistoricalPipelineStage(str, Enum):
    """A future authoring registry with every historical member name removed."""

    FUTURE_STAGE = "future_stage"
    RAW_INPUTS_V3 = "raw_inputs_v3"
    PREPARED_INPUTS_V3 = "prepared_inputs_v3"
    GUIDELINE_CREATION_V3 = "guideline_creation_v3"
    INTENT_DISCOVERY_V3 = "intent_discovery_v3"
    COVERAGE_REVIEW_V3 = "coverage_review_v3"
    LABEL_CREATION_V3 = "label_creation_v3"
    SYNTHETIC_CREATION_V3 = "synthetic_creation_v3"
    SPLIT_CREATION_V3 = "split_creation_v3"


def _install_drifted_authoring_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Install one coherent simulated future authoring registry."""
    labels_by_value = {
        stage.value: label
        for stage, label in evaluation_asset_models.STAGE_LABELS.items()
    }
    counts_by_value = {
        stage.value: frozenset(keys)
        for stage, keys in evaluation_asset_models.STAGE_COUNT_KEYS.items()
    }
    drifted_labels = {
        stage: labels_by_value.get(stage.value, "Future authoring stage")
        for stage in _DriftedPipelineStage
    }
    drifted_counts = {
        stage: counts_by_value.get(stage.value, frozenset({"future_records"}))
        for stage in _DriftedPipelineStage
    }
    drifted_dependencies = {
        field: _DriftedPipelineStage(stage.value)
        for field, stage in evaluation_asset_models.CONFIG_STAGE_DEPENDENCIES.items()
    }
    for module in (
        evaluation_asset_models,
        durability_module,
        journal_transitions_module,
        journal_validation_module,
        workspace_module,
    ):
        monkeypatch.setattr(module, "PipelineStage", _DriftedPipelineStage)
    for module in (
        evaluation_asset_models,
        durability_module,
        journal_transitions_module,
        journal_validation_module,
    ):
        monkeypatch.setattr(module, "STAGE_COUNT_KEYS", drifted_counts)
    for module in (
        evaluation_asset_models,
        durability_module,
        journal_validation_module,
    ):
        monkeypatch.setattr(module, "STAGE_LABELS", drifted_labels)
    for module in (
        evaluation_asset_models,
        journal_transitions_module,
        journal_validation_module,
        workspace_module,
    ):
        monkeypatch.setattr(
            module,
            "CONFIG_STAGE_DEPENDENCIES",
            drifted_dependencies,
            raising=False,
        )


def _studio_persistence_paths(source_root: Path) -> tuple[Path, ...]:
    """Return the complete declared Studio production persistence boundary."""
    paths = {
        source_root / "artifact_io.py",
        source_root / "local_authority_io.py",
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
    *,
    seen: frozenset[str] = frozenset(),
) -> str:
    active_assignments = assignments or {}
    if isinstance(node, ast.NamedExpr):
        return _qualified_ast_name(
            node.value,
            aliases,
            active_assignments,
            seen=seen,
        )
    if isinstance(node, ast.Name):
        if node.id in active_assignments and node.id not in seen:
            return _qualified_ast_name(
                active_assignments[node.id],
                aliases,
                active_assignments,
                seen=seen | {node.id},
            )
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = _qualified_ast_name(
            node.value,
            aliases,
            active_assignments,
            seen=seen,
        )
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        call_name = _qualified_ast_name(
            node.func,
            aliases,
            active_assignments,
            seen=seen,
        )
        if call_name in {"globals", "builtins.globals"} and not node.args:
            return "globals"
        if call_name in {"locals", "builtins.locals"} and not node.args:
            return "locals"
        if call_name in {"vars", "builtins.vars"}:
            if not node.args:
                return "vars"
            if len(node.args) == 1:
                receiver = _qualified_ast_name(
                    node.args[0],
                    aliases,
                    active_assignments,
                    seen=seen,
                )
                return f"{receiver}.__dict__" if receiver else ""
        if (
            call_name
            in {
                "__import__",
                "builtins.__import__",
                "__builtins__.__import__",
                "importlib.import_module",
            }
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and (
                node.args[0].value.split(".", 1)[0] in _PERSISTENCE_MODULES
                or node.args[0].value == "importlib"
            )
        ):
            return node.args[0].value
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    ):
        container = ""
        if (
            isinstance(node.value, ast.Call)
            and _qualified_ast_name(
                node.value.func,
                aliases,
                active_assignments,
                seen=seen,
            )
            in {"vars", "builtins.vars"}
            and len(node.value.args) == 1
        ):
            container = _qualified_ast_name(
                node.value.args[0],
                aliases,
                active_assignments,
                seen=seen,
            )
        else:
            container = _qualified_ast_name(
                node.value,
                aliases,
                active_assignments,
                seen=seen,
            )
            if container.endswith(".__dict__"):
                container = container.removesuffix(".__dict__")
        return (
            f"{container}.{node.slice.value}"
            if container
            else node.slice.value
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        in {"__getattribute__", "__getitem__", "get", "pop", "setdefault"}
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        receiver = _qualified_ast_name(
            node.func.value,
            aliases,
            active_assignments,
            seen=seen,
        )
        if node.func.attr in {"get", "pop", "setdefault", "__getitem__"}:
            literal_name = node.args[0].value
            mapping_receiver = receiver.removesuffix(".__dict__")
            if mapping_receiver in {
                "globals",
                "locals",
                "vars",
                "sys.modules",
            }:
                return (
                    literal_name
                    if literal_name.split(".", 1)[0] in _PERSISTENCE_MODULES
                    else ""
                )
            if mapping_receiver in {"builtins", "__builtins__"}:
                return (
                    "builtins.__import__"
                    if literal_name == "__import__"
                    else ""
                )
            if not receiver.endswith(".__dict__"):
                return ""
        receiver = receiver.removesuffix(".__dict__")
        return (
            f"{receiver}.{node.args[0].value}"
            if receiver
            else node.args[0].value
        )
    if (
        isinstance(node, ast.Call)
        and _qualified_ast_name(
            node.func,
            aliases,
            active_assignments,
            seen=seen,
        )
        in {"getattr", "builtins.getattr"}
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        receiver = _qualified_ast_name(
            node.args[0],
            aliases,
            active_assignments,
            seen=seen,
        )
        return (
            f"{receiver}.{node.args[1].value}"
            if receiver
            else node.args[1].value
        )
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
    "mkdir",
    "rename",
    "replace",
    "rmdir",
    "touch",
    "truncate",
    "unlink",
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
    "shutil.rmtree",
}
_PERSISTENCE_LOW_LEVEL_SINKS = {
    "ctypes.CDLL",
    "os.copy_file_range",
    "os.ftruncate",
    "os.makedirs",
    "os.mkdir",
    "os.remove",
    "os.removedirs",
    "os.rmdir",
    "os.pwrite",
    "os.pwritev",
    "os.rename",
    "os.replace",
    "os.sendfile",
    "os.splice",
    "os.truncate",
    "os.unlink",
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
_OPERATOR_ATTRIBUTE_FACTORIES = {
    "operator.attrgetter",
    "operator.methodcaller",
}
_OPERATOR_ATTRIBUTE_FACTORY_IMPORTS = {
    qualified.rsplit(".", 1)[-1]: qualified
    for qualified in _OPERATOR_ATTRIBUTE_FACTORIES
}
_PERSISTENCE_OPERATOR_ATTRIBUTES = frozenset(
    _PERSISTENCE_METHOD_SINKS
    | {
        qualified.rsplit(".", 1)[-1]
        for qualified in (
            _PERSISTENCE_COPY_SINKS
            | _PERSISTENCE_LOW_LEVEL_SINKS
            | _PERSISTENCE_DUMP_SINKS
            | _PERSISTENCE_CSV_FACTORIES
        )
    }
    | {"dump", "open", "safe_dump"}
)
_PERSISTENCE_MODULES = {
    "builtins",
    "csv",
    "ctypes",
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
    "_normalize_aliased_guideline_response",
    "_normalize_applicability_response",
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
    parts = name.split(".")
    for index, part in enumerate(parts[1:], 1):
        reexported_module = part.removeprefix("_")
        if (
            reexported_module in _PERSISTENCE_MODULES
            and index + 1 < len(parts)
        ):
            canonical_module = (
                "os"
                if reexported_module in {"nt", "posix"}
                else reexported_module
            )
            return canonical_module + "." + ".".join(parts[index + 1 :])
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


def _literal_operator_persistence_attribute(
    call: ast.Call,
    qualified_factory: str,
    assignments: Mapping[str, ast.AST],
) -> str | None:
    """Resolve only literal persistence attributes from finite operator factories."""
    if qualified_factory not in _OPERATOR_ATTRIBUTE_FACTORIES or not call.args:
        return None
    candidates = (
        call.args
        if qualified_factory == "operator.attrgetter"
        else call.args[:1]
    )
    for candidate in candidates:
        resolved = _assigned_ast_node(candidate, assignments)
        if not isinstance(resolved, ast.Constant) or not isinstance(
            resolved.value,
            str,
        ):
            continue
        attribute = resolved.value.rsplit(".", 1)[-1]
        if attribute in _PERSISTENCE_OPERATOR_ATTRIBUTES:
            return attribute
    return None


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


def _visible_persistence_references(tree: ast.AST) -> list[tuple[ast.AST, str]]:
    """Return declared writer references that escape direct-call inspection."""
    aliases: dict[str, str] = {}
    imported_sinks: list[tuple[ast.AST, str]] = []
    for candidate in ast.walk(tree):
        if isinstance(candidate, ast.Import):
            for item in candidate.names:
                name = item.asname or item.name.split(".", 1)[0]
                if item.name.split(".", 1)[0] in _PERSISTENCE_MODULES:
                    aliases.setdefault(name, item.name)
        elif isinstance(candidate, ast.ImportFrom) and candidate.module:
            for item in candidate.names:
                if item.name == "*" and candidate.module == "operator":
                    for name, qualified in (
                        _OPERATOR_ATTRIBUTE_FACTORY_IMPORTS.items()
                    ):
                        aliases.setdefault(name, qualified)
                    continue
                if (
                    item.name == "*"
                    and candidate.module.split(".", 1)[0]
                    in _PERSISTENCE_MODULES
                ):
                    imported_sinks.append(
                        (candidate, f"{candidate.module}.*")
                    )
                    continue
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
                    imported_sinks.append((candidate, qualified))

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
        raw_qualified = _qualified_ast_name(candidate, aliases)
        qualified = _canonical_sink_name(raw_qualified)
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
            and not parent.args[1].value.startswith("__")
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
        direct_module_attribute = (
            isinstance(parent, ast.Attribute)
            and parent.value is candidate
            and not parent.attr.startswith("__")
        )
        persistence_rooted = (
            raw_qualified.split(".", 1)[0] in _PERSISTENCE_MODULES
        )
        dunder_module_traversal = persistence_rooted and (
            isinstance(candidate, ast.Attribute)
            and candidate.attr.startswith("__")
            or isinstance(parent, ast.Call)
            and parent.args
            and parent.args[0] is candidate
            and _qualified_ast_name(parent.func, aliases)
            in {"getattr", "builtins.getattr"}
            and len(parent.args) >= 2
            and isinstance(parent.args[1], ast.Constant)
            and isinstance(parent.args[1].value, str)
            and parent.args[1].value.startswith("__")
        )
        module_escape = (
            qualified in _PERSISTENCE_MODULES
            or isinstance(candidate, ast.Name)
            and candidate.id in module_alias_names
            or dunder_module_traversal
        ) and not direct_module_attribute and not simple_module_alias and not (
            safe_module_introspection
        )
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
                    candidate,
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
            if item.name == "*" and node.module == "operator":
                for name, qualified in (
                    _OPERATOR_ATTRIBUTE_FACTORY_IMPORTS.items()
                ):
                    self.bindings.pop(name, None)
                    self.aliases[name] = qualified
                continue
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
    """Record the exact runtime definition stack enclosing each AST node."""

    def __init__(self) -> None:
        self.stack: list[tuple[str, str]] = []
        self.calls: dict[int, tuple[tuple[str, str], ...]] = {}
        self.contexts: dict[int, tuple[tuple[str, str], ...]] = {}

    def visit(self, node: ast.AST) -> Any:
        self.contexts[id(node)] = tuple(self.stack)
        return super().visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(("class_header", node.name))
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.stack.pop()
        self.stack.append(("class", node.name))
        for statement in node.body:
            self.visit(statement)
        self.stack.pop()

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        kind: str,
    ) -> None:
        self.stack.append((f"{kind}_header", node.name))
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.visit(node.args)
        if node.returns is not None:
            self.visit(node.returns)
        self.stack.pop()
        self.stack.append((kind, node.name))
        for statement in node.body:
            self.visit(statement)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, kind="function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, kind="async_function")

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.stack.append(("lambda_header", f"{node.lineno}:{node.col_offset}"))
        self.visit(node.args)
        self.stack.pop()
        self.stack.append(("lambda", f"{node.lineno}:{node.col_offset}"))
        self.visit(node.body)
        self.stack.pop()

    def _visit_comprehension_scope(
        self,
        node: ast.GeneratorExp | ast.ListComp | ast.SetComp | ast.DictComp,
    ) -> None:
        """Keep implicit comprehension execution outside audited body seams."""
        name = f"{type(node).__name__}:{node.lineno}:{node.col_offset}"
        self.stack.append(("comprehension", name))
        self.generic_visit(node)
        self.stack.pop()

    visit_GeneratorExp = _visit_comprehension_scope
    visit_ListComp = _visit_comprehension_scope
    visit_SetComp = _visit_comprehension_scope
    visit_DictComp = _visit_comprehension_scope

    def visit_Call(self, node: ast.Call) -> None:
        self.calls[id(node)] = tuple(self.stack)
        self.generic_visit(node)


def _call_function_contexts(
    tree: ast.AST,
) -> tuple[
    dict[int, tuple[tuple[str, str], ...]],
    dict[int, tuple[tuple[str, str], ...]],
]:
    collector = _FunctionContextCollector()
    collector.visit(tree)
    return collector.calls, collector.contexts


_AUDITED_ARTIFACT_PRODUCER_OWNERS = frozenset(
    {
        "atomic_append_jsonl",
        "atomic_copy_file",
        "atomic_write_json",
        "atomic_write_jsonl",
        "atomic_write_text",
    }
)


def _inside_exact_top_level_function(
    context: tuple[tuple[str, str], ...],
    names: set[str],
    definition_counts: Mapping[tuple[tuple[str, str], ...], int],
) -> bool:
    """Require one unique audited body or its exact producer closure."""
    if not context or context[0][0] != "function":
        return False
    owner = context[0][1]
    owner_context = (("function", owner),)
    if owner not in names or definition_counts.get(owner_context) != 1:
        return False
    return context == owner_context or (
        owner in _AUDITED_ARTIFACT_PRODUCER_OWNERS
        and context == (*owner_context, ("function", "produce"))
        and definition_counts.get(context) == 1
    )


def _inside_exact_handler_method(
    context: tuple[tuple[str, str], ...],
    definition_counts: Mapping[tuple[tuple[str, str], ...], int],
) -> bool:
    """Require one unique audited server class and method definition."""
    if len(context) != 2:
        return False
    class_context = (("class", "_Handler"),)
    return bool(
        context[0] == class_context[0]
        and context[1][0] == "function"
        and context[1][1] in {"_send_file", "_send_html", "_send_json"}
        and definition_counts.get(class_context) == 1
        and definition_counts.get(context) == 1
    )


def _has_only_literal_true_keywords(
    call: ast.Call,
    names: set[str],
) -> bool:
    """Match one direct no-positional call with exact literal-true options."""
    return bool(
        not call.args
        and len(call.keywords) == len(names)
        and {keyword.arg for keyword in call.keywords} == names
        and all(
            isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in call.keywords
        )
    )


def _studio_writer_violations(path: Path, source: str) -> list[str]:
    """Find direct persistence calls, resolving qualified and imported aliases."""
    tree = ast.parse(source, filename=str(path))
    call_bindings, sink_store_lines = _call_binding_snapshots(tree)
    function_contexts, node_contexts = _call_function_contexts(tree)
    parents = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    definition_counts: dict[tuple[tuple[str, str], ...], int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            kind = "function"
        elif isinstance(node, ast.AsyncFunctionDef):
            kind = "async_function"
        elif isinstance(node, ast.ClassDef):
            kind = "class"
        else:
            continue
        context = (
            *node_contexts.get(id(node), ()),
            (kind, node.name),
        )
        definition_counts[context] = definition_counts.get(context, 0) + 1

    path_text = path.as_posix()
    artifact_seam = path_text.endswith("src/hephaestus/artifact_io.py")
    publication_seam = path_text.endswith(
        "src/hephaestus/evaluation_assets/publication.py"
    )
    control_seam = path_text.endswith(
        "src/hephaestus/evaluation_assets/control_jsonl.py"
    )
    authority_adapter_seam = path_text.endswith(
        "src/hephaestus/local_authority_io.py"
    )
    deprecated_assembler_seam = path_text.endswith(
        "src/hephaestus/datasets/evaluation_assets.py"
    )
    artifact_contexts = {
        "atomic_append_jsonl",
        "atomic_copy_file",
        "atomic_write_bytes_at",
        "atomic_write_json",
        "atomic_write_jsonl",
        "atomic_write_text",
        "_atomic_write_binary",
        "_atomic_write_text",
        "sync_directory",
    }
    violations: list[str] = [
        f"{path.name}:{line}:os.write" for line in sink_store_lines
    ]
    for reference, operation in _visible_persistence_references(tree):
        line = reference.lineno
        parent = parents.get(id(reference))
        grandparent = parents.get(id(parent)) if parent is not None else None
        direct_dynamic_call = (
            operation.endswith(".*")
            and isinstance(parent, ast.Call)
            and parent.args
            and parent.args[0] is reference
            and len(parent.args) >= 2
            and isinstance(parent.args[1], ast.Constant)
            and isinstance(parent.args[1].value, str)
            and isinstance(grandparent, ast.Call)
            and grandparent.func is parent
        )
        function_context = node_contexts.get(id(reference), ())
        if direct_dynamic_call and (
            artifact_seam
            and _inside_exact_top_level_function(
                function_context,
                artifact_contexts,
                definition_counts,
            )
            or publication_seam
            and _inside_exact_top_level_function(
                function_context,
                {"install_generation"},
                definition_counts,
            )
        ):
            continue
        violations.append(f"{path.name}:{line}:{operation}")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_context = function_contexts.get(id(node), ())
        artifact_function = (
            artifact_seam
            and _inside_exact_top_level_function(
                function_context,
                artifact_contexts,
                definition_counts,
            )
        )
        legacy_temp_cleanup_function = (
            artifact_seam
            and _inside_exact_top_level_function(
                function_context,
                {"_atomic_write_text", "_atomic_write_binary"},
                definition_counts,
            )
        )
        bound_descriptor_function = (
            artifact_seam
            and _inside_exact_top_level_function(
                function_context,
                {"atomic_write_bytes_at"},
                definition_counts,
            )
        )
        publication_function = (
            publication_seam
            and _inside_exact_top_level_function(
                function_context,
                {"install_generation"},
                definition_counts,
            )
        )
        native_rename_function = (
            artifact_seam
            and _inside_exact_top_level_function(
                function_context,
                {"_rename_with_flags_at"},
                definition_counts,
            )
        )
        local_lock_function = (
            control_seam
            and _inside_exact_top_level_function(
                function_context,
                {"acquire_local_authority_lock"},
                definition_counts,
            )
        )
        bound_directory_creation_function = (
            control_seam
            and _inside_exact_top_level_function(
                function_context,
                {"create_and_open_local_directory_at"},
                definition_counts,
            )
        )
        authority_adapter_open_child_file_function = (
            authority_adapter_seam
            and _inside_exact_top_level_function(
                function_context,
                {"open_child_file"},
                definition_counts,
            )
        )
        deprecated_assembler_function = (
            deprecated_assembler_seam
            and _inside_exact_top_level_function(
                function_context,
                {"assemble_dataset_bundle"},
                definition_counts,
            )
        )
        server_function = path_text.endswith(
            "src/hephaestus/webui/server.py"
        ) and _inside_exact_handler_method(
            function_context,
            definition_counts,
        )
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
        operator_attribute = _literal_operator_persistence_attribute(
            inspected_call,
            qualified,
            assignments,
        )
        if operator_attribute is not None:
            violations.append(
                f"{path.name}:{node.lineno}:{qualified}({operator_attribute})"
            )
            continue
        literal_bound_directory_mkdir = (
            bound_directory_creation_function
            and qualified == "os.mkdir"
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "mkdir"
            and len(node.args) == 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "private_name"
            and isinstance(node.args[1], ast.Name)
            and node.args[1].id == "private_mode"
            and len(node.keywords) == 1
            and node.keywords[0].arg == "dir_fd"
            and isinstance(node.keywords[0].value, ast.Name)
            and node.keywords[0].value.id == "parent_descriptor"
        )
        literal_artifact_parent_mkdir = (
            legacy_temp_cleanup_function
            and attribute == "mkdir"
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "mkdir"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "parent"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "path"
            and _has_only_literal_true_keywords(
                node,
                {"parents", "exist_ok"},
            )
        )
        literal_deprecated_assembler_mkdir = (
            deprecated_assembler_function
            and attribute == "mkdir"
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "mkdir"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "output_dir"
            and _has_only_literal_true_keywords(
                node,
                {"parents", "exist_ok"},
            )
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
                call_parent = parents.get(id(node))
                direct_method_invocation = (
                    isinstance(call_parent, ast.Call)
                    and call_parent.func is node
                )
                allowed = (
                    artifact_function
                    and direct_method_invocation
                    and (
                        sink in _PERSISTENCE_DUMP_SINKS
                        or sink == "shutil.copyfileobj"
                        or sink == "tempfile.NamedTemporaryFile"
                        or sink == "os.replace"
                        or method_node.value in {"write", "writelines", "truncate"}
                    )
                ) or (
                    publication_function
                    and direct_method_invocation
                    and sink == "os.rename"
                ) or (
                    server_function
                    and direct_method_invocation
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
            ) or (
                bound_descriptor_function
                and qualified in {"os.write", "os.replace"}
            ) or (
                native_rename_function and qualified == "ctypes.CDLL"
            ) or (
                authority_adapter_seam
                and any(
                    qualified == operation
                    and _inside_exact_top_level_function(
                        function_context,
                        {function_name},
                        definition_counts,
                    )
                    for function_name, operation in (
                        ("_rename_with_flags_posix", "ctypes.CDLL"),
                        ("create_child_directory", "os.mkdir"),
                        (
                            "_discard_just_created_node_locked",
                            "os.unlink",
                        ),
                        (
                            "_discard_just_created_node_locked",
                            "os.rmdir",
                        ),
                        ("_reclaim_owned_leaf_locked", "os.unlink"),
                        ("_reclaim_owned_tree_locked", "os.rmdir"),
                        ("write_bound_file", "os.write"),
                    )
                )
            ) or (
                literal_bound_directory_mkdir
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
            if status is not False and not (
                bound_descriptor_function
                or local_lock_function
                or authority_adapter_open_child_file_function
            ):
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
            "mkdir",
            "rmdir",
            "unlink",
            "write",
            "writeheader",
            "writerow",
            "writerows",
            "writelines",
            "truncate",
        }:
            literal_legacy_temp_unlink = (
                legacy_temp_cleanup_function
                and attribute == "unlink"
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "unlink"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "temporary_path"
                and not node.args
                and len(node.keywords) == 1
                and node.keywords[0].arg == "missing_ok"
                and isinstance(node.keywords[0].value, ast.Constant)
                and node.keywords[0].value.value is True
            )
            allowed = (
                artifact_function
                and attribute in {"write", "writelines", "truncate"}
            ) or literal_legacy_temp_unlink or literal_artifact_parent_mkdir or (
                literal_deprecated_assembler_mkdir
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
        "local_authority_io.py",
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
        (
            "from os import *\nwrite(fd, b'body')",
            "os",
        ),
        (
            "from os import *\nconsumer(write)",
            "os",
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
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "class atomic_write_json:\n"
            "    def unauthorized(self):\n"
            "        os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "class install_generation:\n"
            "    def unauthorized(self):\n"
            "        os.rename(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    class Rogue:\n"
            "        def persist(self):\n"
            "            os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "def install_generation():\n"
            "    class Rogue:\n"
            "        def persist(self):\n"
            "            os.rename(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    def persist():\n"
            "        os.replace(source, target)\n"
            "    return persist",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json(result=os.replace(source, target)):\n"
            "    pass",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "@os.replace(source, target)\n"
            "def atomic_write_json():\n"
            "    pass",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "def install_generation(result=os.rename(source, target)):\n"
            "    pass",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "@os.rename(source, target)\n"
            "def install_generation():\n"
            "    pass",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    pass\n"
            "def atomic_write_json():\n"
            "    os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def atomic_write_json():\n"
            "    return getattr(handle, 'write')",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def atomic_write_json():\n"
            "    consumer(getattr(handle, 'write'))",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "def install_generation():\n"
            "    pass\n"
            "def install_generation():\n"
            "    os.rename(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return lambda: os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    def produce(handle):\n"
            "        pass\n"
            "    def produce(handle):\n"
            "        os.replace(source, target)\n"
            "    return produce",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    if condition:\n"
            "        def produce(handle):\n"
            "            pass\n"
            "    else:\n"
            "        def produce(handle):\n"
            "            os.replace(source, target)\n"
            "    return produce",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def atomic_write_json():\n"
            "    from os import *\n"
            "    write(descriptor, b'body')",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def atomic_write_json():\n"
            "    from os import *\n"
            "    consumer(write)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "def install_generation():\n"
            "    from os import *\n"
            "    rename(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return os.write",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return {'writers': [os.write]}",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return os.write\n"
            "sink = atomic_write_json()\n"
            "sink(descriptor, b'body')",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import ctypes\n"
            "def _rename_with_flags_at():\n"
            "    pass\n"
            "def _rename_with_flags_at():\n"
            "    ctypes.CDLL(None)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_bytes_at():\n"
            "    pass\n"
            "def atomic_write_bytes_at():\n"
            "    os.write(descriptor, b'body')",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_bytes_at():\n"
            "    pass\n"
            "def atomic_write_bytes_at():\n"
            "    os.open(name, os.O_WRONLY)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_bytes_at():\n"
            "    pass\n"
            "def atomic_write_bytes_at():\n"
            "    os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "import os\n"
            "def remove_local_authority_file():\n"
            "    class Rogue:\n"
            "        def remove(self):\n"
            "            os.unlink(target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "def remove_local_authority_file():\n"
            "    from os import *\n"
            "    unlink(target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    def produce(handle, result=os.replace(source, target)):\n"
            "        pass",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    @os.replace(source, target)\n"
            "    def produce(handle):\n"
            "        pass",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    def unrelated(result=os.replace(source, target)):\n"
            "        pass",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    @os.replace(source, target)\n"
            "    class Rogue:\n"
            "        pass",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "class _Handler:\n"
            "    def _send_json(self):\n"
            "        pass\n"
            "    def _send_json(self):\n"
            "        self.wfile.write(body)",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "class _Handler:\n"
            "    def _send_json(self):\n"
            "        pass\n"
            "class _Handler:\n"
            "    def _send_json(self):\n"
            "        self.wfile.write(body)",
        ),
        (
            Path("src/hephaestus/webui/server.py"),
            "class _Handler:\n"
            "    def _send_json(self):\n"
            "        def nested(result=self.wfile.write(body)):\n"
            "            pass",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_bytes_at():\n"
            "    return (os.write(descriptor, body) for body in values)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return (os.replace(source, target) for _ in values)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    def produce(handle):\n"
            "        return (os.replace(source, target) for _ in values)\n"
            "    return produce",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return [os.replace(source, target) for _ in values]",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return {os.replace(source, target) for _ in values}",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    return {key: os.replace(source, target) for key in values}",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    name = 'write'\n"
            "    getattr(os, name)(descriptor, body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    def produce(handle):\n"
            "        name = 'replace'\n"
            "        getattr(os, name)(source, target)\n"
            "    return produce",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "def install_generation():\n"
            "    name = 'rename'\n"
            "    getattr(os, name)(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os as operating_system\n"
            "def atomic_write_json():\n"
            "    method = 'replace'\n"
            "    getattr(operating_system, method)(source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    os.__dict__['write'](descriptor, body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    os.__getattribute__('write')(descriptor, body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os as operating_system\n"
            "def atomic_write_json():\n"
            "    operating_system.__dict__['replace'](source, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    getattr(os, '__dict__')['write'](descriptor, body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    getattr(os, '__class__').__getattribute__(os, 'write')"
            "(descriptor, body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    os.path.os.write(descriptor, body)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import shutil\n"
            "def atomic_write_json():\n"
            "    shutil.os.write(descriptor, body)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/pipeline.py"),
            "import tempfile\n"
            "def unauthorized():\n"
            "    tempfile._shutil.copyfile(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/pipeline.py"),
            "import tempfile\n"
            "def unauthorized():\n"
            "    tempfile._os.sendfile(target_fd, source_fd, 0, count)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/pipeline.py"),
            "import tempfile\n"
            "def unauthorized():\n"
            "    getattr(tempfile, '_shutil').copyfile(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/pipeline.py"),
            "import tempfile\n"
            "def unauthorized():\n"
            "    getattr(tempfile, '_os').pwrite(descriptor, body, 0)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/pipeline.py"),
            "import shutil\n"
            "def unauthorized():\n"
            "    getattr(shutil, 'os').pwrite(descriptor, body, 0)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/pipeline.py"),
            "import os\n"
            "def unauthorized():\n"
            "    getattr(os.path, 'os').pwrite(descriptor, body, 0)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/example.py"),
            "import os\n"
            "os.path.__dict__['os'].__dict__['pwrite'](descriptor, body, 0)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/example.py"),
            "import os\n"
            "getattr(os.path, '__dict__')['os'].__dict__['pwrite']"
            "(descriptor, body, 0)",
        ),
        *(
            (
                Path("src/hephaestus/evaluation_assets/example.py"),
                "import os\n" + expression,
            )
            for expression in (
                "os.path.__getattribute__('os').pwrite(descriptor, body, 0)",
                "os.path.__dict__.get('os').pwrite(descriptor, body, 0)",
                "vars(os.path)['os'].pwrite(descriptor, body, 0)",
            )
        ),
        *(
            (
                Path("src/hephaestus/artifact_io.py"),
                "import os\ndef atomic_write_json():\n    " + expression,
            )
            for expression in (
                "os.path.__getattribute__('os').pwrite(descriptor, body, 0)",
                "os.path.__dict__.get('os').pwrite(descriptor, body, 0)",
                "vars(os.path)['os'].pwrite(descriptor, body, 0)",
            )
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "async def atomic_write_bytes_at():\n"
            "    os.write(descriptor, body)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "async def install_generation():\n"
            "    os.rename(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "import os\n"
            "async def remove_local_authority_file():\n"
            "    os.unlink(target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    async def produce(handle):\n"
            "        os.replace(source, target)\n"
            "    return produce",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import os\n"
            "def atomic_write_json():\n"
            "    pass\n"
            "async def atomic_write_json():\n"
            "    os.replace(source, target)",
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
            "    getattr(os, 'replace')(source, target)\n"
            "def atomic_write_bytes_at():\n"
            "    os.open(name, os.O_WRONLY)\n"
            "    os.write(descriptor, b'body')\n"
            "    os.replace(source, target)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/publication.py"),
            "import os\n"
            "def install_generation():\n"
            "    os.rename(temporary, target)\n"
            "    getattr(os, 'rename')(temporary, target)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import ctypes\n"
            "def _rename_with_flags_at():\n"
            "    ctypes.CDLL(None)",
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


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os').pwrite(fd, body, 0)",
        "getattr(__import__('os'), 'pwrite')(fd, body, 0)",
        "import importlib\nimportlib.import_module('os').pwrite(fd, body, 0)",
        "import os\nglobals().get('os').pwrite(fd, body, 0)",
        "import sys\nsys.modules.get('os').pwrite(fd, body, 0)",
        "import os\nglobals().__getitem__('os').pwrite(fd, body, 0)",
        "import os\nlocals().get('os').pwrite(fd, body, 0)",
        "import os\nvars().get('os').pwrite(fd, body, 0)",
        "import os\nglobals().pop('os').pwrite(fd, body, 0)",
        "import sys\nsys.modules.pop('os').pwrite(fd, body, 0)",
        "import sys\nsys.modules.setdefault('os').pwrite(fd, body, 0)",
        "__builtins__['__import__']('os').pwrite(fd, body, 0)",
        "__builtins__.get('__import__')('os').pwrite(fd, body, 0)",
        "vars(__builtins__).get('__import__')('os').pwrite(fd, body, 0)",
        "__import__('importlib').import_module('os').pwrite(fd, body, 0)",
        "getattr(__import__('importlib'), 'import_module')('os').pwrite(fd, body, 0)",
    ],
)
def test_studio_writer_guard_rejects_literal_module_namespace_escapes(
    source: str,
) -> None:
    """Literal imports and runtime module namespaces cannot hide finite sinks."""
    violations = _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/pipeline.py"),
        source,
    )

    assert violations


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


def test_pr2_pipeline_state_preserves_positional_constructor_contract() -> None:
    """The exported state model keeps its historical status positional slot."""
    queued = PipelineState("tenant_a", "v1")
    running = PipelineState("tenant_a", "v1", "running")
    keyword = PipelineState(
        tenant_id="tenant_a",
        asset_id="v1",
        status="failed",
        schema_version=STATE_SCHEMA_VERSION,
    )

    assert queued.status == "queued"
    assert queued.schema_version == STATE_SCHEMA_VERSION
    assert running.status == "running"
    assert running.schema_version == STATE_SCHEMA_VERSION
    assert keyword.to_dict()["status"] == "failed"
    assert PipelineState.new(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        "2026-08-21T00:00:00+00:00",
    ).status == "draft"


@pytest.mark.parametrize("schema_version", [None, "", "running", "future-v3"])
def test_pr2_pipeline_state_serializer_rejects_every_unknown_schema(
    schema_version: Any,
) -> None:
    """Direct model construction cannot serialize an unsupported state schema."""
    state = PipelineState("tenant_a", "v1", status="running")
    state.schema_version = schema_version  # type: ignore[assignment]

    with pytest.raises(ValueError, match="state schema"):
        state.to_dict()


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


def test_asset_lock_is_reentrant_for_nested_same_thread_callers(
    tmp_path: Path,
) -> None:
    """Public nested mutation helpers reuse one exact outer asset lock."""
    (tmp_path / "tenants").mkdir()
    layout = EvaluationAssetLayout(
        tmp_path / "tenants",
        "tenant_a",
        "v1",
        repository_base=tmp_path,
    )

    with layout.asset_lock():
        with layout.asset_lock():
            assert layout.lock_path.is_file()


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
            _run_to_release(pipeline)
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

    monkeypatch.chdir(tmp_path)
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

        manager = EvaluationAssetRunManager(
            tenants_root,
            repository_base=tmp_path,
        )
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
    manager = EvaluationAssetRunManager(
        tenants_root,
        repository_base=tmp_path,
    )
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
    manager = EvaluationAssetRunManager(
        tenants_root,
        repository_base=tmp_path,
    )
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
    _run_to_release(pipeline)
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
    manager = EvaluationAssetRunManager(
        layout.tenants_root,
        repository_base=layout.repository_base,
    )
    expected = (
        EvaluationAssetImmutableError
        if condition == "released"
        else EvaluationAssetIntegrityError
    )

    with pytest.raises(expected):
        manager.resume(layout.tenant_id, layout.asset_id)

    assert not manager.is_running(layout.tenant_id, layout.asset_id)


def test_service_accepts_terminal_release_recovery_and_cleans_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real prepared release roll-forward is an admitted completed resume."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def stop_after_release_prepare(name: str) -> None:
        if name == "after_release_publication_prepared":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_release_prepare)
    with pytest.raises(_InjectedFault, match="after_release_publication_prepared"):
        _run_to_release(pipeline)
    layout = pipeline.layout
    rows = _read_jsonl(layout.recovery_journal_path)
    assert rows[-1]["phase"] == "prepared"
    assert rows[-1]["kind"] == "release_publication"
    monkeypatch.setattr(workspace_module, "_fault_point", lambda _name: None)
    manager = EvaluationAssetRunManager(
        layout.tenants_root,
        repository_base=layout.repository_base,
    )

    response = manager.resume(layout.tenant_id, layout.asset_id)

    assert response["status"] == "released"
    deadline = time.monotonic() + 2
    while manager.is_running(layout.tenant_id, layout.asset_id):
        if time.monotonic() >= deadline:
            pytest.fail("terminal recovery worker did not clear its registry entry")
        time.sleep(0.01)
    with manager._lock:
        assert (layout.tenant_id, layout.asset_id) not in manager._threads
    verify_released_asset(layout, layout.load_state())


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
        repository_base=tmp_path,
    )
    _run_to_release(parent_pipeline)
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
    manager = EvaluationAssetRunManager(
        tenants_root,
        repository_base=tmp_path,
    )
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
        repository_base=tmp_path,
    )

    assert constructed == []
    released = _run_to_release(pipeline, config_updates={"rubric_model": "new-rubric"})

    assert released.status == "released"
    assert constructed
    assert set(constructed) == {"new-rubric"}
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
        repository_base=tmp_path,
        rubric_provider=_SuccessfulRubricProvider(),
    )

    assert constructed == []
    released = _run_to_release(pipeline, config_updates={"embedding_model": revised_model})

    assert released.status == "released"
    assert bool(constructed) is bool(expected_models)
    assert set(constructed) == set(expected_models)
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

    _run_to_release(pipeline)

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
    ) + _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "protected_feedback_evidence.jsonl",
        )
    )
    guidelines = _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
    ) + _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "protected_evaluation_guidelines.jsonl",
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
    assert {row["rubric_model"] for row in inferred} == {"actual-rubric"}


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
        _run_to_release(pipeline)
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
    released = _run_to_release(
        EvaluationAssetPipeline(
            pipeline.layout,
            rubric_provider=changed_rubric,
            embedding_provider=embedding,
        )
    )

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
    released = _run_to_release(pipeline)
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
        repository_base=tmp_path,
    )
    before = _authority_bytes(pipeline.layout)

    with pytest.raises(ValueError, match="injected rubric provider identity is unavailable"):
        _run_to_release(pipeline)

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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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

    released = _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=rubric,
            embedding_provider=new_embedding,
        )
    )

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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
        repository_base=tmp_path,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
        _run_to_release(pipeline)

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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
        repository_base=tmp_path,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    _run_to_release(pipeline)
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
        ready = threading.Event()
        release = threading.Event()
        holder_errors: list[BaseException] = []

        def hold_from_another_thread() -> None:
            try:
                with layout.asset_lock():
                    ready.set()
                    if not release.wait(timeout=5):
                        raise RuntimeError("busy-lock test holder timed out")
            except BaseException as exc:
                holder_errors.append(exc)

        holder = threading.Thread(target=hold_from_another_thread)
        holder.start()
        assert ready.wait(timeout=2)
        try:
            with pytest.raises(EvaluationAssetBusyError):
                _run_to_release(candidate)
        finally:
            release.set()
            holder.join(timeout=2)
        assert not holder.is_alive()
        assert holder_errors == []
    elif rejection == "released":
        with pytest.raises(EvaluationAssetImmutableError):
            _run_to_release(candidate)
    else:
        with pytest.raises(EvaluationAssetIntegrityError):
            _run_to_release(candidate)


def test_stage_specification_exhaustively_declares_required_artifacts() -> None:
    """One declarative map covers every current stage-owned release artifact."""
    expected = {
        PipelineStage.RAW_INPUTS: {"input_manifest.json"},
        PipelineStage.PREPARED_INPUTS: {
            "normalized_feedback.jsonl",
            "intent_records.jsonl",
            "trusted_split_plan.jsonl",
            "feedback_eligibility.jsonl",
        },
        PipelineStage.RUBRIC_EXTRACTION: {
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
            "protected_feedback_evidence.jsonl",
            "protected_candidate_guidelines.jsonl",
            "protected_evaluation_guidelines.jsonl",
            "protected_trusted_cases.jsonl",
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
            "inference_dependencies.jsonl",
            "held_inference_outputs.jsonl",
        },
        PipelineStage.SYNTHETIC_COVERAGE: {
            "synthetic_candidates.jsonl",
            "rejected_synthetic.jsonl",
            "synthetic_filter_issues.jsonl",
            "synthetic_cases.jsonl",
            "synthetic_dependencies.jsonl",
            "derived_review_items.jsonl",
            "duplicate_families.jsonl",
            "held_derived_cases.jsonl",
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
            "review_snapshot.json",
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

    state = _run_to_release(pipeline)

    assert state.status == "released"
    assert state.schema_version == STATE_SCHEMA_VERSION
    assert all(stage.status == "completed" for stage in state.stages)
    assert rubric.calls > 0
    assert embedding.calls > 0
    expected_algorithms = provenance_module.build_algorithm_inventory(
        pipeline.layout.load_config().to_dict(),
        extension=False,
    )
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
        stage_provenance_path = pipeline.layout.stage_provenance_path(stage)
        stage_provenance = json.loads(
            stage_provenance_path.read_text(encoding="utf-8")
        )
        assert stage_provenance["algorithms"] == {
            "stage": stage.value,
            "revision": expected_algorithms[stage.value],
        }
        receipt_outputs = {
            str(output["path"]): output for output in receipt["outputs"]
        }
        provenance_relative = stage_provenance_path.relative_to(
            pipeline.layout.root
        ).as_posix()
        assert receipt_outputs[provenance_relative]["sha256"] == file_sha256(
            stage_provenance_path
        )
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
    assert build_provenance["identity"]["algorithms"] == expected_algorithms
    assert len(build_provenance["identity"]["calls"]) == len(ledger_rows)
    assert len(build_provenance["audit"]["calls"]) == len(ledger_rows)
    asset_manifest = json.loads(
        pipeline.layout.manifest_path.read_text(encoding="utf-8")
    )
    assert asset_manifest["regression_gate"]["selection"] == (
        "deterministic_early_connected_group_hash"
    )
    assert asset_manifest["review_policy"] == {
        "evaluation_guidelines": "active_from_trusted_evidence",
        "guideline_calibration": "uncalibrated",
        "derived_cases": "approved_only",
        "coverage_labeling_queue": "human_label_required",
        "trusted_split_assignment": "before_guideline_authoring",
        "exact_duplicate_conflicts": "triage_hold",
    }


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
    _run_to_release(pipeline)
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

    resumed = _run_to_release(
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        )
    )

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
    _run_to_release(pipeline)
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

    resumed = _run_to_release(
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    prefix = {
        PipelineStage.RAW_INPUTS: layout.receipt_path(
            PipelineStage.RAW_INPUTS
        ).read_bytes()
    }

    revision = layout.revise_config({"split_seed": 73})
    resumed = _run_to_release(
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

    assert revision["invalidated_from_stage"] == "prepared_inputs"
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
    released = _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
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
    _run_to_release(pipeline)
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    revised = _run_to_release(
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ),
        config_updates={"match_threshold": 0.2},
    )

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
        _run_to_release(
            EvaluationAssetPipeline(
                layout,
                rubric_provider=_SuccessfulRubricProvider(),
                embedding_provider=_SuccessfulEmbeddingProvider(),
            )
        )

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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
        _run_to_release(resumed, config_updates={"match_threshold": 0.2})

    assert pipeline.layout.load_state().status != "released"
    assert _authority_bytes(pipeline.layout) == before_verification["authority"]


def test_released_verification_requires_config_history_authority(
    tmp_path: Path,
) -> None:
    """Receipt config hashes must be backed by the persisted revision history."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = _run_to_release(pipeline)
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
        _run_to_release(pipeline)

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

    released = _run_to_release(pipeline)

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
    _run_to_release(pipeline)
    _make_released_checkpoint_mutable(pipeline.layout)
    _run_to_release(
        EvaluationAssetPipeline(
            pipeline.layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ),
        config_updates={"match_threshold": 0.2},
    )
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
    _run_to_release(parent)
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
    released = _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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


def test_adoption_recovery_rechecks_generated_provenance_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generated adoption inputs share the legacy snapshot's first-write bound."""
    layout, prepared = _prepared_adoption(tmp_path, monkeypatch)
    target = layout.stage_provenance_path(PipelineStage.RAW_INPUTS)
    artifact_io.atomic_write_json(
        target,
        prepared["target_provenance"]["stages"][PipelineStage.RAW_INPUTS.value],
    )
    genuine = target.read_bytes()
    before = _authority_bytes(layout)
    original = workspace_module._assert_legacy_authority_unchanged
    attacked = False

    def mutate_after_recheck(*args: Any, **kwargs: Any) -> None:
        nonlocal attacked
        original(*args, **kwargs)
        if not attacked:
            target.write_bytes(b'{"corrupt":true}\n')
            attacked = True

    monkeypatch.setattr(
        workspace_module,
        "_assert_legacy_authority_unchanged",
        mutate_after_recheck,
    )
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            layout.recover()
    finally:
        target.write_bytes(genuine)

    assert attacked
    assert _authority_bytes(layout) == before
    assert not any(layout.receipts_root.glob("*.json"))


def test_adoption_recovery_binds_snapshot_inside_first_roll_forward_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A swap inside roll-forward cannot precede adoption manifests or receipts."""
    layout, _ = _prepared_adoption(tmp_path, monkeypatch)
    target = layout.historical_feedback_path
    genuine = target.read_bytes()
    before = _authority_bytes(layout)
    original = workspace_module.write_local_authority_json
    writes: list[Path] = []
    attacked = False

    def mutate_inside_first_bound_write(
        path: Path,
        trusted_root: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal attacked
        if not attacked:
            target.write_bytes(genuine + b"\n")
            attacked = True
        original(path, trusted_root, payload, **kwargs)
        writes.append(path)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_json",
        mutate_inside_first_bound_write,
    )
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            layout.recover()
    finally:
        target.write_bytes(genuine)

    assert attacked
    assert writes == []
    assert _authority_bytes(layout) == before
    assert not any(layout.receipts_root.glob("*.json"))


def test_adoption_recovery_rejects_foreign_generation_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepared adoption recovery retains one closed generation inventory."""
    layout, _ = _prepared_adoption(tmp_path, monkeypatch)
    foreign = layout.generations_root / f"sha256-{'0' * 64}"
    foreign.mkdir(parents=True)
    (foreign / "foreign.txt").write_text("foreign", encoding="utf-8")
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before
    assert not any(layout.receipts_root.glob("*.json"))
    assert foreign.is_dir()


def test_recovery_journal_rejects_commit_that_precedes_its_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching commit is authoritative only after its prepare record."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    resumed = _run_to_release(
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

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


def test_revision_cleanup_never_follows_a_swapped_stage_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalidation cannot delete artifacts through a raced ancestor symlink."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def stop_at_completed_handoff(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_at_completed_handoff)
    with pytest.raises(_InjectedFault):
        _run_to_release(pipeline)
    layout = pipeline.layout
    stage_directory = layout.stage_directory(PipelineStage.COVERAGE_DECISIONS)
    parked = tmp_path / "parked-stage-five"
    external = tmp_path / "external-stage-five"
    external.mkdir()
    victim = external / "intent_matches.jsonl"
    victim.write_bytes(b"KEEP")
    swapped = False

    def swap_before_cleanup(name: str) -> None:
        nonlocal swapped
        if name != "before_cleanup":
            return
        stage_directory.rename(parked)
        stage_directory.symlink_to(external, target_is_directory=True)
        swapped = True

    monkeypatch.setattr(workspace_module, "_fault_point", swap_before_cleanup)

    with pytest.raises(ValueError, match="exact directory"):
        layout.revise_config({"match_threshold": 0.5})

    assert swapped
    assert victim.read_bytes() == b"KEEP"
    assert stage_directory.is_symlink()
    assert parked.is_dir()


def test_authority_cleanup_rejects_a_replaced_leaf_without_deleting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cleanup quarantines by identity and restores a raced replacement leaf."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "target.jsonl"
    target.write_bytes(b"OLD\n")
    parked = tmp_path / "parked-target.jsonl"
    victim = tmp_path / "victim.jsonl"
    victim.write_bytes(b"KEEP\n")
    victim_identity = victim.stat()
    original = control_jsonl_module.rename_noreplace_at
    swapped = False

    def race_cleanup(
        directory_descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> bool:
        nonlocal swapped
        if not swapped:
            target.rename(parked)
            victim.rename(target)
            swapped = True
        return original(
            directory_descriptor,
            source,
            destination,
            **kwargs,
        )

    monkeypatch.setattr(
        control_jsonl_module,
        "rename_noreplace_at",
        race_cleanup,
    )

    with pytest.raises(ValueError, match="expected identity"):
        control_jsonl_module.remove_local_authority_file(target, trusted_root)

    assert swapped
    assert target.read_bytes() == b"KEEP\n"
    assert target.stat().st_ino == victim_identity.st_ino
    assert parked.read_bytes() == b"OLD\n"


@pytest.mark.parametrize("schema_mode", ["removed", "explicit-v1"])
def test_legacy_adoption_builds_honest_receipts_then_releases(
    tmp_path: Path,
    schema_mode: str,
) -> None:
    """Explicit adoption converts only a fully validated legacy completion."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    if schema_mode == "explicit-v1":
        raw_state = json.loads(layout.state_path.read_text(encoding="utf-8"))
        raw_state["schema_version"] = "fapo-evaluation-asset-state-v1"
        artifact_io.atomic_write_json(layout.state_path, raw_state)

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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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


@pytest.mark.parametrize("replacement_kind", ["symlink", "regular"])
def test_legacy_adoption_semantic_reads_reject_validation_seam_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    """Semantic adoption reads cannot follow authority swapped after syntax checks."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    target = layout.artifact_path(
        PipelineStage.PREPARED_INPUTS,
        "normalized_feedback.jsonl",
    )
    genuine = target.read_bytes()
    corrupted = _read_jsonl(target)
    corrupted[0]["user_input"] = "Semantically invalid local authority."
    artifact_io.atomic_write_jsonl(target, corrupted)
    external = tmp_path / "external-normalized-feedback.jsonl"
    artifact_io.atomic_write_text(external, genuine.decode("utf-8"))
    parked = target.with_name("normalized_feedback.parked.jsonl")
    before = _authority_bytes(layout)
    original_semantic_validation = (
        durability_module.validate_legacy_stage_semantics
    )
    swapped = False

    def validate_while_swapped(
        candidate_layout: EvaluationAssetLayout,
        artifact_profiles: Mapping[Any, str],
        *,
        artifact_snapshot: Mapping[Path, bytes],
    ) -> None:
        nonlocal swapped
        target.rename(parked)
        if replacement_kind == "symlink":
            target.symlink_to(external)
        else:
            artifact_io.atomic_write_text(target, genuine.decode("utf-8"))
        swapped = True
        try:
            original_semantic_validation(
                candidate_layout,
                artifact_profiles,
                artifact_snapshot=artifact_snapshot,
            )
        finally:
            target.unlink()
            parked.rename(target)

    monkeypatch.setattr(
        durability_module,
        "validate_legacy_stage_semantics",
        validate_while_swapped,
    )

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert swapped
    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))
    assert not layout.release_pointer_path.exists()


@pytest.mark.parametrize("replacement_kind", ["regular", "symlink", "appeared"])
def test_legacy_adoption_rechecks_the_complete_snapshot_before_first_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    """Every captured byte and absent alternative is rechecked at write boundary."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    if replacement_kind == "appeared":
        _convert_to_legacy_rubric_profile(layout)
        (layout.stages_root / "03_evaluation_guidelines").rename(
            layout.stages_root / "03_rubric_extraction"
        )
    _downgrade_to_legacy_completed(layout)
    present_target = layout.artifact_path(
        PipelineStage.PREPARED_INPUTS,
        "normalized_feedback.jsonl",
    )
    absent_target = (
        layout.stages_root
        / "03_evaluation_guidelines"
        / "candidate_guidelines.jsonl"
    )
    target = absent_target if replacement_kind == "appeared" else present_target
    parked = present_target.with_name("normalized_feedback.pre-write.parked")
    external = tmp_path / "external-pre-write.jsonl"
    external.write_bytes(present_target.read_bytes())
    before = _authority_bytes(layout)
    original = workspace_module._validate_asset_write_targets
    validations = 0
    swapped = False

    def swap_after_target_validation(*args: Any, **kwargs: Any) -> None:
        nonlocal validations, swapped
        original(*args, **kwargs)
        validations += 1
        if validations != 3:
            return
        swapped = True
        if replacement_kind == "appeared":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'{"unexpected":true}\n')
            return
        present_target.rename(parked)
        if replacement_kind == "symlink":
            present_target.symlink_to(external)
        else:
            present_target.write_bytes(b'{"semantically":"changed"}\n')

    monkeypatch.setattr(
        workspace_module,
        "_validate_asset_write_targets",
        swap_after_target_validation,
    )
    try:
        with pytest.raises(EvaluationAssetLegacyError):
            layout.adopt_legacy()
    finally:
        if replacement_kind == "appeared":
            target.unlink(missing_ok=True)
            target.parent.rmdir()
        elif swapped:
            present_target.unlink(missing_ok=True)
            parked.rename(present_target)

    assert validations == 3
    assert swapped
    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


def test_legacy_adoption_binds_snapshot_inside_first_authority_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A swap inside the first adoption writer leaves no adopted authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    target = layout.historical_feedback_path
    genuine = target.read_bytes()
    before = _authority_bytes(layout)
    first_provenance = layout.stage_provenance_path(PipelineStage.RAW_INPUTS)
    original = workspace_module.write_local_authority_json
    writes: list[Path] = []
    attacked = False

    def mutate_inside_first_write(
        path: Path,
        trusted_root: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal attacked
        if path == first_provenance and not attacked:
            target.write_bytes(genuine + b"\n")
            attacked = True
        original(path, trusted_root, payload, **kwargs)
        writes.append(path)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_json",
        mutate_inside_first_write,
    )
    try:
        with pytest.raises((EvaluationAssetIntegrityError, EvaluationAssetLegacyError)):
            layout.adopt_legacy()
    finally:
        target.write_bytes(genuine)

    assert attacked
    assert writes == []
    after = _authority_bytes(layout)
    recovery_keys = [
        key for key in after if key.endswith("recovery_journal.jsonl")
    ]
    assert len(recovery_keys) == 1
    after.pop(recovery_keys[0])
    assert after == before
    assert not any(layout.receipts_root.glob("*.json"))


@pytest.mark.parametrize("node", ["receipt", "event"])
@pytest.mark.parametrize("replacement_kind", ["regular", "symlink"])
def test_legacy_adoption_rechecks_native_controls_before_first_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node: str,
    replacement_kind: str,
) -> None:
    """Late native receipt/event authority cannot be overwritten by adoption."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    target = (
        layout.receipt_path(PipelineStage.RAW_INPUTS)
        if node == "receipt"
        else layout.events_path
    )
    parked = target.with_name(f"{target.name}.native-control.parked")
    external = tmp_path / f"external-{node}.jsonl"
    native_bytes = (
        b'{"native":"appeared"}\n'
        if node == "receipt"
        else (
            json.dumps(
                {
                    "timestamp": "2026-08-20T00:00:00+00:00",
                    "event": "pipeline_released",
                    "tenant_id": layout.tenant_id,
                    "asset_id": layout.asset_id,
                    "details": {},
                    "operation_id": "0" * 32,
                },
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
    )
    external.write_bytes(native_bytes)
    before = _authority_bytes(layout)
    original = workspace_module._validate_asset_write_targets
    validations = 0
    swapped = False

    def install_native_control(*args: Any, **kwargs: Any) -> None:
        nonlocal validations, swapped
        original(*args, **kwargs)
        validations += 1
        if validations != 3:
            return
        if target.exists() or target.is_symlink():
            target.rename(parked)
        if replacement_kind == "symlink":
            target.symlink_to(external)
        else:
            target.write_bytes(native_bytes)
        swapped = True

    monkeypatch.setattr(
        workspace_module,
        "_validate_asset_write_targets",
        install_native_control,
    )
    try:
        with pytest.raises(EvaluationAssetLegacyError):
            layout.adopt_legacy()
    finally:
        if swapped:
            target.unlink(missing_ok=True)
            if parked.exists():
                parked.rename(target)

    assert validations == 3
    assert swapped
    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()


def test_legacy_adoption_rejects_foreign_stage_provenance_without_writes(
    tmp_path: Path,
) -> None:
    """Only exact retry-owned pre-WAL provenance can precede adoption."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    artifact_io.atomic_write_json(
        layout.stage_provenance_path(PipelineStage.RAW_INPUTS),
        {},
    )
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()


def test_legacy_adoption_rejects_foreign_generation_without_writes(
    tmp_path: Path,
) -> None:
    """A foreign generation is native authority, not a legacy retry artifact."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    foreign = layout.generations_root / f"sha256-{'0' * 64}"
    foreign.mkdir(parents=True)
    (foreign / "foreign.txt").write_text("foreign", encoding="utf-8")
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert foreign.is_dir()
    assert not layout.recovery_journal_path.exists()


@pytest.mark.parametrize("replacement_kind", ["regular", "symlink"])
def test_legacy_adoption_rechecks_generation_inventory_before_first_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    """A generation appearing after validation cannot precede adoption writes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    foreign = layout.generations_root / f"sha256-{'0' * 64}"
    external = tmp_path / "external-generation"
    external.mkdir()
    (external / "foreign.txt").write_text("foreign", encoding="utf-8")
    before = _authority_bytes(layout)
    original = workspace_module._validate_asset_write_targets
    validations = 0

    def install_foreign_generation(*args: Any, **kwargs: Any) -> None:
        nonlocal validations
        original(*args, **kwargs)
        validations += 1
        if validations != 3:
            return
        foreign.parent.mkdir(parents=True, exist_ok=True)
        if replacement_kind == "symlink":
            foreign.symlink_to(external, target_is_directory=True)
        else:
            foreign.mkdir()
            (foreign / "foreign.txt").write_text("foreign", encoding="utf-8")

    monkeypatch.setattr(
        workspace_module,
        "_validate_asset_write_targets",
        install_foreign_generation,
    )
    try:
        with pytest.raises(EvaluationAssetLegacyError):
            layout.adopt_legacy()
    finally:
        if foreign.is_symlink():
            foreign.unlink()
        elif foreign.exists():
            shutil.rmtree(foreign)

    assert validations == 3
    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()


def test_legacy_adoption_rechecks_final_generation_bytes_before_first_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validated retry generation members remain frozen through the write boundary."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def stop_after_generation_install(name: str) -> None:
        if name == "after_generation_install":
            raise _InjectedFault(name)

    monkeypatch.setattr(
        workspace_module,
        "_fault_point",
        stop_after_generation_install,
    )
    with pytest.raises(_InjectedFault, match="after_generation_install"):
        layout.adopt_legacy()
    generation = next(
        path
        for path in layout.generations_root.iterdir()
        if path.name.startswith("sha256-")
    )
    target = generation / "train.jsonl"
    genuine = target.read_bytes()
    original_capture = workspace_module._capture_legacy_generation_inventory
    capture_calls = 0
    attacked = False

    def corrupt_after_generation_capture(*args: Any, **kwargs: Any) -> Any:
        nonlocal capture_calls, attacked
        result = original_capture(*args, **kwargs)
        capture_calls += 1
        if capture_calls == 1:
            target.write_bytes(b'{"corrupt":true}\n')
            attacked = True
        return result

    writes: list[Path] = []
    original_write = EvaluationAssetLayout._write_authority_json

    def record_write(
        self: EvaluationAssetLayout,
        path: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        writes.append(path)
        original_write(self, path, payload, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "_capture_legacy_generation_inventory",
        corrupt_after_generation_capture,
    )
    monkeypatch.setattr(EvaluationAssetLayout, "_write_authority_json", record_write)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            layout.recover()
    finally:
        target.write_bytes(genuine)

    assert capture_calls == 1
    assert attacked
    assert writes == []
    assert _read_jsonl(layout.recovery_journal_path)[-1]["phase"] == "prepared"


@pytest.mark.parametrize(
    "fault_name",
    [
        "after_generation_temp_created",
        "after_generation_split_train",
        "after_generation_split_validation",
        "after_generation_split_test",
        "after_generation_split_regression_trusted",
        "after_generation_manifest_write",
        "after_generation_temp_sync",
    ],
)
def test_legacy_adoption_generation_fault_reclaims_staging_and_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """An internal generation fault leaves WAL intent but no owned hidden tree."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def inject(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match=fault_name):
        layout.adopt_legacy()
    assert not list(layout.generations_root.glob(".*.tmp"))
    assert not list(layout.generations_root.glob(".*.rejected"))
    rows = _read_jsonl(layout.recovery_journal_path)
    assert [row["phase"] for row in rows] == ["prepared"]

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    assert layout.recover() == [rows[0]["operation_id"]]
    adopted = layout.load_state()
    assert adopted.status == "released"
    assert not list(layout.generations_root.glob(".*.tmp"))
    assert not list(layout.generations_root.glob(".*.rejected"))
    verify_released_asset(layout, adopted)


@pytest.mark.parametrize(
    "fault_name",
    [
        "after_prepared_journal",
        "after_state_replace",
        "after_event_append",
    ],
)
def test_legacy_adoption_recovers_historical_crlf_control_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Recovery authenticates exact Windows output from the legacy text writer."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    before_payloads: dict[str, Mapping[str, Any]] = {}
    before_hashes: dict[str, str] = {}
    for name, path in (
        ("config", layout.config_path),
        ("state", layout.state_path),
    ):
        payload = _rewrite_control_json_with_crlf(layout, path)
        before_payloads[name] = payload
        before_hashes[name] = file_sha256(path)
        assert before_hashes[name] != durability_module.persisted_json_sha256(
            payload
        )

    def inject(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match=fault_name):
        layout.adopt_legacy()
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    assert prepared["before_config"] == before_payloads["config"]
    assert prepared["before_state"] == before_payloads["state"]
    assert prepared["before"]["config_sha256"] == before_hashes["config"]
    assert prepared["before"]["state_sha256"] == before_hashes["state"]

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    assert layout.recover() == [prepared["operation_id"]]
    adopted = layout.load_state()
    assert adopted.status == "released"
    verify_released_asset(layout, adopted)


def test_legacy_adoption_recovery_rejects_crlf_to_lf_change_after_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid alternate legacy encoding remains byte-bound after WAL prepare."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    _rewrite_control_json_with_crlf(layout, layout.state_path)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault, match="after_prepared_journal"):
        layout.adopt_legacy()
    prepared = _read_jsonl(layout.recovery_journal_path)[0]
    assert prepared["before"]["state_sha256"] == file_sha256(layout.state_path)

    control_jsonl_module.write_local_authority_json(
        layout.state_path,
        layout.tenants_root,
        prepared["before_state"],
        expected_current=layout.state_path.read_bytes(),
        check_expected_current=True,
    )
    assert prepared["before"]["state_sha256"] != file_sha256(layout.state_path)
    before = _authority_bytes(layout)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("control_name", ["config", "state"])
def test_legacy_adoption_rejects_unsupported_control_serialization_before_writes(
    tmp_path: Path,
    control_name: str,
) -> None:
    """Unsupported legacy JSON bytes fail before WAL or generated authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    path = layout.config_path if control_name == "config" else layout.state_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    control_jsonl_module.write_local_authority_text(
        path,
        layout.tenants_root,
        json.dumps(payload, sort_keys=True, allow_nan=False),
        expected_current=path.read_bytes(),
        check_expected_current=True,
    )
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()
    assert not layout.generations_root.exists()
    assert not any(layout.receipts_root.glob("*.json"))


def test_legacy_adoption_counts_use_the_validated_artifact_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optional artifact presence cannot change between semantics and counts."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    target = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "evaluation_guidelines.jsonl",
    )
    expected_count = len(_read_jsonl(target))
    parked = target.with_name("evaluation_guidelines.parked.jsonl")
    original = durability_module._derive_legacy_counts
    hidden = False

    def derive_while_hidden(
        candidate_layout: EvaluationAssetLayout,
        split_counts: Mapping[str, int],
        artifact_snapshot: Mapping[Path, bytes] | None = None,
    ) -> dict[str, int]:
        nonlocal hidden
        target.rename(parked)
        hidden = True
        try:
            return original(
                candidate_layout,
                split_counts,
                artifact_snapshot,
            )
        finally:
            parked.rename(target)

    monkeypatch.setattr(
        durability_module,
        "_derive_legacy_counts",
        derive_while_hidden,
    )

    adopted = layout.adopt_legacy()

    receipt = json.loads(
        layout.receipt_path(PipelineStage.RUBRIC_EXTRACTION).read_text(
            encoding="utf-8"
        )
    )
    assert hidden
    assert adopted.counts["evaluation_guidelines"] == expected_count
    assert receipt["counts"]["evaluation_guidelines"] == expected_count


def test_legacy_extension_semantics_use_the_same_captured_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extension semantics cannot validate bytes different from adopted bytes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )
    _downgrade_to_legacy_completed(child)
    dataset_manifest_path = child.artifact_path(
        PipelineStage.DATASET_SPLITS,
        "dataset_manifest.json",
    )
    targets = (
        child.lineage_path,
        child.manifest_path,
        dataset_manifest_path,
    )
    genuine = {path: path.read_bytes() for path in targets}
    forged_lineage = json.loads(genuine[child.lineage_path])
    forged_lineage["creation_mode"] = "forged-mode"
    artifact_io.atomic_write_json(child.lineage_path, forged_lineage)
    for path in targets[1:]:
        manifest = json.loads(genuine[path])
        manifest["lineage"] = forged_lineage
        artifact_io.atomic_write_json(path, manifest)
    before = _authority_bytes(child)
    original = lineage_validation_module.validate_extension_evidence
    swaps = 0

    def validate_while_genuine(*args: Any, **kwargs: Any) -> Any:
        nonlocal swaps
        parked: list[tuple[Path, Path]] = []
        for path in targets:
            saved = path.with_name(f"{path.name}.forged")
            path.rename(saved)
            artifact_io.atomic_write_text(path, genuine[path].decode("utf-8"))
            parked.append((path, saved))
        swaps += 1
        try:
            return original(*args, **kwargs)
        finally:
            for path, saved in parked:
                path.unlink()
                saved.rename(path)

    monkeypatch.setattr(
        lineage_validation_module,
        "validate_extension_evidence",
        validate_while_genuine,
    )

    with pytest.raises(EvaluationAssetLegacyError):
        child.adopt_legacy()

    assert swaps >= 1
    assert _authority_bytes(child) == before
    assert not child.recovery_journal_path.exists()
    assert not any(child.receipts_root.glob("*.json"))


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
    _run_to_release(pipeline)
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
        repository_base=tmp_path,
        rubric_provider=provider,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )

    with pytest.raises(ProviderCallError, match="invalid response"):
        _run_to_release(pipeline)

    assert not pipeline.layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "candidate_guidelines.jsonl",
    ).exists()


@pytest.mark.parametrize(
    "duplicate_shape",
    ["exact_candidate", "derived_id_collision"],
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
        repository_base=tmp_path,
        rubric_provider=provider,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )

    with pytest.raises(ProviderCallError, match="invalid response"):
        _run_to_release(pipeline)

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
    _run_to_release(pipeline)
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
        repository_base=tmp_path,
        rubric_provider=provider,
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    provider = _SuccessfulSyntheticRubricProvider()
    _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=provider,
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )
    synthetic = _read_jsonl(
        child.artifact_path(PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl")
    )
    assert provider.synthetic_calls == 1
    assert len(synthetic) == 1
    assert synthetic[0]["metadata"]["dataset_version"] == "v2"
    assert len(
        _read_jsonl(
            child.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_candidates.jsonl",
            )
        )
    ) == 1
    _downgrade_to_legacy_completed(child)
    assert not _read_jsonl(
        child.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_candidates.jsonl",
        )
    )

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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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


@pytest.mark.parametrize("replacement_kind", ["regular", "symlink"])
def test_legacy_adoption_recovery_rechecks_snapshot_before_roll_forward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    """Recovery cannot authenticate one snapshot and roll forward another."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault, match="after_prepared_journal"):
        layout.adopt_legacy()
    target = layout.artifact_path(
        PipelineStage.PREPARED_INPUTS,
        "normalized_feedback.jsonl",
    )
    parked = target.with_name("normalized_feedback.recovery.parked")
    external = tmp_path / "external-recovery.jsonl"
    external.write_bytes(target.read_bytes())
    before = _authority_bytes(layout)
    original = workspace_module.validate_legacy_release_candidate
    swapped = False

    def swap_after_snapshot(*args: Any, **kwargs: Any) -> dict[str, int]:
        nonlocal swapped
        result = original(*args, **kwargs)
        target.rename(parked)
        if replacement_kind == "symlink":
            target.symlink_to(external)
        else:
            target.write_bytes(b'{"semantically":"changed"}\n')
        swapped = True
        return result

    monkeypatch.setattr(
        workspace_module,
        "validate_legacy_release_candidate",
        swap_after_snapshot,
    )
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            layout.recover()
    finally:
        if swapped:
            target.unlink(missing_ok=True)
            parked.rename(target)

    assert swapped
    assert _authority_bytes(layout) == before
    rows = _read_jsonl(layout.recovery_journal_path)
    assert [row["phase"] for row in rows] == ["prepared"]


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
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def inject(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match=fault_name):
        layout.adopt_legacy()

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
    assert released.status == "released"
    _downgrade_to_legacy_completed(pipeline.layout)

    adopted = pipeline.layout.adopt_legacy()

    assert adopted.status == "released"
    assert pipeline.layout.tenants_root == (tmp_path / "tenants").resolve()
    verify_released_asset(pipeline.layout, adopted)


def test_service_adopt_is_a_thin_locked_core_api(tmp_path: Path) -> None:
    """Service callers use the same adoption transaction as library callers."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    response = EvaluationAssetRunManager(
        layout.tenants_root,
        repository_base=layout.repository_base,
    ).adopt(
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
    _run_to_release(pipeline)
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


def test_extension_rejects_parent_source_swap_after_release_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child copies remain tied to the exact parent bytes release verification saw."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    additional = _write_additional_feedback(parent.tenants_root)
    target = parent.historical_feedback_path
    genuine = target.read_bytes()
    raced = _read_jsonl(target)
    raced[0]["user_input"] = "Different but contract-valid parent input."
    original = workspace_module.released_parent_evidence
    attacked = False

    def swap_after_verification(*args: Any, **kwargs: Any) -> dict[str, str]:
        nonlocal attacked
        evidence = original(*args, **kwargs)
        if not attacked:
            artifact_io.atomic_write_jsonl(target, raced)
            attacked = True
        return evidence

    monkeypatch.setattr(
        workspace_module,
        "released_parent_evidence",
        swap_after_verification,
    )
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            child.initialize_extension(
                parent,
                additional_feedback=additional,
                additional_unlabeled=None,
                clustering_mode="keep",
            )
    finally:
        target.write_bytes(genuine)

    assert attacked
    assert not child.root.exists()


def test_extension_rechecks_full_parent_authority_at_first_write_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child creation is bound to all authority authenticating its parent."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    additional = _write_additional_feedback(parent.tenants_root)
    target = parent.build_provenance_path
    genuine = target.read_bytes()
    original = EvaluationAssetLayout.ensure
    attacked = False

    def mutate_at_first_write_boundary(
        active_layout: EvaluationAssetLayout,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        nonlocal attacked
        if active_layout is child and not attacked:
            target.write_bytes(genuine + b"\n")
            attacked = True
        original(active_layout, *args, **kwargs)

    monkeypatch.setattr(
        EvaluationAssetLayout,
        "ensure",
        mutate_at_first_write_boundary,
    )
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            child.initialize_extension(
                parent,
                additional_feedback=additional,
                additional_unlabeled=None,
                clustering_mode="keep",
            )
    finally:
        target.write_bytes(genuine)

    assert attacked
    assert not child.root.exists()


def test_extension_points_legacy_parent_to_adoption_without_child_creation(
    tmp_path: Path,
) -> None:
    """Legacy completed is never accepted as a released parent alias."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
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
    parent_state = _run_to_release(pipeline)
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

    released = _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

    assert released.status == "released"
    expected_algorithms = provenance_module.build_algorithm_inventory(
        child.load_config().to_dict(),
        extension=True,
    )
    for stage in (
        PipelineStage.LABEL_INFERENCE,
        PipelineStage.SYNTHETIC_COVERAGE,
    ):
        provenance_path = child.stage_provenance_path(stage)
        stage_provenance = json.loads(
            provenance_path.read_text(encoding="utf-8")
        )
        assert stage_provenance["algorithms"] == {
            "stage": stage.value,
            "revision": expected_algorithms[stage.value],
        }
        receipt = json.loads(
            child.receipt_path(stage).read_text(encoding="utf-8")
        )
        relative = provenance_path.relative_to(child.root).as_posix()
        output = next(
            item for item in receipt["outputs"] if item["path"] == relative
        )
        assert output["sha256"] == file_sha256(provenance_path)
    build_provenance = json.loads(
        child.build_provenance_path.read_text(encoding="utf-8")
    )
    assert build_provenance["identity"]["algorithms"] == expected_algorithms
    verify_released_asset(child, released)


@pytest.mark.parametrize("parent_kind", ["native", "adopted"])
def test_extension_creation_uses_frozen_released_parent_stage_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    parent_kind: str,
) -> None:
    """Removed current member names cannot strand a released extension parent."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    if parent_kind == "adopted":
        _downgrade_to_legacy_completed(parent)
        parent.adopt_legacy()
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    for module in (lineage_validation_module, workspace_module):
        monkeypatch.setattr(
            module,
            "PipelineStage",
            _RemovedHistoricalPipelineStage,
        )

    state = child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
        config_updates=(
            {
                "rubric_provider": "chosen-rubric-provider",
                "rubric_model": "chosen-rubric-model",
                "embedding_provider": "chosen-embedding-provider",
                "embedding_model": "chosen-embedding-model",
            }
            if parent_kind == "adopted"
            else None
        ),
    )

    assert state.status == "draft"
    assert json.loads(child.lineage_path.read_text(encoding="utf-8"))[
        "parent_asset_id"
    ] == parent.asset_id
    assert child.historical_feedback_path.is_file()
    assert child.historical_parent_snapshot.is_dir()


def test_extension_receipts_anchor_lineage_and_every_parent_snapshot_input(
    tmp_path: Path,
) -> None:
    """Incremental receipts bind the self-contained parent evidence they consume."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

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


def test_historical_extension_override_map_is_closed_and_exhaustive(
    tmp_path: Path,
) -> None:
    """A partial frozen map cannot silently fall back to live authority reads."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

    with pytest.raises(ValueError, match="snapshot is incomplete"):
        lineage_validation_module.validate_extension_evidence(
            child,
            require_asset_manifest=True,
            historical=True,
            artifact_overrides={
                child.lineage_path: child.lineage_path.read_bytes(),
                child.reuse_manifest_path: child.reuse_manifest_path.read_bytes(),
            },
        )


@pytest.mark.parametrize("release_kind", ["native", "adopted"])
def test_released_extension_uses_frozen_stage_profile_after_registry_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release_kind: str,
) -> None:
    """Live stage changes cannot strand native or adopted extension history."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )
    if release_kind == "adopted":
        _downgrade_to_legacy_completed(child)
        child.adopt_legacy()
    for module in (
        evaluation_asset_models,
        durability_module,
        journal_validation_module,
    ):
        monkeypatch.setattr(module, "PipelineStage", _DriftedPipelineStage)
    for module in (lineage_validation_module, workspace_module):
        monkeypatch.setattr(
            module,
            "PipelineStage",
            _RemovedHistoricalPipelineStage,
        )

    released = child.load_state()

    assert released.status == "released"
    assert "future_stage" not in {item.stage for item in released.stages}
    verify_released_asset(child, released)


@pytest.mark.parametrize("phase", ["completed-handoff", "released"])
def test_historical_provenance_ignores_removed_live_stage_specifications(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    released_asset_template: Path,
    phase: str,
) -> None:
    """Frozen provenance validation never indexes the live authoring specs."""
    source = (
        completed_handoff_template
        if phase == "completed-handoff"
        else released_asset_template
    )
    tenants_root = tmp_path / "tenants"
    shutil.copytree(source, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.load_state()
    monkeypatch.setattr(durability_module, "STAGE_SPECIFICATIONS", {})

    if phase == "completed-handoff":
        durability_module.verify_completed_release_candidate(layout, state)
    else:
        verify_released_asset(layout, state)


def test_completed_handoff_uses_one_closed_authority_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
) -> None:
    """A semantically identical control rewrite during handoff verification fails."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(completed_handoff_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.load_state()
    receipt_path = layout.receipt_path(
        journal_transitions_module.PERSISTED_STAGE_VALUES_V2[-1]
    )
    original = durability_module._validate_stage_provenance_evidence
    mutated = False

    def mutate_after_snapshot(*args: Any, **kwargs: Any) -> Any:
        nonlocal mutated
        if not mutated:
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt_path.write_text(
                json.dumps(payload, separators=(",", ":")),
                encoding="utf-8",
            )
            mutated = True
        return original(*args, **kwargs)

    monkeypatch.setattr(
        durability_module,
        "_validate_stage_provenance_evidence",
        mutate_after_snapshot,
    )

    with pytest.raises(EvaluationAssetIntegrityError, match="changed"):
        durability_module.verify_completed_release_candidate(layout, state)

    assert mutated


def test_historical_profile_import_ignores_removed_live_stage_members() -> None:
    """A future authoring enum cannot prevent historical verifier import."""
    script = """
import importlib
from enum import Enum
from src.hephaestus.evaluation_assets import models

class FutureStage(str, Enum):
    FUTURE = "future"

models.PipelineStage = FutureStage
from src.hephaestus.evaluation_assets import durability
durability = importlib.reload(durability)

assert tuple(stage.value for stage in durability._HISTORICAL_PIPELINE_STAGES_V1) == (
    "raw_inputs",
    "prepared_inputs",
    "rubric_extraction",
    "intent_clustering",
    "coverage_decisions",
    "label_inference",
    "synthetic_coverage",
    "dataset_splits",
)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


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
    _run_to_release(pipeline)
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
        _run_to_release(first)

    def reject_recluster(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("keep-mode extension attempted to recluster")

    monkeypatch.setattr(pipeline_module, "cluster_records_fixed_count", reject_recluster)
    resumed = _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

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
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    acquired: list[str] = []

    class RecordingLock:
        def __init__(self, path: Path) -> None:
            self.path = path

        def __enter__(self) -> None:
            acquired.append(str(self.path.absolute()))

        def __exit__(self, *args: Any) -> None:
            pass

    def recording_lock(
        path: Path,
        trusted_root: Path,
        *,
        timeout: float,
    ) -> RecordingLock:
        del trusted_root, timeout
        return RecordingLock(path)

    monkeypatch.setattr(
        workspace_module,
        "acquire_local_authority_lock",
        recording_lock,
    )

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


@pytest.mark.parametrize("linked_node", ["directory", "leaf"])
def test_asset_lock_rejects_symlinks_without_external_writes(
    tmp_path: Path,
    linked_node: str,
) -> None:
    """Lock acquisition never follows a collection or leaf symlink."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    external = tmp_path / "external-locks"
    external.mkdir()
    victim = external / "v1.lock"
    victim.write_bytes(b"KEEP")
    if linked_node == "directory":
        layout.assets_root.mkdir(parents=True)
        layout.lock_path.parent.symlink_to(external, target_is_directory=True)
    else:
        layout.lock_path.parent.mkdir(parents=True)
        layout.lock_path.symlink_to(victim)

    with pytest.raises(EvaluationAssetIntegrityError, match="unsafe"):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert victim.read_bytes() == b"KEEP"
    assert not layout.root.exists()


def test_ensure_rejects_asset_root_swap_before_directory_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical directory creation cannot escape through a raced asset root."""
    tenants_root = tmp_path / "tenants"
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.assets_root.mkdir(parents=True)
    external = tmp_path / "external-asset"
    external.mkdir()
    original = workspace_module.open_local_authority_directory
    swapped = False

    def swap_before_bound_creation(*args: Any, **kwargs: Any) -> Any:
        nonlocal swapped
        if not swapped:
            layout.root.symlink_to(external, target_is_directory=True)
            swapped = True
        return original(*args, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "open_local_authority_directory",
        swap_before_bound_creation,
    )

    with pytest.raises(ValueError, match="exact directory"):
        layout.ensure()

    assert swapped
    assert list(external.iterdir()) == []


class _InjectedFault(RuntimeError):
    pass


@pytest.mark.parametrize("stage", list(PipelineStage), ids=lambda stage: stage.value)
def test_each_stage_provenance_rejects_self_consistent_secret_rehash_without_writes(
    tmp_path: Path,
    stage: PipelineStage,
) -> None:
    """A receipt hash authenticates only strict body-free provenance semantics."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="stage raw_inputs receipt payload is invalid",
    ):
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
    _run_to_release(pipeline)
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

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="stage raw_inputs receipt payload is invalid",
    ):
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
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
        if profile == provenance_module.HISTORICAL_PROVENANCE_PROFILE_V3
    } == {
        stage.value for stage in PipelineStage
    }


def test_legacy_adoption_candidate_validates_every_stage_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prospective adoption rejects provenance before installing release authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
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
        == provenance_module.HISTORICAL_LEGACY_PROVENANCE_PROFILE_V3
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
        _run_to_release(pipeline)

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
        recovered = _run_to_release(resumed)

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
        _run_to_release(pipeline)
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
        _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
    layout = pipeline.layout
    stage = PipelineStage.RUBRIC_EXTRACTION
    receipt = json.loads(layout.receipt_path(stage).read_text(encoding="utf-8"))
    receipt["schema_version"] = "fapo-stage-receipt-v1"
    artifact_io.atomic_write_json(layout.receipt_path(stage), receipt)
    next(
        item for item in released.stages if item.stage == stage.value
    ).receipt_sha256 = file_sha256(layout.receipt_path(stage))

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="required output inventory",
    ):
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
        _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
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
    released = _run_to_release(pipeline)
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

    released = _run_to_release(pipeline)

    assert released.status == "released"
    verify_released_asset(layout, released)


def test_extension_build_lineage_is_bound_to_local_lineage_authority(
    tmp_path: Path,
) -> None:
    """Extension build hashes cannot contradict validated local lineage files."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    released = _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )
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
    released = _run_to_release(pipeline)
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


@pytest.fixture(scope="module")
def released_asset_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create one released tree copied by no-follow authority probes."""
    template_root = tmp_path_factory.mktemp("released-authority")
    pipeline, _, _ = _create_pipeline(template_root)
    _run_to_release(pipeline)
    return pipeline.layout.tenants_root


_LOCAL_AUTHORITY_TARGETS = (
    "state",
    "config",
    "config-history",
    "events",
    "journal",
    "receipt",
    "stage-provenance",
    "provider-ledger",
    "build-provenance",
    "asset-manifest",
    "dataset-manifest",
    "generation-manifest",
    "catalog-generation-manifest",
    "catalog-split",
    "release-pointer",
)


def _local_authority_target(
    layout: EvaluationAssetLayout,
    name: str,
) -> Path:
    stage = PipelineStage.RUBRIC_EXTRACTION
    generation_id = json.loads(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        ).read_text(encoding="utf-8")
    )["generation_id"]
    generation_root = layout.generations_root / generation_id
    targets = {
        "state": layout.state_path,
        "config": layout.config_path,
        "config-history": layout.config_history_path,
        "events": layout.events_path,
        "journal": layout.recovery_journal_path,
        "receipt": layout.receipt_path(stage),
        "stage-provenance": layout.stage_provenance_path(stage),
        "provider-ledger": layout.artifact_path(stage, "provider_calls.jsonl"),
        "build-provenance": layout.build_provenance_path,
        "asset-manifest": layout.manifest_path,
        "dataset-manifest": layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "dataset_manifest.json",
        ),
        "generation-manifest": layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        ),
        "catalog-generation-manifest": generation_root
        / "generation_manifest.json",
        "catalog-split": generation_root / "train.jsonl",
        "release-pointer": layout.release_pointer_path,
    }
    return targets[name]


def _install_authority_symlink(
    layout: EvaluationAssetLayout,
    path: Path,
    *,
    mode: str,
    tmp_path: Path,
) -> None:
    payload = path.read_bytes() if path.is_file() else b""
    path.unlink(missing_ok=True)
    if mode == "external":
        target = tmp_path / "outside" / path.name
    elif mode == "cross-tenant":
        target = layout.tenants_root / "tenant_b" / "authority" / path.name
    elif mode == "in-root":
        target = layout.root / "authority-alias-targets" / path.name
    elif mode == "dangling":
        target = tmp_path / "absent" / path.name
    else:
        assert mode == "wrong-type"
        target = tmp_path / "directory-target" / path.name
        target.mkdir(parents=True)
        path.symlink_to(target, target_is_directory=True)
        return
    if mode != "dangling":
        target.parent.mkdir(parents=True, exist_ok=True)
        artifact_io.atomic_write_text(target, payload.decode("utf-8"))
    path.symlink_to(target)


@pytest.mark.parametrize("phase", ["candidate", "released"])
@pytest.mark.parametrize("authority_name", _LOCAL_AUTHORITY_TARGETS)
def test_all_local_authority_files_reject_external_symlinks_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    released_asset_template: Path,
    phase: str,
    authority_name: str,
) -> None:
    """Every candidate/final control family is exact local file authority."""
    tenants_root = tmp_path / "tenants"
    source = (
        completed_handoff_template
        if phase == "candidate"
        else released_asset_template
    )
    shutil.copytree(source, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    released_state = layout.load_state() if phase == "released" else None
    target = _local_authority_target(layout, authority_name)
    _install_authority_symlink(layout, target, mode="external", tmp_path=tmp_path)
    linked_to = target.readlink()
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unsafe authority reached a stage or provider")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)
    rubric.generate_json = forbidden  # type: ignore[method-assign]
    embedding.embed_texts = forbidden  # type: ignore[method-assign]

    with pytest.raises(EvaluationAssetIntegrityError):
        if phase == "candidate":
            EvaluationAssetPipeline(
                layout,
                rubric_provider=rubric,
                embedding_provider=embedding,
            ).run()
        else:
            assert released_state is not None
            verify_released_asset(layout, released_state)

    assert target.is_symlink()
    assert target.readlink() == linked_to
    assert rubric.calls == 0
    assert embedding.calls == 0


@pytest.mark.parametrize("swap_point", ["stage-8-receipt", "workspace-split"])
def test_release_verification_rejects_authority_swap_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    released_asset_template: Path,
    swap_point: str,
) -> None:
    """Every later authority hash is bound to a fresh no-follow handle."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(released_asset_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    released = layout.load_state()
    target = (
        layout.receipt_path(PipelineStage.DATASET_SPLITS)
        if swap_point == "stage-8-receipt"
        else layout.artifact_path(PipelineStage.DATASET_SPLITS, "train.jsonl")
    )
    before = _authority_bytes(layout)

    def install_identical_external_link() -> None:
        _install_authority_symlink(
            layout,
            target,
            mode="external",
            tmp_path=tmp_path,
        )

    if swap_point == "stage-8-receipt":
        original_receipt_chain = durability_module.verify_receipt_chain

        def swap_after_receipts(*args: Any, **kwargs: Any) -> Any:
            receipts = original_receipt_chain(*args, **kwargs)
            install_identical_external_link()
            return receipts

        monkeypatch.setattr(
            durability_module,
            "verify_receipt_chain",
            swap_after_receipts,
        )
    else:
        original_generation_links = (
            durability_module._verify_generation_content_links
        )

        def swap_before_generation_links(*args: Any, **kwargs: Any) -> Any:
            install_identical_external_link()
            return original_generation_links(*args, **kwargs)

        monkeypatch.setattr(
            durability_module,
            "_verify_generation_content_links",
            swap_before_generation_links,
        )

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(layout, released)

    assert target.is_symlink()
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("access", ["read", "write"])
def test_local_authority_resolver_rejects_checked_ancestor_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    access: str,
) -> None:
    """A checked ancestor stays descriptor-bound through the leaf operation."""
    trusted_root = tmp_path / "trusted"
    authority_directory = trusted_root / "authority"
    external_directory = tmp_path / "external-authority"
    parked_directory = tmp_path / "parked-authority"
    authority_directory.mkdir(parents=True)
    external_directory.mkdir()
    artifact_io.atomic_write_text(
        authority_directory / "control.json",
        "LOCAL",
    )
    artifact_io.atomic_write_text(
        external_directory / "control.json",
        "EXTERNAL",
    )
    original_stat = control_jsonl_module.os.stat
    swapped = False

    def swap_after_ancestor_stat(
        path: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal swapped
        result = original_stat(path, *args, **kwargs)
        if path == "authority" and kwargs.get("dir_fd") is not None and not swapped:
            swapped = True
            control_jsonl_module.os.rename(
                authority_directory,
                parked_directory,
            )
            control_jsonl_module.os.symlink(
                external_directory,
                authority_directory,
                target_is_directory=True,
            )
        return result

    monkeypatch.setattr(control_jsonl_module.os, "stat", swap_after_ancestor_stat)

    with pytest.raises(ValueError):
        control_jsonl_module.resolve_local_authority_file(
            authority_directory / "control.json",
            trusted_root,
            access=access,
        )

    assert swapped
    assert authority_directory.is_symlink()


def test_local_authority_write_resolver_binds_checked_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Write validation cannot accept a leaf replaced after its lstat."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    authority_path = trusted_root / "control.json"
    external_path = tmp_path / "external-control.json"
    artifact_io.atomic_write_text(authority_path, "LOCAL")
    artifact_io.atomic_write_text(external_path, "EXTERNAL")
    original_stat = control_jsonl_module.os.stat
    swapped = False

    def swap_after_leaf_stat(
        path: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal swapped
        result = original_stat(path, *args, **kwargs)
        if path == "control.json" and kwargs.get("dir_fd") is not None and not swapped:
            swapped = True
            authority_path.unlink()
            authority_path.symlink_to(external_path)
        return result

    monkeypatch.setattr(control_jsonl_module.os, "stat", swap_after_leaf_stat)

    with pytest.raises(ValueError, match="changed while opening"):
        control_jsonl_module.resolve_local_authority_file(
            authority_path,
            trusted_root,
            access="write",
        )

    assert swapped
    assert authority_path.is_symlink()


def test_local_authority_write_rechecks_expected_bytes_after_precondition(
    tmp_path: Path,
) -> None:
    """A same-inode mutation at the writer boundary cannot be overwritten."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    authority_path = trusted_root / "control.json"
    authority_path.write_bytes(b"OLD")

    def mutate_checked_inode() -> None:
        with authority_path.open("r+b") as handle:
            handle.seek(0)
            handle.write(b"FOREIGN")
            handle.truncate()

    with pytest.raises(ValueError, match="bytes changed"):
        control_jsonl_module.resolve_local_authority_file(
            authority_path,
            trusted_root,
            access="write",
            write_data=b"NEW",
            expected_write_data=b"OLD",
            check_expected_write_data=True,
            write_precondition=mutate_checked_inode,
        )

    assert authority_path.read_bytes() == b"FOREIGN"


@pytest.mark.parametrize("appearance", ["regular", "symlink"])
def test_optional_event_read_has_no_existence_probe_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    appearance: str,
) -> None:
    """A native event appearing at optional-read entry is read or rejected."""
    tenants_root = tmp_path / "tenants"
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.root.mkdir(parents=True)
    external = tmp_path / "external-events.jsonl"
    native_row = {
        "timestamp": "2026-08-20T00:00:00+00:00",
        "event": "pipeline_released",
        "tenant_id": layout.tenant_id,
        "asset_id": layout.asset_id,
        "details": {},
        "operation_id": "0" * 32,
    }
    artifact_io.atomic_write_jsonl(external, [native_row])
    original = durability_module.read_strict_jsonl_objects
    appeared = False

    def appear_before_bound_optional_read(
        path: Path,
        *,
        trusted_root: Path | None = None,
    ) -> list[dict[str, Any]]:
        nonlocal appeared
        if path == layout.events_path and not appeared:
            appeared = True
            if appearance == "symlink":
                path.symlink_to(external)
            else:
                path.write_bytes(external.read_bytes())
        return original(path, trusted_root=trusted_root)

    monkeypatch.setattr(
        durability_module,
        "read_strict_jsonl_objects",
        appear_before_bound_optional_read,
    )

    assert durability_module._has_native_event_authority(layout)
    assert appeared


@pytest.mark.parametrize("initially_present", [False, True])
def test_local_authority_write_rejects_target_swap_before_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    initially_present: bool,
) -> None:
    """Bound writes neither overwrite new names nor replaced checked leaves."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    authority_path = trusted_root / "control.json"
    parked = tmp_path / "parked-control.json"
    if initially_present:
        authority_path.write_bytes(b"LOCAL")
    victim = tmp_path / "victim.json"
    victim.write_bytes(b"KEEP")
    victim_identity = victim.stat()
    original = control_jsonl_module.atomic_write_bytes_at
    swapped = False

    def swap_before_install(
        descriptor: int,
        filename: str,
        content: bytes,
        **kwargs: Any,
    ) -> None:
        nonlocal swapped
        if initially_present:
            authority_path.rename(parked)
        victim.rename(authority_path)
        swapped = True
        original(descriptor, filename, content, **kwargs)

    monkeypatch.setattr(
        control_jsonl_module,
        "atomic_write_bytes_at",
        swap_before_install,
    )

    with pytest.raises(ValueError, match="target"):
        control_jsonl_module.resolve_local_authority_file(
            authority_path,
            trusted_root,
            access="write",
            write_data=b"NEW",
        )

    assert swapped
    assert authority_path.read_bytes() == b"KEEP"
    assert authority_path.stat().st_ino == victim_identity.st_ino
    if initially_present:
        assert parked.read_bytes() == b"LOCAL"


@pytest.mark.parametrize(
    "publication_node",
    ["release-pointer", "generation-manifest", "generation-split"],
)
def test_publication_reads_use_shared_bound_authority_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    released_asset_template: Path,
    publication_node: str,
) -> None:
    """Pointer, manifest, and split reads cannot reopen a swapped path."""
    tenants_root = tmp_path / "tenants"
    shutil.copytree(released_asset_template, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    released = layout.load_state()
    generation_id = json.loads(
        layout.release_pointer_path.read_text(encoding="utf-8")
    )["generation_id"]
    generation_root = layout.generations_root / generation_id
    target = {
        "release-pointer": layout.release_pointer_path,
        "generation-manifest": generation_root / "generation_manifest.json",
        "generation-split": generation_root / "train.jsonl",
    }[publication_node]
    before = _authority_bytes(layout)
    original_resolver = publication_module.resolve_local_authority_file
    original_bound_read = (
        publication_module.read_local_authority_file_with_identity_at
    )
    swapped = False

    def swap_before_publication_read(
        path: Path,
        trusted_root: Path,
        *,
        access: str,
    ) -> Any:
        nonlocal swapped
        if Path(path) == target and access == "read" and not swapped:
            swapped = True
            _install_authority_symlink(
                layout,
                target,
                mode="external",
                tmp_path=tmp_path,
            )
        return original_resolver(path, trusted_root, access=access)

    monkeypatch.setattr(
        publication_module,
        "resolve_local_authority_file",
        swap_before_publication_read,
    )

    def swap_before_bound_generation_read(
        directory_descriptor: int,
        filename: str,
    ) -> tuple[bytes, tuple[int, int, int]]:
        nonlocal swapped
        if publication_node != "release-pointer" and filename == target.name and not swapped:
            swapped = True
            _install_authority_symlink(
                layout,
                target,
                mode="external",
                tmp_path=tmp_path,
            )
        return original_bound_read(directory_descriptor, filename)

    monkeypatch.setattr(
        publication_module,
        "read_local_authority_file_with_identity_at",
        swap_before_bound_generation_read,
    )

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(layout, released)

    assert swapped
    assert target.is_symlink()
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize("phase", ["candidate", "released"])
@pytest.mark.parametrize(
    "symlink_mode",
    ["cross-tenant", "in-root", "dangling", "wrong-type"],
)
def test_receipt_authority_rejects_every_symlink_target_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    released_asset_template: Path,
    phase: str,
    symlink_mode: str,
) -> None:
    """Receipt authority cannot remain linked across any target topology."""
    tenants_root = tmp_path / "tenants"
    source = (
        completed_handoff_template
        if phase == "candidate"
        else released_asset_template
    )
    shutil.copytree(source, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    receipt = layout.receipt_path(PipelineStage.RUBRIC_EXTRACTION)
    _install_authority_symlink(
        layout,
        receipt,
        mode=symlink_mode,
        tmp_path=tmp_path,
    )
    linked_to = receipt.readlink()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unsafe receipt authority reran pipeline work")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)
    with pytest.raises(EvaluationAssetIntegrityError):
        if phase == "candidate":
            EvaluationAssetPipeline(layout).run()
        else:
            verify_released_asset(layout, layout.load_state())

    assert receipt.is_symlink()
    assert receipt.readlink() == linked_to


@pytest.mark.parametrize("phase", ["candidate", "released"])
@pytest.mark.parametrize("linked_root", ["tenant", "asset"])
def test_authority_rejects_linked_tenant_or_asset_root_before_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_handoff_template: Path,
    released_asset_template: Path,
    phase: str,
    linked_root: str,
) -> None:
    """Explicit authority roots are checked lexically before lock or data access."""
    tenants_root = tmp_path / "tenants"
    source = (
        completed_handoff_template
        if phase == "candidate"
        else released_asset_template
    )
    shutil.copytree(source, tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    linked = layout.tenant_root if linked_root == "tenant" else layout.root
    relocated = tmp_path / "relocated" / linked_root
    relocated.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(linked), str(relocated))
    linked.symlink_to(relocated, target_is_directory=True)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("linked authority root reached pipeline work")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", forbidden)
    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        if phase == "candidate":
            EvaluationAssetPipeline(layout).run()
        else:
            verify_released_asset(layout, layout.load_state())

    assert linked.is_symlink()


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
            _run_to_release(pipeline)
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
        repository_base=template_root,
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
            _run_to_release(pipeline)
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


def _legacy_event_row(
    layout: EvaluationAssetLayout,
    event: str,
) -> dict[str, Any]:
    """Build one exact row emitted by the genuine pre-v2 event writer."""
    details: dict[str, Any]
    if event == "pipeline_created":
        details = {"status": "draft"}
    elif event == "pipeline_extended":
        details = {
            "parent_asset_id": "v0",
            "clustering_mode": "keep",
            "added_labeled_records": 1,
            "added_unlabeled_records": 0,
        }
    elif event == "pipeline_started":
        details = {}
    elif event == "stage_started":
        details = {"stage": PipelineStage.RAW_INPUTS.value}
    elif event == "stage_failed":
        details = {
            "stage": PipelineStage.RAW_INPUTS.value,
            "error": "legacy failure",
        }
    elif event == "stage_completed":
        details = {
            "stage": PipelineStage.RAW_INPUTS.value,
            "counts": {"feedback_records": 1, "unlabeled_records": 1},
        }
    elif event == "pipeline_completed":
        details = {
            "counts": {
                key: 0
                for keys in durability_module._HISTORICAL_STAGE_COUNT_KEYS_V1.values()
                for key in keys
            }
        }
    else:
        assert event == "configuration_updated"
        details = {
            "revision": 2,
            "changed_fields": {
                "match_threshold": {"previous": 0.5, "new": 0.4}
            },
            "invalidated_from_stage": PipelineStage.COVERAGE_DECISIONS.value,
            "resume_from_stage": PipelineStage.COVERAGE_DECISIONS.value,
        }
    return {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "event": event,
        "tenant_id": layout.tenant_id,
        "asset_id": layout.asset_id,
        "details": details,
    }


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
            _legacy_event_row(layout, legacy_event),
        )

    released = _run_to_release(
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        )
    )

    assert released.status == "released"
    assert released.schema_version == STATE_SCHEMA_VERSION


@pytest.mark.parametrize(
    "legacy_event",
    [
        "pipeline_created",
        "pipeline_extended",
        "pipeline_started",
        "stage_started",
        "stage_failed",
        "stage_completed",
        "pipeline_completed",
        "configuration_updated",
    ],
)
def test_exact_pre_v2_event_profile_remains_receipt_free_compatible(
    tmp_path: Path,
    legacy_event: str,
) -> None:
    """Only genuine pre-v2 event rows remain compatible with legacy fallback."""
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    layout.root.mkdir(parents=True)
    artifact_io.atomic_write_jsonl(
        layout.events_path,
        [_legacy_event_row(layout, legacy_event)],
    )

    assert not durability_module._has_native_authority_evidence(
        layout,
        {"stages": []},
    )


@pytest.mark.parametrize(
    "event_row",
    [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "configuration_updated",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "operation_id": "0" * 32,
            "details": {
                "revision": 2,
                "changed_fields": {},
                "invalidated_from_stage": "coverage_decisions",
                "resume_from_stage": "coverage_decisions",
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "checkpoint_rebuild_started",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "operation_id": "0" * 32,
            "details": {"stage": "raw_inputs"},
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "legacy_asset_adopted",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "operation_id": "0" * 32,
            "details": {"previous_status": "completed"},
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "pipeline_released",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "operation_id": "0" * 32,
            "details": {
                "generation_id": "generation",
                "release_sha256": "0" * 64,
                "stage_8_receipt_sha256": "1" * 64,
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "pipeline_extended",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "operation_id": "0" * 32,
            "details": {},
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "pipeline_resume_requested",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {
                "changed_fields": {},
                "invalidated_from_stage": None,
                "resume_from_stage": None,
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "future_native_event",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {},
        },
        {
            "event": "pipeline_started",
        },
    ],
    ids=[
        "v2-configuration",
        "v2-rebuild",
        "v2-adoption",
        "v2-release",
        "v2-extension-shape",
        "unwritten-resume-shape",
        "unknown",
        "malformed-known-event",
    ],
)
def test_non_v2_event_authority_fails_closed_for_every_nonlegacy_row(
    tmp_path: Path,
    event_row: dict[str, Any],
) -> None:
    """Known-native, unknown, and malformed rows are all native evidence."""
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    layout.root.mkdir(parents=True)
    artifact_io.atomic_write_jsonl(layout.events_path, [event_row])
    before = _tree_bytes(layout.tenant_root)

    assert durability_module._has_native_authority_evidence(
        layout,
        {"stages": []},
    )
    assert _tree_bytes(layout.tenant_root) == before


@pytest.mark.parametrize("schema_mode", ["removed", "explicit-v1"])
@pytest.mark.parametrize(
    "malformed_event",
    [
        {
            "timestamp": "2026-01-01T01:00:00+01:00",
            "event": "stage_completed",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {
                "stage": "raw_inputs",
                "counts": {"future_native_count": 1},
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "configuration_updated",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {
                "revision": 2,
                "changed_fields": {},
                "invalidated_from_stage": "raw_inputs",
                "resume_from_stage": "dataset_splits",
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "pipeline_extended",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {
                "parent_asset_id": "v0",
                "clustering_mode": "keep",
                "added_labeled_records": 0,
                "added_unlabeled_records": 1,
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "pipeline_extended",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {
                "parent_asset_id": "v0",
                "clustering_mode": "refresh",
                "added_labeled_records": 0,
                "added_unlabeled_records": 0,
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "pipeline_extended",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {
                "parent_asset_id": "v1",
                "clustering_mode": "refresh",
                "added_labeled_records": 1,
                "added_unlabeled_records": 0,
            },
        },
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "event": "pipeline_extended",
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "details": {
                "parent_asset_id": "../v0",
                "clustering_mode": "refresh",
                "added_labeled_records": 1,
                "added_unlabeled_records": 0,
            },
        },
    ],
    ids=[
        "noncanonical-stage-count-hybrid",
        "impossible-empty-revision",
        "keep-with-unlabeled",
        "empty-extension",
        "self-parent",
        "unsafe-parent-id",
    ],
)
def test_semantically_impossible_legacy_event_fails_before_writes_or_calls(
    tmp_path: Path,
    schema_mode: str,
    malformed_event: Mapping[str, Any],
) -> None:
    """A known event name cannot make an impossible row legacy-compatible."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    layout = pipeline.layout
    raw_state = json.loads(layout.state_path.read_text(encoding="utf-8"))
    if schema_mode == "removed":
        del raw_state["schema_version"]
    else:
        raw_state["schema_version"] = "fapo-evaluation-asset-state-v1"
    artifact_io.atomic_write_json(layout.state_path, raw_state)
    artifact_io.atomic_append_jsonl(layout.events_path, malformed_event)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


@pytest.mark.parametrize("schema_mode", ["removed", "explicit-v1"])
@pytest.mark.parametrize("entrypoint", ["run", "adopt"])
def test_current_extension_event_is_native_before_any_authority_write_or_call(
    tmp_path: Path,
    schema_mode: str,
    entrypoint: str,
) -> None:
    """Current extension authoring emits explicit native event authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    extension_event = next(
        row
        for row in _read_jsonl(child.events_path)
        if row.get("event") == "pipeline_extended"
    )
    assert set(extension_event) == {
        "timestamp",
        "event",
        "tenant_id",
        "asset_id",
        "operation_id",
        "details",
    }
    assert re.fullmatch(r"[0-9a-f]{32}", extension_event["operation_id"])
    raw_state = json.loads(child.state_path.read_text(encoding="utf-8"))
    if schema_mode == "removed":
        del raw_state["schema_version"]
    else:
        raw_state["schema_version"] = "fapo-evaluation-asset-state-v1"
    if entrypoint == "adopt":
        raw_state["status"] = "completed"
        raw_state["current_stage"] = None
        raw_state.pop("mutation_sequence")
        raw_state.pop("last_operation_id")
        for stage_state in raw_state["stages"]:
            stage_state["status"] = "completed"
            stage_state.pop("receipt_sha256")
    artifact_io.atomic_write_json(child.state_path, raw_state)
    before = _authority_bytes(child)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    expected_error = (
        EvaluationAssetIntegrityError
        if entrypoint == "run"
        else EvaluationAssetLegacyError
    )
    with pytest.raises(expected_error):
        if entrypoint == "run":
            EvaluationAssetPipeline(
                child,
                rubric_provider=rubric,
                embedding_provider=embedding,
            ).run()
        else:
            child.adopt_legacy()

    assert _authority_bytes(child) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


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
    _run_to_release(pipeline)
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
    monkeypatch.setattr(durability_module, "CONFIG_STAGE_DEPENDENCIES", {})

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
    _run_to_release(pipeline)
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
    monkeypatch.setattr(
        workspace_module,
        "PipelineStage",
        _RemovedHistoricalPipelineStage,
    )
    monkeypatch.setattr(
        lineage_validation_module,
        "PipelineStage",
        _RemovedHistoricalPipelineStage,
    )

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
    _run_to_release(pipeline)
    layout = pipeline.layout
    if release_kind == "adopted":
        _downgrade_to_legacy_completed(layout)
        layout.adopt_legacy()
    labels = dict(evaluation_asset_models.STAGE_LABELS)
    labels[PipelineStage.RAW_INPUTS] = "Current deployment label"
    monkeypatch.setattr(evaluation_asset_models, "STAGE_LABELS", labels)
    monkeypatch.setattr(
        durability_module,
        "PipelineStage",
        _DriftedPipelineStage,
    )
    monkeypatch.setattr(
        journal_validation_module,
        "PipelineStage",
        _DriftedPipelineStage,
    )
    monkeypatch.setattr(
        workspace_module,
        "PipelineStage",
        _RemovedHistoricalPipelineStage,
    )
    monkeypatch.setattr(
        lineage_validation_module,
        "PipelineStage",
        _RemovedHistoricalPipelineStage,
    )
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


def test_released_revision_journal_uses_only_frozen_stage_profiles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A finalized nonempty revision remains valid after registry replacement."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def stop_at_completed_handoff(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_at_completed_handoff)
    with pytest.raises(_InjectedFault):
        _run_to_release(pipeline)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    released = _run_to_release(pipeline, config_updates={"match_threshold": 0.5})
    assert released.status == "released"
    assert any(
        row.get("kind") == "configuration_revision"
        for row in _read_jsonl(pipeline.layout.recovery_journal_path)
    )
    for module in (journal_transitions_module, journal_validation_module):
        monkeypatch.setattr(module, "PipelineStage", _RemovedHistoricalPipelineStage)
        monkeypatch.setattr(module, "STAGE_COUNT_KEYS", {})
        monkeypatch.setattr(
            module,
            "CONFIG_STAGE_DEPENDENCIES",
            {},
            raising=False,
        )
    monkeypatch.setattr(
        durability_module,
        "PipelineStage",
        _RemovedHistoricalPipelineStage,
    )
    monkeypatch.setattr(durability_module, "STAGE_COUNT_KEYS", {})
    monkeypatch.setattr(durability_module, "CONFIG_STAGE_DEPENDENCIES", {})
    monkeypatch.setattr(journal_validation_module, "STAGE_LABELS", {})

    restarted = pipeline.layout.load_state()

    assert restarted.status == "released"
    verify_released_asset(pipeline.layout, restarted)


def test_completed_revised_handoff_uses_only_frozen_journal_profiles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A completed pre-publication revision survives removed live registries."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def stop_at_completed_handoff(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_at_completed_handoff)
    with pytest.raises(_InjectedFault):
        _run_to_release(pipeline)
    with pytest.raises(_InjectedFault):
        _run_to_release(pipeline, config_updates={"match_threshold": 0.5})
    handoff = pipeline.layout.load_state()
    assert handoff.status == "running"
    assert all(stage.status == "completed" for stage in handoff.stages)
    assert any(
        row.get("kind") == "configuration_revision"
        for row in _read_jsonl(pipeline.layout.recovery_journal_path)
    )
    for module in (journal_transitions_module, journal_validation_module):
        monkeypatch.setattr(module, "PipelineStage", _RemovedHistoricalPipelineStage)
        monkeypatch.setattr(module, "STAGE_COUNT_KEYS", {})
        monkeypatch.setattr(
            module,
            "CONFIG_STAGE_DEPENDENCIES",
            {},
            raising=False,
        )
    monkeypatch.setattr(
        durability_module,
        "PipelineStage",
        _RemovedHistoricalPipelineStage,
    )
    monkeypatch.setattr(durability_module, "STAGE_COUNT_KEYS", {})
    monkeypatch.setattr(durability_module, "CONFIG_STAGE_DEPENDENCIES", {})
    monkeypatch.setattr(journal_validation_module, "STAGE_LABELS", {})
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    released = EvaluationAssetPipeline(pipeline.layout).run()

    assert released.status == "released"
    verify_released_asset(pipeline.layout, released)


@pytest.mark.parametrize("schema_version", ["v1", "v2"])
def test_incomplete_checkpoint_normalizes_to_current_authoring_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    schema_version: str,
) -> None:
    """Mutable v1/v2 checkpoints adopt current membership and ordering."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    raw = json.loads(layout.state_path.read_text(encoding="utf-8"))
    if schema_version == "v1":
        raw["schema_version"] = "fapo-evaluation-asset-state-v1"
    artifact_io.atomic_write_json(layout.state_path, raw)
    _install_drifted_authoring_registry(monkeypatch)

    loaded = layout.load_state()

    assert tuple(item.stage for item in loaded.stages) == tuple(
        stage.value for stage in _DriftedPipelineStage
    )
    future = loaded.stages[0]
    assert future.stage == _DriftedPipelineStage.FUTURE_STAGE.value
    assert future.status == "pending"
    assert future.receipt_sha256 is None


def test_nonempty_revision_rejects_unversioned_stage_registry_expansion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new stage cannot be persisted under the frozen v3 journal schema."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    _install_drifted_authoring_registry(monkeypatch)
    before = _authority_bytes(layout)

    with pytest.raises(
        ValueError,
        match="stage inventory is incompatible with journal schema",
    ):
        layout.revise_config({"match_threshold": 0.5})

    assert _authority_bytes(layout) == before
    assert durability_module.load_completed_release_handoff_control(layout) is None


def test_failed_full_count_checkpoint_restarts_with_current_authoring_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed receipted checkpoint remains mutable after live stage expansion."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def stop_at_completed_handoff(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_at_completed_handoff)
    with pytest.raises(_InjectedFault):
        _run_to_release(pipeline)
    layout = pipeline.layout
    raw = json.loads(layout.state_path.read_text(encoding="utf-8"))
    raw["status"] = "failed"
    raw["error"] = "retry with the current authoring registry"
    artifact_io.atomic_write_json(layout.state_path, raw)
    _install_drifted_authoring_registry(monkeypatch)
    current = layout.load_state()
    layout.save_state(current)

    assert current.status == "failed"
    assert current.stages[0].stage == _DriftedPipelineStage.FUTURE_STAGE.value
    assert durability_module.load_completed_release_handoff_control(layout) is None
    restarted = EvaluationAssetLayout(
        layout.tenants_root,
        layout.tenant_id,
        layout.asset_id,
    ).load_state()
    assert tuple(item.stage for item in restarted.stages) == tuple(
        stage.value for stage in _DriftedPipelineStage
    )


def test_failed_full_receipt_checkpoint_uses_live_same_membership_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed checkpoint prepares and recovers with the evolved live profile."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def stop_at_completed_handoff(name: str) -> None:
        if name == "after_stage_8_receipt_state_complete":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_at_completed_handoff)
    with pytest.raises(_InjectedFault):
        _run_to_release(pipeline)
    layout = pipeline.layout
    raw = json.loads(layout.state_path.read_text(encoding="utf-8"))
    raw["status"] = "failed"
    raw["error"] = "retry with the evolved authoring profile"
    raw["stages"][0]["label"] = "Future raw-input authoring"
    raw["counts"]["future_authoring_count"] = 0
    artifact_io.atomic_write_json(layout.state_path, raw)
    labels = dict(evaluation_asset_models.STAGE_LABELS)
    labels[PipelineStage.RAW_INPUTS] = "Future raw-input authoring"
    count_keys = dict(evaluation_asset_models.STAGE_COUNT_KEYS)
    count_keys[PipelineStage.RAW_INPUTS] = (
        *count_keys[PipelineStage.RAW_INPUTS],
        "future_authoring_count",
    )
    for module in (
        evaluation_asset_models,
        durability_module,
        journal_validation_module,
    ):
        monkeypatch.setattr(module, "STAGE_LABELS", labels)
        monkeypatch.setattr(module, "STAGE_COUNT_KEYS", count_keys)

    assert durability_module.load_completed_release_handoff_control(layout) is None
    restarted = layout.load_state()
    assert restarted.status == "failed"
    assert restarted.stages[0].label == "Future raw-input authoring"
    assert restarted.counts["future_authoring_count"] == 0

    def stop_after_revision_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_revision_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.5})

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    recovered = layout.recover()

    assert len(recovered) == 1
    assert layout.load_config().match_threshold == 0.5
    assert layout.load_state().counts["future_authoring_count"] == 0


def test_pre_v2_adoption_uses_only_frozen_stage_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A current enum addition or reorder cannot alter historical adoption."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    for module in (
        evaluation_asset_models,
        durability_module,
        journal_validation_module,
    ):
        monkeypatch.setattr(module, "PipelineStage", _DriftedPipelineStage)
    for module in (lineage_validation_module, workspace_module):
        monkeypatch.setattr(
            module,
            "PipelineStage",
            _RemovedHistoricalPipelineStage,
        )
    monkeypatch.setattr(
        durability_module,
        "STAGE_SPECIFICATIONS",
        {
            stage: replace(
                specification,
                required_outputs=("future-only.json",),
                direct_inputs=(),
                upstream_stages=(),
                config_fields=(),
                provider_roles=(),
            )
            for stage, specification in STAGE_SPECIFICATIONS.items()
        },
    )

    adopted = layout.adopt_legacy()

    assert adopted.status == "released"
    assert tuple(item.stage for item in adopted.stages) == tuple(
        stage.value for stage in PipelineStage
    )
    assert "future_stage" not in {item.stage for item in adopted.stages}
    verify_released_asset(layout, adopted)


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
        "review-schema",
        "stage-membership-order",
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
    """Current registries/providers cannot strand captured v3 provenance."""
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
            "fapo-stage-receipt-v4",
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
            "fapo-stage-provenance-v4",
        )
        monkeypatch.setattr(
            provenance_module,
            "BUILD_PROVENANCE_SCHEMA_VERSION",
            "fapo-evaluation-build-provenance-v4",
        )
        monkeypatch.setattr(
            durability_module,
            "BUILD_PROVENANCE_SCHEMA_VERSION",
            "fapo-evaluation-build-provenance-v4",
            raising=False,
        )
        monkeypatch.setattr(
            provenance_module,
            "BUILD_IDENTITY_SCHEMA_VERSION",
            "fapo-evaluation-build-identity-v4",
        )
    elif registry_drift == "review-schema":
        monkeypatch.setattr(
            review_module,
            "REVIEW_FINALIZATION_SCHEMA_VERSION",
            "fapo-review-finalization-v2",
        )
        monkeypatch.setattr(
            review_module,
            "REVIEW_FINALIZATION_IDENTITY_SCHEMA_VERSION",
            "fapo-review-finalization-identity-v2",
        )
        monkeypatch.setattr(
            review_module,
            "REVIEW_FINALIZATION_FIELDS",
            review_module.REVIEW_FINALIZATION_FIELDS | {"future_field"},
        )
        monkeypatch.setattr(
            review_module,
            "DERIVED_CASE_CONTENT_SCHEMA_VERSION",
            "fapo-derived-case-content-v2",
        )
    elif registry_drift == "stage-membership-order":
        monkeypatch.setattr(
            durability_module,
            "PipelineStage",
            _DriftedPipelineStage,
        )
        monkeypatch.setattr(
            journal_validation_module,
            "PipelineStage",
            _DriftedPipelineStage,
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


def test_generation_temp_created_fault_retains_only_empty_owned_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The earliest generation fault retains no temporary authority bytes."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == "after_generation_temp_created":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match="after_generation_temp_created"):
        _run_to_release(pipeline)

    generations_root = pipeline.layout.generations_root
    assert not list(generations_root.glob(".*.tmp"))


def _assert_revisions_reclaim_exact_owned_hidden_nodes(
    tmp_path: Path,
    *,
    iterations: int,
) -> None:
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    _make_released_checkpoint_mutable(pipeline.layout)

    for index in range(iterations):
        pipeline.layout.revise_config(
            {"match_threshold": 0.2 if index % 2 == 0 else 0.3}
        )
        hidden = [
            path
            for path in pipeline.layout.tenant_root.rglob(".*")
            if path.name.endswith((".tmp", ".removed", ".rejected"))
        ]
        assert hidden == []


def test_pr2_repeated_revisions_reclaim_exact_owned_hidden_nodes(
    tmp_path: Path,
) -> None:
    """Ordinary authority replacement has bounded operation-owned storage."""
    _assert_revisions_reclaim_exact_owned_hidden_nodes(tmp_path, iterations=100)


def test_native_revisions_reclaim_exact_owned_hidden_nodes(
    tmp_path: Path,
) -> None:
    """Native authority replacement reclaims operation-owned hidden nodes."""
    _assert_revisions_reclaim_exact_owned_hidden_nodes(tmp_path, iterations=3)


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
        _run_to_release(pipeline)
    layout = pipeline.layout
    assert not layout.release_pointer_path.exists()


def test_release_recovery_rechecks_candidate_before_pointer_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate swap after verification cannot leave pointer authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)

    def inject(name: str) -> None:
        if name == "after_release_publication_prepared":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject)
    with pytest.raises(_InjectedFault, match="after_release_publication_prepared"):
        _run_to_release(pipeline)
    layout = pipeline.layout
    target = layout.build_provenance_path
    genuine = target.read_bytes()
    before = _authority_bytes(layout)
    original = workspace_module.verify_release_candidate
    attacked = False

    def mutate_after_verification(*args: Any, **kwargs: Any) -> None:
        nonlocal attacked
        original(*args, **kwargs)
        if not attacked:
            target.write_bytes(b'{"corrupt":true}\n')
            attacked = True

    monkeypatch.setattr(
        workspace_module,
        "verify_release_candidate",
        mutate_after_verification,
    )
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            layout.recover()
    finally:
        target.write_bytes(genuine)

    assert attacked
    assert not layout.release_pointer_path.exists()
    assert _authority_bytes(layout) == before
    provenance = json.loads(layout.build_provenance_path.read_text(encoding="utf-8"))
    provenance["created_at"] = "2026-08-20T00:00:00+00:00"
    artifact_io.atomic_write_json(layout.build_provenance_path, provenance)
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert not layout.release_pointer_path.exists()


def test_direct_release_rechecks_candidate_after_pointer_fault_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-verification authority swap cannot publish a direct pointer."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    target = pipeline.layout.build_provenance_path
    genuine = b""
    attacked = False

    def mutate_at_pointer_seam(name: str) -> None:
        nonlocal attacked, genuine
        if name == "before_release_pointer_replace":
            genuine = target.read_bytes()
            target.write_bytes(b'{"corrupt":true}\n')
            attacked = True

    monkeypatch.setattr(workspace_module, "_fault_point", mutate_at_pointer_seam)
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            _run_to_release(pipeline)
    finally:
        if attacked:
            target.write_bytes(genuine)

    assert attacked
    assert not pipeline.layout.release_pointer_path.exists()


def test_direct_release_rolls_back_pointer_after_writer_boundary_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate mutation inside pointer installation leaves no live pointer."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    target = pipeline.layout.build_provenance_path
    original = workspace_module.write_release_pointer
    genuine = b""
    attacked = False

    def mutate_inside_pointer_write(*args: Any, **kwargs: Any) -> Any:
        nonlocal attacked, genuine
        genuine = target.read_bytes()
        target.write_bytes(genuine + b"\n")
        attacked = True
        return original(*args, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_release_pointer",
        mutate_inside_pointer_write,
    )
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            _run_to_release(pipeline)
    finally:
        if attacked:
            target.write_bytes(genuine)

    assert attacked
    assert not pipeline.layout.release_pointer_path.exists()


def test_release_pointer_rollback_preserves_same_bytes_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rollback quarantines only the exact pointer inode installed by the writer."""
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    layout.published_datasets.mkdir(parents=True)
    payload = b'{"pointer":"owned"}\n'
    layout.release_pointer_path.write_bytes(payload)
    installed = control_jsonl_module.resolve_local_authority_file(
        layout.release_pointer_path,
        layout.tenant_root,
        access="read",
    )
    assert installed.identity is not None
    parked = tmp_path / "parked-owned-pointer.json"
    replacement_identity: int | None = None
    original = workspace_module.remove_local_authority_file

    def replace_before_cleanup(*args: Any, **kwargs: Any) -> bool:
        nonlocal replacement_identity
        layout.release_pointer_path.rename(parked)
        layout.release_pointer_path.write_bytes(payload)
        replacement_identity = layout.release_pointer_path.stat().st_ino
        return original(*args, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "remove_local_authority_file",
        replace_before_cleanup,
    )

    workspace_module._rollback_new_release_pointer(
        layout,
        preexisting=False,
        pointer={},
        installed_identity=installed.identity,
    )

    assert layout.release_pointer_path.read_bytes() == payload
    assert layout.release_pointer_path.stat().st_ino == replacement_identity
    assert parked.read_bytes() == payload


def test_direct_release_rejects_pointer_appearing_at_writer_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An expected-absent pointer cannot overwrite a newly appeared authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    original = workspace_module.write_release_pointer
    foreign = b"FOREIGN\n"
    appeared = False

    def appear_inside_pointer_write(*args: Any, **kwargs: Any) -> Any:
        nonlocal appeared
        layout.release_pointer_path.write_bytes(foreign)
        appeared = True
        return original(*args, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_release_pointer",
        appear_inside_pointer_write,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        _run_to_release(pipeline)

    assert appeared
    assert layout.release_pointer_path.read_bytes() == foreign
    assert layout.load_state().status == "running"


def test_direct_release_rejects_pointer_appearing_before_expected_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The WAL expectation cannot be replaced by a late pointer observation."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    original = workspace_module._optional_local_authority_bytes
    foreign = b"FOREIGN\n"
    appeared = False

    def appear_before_late_snapshot(
        active_layout: EvaluationAssetLayout,
        path: Path,
    ) -> tuple[bool, bytes]:
        nonlocal appeared
        if active_layout is layout and path == layout.release_pointer_path and not appeared:
            path.write_bytes(foreign)
            appeared = True
        return original(active_layout, path)

    monkeypatch.setattr(
        workspace_module,
        "_optional_local_authority_bytes",
        appear_before_late_snapshot,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        _run_to_release(pipeline)

    assert appeared
    assert layout.release_pointer_path.read_bytes() == foreign
    assert layout.load_state().status == "running"


def test_append_only_event_rejects_regular_replacement_at_writer_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An append cannot erase a control row raced in after its bound read."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    original = workspace_module.write_local_authority_text
    native_row = {
        "timestamp": "2026-08-20T00:00:00+00:00",
        "event": "legacy_asset_adopted",
        "tenant_id": layout.tenant_id,
        "asset_id": layout.asset_id,
        "operation_id": "0" * 32,
        "details": {},
    }
    foreign = layout.events_path.read_bytes() + (
        json.dumps(native_row, sort_keys=True) + "\n"
    ).encode("utf-8")
    replaced = False

    def replace_before_append(
        path: Path,
        trusted_root: Path,
        content: str,
        **kwargs: Any,
    ) -> None:
        nonlocal replaced
        if path == layout.events_path and not replaced:
            path.write_bytes(foreign)
            replaced = True
        original(path, trusted_root, content, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_text",
        replace_before_append,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        _run_to_release(pipeline)

    assert replaced
    assert layout.events_path.read_bytes() == foreign
    assert layout.load_state().status == "running"


@pytest.mark.parametrize("mode", ["direct", "recovery"])
@pytest.mark.parametrize("control_name", ["config", "state"])
def test_revision_rejects_control_replacement_at_writer_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    control_name: str,
) -> None:
    """A revision cannot replace control authority raced in after its WAL."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _make_released_checkpoint_mutable(layout)
    original = workspace_module.write_local_authority_json
    foreign = b'{"foreign":true}\n'
    replaced = False
    target = layout.config_path if control_name == "config" else layout.state_path

    if mode == "recovery":
        def stop_after_prepare(name: str) -> None:
            if name == "after_prepared_journal":
                raise _InjectedFault(name)

        monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
        with pytest.raises(_InjectedFault):
            layout.revise_config({"match_threshold": 0.2})
        monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    def replace_before_control_write(
        path: Path,
        trusted_root: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal replaced
        if path == target and not replaced:
            path.write_bytes(foreign)
            replaced = True
        original(path, trusted_root, payload, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_json",
        replace_before_control_write,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        if mode == "direct":
            layout.revise_config({"match_threshold": 0.2})
        else:
            layout.recover()

    assert replaced
    assert target.read_bytes() == foreign


@pytest.mark.parametrize(
    "operation",
    ["direct_release", "recovery_release", "direct_adoption", "recovery_adoption"],
)
def test_terminal_state_replacement_at_writer_boundary_retains_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """A terminal WAL cannot publish over state raced in at its writer."""
    if operation == "recovery_adoption":
        layout, _ = _prepared_adoption(tmp_path, monkeypatch)
        monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
        invoke = layout.recover
    else:
        pipeline, _, _ = _create_pipeline(tmp_path)
        layout = pipeline.layout
        if operation == "direct_adoption":
            _run_to_release(pipeline)
            _downgrade_to_legacy_completed(layout)
            invoke = layout.adopt_legacy
        elif operation == "recovery_release":
            def stop_after_prepare(name: str) -> None:
                if name == "after_release_publication_prepared":
                    raise _InjectedFault(name)

            monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
            with pytest.raises(_InjectedFault):
                _run_to_release(pipeline)
            monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
            invoke = layout.recover
        else:
            invoke = partial(_run_to_release, pipeline)

    original = workspace_module.write_local_authority_json
    foreign = b'{"foreign":true}\n'
    replaced = False

    def replace_before_terminal_state_write(
        path: Path,
        trusted_root: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal replaced
        if (
            path == layout.state_path
            and payload.get("status") == "released"
            and not replaced
        ):
            path.write_bytes(foreign)
            replaced = True
        original(path, trusted_root, payload, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_json",
        replace_before_terminal_state_write,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        invoke()

    assert replaced
    assert layout.state_path.read_bytes() == foreign
    assert layout.release_pointer_path.is_file()


@pytest.mark.parametrize("mode", ["direct", "recovery"])
@pytest.mark.parametrize("control_name", ["manifest", "receipt"])
def test_adoption_rejects_generated_control_replacement_at_writer_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    control_name: str,
) -> None:
    """Adoption cannot overwrite a manifest or receipt raced in after its WAL."""
    if mode == "recovery":
        layout, _ = _prepared_adoption(tmp_path, monkeypatch)
        monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
        invoke = layout.recover
    else:
        pipeline, _, _ = _create_pipeline(tmp_path)
        _run_to_release(pipeline)
        layout = pipeline.layout
        _downgrade_to_legacy_completed(layout)
        invoke = layout.adopt_legacy
    target = (
        layout.manifest_path
        if control_name == "manifest"
        else layout.receipt_path(PipelineStage.RAW_INPUTS)
    )
    original = workspace_module.write_local_authority_json
    foreign = b'{"foreign":true}\n'
    replaced = False

    def replace_before_control_write(
        path: Path,
        trusted_root: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal replaced
        if path == target and not replaced:
            path.write_bytes(foreign)
            replaced = True
        original(path, trusted_root, payload, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_json",
        replace_before_control_write,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        invoke()

    assert replaced
    assert target.read_bytes() == foreign
    assert not layout.release_pointer_path.exists()


def test_run_rejects_state_replacement_at_save_writer_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A normal checkpoint save binds the exact state that was loaded."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    layout = pipeline.layout
    original = workspace_module.write_local_authority_json
    foreign = b'{"foreign":true}\n'
    replaced = False

    def replace_before_state_write(
        path: Path,
        trusted_root: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal replaced
        if path == layout.state_path and payload.get("status") == "running" and not replaced:
            path.write_bytes(foreign)
            replaced = True
        original(path, trusted_root, payload, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_json",
        replace_before_state_write,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        _run_to_release(pipeline)

    assert replaced
    assert layout.state_path.read_bytes() == foreign
    assert rubric.calls == 0
    assert embedding.calls == 0


def test_provider_ledger_rejects_appearance_at_writer_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stage ledger expected absent cannot overwrite a raced control node."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    target = layout.artifact_path(PipelineStage.RUBRIC_EXTRACTION, "provider_calls.jsonl")
    original = provenance_module.write_local_authority_jsonl
    foreign = b"FOREIGN\n"
    appeared = False

    def appear_before_ledger_write(
        path: Path,
        trusted_root: Path,
        rows: Iterable[Mapping[str, Any]],
        **kwargs: Any,
    ) -> None:
        nonlocal appeared
        if path == target and not appeared:
            path.write_bytes(foreign)
            appeared = True
        original(path, trusted_root, rows, **kwargs)

    monkeypatch.setattr(
        provenance_module,
        "write_local_authority_jsonl",
        appear_before_ledger_write,
    )

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        _run_to_release(pipeline)

    assert appeared
    assert target.read_bytes() == foreign


def test_initial_input_copy_rejects_appearance_at_writer_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An initial input copy cannot overwrite a raced local authority node."""
    target = (
        tmp_path
        / "tenants"
        / "tenant_a"
        / "evaluation_assets"
        / "v1"
        / "stages"
        / "01_raw_inputs"
        / "labeled_feedback.jsonl"
    )
    original = workspace_module.write_local_authority_text
    foreign = b"FOREIGN\n"
    appeared = False

    def appear_before_input_copy(
        path: Path,
        trusted_root: Path,
        content: str,
        **kwargs: Any,
    ) -> None:
        nonlocal appeared
        if path == target and not appeared:
            path.write_bytes(foreign)
            appeared = True
        original(path, trusted_root, content, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "write_local_authority_text",
        appear_before_input_copy,
    )

    with pytest.raises(ValueError):
        _create_pipeline(tmp_path)

    assert appeared
    assert target.read_bytes() == foreign


@pytest.mark.parametrize(
    "authority_name",
    [
        "state",
        "config",
        "events",
        "journal",
        "history",
        "receipt",
        "stage_provenance",
        "provider_ledger",
        "build_provenance",
    ],
)
def test_released_verification_uses_one_closed_authority_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority_name: str,
) -> None:
    """Semantic reopens cannot validate bytes different from authenticated bytes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = _run_to_release(pipeline)
    layout = pipeline.layout
    targets = {
        "state": layout.state_path,
        "config": layout.config_path,
        "events": layout.events_path,
        "journal": layout.recovery_journal_path,
        "history": layout.config_history_path,
        "receipt": layout.receipt_path(PipelineStage.DATASET_SPLITS),
        "stage_provenance": layout.stage_provenance_path(PipelineStage.RAW_INPUTS),
        "provider_ledger": layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "provider_calls.jsonl",
        ),
        "build_provenance": layout.build_provenance_path,
    }
    target = targets[authority_name]
    original = durability_module.verify_receipt_chain
    changed = False

    def compact_reserialize(path: Path) -> None:
        if path.suffix == ".jsonl":
            rows = _read_jsonl(path)
            payload = "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in rows
            ).encode("utf-8")
        else:
            payload = (
                json.dumps(
                    json.loads(path.read_text(encoding="utf-8")),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
        assert payload != path.read_bytes()
        path.write_bytes(payload)

    def mutate_after_journal(*args: Any, **kwargs: Any) -> Any:
        nonlocal changed
        compact_reserialize(target)
        changed = True
        return original(*args, **kwargs)

    monkeypatch.setattr(
        durability_module,
        "verify_receipt_chain",
        mutate_after_journal,
    )

    with pytest.raises(EvaluationAssetIntegrityError, match="changed during verification"):
        verify_released_asset(layout, released)

    assert changed


def test_pipeline_receipt_hash_rejects_post_write_authority_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Receipt state hashes come from a bound local authority read."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    target = layout.receipt_path(PipelineStage.RAW_INPUTS)
    external = tmp_path / "external-receipt.json"
    original = EvaluationAssetLayout._write_authority_json
    genuine = b""
    attacked = False
    restore_before_next_write = False

    def race_after_receipt_write(
        active_layout: EvaluationAssetLayout,
        path: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal attacked, genuine, restore_before_next_write
        if active_layout is layout and restore_before_next_write:
            target.unlink()
            target.write_bytes(genuine)
            restore_before_next_write = False
        original(active_layout, path, payload, **kwargs)
        if active_layout is layout and Path(path) == target and not attacked:
            genuine = target.read_bytes()
            external.write_bytes(genuine)
            target.unlink()
            target.symlink_to(external)
            attacked = True
            restore_before_next_write = True

    monkeypatch.setattr(
        EvaluationAssetLayout,
        "_write_authority_json",
        race_after_receipt_write,
    )
    try:
        with pytest.raises(ValueError):
            _run_to_release(pipeline)
    finally:
        if target.is_symlink():
            target.unlink()
            target.write_bytes(genuine)

    assert attacked


@pytest.mark.parametrize("authority_name", ["provider-ledger", "input-manifest"])
def test_stage_eight_control_reads_reject_post_preflight_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority_name: str,
) -> None:
    """Stage 8 consumes ledgers and manifests only through bound authority."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    target = (
        layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "provider_calls.jsonl",
        )
        if authority_name == "provider-ledger"
        else layout.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json")
    )
    external = tmp_path / f"external-{authority_name}.json"
    original = pipeline._finalize_stage_eight_artifacts
    attacked = False

    def race_before_control_read() -> None:
        nonlocal attacked
        genuine = target.read_bytes()
        external.write_bytes(genuine)
        target.unlink()
        target.symlink_to(external)
        attacked = True
        try:
            original()
        finally:
            target.unlink()
            target.write_bytes(genuine)

    monkeypatch.setattr(
        pipeline,
        "_finalize_stage_eight_artifacts",
        race_before_control_read,
    )

    with pytest.raises(ValueError):
        _run_to_release(pipeline)

    assert attacked
    assert not layout.build_provenance_path.exists()
    assert not layout.generations_root.exists()


def test_pipeline_lineage_load_rejects_post_preflight_symlink_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The optional lineage read is one bound observation before authoring."""
    parent_pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(parent_pipeline)
    parent = parent_pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()
    pipeline = EvaluationAssetPipeline(
        child,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    target = child.lineage_path
    genuine = target.read_bytes()
    external = tmp_path / "external-lineage.json"
    external.write_bytes(genuine)
    before = _authority_bytes(child)
    original = pipeline._validate_injected_provider_identities
    attacked = False

    def swap_after_preflight() -> None:
        nonlocal attacked
        original()
        target.unlink()
        target.symlink_to(external)
        attacked = True

    monkeypatch.setattr(
        pipeline,
        "_validate_injected_provider_identities",
        swap_after_preflight,
    )
    try:
        with pytest.raises(ValueError):
            _run_to_release(pipeline)
    finally:
        if target.is_symlink():
            target.unlink()
            target.write_bytes(genuine)

    assert attacked
    assert rubric.calls == 0
    assert embedding.calls == 0
    assert _authority_bytes(child) == before


def test_adoption_recovery_rechecks_candidate_before_pointer_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raced adoption candidate cannot leave public pointer authority."""
    layout, prepared = _prepared_adoption(tmp_path, monkeypatch)
    _install_adoption_target_manifests(layout, prepared)
    for stage in PipelineStage:
        artifact_io.atomic_write_json(
            layout.receipt_path(stage),
            prepared["target_receipts"][stage.value],
        )
    target = layout.stage_provenance_path(PipelineStage.RAW_INPUTS)
    genuine = target.read_bytes()
    original = workspace_module.verify_release_candidate
    attacked = False

    def mutate_after_verification(*args: Any, **kwargs: Any) -> None:
        nonlocal attacked
        original(*args, **kwargs)
        if not attacked:
            target.write_bytes(b'{"corrupt":true}\n')
            attacked = True

    monkeypatch.setattr(
        workspace_module,
        "verify_release_candidate",
        mutate_after_verification,
    )
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    try:
        with pytest.raises(EvaluationAssetIntegrityError):
            layout.recover()
    finally:
        target.write_bytes(genuine)

    assert attacked
    assert not layout.release_pointer_path.exists()
    assert prepared["target_state"]["status"] == "released"


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
    released = _run_to_release(pipeline)
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
        repository_base=tmp_path,
    )
    return pipeline, rubric, embedding


def _run_to_release(
    pipeline: EvaluationAssetPipeline,
    **run_kwargs: Any,
) -> PipelineState:
    """Exercise the explicit review boundary before legacy release assertions."""
    state = pipeline.run(**run_kwargs)
    if state.status != "awaiting_review":
        return state
    page = pipeline.layout.list_review_items()
    for item in page["items"]:
        if item["status"] != "pending":
            continue
        pipeline.layout.decide_review(
            item["case_id"],
            item["fingerprint"],
            "approved",
            reviewer="durability-test",
            expected_review_set_fingerprint=page[
                "review_set_fingerprint"
            ],
        )
    page = pipeline.layout.list_review_items()
    return pipeline.finalize_review(
        reviewer="durability-test",
        expected_review_set_fingerprint=page["review_set_fingerprint"],
        expected_decision_set_fingerprint=page["decision_set_fingerprint"],
    )


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
        repository_base=tmp_path,
    )
    return pipeline, rubric


def _write_input_pair(tenants_root: Path) -> tuple[Path, Path]:
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    common = {
        "schema_version": "fapo-evaluation-input-v1",
        "group_id": "group-train-0",
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
    _run_to_release(pipeline)
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )
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
    _run_to_release(pipeline)
    updates = (
        {"match_threshold": 0.2},
        {"split_seed": 73},
    )
    for revision_updates in updates[:revision_count]:
        _make_released_checkpoint_mutable(pipeline.layout)
        _run_to_release(
            EvaluationAssetPipeline(
                pipeline.layout,
                rubric_provider=rubric,
                embedding_provider=embedding,
            ),
            config_updates=revision_updates,
        )
    return pipeline.layout


def _layout_after_final_committed_mutation(
    tmp_path: Path,
    *,
    operation_kind: str,
    lifecycle: str,
) -> EvaluationAssetLayout:
    """Build a writer-reachable post-commit state for revision/rebuild recovery."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
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
            _run_to_release(
                pipeline,
                config_updates=config_updates,
                _preflight_accepted_callback=stop_after_pipeline_started,
            )
    elif lifecycle == "failed":
        def fail_stage(stage: PipelineStage) -> dict[str, int]:
            raise _InjectedFault(f"failed_{stage.value}")

        pipeline._run_stage = fail_stage  # type: ignore[method-assign]
        with pytest.raises(_InjectedFault, match="failed_"):
            _run_to_release(pipeline, config_updates=config_updates)
    elif lifecycle == "released":
        _run_to_release(pipeline, config_updates=config_updates)
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
    _run_to_release(pipeline)
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
    provenance = prepared["target_provenance"]
    for stage in durability_module.PERSISTED_STAGE_VALUES_V2:
        artifact_io.atomic_write_json(
            layout.stage_provenance_path(stage),
            provenance["stages"][stage],
        )
    artifact_io.atomic_write_json(
        layout.build_provenance_path,
        provenance["build"],
    )
    publication_module.install_generation(
        layout.published_datasets,
        tenant_id=layout.tenant_id,
        asset_id=layout.asset_id,
        split_paths={
            split: layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
            for split in publication_module.LOGICAL_SPLITS
        },
        build_fingerprint=provenance["build"]["identity_sha256"],
        trusted_root=layout.tenant_root,
    )
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
    replayed = stage_three_contract.replay_legacy_stage_three(
        [normalized],
        [rubric],
        asset_id=layout.asset_id,
    )
    trusted_intent = replayed["trusted_intents"][0]
    trusted_case = replayed["trusted_cases"][0]
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
    native_guidelines = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "evaluation_guidelines.jsonl",
    )
    if native_guidelines.is_file():
        _rewrite_stage_three_as_historical_native(layout)
    else:
        _rewrite_stage_seven_as_historical(layout)
        _rewrite_stage_eight_as_historical(layout)
    layout.artifact_path(
        PipelineStage.PREPARED_INPUTS,
        "trusted_split_plan.jsonl",
    ).unlink(missing_ok=True)
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
            (
                {
                    key: value
                    for key, value in event.items()
                    if not (
                        event.get("event") == "pipeline_extended"
                        and key == "operation_id"
                    )
                }
            )
            for event in _read_jsonl(layout.events_path)
            if event.get("event")
            not in {"pipeline_released", "review_required"}
        ],
    )
    if layout.reviews_root.exists():
        shutil.rmtree(layout.reviews_root)
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


def _rewrite_stage_three_as_historical_native(
    layout: EvaluationAssetLayout,
) -> None:
    """Convert a current test release into the frozen pre-v3 native profile."""
    stage_three = PipelineStage.RUBRIC_EXTRACTION
    normalized = _read_jsonl(
        layout.artifact_path(
            PipelineStage.PREPARED_INPUTS,
            "normalized_feedback.jsonl",
        )
    )

    def unprotect(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                key: value
                for key, value in row.items()
                if key
                not in {
                    "protected_split",
                    "source_group_id",
                    "split_group_id",
                    "visibility",
                }
            }
            for row in rows
        ]

    evidence = [
        *_read_jsonl(layout.artifact_path(stage_three, "feedback_evidence.jsonl")),
        *unprotect(
            _read_jsonl(
                layout.artifact_path(
                    stage_three,
                    "protected_feedback_evidence.jsonl",
                )
            )
        ),
    ]
    candidates = [
        *_read_jsonl(
            layout.artifact_path(stage_three, "candidate_guidelines.jsonl")
        ),
        *unprotect(
            _read_jsonl(
                layout.artifact_path(
                    stage_three,
                    "protected_candidate_guidelines.jsonl",
                )
            )
        ),
    ]
    old_guidelines = [
        *_read_jsonl(
            layout.artifact_path(stage_three, "evaluation_guidelines.jsonl")
        ),
        *_read_jsonl(
            layout.artifact_path(
                stage_three,
                "protected_evaluation_guidelines.jsonl",
            )
        ),
    ]
    old_intents = _read_jsonl(
        layout.artifact_path(stage_three, "trusted_intents.jsonl")
    )
    replayed = stage_three_contract.replay_native_stage_three(
        normalized,
        evidence,
        candidates,
        asset_id=layout.asset_id,
        identity_profile="historical_v1",
        text_profile="historical_v1",
    )

    def guideline_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            row.get("route"),
            row.get("intent_label"),
            row.get("description"),
            tuple(row.get("source_record_ids") or []),
        )

    new_guidelines_by_key = {
        guideline_key(row): row for row in replayed["guidelines"]
    }
    identity_replacements = {
        str(row["guideline_id"]): str(
            new_guidelines_by_key[guideline_key(row)]["guideline_id"]
        )
        for row in old_guidelines
    }
    new_intents_by_sources = {
        tuple(row["metadata"]["source_record_ids"]): row
        for row in replayed["trusted_intents"]
    }
    identity_replacements.update(
        {
            str(row["intent_id"]): str(
                new_intents_by_sources[
                    tuple(row["metadata"]["source_record_ids"])
                ]["intent_id"]
            )
            for row in old_intents
        }
    )
    for name, rows in (
        ("feedback_evidence.jsonl", evidence),
        ("candidate_guidelines.jsonl", replayed["candidates"]),
        ("evaluation_guidelines.jsonl", replayed["guidelines"]),
        ("trusted_intents.jsonl", replayed["trusted_intents"]),
        ("trusted_cases.jsonl", replayed["trusted_cases"]),
    ):
        artifact_io.atomic_write_jsonl(
            layout.artifact_path(stage_three, name),
            rows,
        )
    for stage in tuple(PipelineStage)[3:]:
        stage_root = layout.artifact_path(stage, "placeholder").parent
        for path in stage_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in {".json", ".jsonl", ".md"}:
                text = path.read_text(encoding="utf-8")
                for previous, replacement in identity_replacements.items():
                    text = text.replace(previous, replacement)
                artifact_io.atomic_write_text(path, text)
    parent_matches_path = (
        layout.historical_parent_snapshot / "parent_intent_matches.jsonl"
    )
    if parent_matches_path.is_file():
        parent_guidelines = _read_jsonl(
            layout.historical_parent_snapshot
            / "parent_evaluation_guidelines.jsonl"
        )
        parent_identity_replacements = {
            str(row["guideline_id"]): stage_three_contract._guideline_id(
                route=str(row["route"]),
                guideline_payload=row,
                identity_profile="historical_v1",
            )
            for row in parent_guidelines
        }
        text = parent_matches_path.read_text(encoding="utf-8")
        for previous, replacement in {
            **identity_replacements,
            **parent_identity_replacements,
        }.items():
            text = text.replace(previous, replacement)
        artifact_io.atomic_write_text(parent_matches_path, text)
        _refresh_parent_snapshot_manifest(layout, (parent_matches_path,))

    _rewrite_stage_seven_as_historical(layout)
    _rewrite_stage_eight_as_historical(layout)


def _rewrite_stage_seven_as_historical(
    layout: EvaluationAssetLayout,
) -> None:
    """Reconstruct the frozen pre-v3 filtering and keep-mode reuse result."""
    stage = PipelineStage.SYNTHETIC_COVERAGE
    candidates_path = layout.artifact_path(
        stage,
        "synthetic_candidates.jsonl",
    )
    candidates = _read_jsonl(candidates_path)
    synthetic_cases_path = layout.artifact_path(
        stage,
        "synthetic_cases.jsonl",
    )
    if not layout.lineage_path.is_file():
        historical_cases = []
        for case in _read_jsonl(synthetic_cases_path):
            copied = dict(case)
            metadata = dict(copied.get("metadata") or {})
            metadata.pop("dependency_sha256", None)
            copied["metadata"] = metadata
            historical_cases.append(copied)
        artifact_io.atomic_write_jsonl(synthetic_cases_path, historical_cases)
        return
    inherited: list[dict[str, Any]] = []
    reused_cluster_ids: set[str] = set()
    lineage = json.loads(layout.lineage_path.read_text(encoding="utf-8"))
    matches_path = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )
    parent_matches_path = (
        layout.historical_parent_snapshot / "parent_intent_matches.jsonl"
    )
    parent_cases_path = (
        layout.historical_parent_snapshot / "parent_synthetic_cases.jsonl"
    )
    if (
        lineage.get("clustering_mode") == "keep"
        and parent_matches_path.is_file()
        and parent_cases_path.is_file()
    ):
        parent_cases = []
        for case in _read_jsonl(parent_cases_path):
            copied = dict(case)
            metadata = dict(copied.get("metadata") or {})
            metadata.pop("dependency_sha256", None)
            copied["metadata"] = metadata
            parent_cases.append(copied)
        artifact_io.atomic_write_jsonl(parent_cases_path, parent_cases)
        _refresh_parent_snapshot_manifest(layout, (parent_cases_path,))
        matches = {
            str(row["cluster_id"]): row for row in _read_jsonl(matches_path)
        }
        previous = {
            str(row["cluster_id"]): row
            for row in _read_jsonl(parent_matches_path)
        }
        changed = {
            cluster_id
            for cluster_id, match in matches.items()
            if cluster_id not in previous
            or previous[cluster_id].get("status") != match.get("status")
            or previous[cluster_id].get("matched_intent_id")
            != match.get("matched_intent_id")
        }
        for case in parent_cases:
            metadata = dict(case.get("metadata") or {})
            cluster_id = str(metadata.get("source_cluster") or "")
            if (
                cluster_id
                and cluster_id not in changed
                and cluster_id in matches
                and matches[cluster_id].get("status")
                == "matched_trusted_intent"
            ):
                copied = dict(case)
                metadata["dataset_version"] = layout.asset_id
                copied["metadata"] = metadata
                inherited.append(copied)
                reused_cluster_ids.add(cluster_id)
    candidates = [
        case
        for case in candidates
        if str((case.get("metadata") or {}).get("source_cluster"))
        not in reused_cluster_ids
    ]
    filtered = filter_synthetic_cases(
        candidates,
        existing_cases=[
            *_read_jsonl(
                layout.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    "trusted_cases.jsonl",
                )
            ),
            *_read_jsonl(
                layout.artifact_path(
                    PipelineStage.LABEL_INFERENCE,
                    "inferred_cases.jsonl",
                )
            ),
            *inherited,
        ],
    )
    artifact_io.atomic_write_jsonl(candidates_path, candidates)
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(stage, "rejected_synthetic.jsonl"),
        filtered.rejected,
    )
    artifact_io.atomic_write_jsonl(
        layout.artifact_path(stage, "synthetic_filter_issues.jsonl"),
        [
            {
                "case_id": issue.case_id,
                "code": issue.code,
                "message": issue.message,
            }
            for issue in filtered.issues
        ],
    )
    artifact_io.atomic_write_jsonl(
        synthetic_cases_path,
        [*inherited, *filtered.accepted],
    )


def _refresh_parent_snapshot_manifest(
    layout: EvaluationAssetLayout,
    paths: Sequence[Path],
) -> None:
    """Re-anchor test-only snapshot artifacts rewritten to a historical profile."""
    if not paths or not layout.reuse_manifest_path.is_file():
        return
    reuse = json.loads(layout.reuse_manifest_path.read_text(encoding="utf-8"))
    artifacts = reuse["parent_snapshot"]["artifacts"]
    by_name = {str(row["file"]): row for row in artifacts}
    for path in paths:
        row = by_name[path.name]
        row["sha256"] = file_sha256(path)
        row["bytes"] = path.stat().st_size
    artifact_io.atomic_write_json(layout.reuse_manifest_path, reuse)


def _rewrite_stage_eight_as_historical(
    layout: EvaluationAssetLayout,
) -> None:
    """Rebuild current review partitions using the frozen pre-v3 splitter."""
    historical_splits = pipeline_module._default_split_payloads(
        _read_jsonl(
            layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "trusted_cases.jsonl",
            )
        ),
        _read_jsonl(
            layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_cases.jsonl",
            )
        ),
        _read_jsonl(
            layout.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_cases.jsonl",
            )
        ),
        seed=layout.load_config().split_seed,
    )
    for split, rows in historical_splits.items():
        artifact_io.atomic_write_jsonl(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            ),
            rows,
        )
    manifest = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    manifest["split_counts"] = {
        split: len(rows) for split, rows in historical_splits.items()
    }
    artifact_io.atomic_write_json(layout.manifest_path, manifest)
    artifact_io.atomic_write_json(
        layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "dataset_manifest.json",
        ),
        manifest,
    )


def _rewrite_control_json_with_crlf(
    layout: EvaluationAssetLayout,
    path: Path,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    control_jsonl_module.write_local_authority_text(
        path,
        layout.tenants_root,
        canonical.replace("\n", "\r\n"),
        expected_current=path.read_bytes(),
        check_expected_current=True,
    )
    return payload


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


def test_tree_capture_binds_payload_to_inventoried_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient same-name file cannot supply bytes for another inode."""
    trusted_root = tmp_path / "trusted"
    authority_root = trusted_root / "authority"
    authority_root.mkdir(parents=True)
    target = authority_root / "control.json"
    target.write_bytes(b"ORIGINAL")
    parked = tmp_path / "parked-control.json"
    transient = tmp_path / "transient-control.json"
    transient.write_bytes(b"FORGED")
    original = control_jsonl_module.read_local_authority_file_with_identity_at
    attacked = False

    def swap_only_while_bound_read(
        directory_descriptor: int,
        filename: str,
    ) -> tuple[bytes, tuple[int, int, int]]:
        nonlocal attacked
        target.rename(parked)
        transient.rename(target)
        try:
            result = original(directory_descriptor, filename)
        finally:
            target.rename(transient)
            parked.rename(target)
        attacked = True
        return result

    monkeypatch.setattr(
        control_jsonl_module,
        "read_local_authority_file_with_identity_at",
        swap_only_while_bound_read,
    )

    with pytest.raises(ValueError, match="changed while"):
        control_jsonl_module.capture_local_authority_tree(
            authority_root,
            trusted_root,
        )

    assert attacked
    assert target.read_bytes() == b"ORIGINAL"
    assert transient.read_bytes() == b"FORGED"


def test_local_authority_write_binds_returned_inode_to_owned_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-bytes replacement cannot be reported as the installed file."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "control.json"
    parked = tmp_path / "parked-owned-control.json"
    original = control_jsonl_module.atomic_write_bytes_at
    replacement_inode: int | None = None

    def replace_after_install(
        directory_descriptor: int,
        filename: str,
        content: bytes,
        **kwargs: Any,
    ) -> tuple[int, int, int]:
        nonlocal replacement_inode
        installed_identity = original(
            directory_descriptor,
            filename,
            content,
            **kwargs,
        )
        target.rename(parked)
        target.write_bytes(content)
        replacement_inode = target.stat().st_ino
        return installed_identity

    monkeypatch.setattr(
        control_jsonl_module,
        "atomic_write_bytes_at",
        replace_after_install,
    )

    with pytest.raises(ValueError, match="changed after writing"):
        control_jsonl_module.resolve_local_authority_file(
            target,
            trusted_root,
            access="write",
            write_data=b"NEW",
            expected_write_data=None,
            check_expected_write_data=True,
        )

    assert target.read_bytes() == b"NEW"
    assert target.stat().st_ino == replacement_inode
    assert parked.read_bytes() == b"NEW"
    assert parked.stat().st_ino != replacement_inode


def test_asset_lock_rebinds_name_after_flock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The acquired inode must remain the inode named by the lock path."""
    trusted_root = tmp_path / "trusted"
    lock_path = trusted_root / ".locks" / "v1.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_bytes(b"")
    parked = tmp_path / "parked-lock"
    original = local_authority_io.exact_file_lock
    replaced = False

    @contextmanager
    def replace_after_lock(
        file: local_authority_io.BoundFile,
        *,
        timeout: float,
    ) -> Iterable[None]:
        nonlocal replaced
        with original(file, timeout=timeout):
            if not replaced:
                lock_path.rename(parked)
                lock_path.write_bytes(b"")
                replaced = True
            yield

    monkeypatch.setattr(local_authority_io, "exact_file_lock", replace_after_lock)

    with pytest.raises(ValueError, match="changed after acquisition"):
        with control_jsonl_module.acquire_local_authority_lock(
            lock_path,
            trusted_root,
            timeout=0,
        ):
            raise AssertionError("raced lock was yielded")

    assert replaced
    assert lock_path.is_file()
    assert parked.is_file()
    assert lock_path.stat().st_ino != parked.stat().st_ino


def test_created_authority_ancestor_rejects_foreign_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A directory replacing a just-created ancestor is never populated."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "v1" / "stages"
    parked = trusted_root / "parked-owned-v1"
    foreign = trusted_root / "foreign-v1"
    foreign.mkdir()
    (foreign / "KEEP").write_bytes(b"KEEP")
    original = control_jsonl_module.os.mkdir
    replaced = False

    def replace_created_directory(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal replaced
        original(path, mode, dir_fd=dir_fd)
        if (
            isinstance(path, str)
            and path.startswith(".v1.")
            and path.endswith(".directory")
            and dir_fd is not None
            and not replaced
        ):
            created = trusted_root / path
            created.rename(parked)
            foreign.rename(created)
            replaced = True

    monkeypatch.setattr(control_jsonl_module.os, "mkdir", replace_created_directory)

    with pytest.raises(ValueError, match="replaced before opening"):
        with control_jsonl_module.open_local_authority_directory(
            target,
            trusted_root,
            create=True,
        ):
            raise AssertionError("foreign directory was accepted")

    assert replaced
    live = next(
        path
        for path in trusted_root.iterdir()
        if path.name.endswith(".directory") and (path / "KEEP").is_file()
    )
    assert (live / "KEEP").read_bytes() == b"KEEP"
    assert not (live / "stages").exists()
    assert not (trusted_root / "v1").exists()
    assert not any(parked.iterdir())


def test_authority_directory_bootstraps_absent_trusted_root(
    tmp_path: Path,
) -> None:
    """First-time initialization safely creates its trusted tenants root."""
    trusted_root = tmp_path / "tenants"
    target = trusted_root / "tenant_a" / "evaluation_assets" / "v1"

    with control_jsonl_module.open_local_authority_directory(
        target,
        trusted_root,
        create=True,
    ) as descriptor:
        assert local_authority_io.directory_identity(descriptor) == descriptor.identity

    assert target.is_dir()


def test_absent_authority_root_rejects_foreign_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign directory replacing a created tenants root is not populated."""
    trusted_root = tmp_path / "tenants"
    target = trusted_root / "tenant_a"
    parked = tmp_path / "parked-owned-tenants"
    foreign = tmp_path / "foreign-tenants"
    foreign.mkdir()
    (foreign / "KEEP").write_bytes(b"KEEP")
    original = control_jsonl_module.os.mkdir
    replaced = False

    def replace_created_root(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal replaced
        original(path, mode, dir_fd=dir_fd)
        if (
            isinstance(path, str)
            and path.startswith(f".{trusted_root.name}.")
            and path.endswith(".directory")
            and dir_fd is not None
            and not replaced
        ):
            created = trusted_root.parent / path
            created.rename(parked)
            foreign.rename(created)
            replaced = True

    monkeypatch.setattr(control_jsonl_module.os, "mkdir", replace_created_root)

    with pytest.raises(ValueError, match="root was replaced before opening"):
        with control_jsonl_module.open_local_authority_directory(
            target,
            trusted_root,
            create=True,
        ):
            raise AssertionError("foreign trusted root was accepted")

    assert replaced
    live = next(
        path
        for path in trusted_root.parent.iterdir()
        if path.name.endswith(".directory") and (path / "KEEP").is_file()
    )
    assert (live / "KEEP").read_bytes() == b"KEEP"
    assert not (live / "tenant_a").exists()
    assert not trusted_root.exists()
    assert not any(parked.iterdir())


def test_authority_root_symlink_is_never_bootstrapped(
    tmp_path: Path,
) -> None:
    """A linked tenants root is rejected rather than treated as bootstrap state."""
    trusted_root = tmp_path / "tenants"
    external = tmp_path / "external-tenants"
    external.mkdir()
    (external / "KEEP").write_bytes(b"KEEP")
    trusted_root.symlink_to(external, target_is_directory=True)

    with pytest.raises(
        ValueError,
        match="local authority node is not an exact directory",
    ):
        with control_jsonl_module.open_local_authority_directory(
            trusted_root / "tenant_a",
            trusted_root,
            create=True,
        ):
            raise AssertionError("linked trusted root was accepted")

    assert (external / "KEEP").read_bytes() == b"KEEP"
    assert not (external / "tenant_a").exists()


def test_released_journal_validation_uses_one_authority_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Journal semantics cannot transiently reopen different event bytes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    state = _run_to_release(pipeline)
    layout = pipeline.layout
    with layout.events_path.open("ab") as handle:
        handle.write(b'{"tampered":true}\n')

    def reject_live_reopen(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("historical journal reopened live authority")

    monkeypatch.setattr(
        journal_validation_module,
        "resolve_local_authority_file",
        reject_live_reopen,
    )

    with pytest.raises(EvaluationAssetIntegrityError):
        verify_released_asset(layout, state)

    assert layout.events_path.read_bytes().endswith(b'{"tampered":true}\n')


def test_v2_config_history_is_native_evidence_before_provider_calls(
    tmp_path: Path,
) -> None:
    """A schema downgrade cannot hide an operation-bound configuration row."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    layout.revise_config({"match_threshold": 0.5})
    layout.events_path.unlink(missing_ok=True)
    layout.recovery_journal_path.unlink(missing_ok=True)
    raw_state = json.loads(layout.state_path.read_text(encoding="utf-8"))
    raw_state.pop("schema_version")
    artifact_io.atomic_write_json(layout.state_path, raw_state)
    before = _authority_bytes(layout)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    assert durability_module._has_native_authority_evidence(layout, raw_state)
    with pytest.raises(EvaluationAssetIntegrityError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert rubric.calls == 0
    assert embedding.calls == 0
    assert _authority_bytes(layout) == before


def test_direct_adoption_rejects_relabelled_native_revision_without_writes(
    tmp_path: Path,
) -> None:
    """Direct adoption cannot reinterpret operation-bound history as pre-v2."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    layout = pipeline.layout
    layout.revise_config({"match_threshold": 0.5})
    _run_to_release(pipeline)
    _downgrade_to_legacy_completed(layout)
    before = _authority_bytes(layout)
    calls = (rubric.calls, embedding.calls)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert (rubric.calls, embedding.calls) == calls
    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "operation-id",
        "wrong-previous",
        "wrong-boundary",
        "unknown-field",
        "noncanonical-timezone",
    ],
)
def test_config_history_classifier_accepts_only_exact_pre_v2_updates(
    tmp_path: Path,
    mutation: str,
) -> None:
    """Row-local hybrids cannot masquerade as legacy configuration history."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    config = layout.load_config().to_dict()
    rows = _read_jsonl(layout.config_history_path)
    update: dict[str, Any] = {
        "timestamp": rows[0]["timestamp"],
        "revision": 2,
        "event": "configuration_updated",
        "changed_fields": {
            "match_threshold": {"previous": 0.6, "new": 0.5},
        },
        "invalidated_from_stage": "coverage_decisions",
        "resume_from_stage": "coverage_decisions",
    }
    if mutation == "operation-id":
        update["operation_id"] = "0" * 32
    elif mutation == "wrong-previous":
        update["changed_fields"] = {
            "match_threshold": {"previous": 0.4, "new": 0.5},
        }
    elif mutation == "wrong-boundary":
        update["invalidated_from_stage"] = "raw_inputs"
        update["resume_from_stage"] = "raw_inputs"
    elif mutation == "unknown-field":
        update["changed_fields"] = {
            "future_threshold": {"previous": 0.6, "new": 0.5},
        }
    else:
        update["timestamp"] = "2026-08-20T01:00:00+01:00"
    config["match_threshold"] = 0.5
    artifact_io.atomic_write_json(layout.config_path, config)
    artifact_io.atomic_write_jsonl(layout.config_history_path, [*rows, update])

    assert durability_module._has_native_config_history_authority(layout)


def test_exact_pre_v2_config_history_update_remains_compatible(
    tmp_path: Path,
) -> None:
    """The genuine receipt-free update profile remains resumable."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    config = layout.load_config().to_dict()
    rows = _read_jsonl(layout.config_history_path)
    update = {
        "timestamp": rows[0]["timestamp"],
        "revision": 2,
        "event": "configuration_updated",
        "changed_fields": {
            "match_threshold": {"previous": 0.6, "new": 0.5},
        },
        "invalidated_from_stage": "coverage_decisions",
        "resume_from_stage": "coverage_decisions",
    }
    config["match_threshold"] = 0.5
    artifact_io.atomic_write_json(layout.config_path, config)
    artifact_io.atomic_write_jsonl(layout.config_history_path, [*rows, update])

    assert not durability_module._has_native_config_history_authority(layout)


def test_stage_eight_generation_manifest_rejects_writer_boundary_appearance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The workspace generation manifest binds its expected absent target."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    target = layout.artifact_path(
        PipelineStage.DATASET_SPLITS,
        "generation_manifest.json",
    )
    foreign = b"FOREIGN\n"
    original = pipeline_module.resolve_local_authority_file
    attacked = False

    def appear_at_writer_boundary(
        path: Path,
        trusted_root: Path,
        **kwargs: Any,
    ) -> Any:
        nonlocal attacked
        if (
            path == target
            and kwargs.get("access") == "write"
            and kwargs.get("write_data") is not None
            and not attacked
        ):
            path.write_bytes(foreign)
            attacked = True
        return original(path, trusted_root, **kwargs)

    monkeypatch.setattr(
        pipeline_module,
        "resolve_local_authority_file",
        appear_at_writer_boundary,
    )

    with pytest.raises(ValueError, match="appeared before writing"):
        _run_to_release(pipeline)

    assert attacked
    assert target.read_bytes() == foreign
    assert not layout.release_pointer_path.exists()


def test_keep_inventory_rejects_writer_boundary_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep-mode inventory reuse binds its previously snapshotted target."""
    parent_pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(parent_pipeline)
    parent = parent_pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    pipeline = EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    )
    target = child.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    )
    foreign = b"FOREIGN\n"
    original = pipeline_module.resolve_local_authority_file
    attacked = False

    def appear_at_writer_boundary(
        path: Path,
        trusted_root: Path,
        **kwargs: Any,
    ) -> Any:
        nonlocal attacked
        if (
            path == target
            and kwargs.get("access") == "write"
            and kwargs.get("write_data") is not None
            and not attacked
        ):
            path.write_bytes(foreign)
            attacked = True
        return original(path, trusted_root, **kwargs)

    monkeypatch.setattr(
        pipeline_module,
        "resolve_local_authority_file",
        appear_at_writer_boundary,
    )

    with pytest.raises(ValueError, match="bytes changed before writing"):
        _run_to_release(pipeline)

    assert attacked
    assert target.read_bytes() == foreign
    assert not child.release_pointer_path.exists()


def test_atomic_install_does_not_quarantine_late_foreign_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-install replacement remains live under the authority name."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "control.json"
    parked = tmp_path / "parked-owned-control.json"
    original = artifact_io.rename_noreplace_at
    foreign_inode: int | None = None

    def replace_after_install(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        **kwargs: Any,
    ) -> bool:
        nonlocal foreign_inode
        installed = original(
            directory_descriptor,
            source_name,
            target_name,
            **kwargs,
        )
        if installed and target_name == target.name:
            target.rename(parked)
            target.write_bytes(b"LATE-FOREIGN")
            foreign_inode = target.stat().st_ino
        return installed

    monkeypatch.setattr(artifact_io, "rename_noreplace_at", replace_after_install)

    with control_jsonl_module.open_local_authority_directory(
        trusted_root,
        trusted_root,
    ) as descriptor:
        with pytest.raises(ValueError, match="changed during installation"):
            artifact_io.atomic_write_bytes_at(
                descriptor,
                target.name,
                b"NEW",
                expected_target=None,
            )

    assert target.read_bytes() == b"LATE-FOREIGN"
    assert target.stat().st_ino == foreign_inode
    assert parked.read_bytes() == b"NEW"


def test_atomic_rollback_does_not_exchange_over_late_foreign_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Content-mismatch rollback never displaces a replacement target."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "control.json"
    target.write_bytes(b"OLD")
    original_target_inode = target.stat().st_ino
    parked_new = tmp_path / "parked-owned-new.json"
    original = local_authority_io.replace_with_backup
    exchanges = 0
    late_foreign_inode: int | None = None

    def race_exchange(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        **kwargs: Any,
    ) -> local_authority_io.OwnedNode:
        nonlocal exchanges, late_foreign_inode
        exchanges += 1
        if exchanges == 1:
            owned = original(
                directory_descriptor,
                source_name,
                target_name,
                **kwargs,
            )
            (trusted_root / source_name).write_bytes(b"MUTATED-OLD")
            return owned
        target.rename(parked_new)
        target.write_bytes(b"LATE-FOREIGN")
        late_foreign_inode = target.stat().st_ino
        return original(
            directory_descriptor,
            source_name,
            target_name,
            **kwargs,
        )

    monkeypatch.setattr(
        local_authority_io,
        "replace_with_backup",
        race_exchange,
    )

    with control_jsonl_module.open_local_authority_directory(
        trusted_root,
        trusted_root,
    ) as descriptor:
        with pytest.raises(ValueError, match="expected identity"):
            artifact_io.atomic_write_bytes_at(
                descriptor,
                target.name,
                b"NEW",
                expected_target=(
                    target.stat().st_dev,
                    original_target_inode,
                    target.stat().st_mode & 0o170000,
                ),
                expected_target_content=b"OLD",
            )

    assert exchanges == 2
    assert target.read_bytes() == b"LATE-FOREIGN"
    assert target.stat().st_ino == late_foreign_inode
    assert parked_new.read_bytes() == b"NEW"
    hidden = [path for path in trusted_root.iterdir() if path.name.startswith(".control")]
    assert len(hidden) == 1
    assert hidden[0].read_bytes() == b"MUTATED-OLD"


def test_atomic_absent_install_recovers_foreign_source_renamed_after_precheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source-name race cannot leave a foreign node authoritative."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "control.json"
    parked_owned = trusted_root / "parked-owned-control.json"
    original = local_authority_io._rename_with_flags_posix
    attacked = False

    def race_after_identity_check(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        *,
        darwin_flags: int,
        linux_flags: int,
    ) -> bool:
        nonlocal attacked
        if target_name == target.name and linux_flags == 1 and not attacked:
            (trusted_root / source_name).rename(parked_owned)
            (trusted_root / source_name).write_bytes(b"FOREIGN")
            attacked = True
        return original(
            directory_descriptor,
            source_name,
            target_name,
            darwin_flags=darwin_flags,
            linux_flags=linux_flags,
        )

    monkeypatch.setattr(
        local_authority_io,
        "_rename_with_flags_posix",
        race_after_identity_check,
    )
    with control_jsonl_module.open_local_authority_directory(
        trusted_root,
        trusted_root,
    ) as descriptor:
        with pytest.raises(ValueError):
            artifact_io.atomic_write_bytes_at(
                descriptor,
                target.name,
                b"NEW",
                expected_target=None,
            )

    assert attacked
    assert not target.exists()
    assert parked_owned.read_bytes() == b"NEW"
    assert any(
        path.read_bytes() == b"FOREIGN"
        for path in trusted_root.iterdir()
        if path.name.startswith(".control.json.")
    )

    monkeypatch.setattr(local_authority_io, "_rename_with_flags_posix", original)
    with control_jsonl_module.open_local_authority_directory(
        trusted_root,
        trusted_root,
    ) as descriptor:
        artifact_io.atomic_write_bytes_at(
            descriptor,
            target.name,
            b"RETRY",
            expected_target=None,
        )
    assert target.read_bytes() == b"RETRY"


def test_atomic_existing_install_restores_concurrent_target_after_exchange_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A target-name race cannot leave a rejected writer authoritative."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "control.json"
    target.write_bytes(b"OLD")
    expected = target.stat()
    expected_identity = (
        expected.st_dev,
        expected.st_ino,
        expected.st_mode & 0o170000,
    )
    parked_old = trusted_root / "parked-old-control.json"
    original = local_authority_io._rename_with_flags_posix
    attacked = False

    def race_after_identity_check(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        *,
        darwin_flags: int,
        linux_flags: int,
    ) -> bool:
        nonlocal attacked
        if target_name == target.name and linux_flags == 2 and not attacked:
            target.rename(parked_old)
            target.write_bytes(b"FOREIGN")
            attacked = True
        return original(
            directory_descriptor,
            source_name,
            target_name,
            darwin_flags=darwin_flags,
            linux_flags=linux_flags,
        )

    monkeypatch.setattr(
        local_authority_io,
        "_rename_with_flags_posix",
        race_after_identity_check,
    )
    with control_jsonl_module.open_local_authority_directory(
        trusted_root,
        trusted_root,
    ) as descriptor:
        with pytest.raises(ValueError):
            artifact_io.atomic_write_bytes_at(
                descriptor,
                target.name,
                b"NEW",
                expected_target=expected_identity,
                expected_target_content=b"OLD",
            )

    assert attacked
    assert target.read_bytes() == b"FOREIGN"
    assert parked_old.read_bytes() == b"OLD"
    assert not any(
        path.name.startswith(".control.json.")
        for path in trusted_root.iterdir()
    )

    monkeypatch.setattr(local_authority_io, "_rename_with_flags_posix", original)
    retry_expected = target.stat()
    with control_jsonl_module.open_local_authority_directory(
        trusted_root,
        trusted_root,
    ) as descriptor:
        artifact_io.atomic_write_bytes_at(
            descriptor,
            target.name,
            b"RETRY",
            expected_target=(
                retry_expected.st_dev,
                retry_expected.st_ino,
                retry_expected.st_mode & 0o170000,
            ),
            expected_target_content=b"FOREIGN",
        )
    assert target.read_bytes() == b"RETRY"
    assert parked_old.read_bytes() == b"OLD"


def test_detectable_empty_foreign_root_namespace_change_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An extra sibling trace fails closed before a foreign root is used."""
    trusted_root = tmp_path / "tenants"
    target = trusted_root / "tenant_a"
    parked_owned = tmp_path / "parked-owned-tenants"
    foreign = tmp_path / "foreign-tenants"
    foreign_descriptor: int | None = None
    original = control_jsonl_module.os.mkdir
    attacked = False

    def replace_created_root(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal attacked, foreign_descriptor
        original(path, mode, dir_fd=dir_fd)
        if (
            isinstance(path, str)
            and path.startswith(f".{trusted_root.name}.")
            and path.endswith(".directory")
            and dir_fd is not None
            and not attacked
        ):
            created = trusted_root.parent / path
            created.rename(parked_owned)
            original(foreign.name, mode, dir_fd=dir_fd)
            foreign_descriptor = os.open(
                foreign,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            foreign.rename(created)
            attacked = True

    monkeypatch.setattr(control_jsonl_module.os, "mkdir", replace_created_root)
    try:
        with pytest.raises(ValueError):
            with control_jsonl_module.open_local_authority_directory(
                target,
                trusted_root,
                create=True,
            ):
                raise AssertionError("empty foreign root was accepted")
        assert attacked
        assert foreign_descriptor is not None
        assert os.listdir(foreign_descriptor) == []
        assert os.listdir(parked_owned) == []
        monkeypatch.setattr(control_jsonl_module.os, "mkdir", original)
        with control_jsonl_module.open_local_authority_directory(
            target,
            trusted_root,
            create=True,
        ):
            pass
        assert target.is_dir()
        assert os.listdir(foreign_descriptor) == []
    finally:
        if foreign_descriptor is not None:
            os.close(foreign_descriptor)


def test_detectable_empty_foreign_ancestor_namespace_change_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An extra sibling trace fails closed before a foreign ancestor is used."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "v1" / "stages"
    parked_owned = trusted_root / "parked-owned-v1"
    foreign = trusted_root / "foreign-v1"
    foreign_descriptor: int | None = None
    original = control_jsonl_module.os.mkdir
    attacked = False

    def replace_created_ancestor(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal attacked, foreign_descriptor
        original(path, mode, dir_fd=dir_fd)
        if (
            isinstance(path, str)
            and path.startswith(".v1.")
            and path.endswith(".directory")
            and dir_fd is not None
            and not attacked
        ):
            created = trusted_root / path
            created.rename(parked_owned)
            original(foreign.name, mode, dir_fd=dir_fd)
            foreign_descriptor = os.open(
                foreign,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            foreign.rename(created)
            attacked = True

    monkeypatch.setattr(
        control_jsonl_module.os,
        "mkdir",
        replace_created_ancestor,
    )
    try:
        with pytest.raises(ValueError):
            with control_jsonl_module.open_local_authority_directory(
                target,
                trusted_root,
                create=True,
            ):
                raise AssertionError("empty foreign ancestor was accepted")
        assert attacked
        assert foreign_descriptor is not None
        assert os.listdir(foreign_descriptor) == []
        assert os.listdir(parked_owned) == []
        monkeypatch.setattr(control_jsonl_module.os, "mkdir", original)
        with control_jsonl_module.open_local_authority_directory(
            target,
            trusted_root,
            create=True,
        ):
            pass
        assert target.is_dir()
        assert os.listdir(foreign_descriptor) == []
    finally:
        if foreign_descriptor is not None:
            os.close(foreign_descriptor)


def test_directory_creation_holds_bound_parent_lock_through_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every supported creator mutation stays inside the parent lock."""
    parent_descriptor = os.open(
        tmp_path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    original_lock = local_authority_io.exclusive_parent_namespace_lock
    original_mkdir = control_jsonl_module.os.mkdir
    original_rename = control_jsonl_module.rename_noreplace_at
    lock_depth = 0
    observed = {"mkdir": False, "install": False}

    @contextmanager
    def record_lock(
        descriptor: local_authority_io.DirectoryLike,
    ) -> Iterable[None]:
        nonlocal lock_depth
        with original_lock(descriptor):
            if descriptor == parent_descriptor:
                lock_depth += 1
            try:
                yield
            finally:
                if descriptor == parent_descriptor:
                    lock_depth -= 1

    def require_lock_for_mkdir(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        if dir_fd == parent_descriptor:
            assert lock_depth > 0
            observed["mkdir"] = True
        original_mkdir(path, mode, dir_fd=dir_fd)

    def require_lock_for_install(
        directory_descriptor: int,
        source: str,
        destination: str,
        **kwargs: Any,
    ) -> bool:
        if directory_descriptor == parent_descriptor:
            assert lock_depth > 0
            observed["install"] = True
        return original_rename(
            directory_descriptor,
            source,
            destination,
            **kwargs,
        )

    monkeypatch.setattr(
        local_authority_io,
        "exclusive_parent_namespace_lock",
        record_lock,
    )
    monkeypatch.setattr(control_jsonl_module.os, "mkdir", require_lock_for_mkdir)
    monkeypatch.setattr(
        control_jsonl_module,
        "rename_noreplace_at",
        require_lock_for_install,
    )
    directory_descriptor: local_authority_io.BoundDirectory | None = None
    try:
        directory_descriptor, _ = (
            control_jsonl_module.create_and_open_local_directory_at(
                parent_descriptor,
                "owned",
                final_mode=0o700,
                replacement_error="replacement",
            )
        )
        assert observed == {"mkdir": True, "install": True}
        assert lock_depth == 0
    finally:
        if directory_descriptor is not None:
            directory_descriptor.close()
        os.close(parent_descriptor)


@pytest.mark.parametrize(
    "mutation",
    [
        "origin-bool",
        "origin-float",
        "inherited-origin-bool",
        "update-previous-bool",
        "update-new-float",
        "current-config-bool",
    ],
)
def test_pre_v2_config_history_classifier_rejects_type_coercions(
    tmp_path: Path,
    mutation: str,
) -> None:
    """Historical classification uses exact JSON scalar types throughout."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    if mutation == "inherited-origin-bool":
        _run_to_release(pipeline)
        parent = layout
        layout = EvaluationAssetLayout(
            parent.tenants_root,
            parent.tenant_id,
            "v2",
        )
        layout.initialize_extension(
            parent,
            additional_feedback=_write_additional_feedback(parent.tenants_root),
            additional_unlabeled=None,
            clustering_mode="keep",
        )
    rows = _read_jsonl(layout.config_history_path)
    config = json.loads(layout.config_path.read_text(encoding="utf-8"))
    if mutation in {"origin-bool", "inherited-origin-bool"}:
        rows[0]["configuration"]["cluster_count"] = True
        config["cluster_count"] = True
    elif mutation == "origin-float":
        rows[0]["configuration"]["cluster_count"] = 1.0
        config["cluster_count"] = 1.0
    elif mutation == "current-config-bool":
        config["cluster_count"] = True
    else:
        update: dict[str, Any] = {
            "timestamp": rows[0]["timestamp"],
            "revision": 2,
            "event": "configuration_updated",
            "changed_fields": {
                "cluster_count": {"previous": 1, "new": 2},
            },
            "invalidated_from_stage": "intent_clustering",
            "resume_from_stage": "intent_clustering",
        }
        if mutation == "update-previous-bool":
            update["changed_fields"]["cluster_count"]["previous"] = True
        else:
            update["changed_fields"]["cluster_count"]["new"] = 2.0
        rows.append(update)
        config["cluster_count"] = 2 if mutation == "update-previous-bool" else 2.0
    artifact_io.atomic_write_jsonl(layout.config_history_path, rows)
    artifact_io.atomic_write_json(layout.config_path, config)

    assert durability_module._has_native_config_history_authority(layout)


@pytest.mark.parametrize("schema_mode", ["missing", "v1"])
def test_type_coerced_pre_v2_history_fails_before_calls_or_writes(
    tmp_path: Path,
    schema_mode: str,
) -> None:
    """A downgraded native history cannot cross provider or write boundaries."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    layout = pipeline.layout
    rows = _read_jsonl(layout.config_history_path)
    config = json.loads(layout.config_path.read_text(encoding="utf-8"))
    rows[0]["configuration"]["cluster_count"] = True
    config["cluster_count"] = True
    state = json.loads(layout.state_path.read_text(encoding="utf-8"))
    if schema_mode == "missing":
        state.pop("schema_version")
    else:
        state["schema_version"] = "fapo-evaluation-asset-state-v1"
    artifact_io.atomic_write_jsonl(layout.config_history_path, rows)
    artifact_io.atomic_write_json(layout.config_path, config)
    artifact_io.atomic_write_json(layout.state_path, state)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert rubric.calls == 0
    assert embedding.calls == 0
    assert _authority_bytes(layout) == before


def test_revised_release_journal_uses_captured_config_history_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A revised release uses captured history and reports post-capture drift."""
    layout = _release_with_config_revisions(tmp_path, revision_count=1)
    state = layout.load_state()
    before = _authority_bytes(layout)
    history_key = next(
        key for key in before if key.endswith("config_history.jsonl")
    )
    swapped_history = before[history_key] + b'{"post_capture":true}\n'
    original_resolve = journal_validation_module.resolve_local_authority_file
    original_capture = durability_module._capture_release_authority
    live_reopens = 0
    capture_calls = 0

    def reject_live_history(
        path: Path,
        trusted_root: Path,
        **kwargs: Any,
    ) -> Any:
        nonlocal live_reopens
        if Path(path) == layout.config_history_path:
            live_reopens += 1
            raise AssertionError("closed snapshot escaped to live config history")
        return original_resolve(path, trusted_root, **kwargs)

    def capture_then_swap(target_layout: EvaluationAssetLayout) -> Any:
        nonlocal capture_calls
        captured = original_capture(target_layout)
        capture_calls += 1
        if capture_calls == 1:
            layout.config_history_path.write_bytes(swapped_history)
        return captured

    monkeypatch.setattr(
        journal_validation_module,
        "resolve_local_authority_file",
        reject_live_history,
    )
    monkeypatch.setattr(
        durability_module,
        "_capture_release_authority",
        capture_then_swap,
    )

    with pytest.raises(
        EvaluationAssetIntegrityError,
        match="release authority changed during verification",
    ):
        verify_released_asset(layout, state)

    after = _authority_bytes(layout)
    expected = dict(before)
    expected[history_key] = swapped_history
    assert live_reopens == 0
    assert capture_calls == 2
    assert after == expected


def test_outstanding_revision_journal_uses_captured_config_history_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outstanding revision validation never escapes its supplied snapshot."""
    layout = _release_with_config_revisions(tmp_path, revision_count=1)
    _make_released_checkpoint_mutable(layout)

    def stop_after_prepare(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"split_seed": 73})
    entries = _read_jsonl(layout.recovery_journal_path)
    prepared = entries[-1]
    assert prepared["phase"] == "prepared"

    snapshot, snapshot_records = durability_module._capture_release_authority(layout)
    before = _authority_bytes(layout)
    history_key = next(
        key for key in before if key.endswith("config_history.jsonl")
    )
    swapped_history = before[history_key] + b'{"post_capture":true}\n'
    layout.config_history_path.write_bytes(swapped_history)
    original_resolve = journal_validation_module.resolve_local_authority_file
    live_reopens = 0

    def reject_live_history(
        path: Path,
        trusted_root: Path,
        **kwargs: Any,
    ) -> Any:
        nonlocal live_reopens
        if Path(path) == layout.config_history_path:
            live_reopens += 1
            raise AssertionError("closed snapshot escaped to live config history")
        return original_resolve(path, trusted_root, **kwargs)

    monkeypatch.setattr(
        journal_validation_module,
        "resolve_local_authority_file",
        reject_live_history,
    )
    validated = journal_validation_module.validate_recovery_journal(
        layout,
        entries,
        artifact_overrides=snapshot,
    )

    current_snapshot, current_records = durability_module._capture_release_authority(
        layout
    )
    after = _authority_bytes(layout)
    expected = dict(before)
    expected[history_key] = swapped_history
    assert validated.outstanding is not None
    assert validated.outstanding["operation_id"] == prepared["operation_id"]
    assert live_reopens == 0
    assert (current_snapshot, current_records) != (snapshot, snapshot_records)
    assert after == expected


@pytest.mark.parametrize(
    "source",
    [
        "from pathlib import Path\nPath('x').unlink()",
        "from pathlib import Path\nPath('x').rmdir()",
        "import os\nos.remove('x')",
        "import os\nos.unlink('x')",
        "import os\nos.rmdir('x')",
        "import os\nos.removedirs('x')",
        "import shutil\nshutil.rmtree('x')",
        "from os import remove as erase\nerase('x')",
        "import os as operating_system\noperating_system.remove('x')",
        "import os\nerase = os.remove\nerase('x')",
        "import shutil\nconsumer([shutil.rmtree])",
        "import os\nholder.callback = os.removedirs",
    ],
)
def test_studio_writer_guard_rejects_finite_deletion_aliases(source: str) -> None:
    """Every ordinary finite deletion spelling remains behind audited seams."""
    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/example.py"),
        source,
    )


def test_studio_writer_guard_rejects_direct_unlink_in_control_cleanup() -> None:
    """Control cleanup cannot broadly allow a direct authority deletion."""
    source = (
        "import os\n"
        "def remove_local_authority_file():\n"
        "    os.unlink('release.json')\n"
    )

    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
        source,
    )


def test_studio_writer_guard_rejects_getattr_unlink_in_control_cleanup() -> None:
    """Control cleanup cannot broadly allow literal-getattr authority deletion."""
    source = (
        "from shutil import os\n"
        "def remove_local_authority_file():\n"
        "    getattr(os, 'unlink')('release.json')\n"
    )

    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
        source,
    )


@pytest.mark.parametrize(
    "source",
    [
        "from pathlib import Path\nPath('x').mkdir()",
        "import os\nos.mkdir('x')",
        "import os\nos.makedirs('x')",
        "from os import mkdir as make\nmake('x')",
        "from os import makedirs as make\nmake('x')",
        "import os as operating_system\noperating_system.mkdir('x')",
        "import os as operating_system\noperating_system.makedirs('x')",
        "import os\nmake = os.mkdir\nmake('x')",
        "import os\nconsumer([os.makedirs])",
        "import os\nholder.callback = os.mkdir",
        "from pathlib import Path\ngetattr(Path('x'), 'mkdir')()",
    ],
)
def test_studio_writer_guard_rejects_finite_directory_creation_aliases(
    source: str,
) -> None:
    """Every ordinary finite directory-creation spelling is guarded."""
    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/example.py"),
        source,
    )


@pytest.mark.parametrize(
    "source",
    [
        "import operator\noperator.methodcaller('mkdir')(Path('x'))",
        "import operator\noperator.attrgetter('mkdir')(Path('x'))()",
        "import operator\noperator.methodcaller('makedirs', 'x')(os)",
        "import operator\noperator.attrgetter('makedirs')(os)('x')",
        "from operator import methodcaller\nmethodcaller('mkdir')(Path('x'))",
        "from operator import attrgetter as get\nget('mkdir')(Path('x'))()",
        "import operator as op\nop.methodcaller('mkdir')(Path('x'))",
        "import operator\nmake = operator.methodcaller\nmake('mkdir')(Path('x'))",
        "import operator\nconsumer(operator.methodcaller('mkdir'))",
        "import operator\ncallback = operator.attrgetter('mkdir')",
        "import operator\nreturn_callback(operator.attrgetter('path.mkdir'))",
        "import operator\ncallbacks = [operator.methodcaller('mkdir')]",
    ],
)
def test_studio_writer_guard_rejects_literal_operator_sink_factories(
    source: str,
) -> None:
    """Finite literal operator factories cannot hide persistence methods."""
    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/example.py"),
        source,
    )


def test_studio_writer_guard_rejects_wildcard_methodcaller_unlink() -> None:
    """A wildcard-imported literal methodcaller cannot hide deletion."""
    source = (
        "from operator import *\n"
        "from pathlib import Path\n"
        "methodcaller('unlink')(Path('x'))\n"
    )

    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/example.py"),
        source,
    )


def test_studio_writer_guard_rejects_wildcard_attrgetter_mkdir() -> None:
    """A wildcard-imported literal attrgetter cannot hide directory creation."""
    source = (
        "from operator import *\n"
        "from pathlib import Path\n"
        "attrgetter('mkdir')(Path('x'))()\n"
    )

    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/example.py"),
        source,
    )


@pytest.mark.parametrize(
    "source",
    [
        "import operator\noperator.methodcaller('upper')('value')",
        "import operator\noperator.attrgetter('model')(provider)",
        "import operator\noperator.methodcaller(method_name)(target)",
        "import operator\noperator.attrgetter(attribute_name)(target)",
    ],
)
def test_studio_writer_guard_keeps_nonpersistent_operator_factories(
    source: str,
) -> None:
    """The finite guard makes no claim about dynamic operator factories."""
    assert _studio_writer_violations(
        Path("src/hephaestus/evaluation_assets/example.py"),
        source,
    ) == []


@pytest.mark.parametrize(
    ("path", "source"),
    [
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "import os\n"
            "def create_and_open_local_directory_at():\n"
            "    os.mkdir(private_name, private_mode, dir_fd=parent_descriptor)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def _atomic_write_text():\n"
            "    path.parent.mkdir(parents=True, exist_ok=True)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def _atomic_write_binary():\n"
            "    path.parent.mkdir(parents=True, exist_ok=True)",
        ),
        (
            Path("src/hephaestus/datasets/evaluation_assets.py"),
            "def assemble_dataset_bundle():\n"
            "    output_dir.mkdir(parents=True, exist_ok=True)",
        ),
    ],
)
def test_studio_writer_guard_keeps_exact_directory_creation_seams(
    path: Path,
    source: str,
) -> None:
    """Only the four reviewed directory-bootstrap call shapes remain allowed."""
    assert _studio_writer_violations(path, source) == []


@pytest.mark.parametrize(
    ("path", "source"),
    [
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "import os\n"
            "def create_and_open_local_directory_at():\n"
            "    os.mkdir(private_name, private_mode)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "import os\n"
            "def create_and_open_local_directory_at():\n"
            "    os.mkdir(private_name, private_mode, dir_fd=other_descriptor)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "import os\n"
            "def create_and_open_local_directory_at():\n"
            "    make = os.mkdir\n"
            "    make(private_name, private_mode, dir_fd=parent_descriptor)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def _atomic_write_text():\n"
            "    other.parent.mkdir(parents=True, exist_ok=True)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "def _atomic_write_binary():\n"
            "    path.parent.mkdir(parents=False, exist_ok=True)",
        ),
        (
            Path("src/hephaestus/datasets/evaluation_assets.py"),
            "def assemble_dataset_bundle():\n"
            "    other_dir.mkdir(parents=True, exist_ok=True)",
        ),
        (
            Path("src/hephaestus/datasets/evaluation_assets.py"),
            "def assemble_dataset_bundle():\n"
            "    output_dir.mkdir(**options)",
        ),
        (
            Path("src/hephaestus/datasets/evaluation_assets.py"),
            "def other_assembler():\n"
            "    output_dir.mkdir(parents=True, exist_ok=True)",
        ),
        (
            Path("src/hephaestus/artifact_io.py"),
            "import operator\n"
            "def _atomic_write_text():\n"
            "    operator.methodcaller("
            "'mkdir', parents=True, exist_ok=True)(path.parent)",
        ),
        (
            Path("src/hephaestus/evaluation_assets/control_jsonl.py"),
            "import operator\n"
            "def create_and_open_local_directory_at():\n"
            "    operator.methodcaller("
            "'mkdir', private_name, private_mode, "
            "dir_fd=parent_descriptor)(os)",
        ),
    ],
)
def test_studio_writer_guard_rejects_nearby_directory_creation_seams(
    path: Path,
    source: str,
) -> None:
    """A trusted module or function name cannot broaden a reviewed mkdir seam."""
    assert _studio_writer_violations(path, source)


def test_eas_directory_creation_never_bootstraps_through_compatibility_seams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical Studio creation never asks a generic Path.mkdir to create."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()
    original_mkdir = Path.mkdir
    compatibility_creations: list[Path] = []

    def observe_compatibility_mkdir(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        missing = not path.exists()
        original_mkdir(path, *args, **kwargs)
        if missing:
            compatibility_creations.append(path)

    monkeypatch.setattr(Path, "mkdir", observe_compatibility_mkdir)

    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id="v1",
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
        repository_base=tmp_path,
    )
    released = _run_to_release(pipeline)

    assert released.status == "released"
    assert compatibility_creations == []


def test_eas_keep_extension_never_bootstraps_through_compatibility_seams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extension authority and generation parents use the bound helper too."""
    parent_pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(parent_pipeline)
    parent = parent_pipeline.layout
    additional = _write_additional_feedback(parent.tenants_root)
    original_mkdir = Path.mkdir
    compatibility_creations: list[Path] = []

    def observe_compatibility_mkdir(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        missing = not path.exists()
        original_mkdir(path, *args, **kwargs)
        if missing:
            compatibility_creations.append(path)

    monkeypatch.setattr(Path, "mkdir", observe_compatibility_mkdir)
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    child.initialize_extension(
        parent,
        additional_feedback=additional,
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    released = _run_to_release(
        EvaluationAssetPipeline(
            child,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        )
    )

    assert released.status == "released"
    assert child.historical_parent_snapshot.is_dir()
    assert compatibility_creations == []


def test_cleanup_raw_rename_race_restores_concurrent_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cleanup-source race restores the concurrent node to its live name."""
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    target = trusted_root / "target.jsonl"
    target.write_bytes(b"OLD\n")
    parked_old = trusted_root / "parked-old.jsonl"
    original = local_authority_io._rename_with_flags_posix
    foreign_identity: tuple[int, int, int] | None = None
    attacked = False

    def race_after_identity_check(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
        *,
        darwin_flags: int,
        linux_flags: int,
    ) -> bool:
        nonlocal attacked, foreign_identity
        if (
            source_name == target.name
            and target_name.endswith(".removed")
            and linux_flags == 1
            and not attacked
        ):
            target.rename(parked_old)
            target.write_bytes(b"FOREIGN\n")
            foreign = target.stat()
            foreign_identity = (
                foreign.st_dev,
                foreign.st_ino,
                foreign.st_mode & 0o170000,
            )
            attacked = True
        return original(
            directory_descriptor,
            source_name,
            target_name,
            darwin_flags=darwin_flags,
            linux_flags=linux_flags,
        )

    monkeypatch.setattr(
        local_authority_io,
        "_rename_with_flags_posix",
        race_after_identity_check,
    )

    with pytest.raises(ValueError):
        control_jsonl_module.remove_local_authority_file(target, trusted_root)

    restored = target.stat()
    assert attacked
    assert foreign_identity is not None
    assert (
        restored.st_dev,
        restored.st_ino,
        restored.st_mode & 0o170000,
    ) == foreign_identity
    assert target.read_bytes() == b"FOREIGN\n"
    assert parked_old.read_bytes() == b"OLD\n"


@pytest.mark.parametrize(
    "parent_asset_id",
    [
        "",
        "   ",
        " parent ",
        "../v0",
        "v1",
        "-v0",
        "v0/name",
        "a" * 129,
    ],
)
@pytest.mark.parametrize("schema_mode", ["missing", "v1"])
def test_malformed_inherited_pre_v2_history_fails_before_calls_or_writes(
    tmp_path: Path,
    parent_asset_id: str,
    schema_mode: str,
) -> None:
    """Malformed historical parent identity is native before any side effect."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    layout = pipeline.layout
    rows = _read_jsonl(layout.config_history_path)
    rows[0]["event"] = "configuration_inherited"
    rows[0]["parent_asset_id"] = parent_asset_id
    state = json.loads(layout.state_path.read_text(encoding="utf-8"))
    if schema_mode == "missing":
        state.pop("schema_version")
    else:
        state["schema_version"] = "fapo-evaluation-asset-state-v1"
    artifact_io.atomic_write_jsonl(layout.config_history_path, rows)
    artifact_io.atomic_write_json(layout.state_path, state)
    before = _authority_bytes(layout)

    assert durability_module._has_native_config_history_authority(layout)
    with pytest.raises(EvaluationAssetIntegrityError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert rubric.calls == 0
    assert embedding.calls == 0
    assert _authority_bytes(layout) == before


def test_exact_pre_v2_inherited_history_remains_compatible(tmp_path: Path) -> None:
    """A genuine stripped parent identity remains in the legacy profile."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    layout = pipeline.layout
    rows = _read_jsonl(layout.config_history_path)
    rows[0]["event"] = "configuration_inherited"
    rows[0]["parent_asset_id"] = "v0"
    artifact_io.atomic_write_jsonl(layout.config_history_path, rows)
    artifact_io.atomic_write_json(
        layout.lineage_path,
        {"parent_asset_id": "v0"},
    )

    assert not durability_module._has_native_config_history_authority(layout)


def test_pr2_pre_v2_updated_history_adopts_and_verifies(
    tmp_path: Path,
) -> None:
    """One frozen operation-free history grammar serves detection and adoption."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    config = layout.load_config().to_dict()
    history = _read_jsonl(layout.config_history_path)
    history.append(
        {
            "timestamp": history[0]["timestamp"],
            "revision": 2,
            "event": "configuration_updated",
            "changed_fields": {
                "match_threshold": {"previous": 0.6, "new": 0.5},
            },
            "invalidated_from_stage": "coverage_decisions",
            "resume_from_stage": "coverage_decisions",
        }
    )
    config["match_threshold"] = 0.5
    artifact_io.atomic_write_json(layout.config_path, config)
    artifact_io.atomic_write_jsonl(layout.config_history_path, history)

    assert not durability_module._has_native_config_history_authority(layout)
    adopted = layout.adopt_legacy()

    assert adopted.status == "released"
    verify_released_asset(layout, adopted)


@pytest.mark.parametrize(
    "fault_name",
    [
        *(f"after_adoption_provenance_{stage.value}" for stage in PipelineStage),
        "after_adoption_build_provenance",
    ],
)
def test_pr2_adoption_provenance_prefix_is_wal_owned_and_resumable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Every adoption provenance target follows its durable prepared row."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    _run_to_release(pipeline)
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def inject(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(
        workspace_module,
        "_fault_point",
        inject,
    )
    with pytest.raises(_InjectedFault, match=fault_name):
        layout.adopt_legacy()

    rows = _read_jsonl(layout.recovery_journal_path)
    assert [(row["kind"], row["phase"]) for row in rows] == [
        ("legacy_adoption", "prepared")
    ]

    monkeypatch.setattr(workspace_module, "_fault_point", lambda _name: None)
    assert layout.recover() == [rows[0]["operation_id"]]
    verify_released_asset(layout, layout.load_state())


@pytest.mark.parametrize(
    "operation_kind",
    ["configuration_revision", "checkpoint_rebuild"],
)
@pytest.mark.parametrize(
    "field",
    [
        "tenant_id",
        "asset_id",
        "schema_version",
        "created_at",
        "mutation_sequence",
        "last_operation_id",
    ],
)
def test_pr2_final_committed_mutation_binds_stable_state_identity(
    tmp_path: Path,
    operation_kind: str,
    field: str,
) -> None:
    """Final committed mutation recovery authenticates stable state continuity."""
    layout = _layout_after_final_committed_mutation(
        tmp_path,
        operation_kind=operation_kind,
        lifecycle="running",
    )
    raw = json.loads(layout.state_path.read_text(encoding="utf-8"))
    replacements: dict[str, Any] = {
        "tenant_id": "other_tenant",
        "asset_id": "other_asset",
        "schema_version": "fapo-evaluation-asset-state-v1",
        "created_at": "2026-08-01T00:00:00+00:00",
        "mutation_sequence": raw["mutation_sequence"] + 1,
        "last_operation_id": "f" * 32,
    }
    raw[field] = replacements[field]
    artifact_io.atomic_write_json(layout.state_path, raw)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError):
        layout.recover()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "operation",
    ["direct_release", "recovery_release", "direct_adoption", "recovery_adoption"],
)
def test_pr2_post_state_fault_retains_recoverable_release_tuple(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """A post-state verifier fault retains pointer plus target state for recovery."""
    if operation == "recovery_adoption":
        layout, _ = _prepared_adoption(tmp_path, monkeypatch)
        monkeypatch.setattr(workspace_module, "_fault_point", lambda _name: None)
        pipeline = None
        invoke = layout.recover
    else:
        pipeline, _, _ = _create_pipeline(tmp_path)
        layout = pipeline.layout
        if operation == "direct_adoption":
            _run_to_release(pipeline)
            _downgrade_to_legacy_completed(layout)
            invoke = layout.adopt_legacy
        elif operation == "recovery_release":
            def stop_after_prepare(name: str) -> None:
                if name == "after_release_publication_prepared":
                    raise _InjectedFault(name)

            monkeypatch.setattr(workspace_module, "_fault_point", stop_after_prepare)
            with pytest.raises(_InjectedFault, match="after_release_publication_prepared"):
                _run_to_release(pipeline)
            monkeypatch.setattr(workspace_module, "_fault_point", lambda _name: None)
            invoke = layout.recover
        else:
            invoke = partial(_run_to_release, pipeline)

    original_verify = workspace_module.verify_released_asset
    failed = False

    def fail_after_state_install(
        selected: EvaluationAssetLayout,
        state: PipelineState,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal failed
        persisted = selected.load_state()
        if not failed and state.status == "released" and persisted.status == "released":
            failed = True
            raise _InjectedFault("post_state_verifier")
        return original_verify(selected, state, *args, **kwargs)

    monkeypatch.setattr(
        workspace_module,
        "verify_released_asset",
        fail_after_state_install,
    )
    with pytest.raises(_InjectedFault, match="post_state_verifier"):
        invoke()

    rows = _read_jsonl(layout.recovery_journal_path)
    assert failed
    assert layout.load_state().status == "released"
    assert layout.release_pointer_path.is_file()
    assert rows[-1]["phase"] == "prepared"
    calls = (
        (pipeline.rubric_provider.calls, pipeline.embedding_provider.calls)
        if pipeline is not None
        else None
    )

    monkeypatch.setattr(
        workspace_module,
        "verify_released_asset",
        original_verify,
    )
    operation_id = rows[-1]["operation_id"]
    assert layout.recover() == [operation_id]
    assert layout.recover() == []
    if pipeline is not None:
        assert (pipeline.rubric_provider.calls, pipeline.embedding_provider.calls) == calls
    verify_released_asset(layout, layout.load_state())


@pytest.mark.parametrize(
    "function_name",
    ["atomic_write_json", "atomic_write_bytes_at"],
)
def test_studio_writer_guard_rejects_unlink_in_broad_artifact_seams(
    function_name: str,
) -> None:
    """Only the two exact legacy temporary-cleanup functions may unlink."""
    source = (
        "from pathlib import Path\n"
        f"def {function_name}():\n"
        "    Path('authority.json').unlink()\n"
    )
    assert _studio_writer_violations(
        Path("src/hephaestus/artifact_io.py"),
        source,
    )


def test_studio_writer_guard_keeps_exact_legacy_temp_unlink_seam() -> None:
    """The literal missing-ok temporary cleanup remains audited and allowed."""
    source = (
        "from pathlib import Path\n"
        "def _atomic_write_text():\n"
        "    temporary_path = Path('temporary')\n"
        "    temporary_path.unlink(missing_ok=True)\n"
    )
    assert not _studio_writer_violations(
        Path("src/hephaestus/artifact_io.py"),
        source,
    )


_PR2_RUBRIC_INJECTED_FIELDS = (
    "provider_name",
    "model",
    "timeout_seconds",
    "max_retries",
    "retry_backoff_seconds",
    "max_output_tokens",
    "temperature",
    "response_format",
    "seed",
)
_PR2_EMBEDDING_INJECTED_FIELDS = (
    "provider_name",
    "model",
    "timeout_seconds",
    "max_retries",
    "retry_backoff_seconds",
    "batch_size",
    "response_format",
    "seed",
)


@pytest.mark.parametrize(
    ("role", "field_name"),
    [
        *(("rubric", name) for name in _PR2_RUBRIC_INJECTED_FIELDS),
        *(("embedding", name) for name in _PR2_EMBEDDING_INJECTED_FIELDS),
    ],
)
@pytest.mark.parametrize("would_fail", [False, True])
def test_pr2_injected_provider_payloads_fail_before_calls_or_writes(
    tmp_path: Path,
    role: str,
    field_name: str,
    would_fail: bool,
) -> None:
    """Every persisted injected-provider scalar is strict locked preflight."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)
    selected = rubric if role == "rubric" else embedding
    canary = f"sk-{role}-{field_name}-{would_fail}-canary"
    setattr(selected, field_name, canary)
    if would_fail:
        if role == "rubric":
            selected.generate_json = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[method-assign]
                RuntimeError("safe provider failure")
            )
        else:
            selected.embed_texts = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[method-assign]
                RuntimeError("safe provider failure")
            )
    before = _authority_bytes(pipeline.layout)

    with pytest.raises((EvaluationAssetIntegrityError, ValueError)):
        _run_to_release(pipeline)

    assert rubric.calls == 0
    assert embedding.calls == 0
    assert _authority_bytes(pipeline.layout) == before
    assert not any(
        canary.encode("utf-8") in path.read_bytes()
        for path in pipeline.layout.tenant_root.rglob("*")
        if path.is_file()
    )


@pytest.mark.parametrize("payload_kind", ["stage_provenance", "receipt"])
def test_pr2_generated_payloads_validate_before_authority_writers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload_kind: str,
) -> None:
    """Complete generated provenance and receipts are rejected in memory."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    canary = f"sk-{payload_kind}-builder-canary"
    writer_reached = False
    original_write = EvaluationAssetLayout._write_authority_json

    def reject_target_writer(
        layout: EvaluationAssetLayout,
        path: Path,
        payload: Mapping[str, Any],
        **kwargs: Any,
    ) -> None:
        nonlocal writer_reached
        is_target = (
            path == layout.stage_provenance_path(PipelineStage.RAW_INPUTS)
            if payload_kind == "stage_provenance"
            else path == layout.receipt_path(PipelineStage.RAW_INPUTS)
        )
        if is_target:
            writer_reached = True
            raise AssertionError("invalid payload reached its authority writer")
        original_write(layout, path, payload, **kwargs)

    monkeypatch.setattr(
        EvaluationAssetLayout,
        "_write_authority_json",
        reject_target_writer,
    )
    if payload_kind == "stage_provenance":
        original_builder = pipeline_module.build_stage_provenance

        def corrupt_stage_provenance(**kwargs: Any) -> dict[str, Any]:
            payload = original_builder(**kwargs)
            payload["provider_identity"] = {"status": canary}
            return payload

        monkeypatch.setattr(
            pipeline_module,
            "build_stage_provenance",
            corrupt_stage_provenance,
        )
    else:
        original_builder = pipeline_module.build_stage_receipt

        def corrupt_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
            payload = original_builder(*args, **kwargs)
            payload["provider_identity"] = {"provider": canary}
            payload["provider_identity_sha256"] = canonical_sha256(
                payload["provider_identity"]
            )
            return payload

        monkeypatch.setattr(
            pipeline_module,
            "build_stage_receipt",
            corrupt_receipt,
        )

    with pytest.raises(ValueError):
        _run_to_release(pipeline)

    assert not writer_reached


@pytest.mark.parametrize(
    "tenants_argument",
    ["tenants", "custom/tenants", "absolute"],
)
@pytest.mark.parametrize("adopt", [False, True])
def test_pr2_manifest_repository_base_loads_native_and_adopted_generations(
    tmp_path: Path,
    tenants_argument: str,
    adopt: bool,
) -> None:
    """Every supported root emits literals consumed from its repository base."""
    repository_base = tmp_path / "repository"
    repository_base.mkdir()
    tenants_root = (
        repository_base / "custom" / "tenants"
        if tenants_argument == "absolute"
        else Path(tenants_argument)
    )
    concrete_root = (
        tenants_root
        if tenants_root.is_absolute()
        else repository_base / tenants_root
    )
    feedback, unlabeled = _write_input_pair(concrete_root)
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
        repository_base=repository_base,
    )
    state = _run_to_release(pipeline)
    if adopt:
        _downgrade_to_legacy_completed(pipeline.layout)
        state = pipeline.layout.adopt_legacy()

    manifest = json.loads(
        pipeline.layout.manifest_path.read_text(encoding="utf-8")
    )
    stage_manifest = json.loads(
        pipeline.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "dataset_manifest.json",
        ).read_text(encoding="utf-8")
    )
    assert manifest["published_datasets"] == stage_manifest["published_datasets"]
    expected_prefix = (
        "tenants" if tenants_argument == "tenants" else "custom/tenants"
    )
    for emitted in manifest["published_datasets"]["files"].values():
        assert emitted.startswith(f"{expected_prefix}/")
        assert (repository_base / emitted).is_file()
    previous_cwd = Path.cwd()
    try:
        os.chdir(repository_base)
        loaded_counts = {
            split: len(load_cases(Path(emitted)))
            for split, emitted in manifest["published_datasets"]["files"].items()
        }
    finally:
        os.chdir(previous_cwd)
    assert loaded_counts == {
        split: manifest["split_counts"][split] for split in loaded_counts
    }
    restarted = EvaluationAssetLayout(
        tenants_root,
        "tenant_a",
        "v1",
        repository_base=repository_base,
    )
    verify_released_asset(restarted, state)


def test_pr2_manifest_repository_base_rejects_outside_root_before_writes(
    tmp_path: Path,
) -> None:
    """An explicit repository base never authorizes an outside tenant root."""
    repository_base = tmp_path / "repository"
    outside_root = tmp_path / "outside" / "tenants"

    with pytest.raises(ValueError, match="repository base"):
        EvaluationAssetLayout(
            outside_root,
            "tenant_a",
            "v1",
            repository_base=repository_base,
        )

    assert not outside_root.exists()


def test_pr2_explicit_repository_base_rejects_symlinked_tenants_ancestor(
    tmp_path: Path,
) -> None:
    """A lexical in-base root cannot traverse an intermediate symlink."""
    repository_base = tmp_path / "repository"
    repository_base.mkdir()
    outside = tmp_path / "outside"
    tenants_root = outside / "tenants"
    tenants_root.mkdir(parents=True)
    sentinel = outside / "KEEP"
    sentinel.write_bytes(b"KEEP")
    try:
        (repository_base / "escape").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")

    with pytest.raises(ValueError, match="exact repository base"):
        EvaluationAssetLayout(
            repository_base / "escape" / "tenants",
            "tenant_a",
            "v1",
            repository_base=repository_base,
        )

    assert sentinel.read_bytes() == b"KEEP"
    assert not (tenants_root / "tenant_a").exists()


def test_pr2_service_repository_base_rejects_outside_root_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service defaults bind repository-relative paths to its invocation cwd."""
    repository_base = tmp_path / "repository"
    repository_base.mkdir()
    outside_root = tmp_path / "outside" / "tenants"
    monkeypatch.chdir(repository_base)

    with pytest.raises(ValueError, match="repository base"):
        EvaluationAssetRunManager(outside_root)

    assert not outside_root.exists()


def test_pr2_service_rejects_symlinked_tenants_ancestor_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service startup binds every existing component from its invocation base."""
    repository_base = tmp_path / "repository"
    repository_base.mkdir()
    outside = tmp_path / "outside"
    tenants_root = outside / "tenants"
    tenants_root.mkdir(parents=True)
    sentinel = outside / "KEEP"
    sentinel.write_bytes(b"KEEP")
    try:
        (repository_base / "escape").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    monkeypatch.chdir(repository_base)

    with pytest.raises(ValueError, match="exact repository base"):
        EvaluationAssetRunManager(Path("escape/tenants"))

    assert sentinel.read_bytes() == b"KEEP"
    assert not (tenants_root / "service").exists()
