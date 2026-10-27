# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Machine-readable optimization policy for the headless optimization loop.

The policy is the code-enforced counterpart of a tenant playbook's scope
section: which levels may change, which parameters exist and their bounds,
which dataset split plays which role, and how candidates are accepted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.hephaestus.datasets.rubric_providers import DEFAULT_OPENAI_RUBRIC_MODEL

ALLOWED_LEVELS = ("prompt", "parameter")
PARAMETER_TYPES = ("int", "float", "choice", "bool")
# resolve_provider_settings drops unknown keys, so only these can take effect.
TUNABLE_PROVIDER_SETTINGS = ("model", "temperature", "top_p", "max_tokens")
# Prompt and skill wiring is owned by the prompt level, not the parameter level.
RESERVED_CHAIN_CONFIG_KEYS = ("prompt_paths", "skill_paths", "optimization_target")


@dataclass
class ParameterSpec:
    """One tunable parameter addressed by a dotted path into the eval config."""

    path: str
    type: str
    min: Optional[float] = None
    max: Optional[float] = None
    values: List[Any] = field(default_factory=list)

    def validate(self, value: Any) -> Optional[str]:
        """Return an error message when ``value`` is outside this spec, else None."""
        if self.type == "bool":
            return None if isinstance(value, bool) else f"{self.path} must be a boolean"
        if self.type == "choice":
            return None if value in self.values else f"{self.path} must be one of {self.values}"
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"{self.path} must be a number"
        if self.type == "int" and not float(value).is_integer():
            return f"{self.path} must be an integer"
        if self.min is not None and value < self.min:
            return f"{self.path} must be >= {self.min}"
        if self.max is not None and value > self.max:
            return f"{self.path} must be <= {self.max}"
        return None

    def to_payload(self) -> Dict[str, Any]:
        """Describe this spec for role payloads."""
        payload: Dict[str, Any] = {"type": self.type}
        if self.type in ("int", "float"):
            payload.update({"min": self.min, "max": self.max})
        if self.type == "choice":
            payload["values"] = list(self.values)
        return payload


@dataclass
class AcceptancePolicy:
    """Thresholds a candidate must clear to replace the current best."""

    min_train_delta: float = 0.0
    min_val_delta: float = 1.0
    val_repeats: int = 1
    # Accept a candidate that does not lose on val (gain below min_val_delta)
    # but strictly improves train; small val splits tie often.
    train_tiebreak: bool = True


@dataclass
class BudgetPolicy:
    """Limits on how long the loop runs."""

    max_iterations: int = 10
    plateau_patience: int = 3
    target_score: Optional[float] = None


@dataclass
class OptimizationPolicy:
    """Complete configuration for one headless optimization run."""

    base_config: str
    train_dataset: str
    val_dataset: Optional[str] = None
    test_dataset: Optional[str] = None
    levels: List[str] = field(default_factory=lambda: ["prompt"])
    prompt_modules: List[str] = field(default_factory=list)
    parameter_space: List[ParameterSpec] = field(default_factory=list)
    acceptance: AcceptancePolicy = field(default_factory=AcceptancePolicy)
    budget: BudgetPolicy = field(default_factory=BudgetPolicy)
    role_model: str = DEFAULT_OPENAI_RUBRIC_MODEL
    llm_review: bool = True
    guidance_paths: List[str] = field(default_factory=list)
    failure_threshold: float = 100.0
    max_failures_shown: int = 20
    # Show every training case (inputs, expected, metadata, pass/fail) to the
    # analyst and proposer when the train split has at most this many cases.
    train_overview_limit: int = 200

    def parameter(self, path: str) -> Optional[ParameterSpec]:
        """Return the spec for ``path``, or None when it is not tunable."""
        for spec in self.parameter_space:
            if spec.path == path:
                return spec
        return None


def load_policy(path: Path) -> OptimizationPolicy:
    """Load and validate an optimization policy JSON file.

    Args:
        path: Policy file path.

    Returns:
        The validated policy.

    Raises:
        ValueError: If the policy is malformed or grants a disallowed scope.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("optimization policy must be a JSON object")
    datasets = _object(raw.get("datasets"), "datasets")
    acceptance = _object(raw.get("acceptance", {}), "acceptance")
    budget = _object(raw.get("budget", {}), "budget")
    roles = _object(raw.get("roles", {}), "roles")
    parameter_space = [
        _parameter_spec(param_path, _object(spec, f"parameter_space.{param_path}"))
        for param_path, spec in _object(raw.get("parameter_space", {}), "parameter_space").items()
    ]
    policy = OptimizationPolicy(
        base_config=_required_str(raw, "base_config"),
        train_dataset=_required_str(datasets, "train"),
        val_dataset=datasets.get("val"),
        test_dataset=datasets.get("test"),
        levels=list(raw.get("levels", ["prompt"])),
        prompt_modules=list(raw.get("prompt_modules", [])),
        parameter_space=parameter_space,
        acceptance=AcceptancePolicy(
            min_train_delta=float(acceptance.get("min_train_delta", 0.0)),
            min_val_delta=float(acceptance.get("min_val_delta", 1.0)),
            val_repeats=int(acceptance.get("val_repeats", 1)),
            train_tiebreak=bool(acceptance.get("train_tiebreak", True)),
        ),
        budget=BudgetPolicy(
            max_iterations=int(budget.get("max_iterations", 10)),
            plateau_patience=int(budget.get("plateau_patience", 3)),
            target_score=(
                float(budget["target_score"]) if budget.get("target_score") is not None else None
            ),
        ),
        role_model=str(roles.get("model", DEFAULT_OPENAI_RUBRIC_MODEL)),
        llm_review=bool(roles.get("llm_review", True)),
        guidance_paths=list(raw.get("guidance_paths", [])),
        failure_threshold=float(raw.get("failure_threshold", 100.0)),
        max_failures_shown=int(raw.get("max_failures_shown", 20)),
        train_overview_limit=int(raw.get("train_overview_limit", 200)),
    )
    validate_policy(policy)
    return policy


def validate_policy(policy: OptimizationPolicy) -> None:
    """Reject policies that are inconsistent or reach outside the allowed levels."""
    if not policy.levels:
        raise ValueError("levels must list at least one optimization level")
    unknown = sorted(set(policy.levels) - set(ALLOWED_LEVELS))
    if unknown:
        raise ValueError(f"unsupported optimization levels {unknown}; allowed: {list(ALLOWED_LEVELS)}")
    if len(set(policy.levels)) != len(policy.levels):
        raise ValueError("levels must not contain duplicates")
    if "parameter" in policy.levels and not policy.parameter_space:
        raise ValueError("the parameter level requires a non-empty parameter_space")
    for spec in policy.parameter_space:
        _validate_parameter_path(spec.path)
    if policy.acceptance.val_repeats < 1:
        raise ValueError("acceptance.val_repeats must be >= 1")
    if policy.budget.max_iterations < 0:
        raise ValueError("budget.max_iterations must be >= 0")
    if policy.budget.plateau_patience < 1:
        raise ValueError("budget.plateau_patience must be >= 1")
    if policy.max_failures_shown < 1:
        raise ValueError("max_failures_shown must be >= 1")
    if policy.train_overview_limit < 0:
        raise ValueError("train_overview_limit must be >= 0")
    split_paths = [p for p in (policy.train_dataset, policy.val_dataset, policy.test_dataset) if p]
    if len(set(split_paths)) != len(split_paths):
        raise ValueError("train, val, and test datasets must be distinct files")


def _validate_parameter_path(path: str) -> None:
    head, _, key = path.partition(".")
    if head == "provider_settings":
        if key not in TUNABLE_PROVIDER_SETTINGS:
            raise ValueError(
                f"parameter {path!r} is not tunable; provider_settings keys allowed: "
                f"{list(TUNABLE_PROVIDER_SETTINGS)}"
            )
        return
    if path.startswith("chain.config.") and path.count(".") == 2:
        if key.partition(".")[2] in RESERVED_CHAIN_CONFIG_KEYS:
            raise ValueError(f"parameter {path!r} is owned by the prompt level, not the parameter level")
        return
    raise ValueError(
        f"parameter {path!r} must be 'provider_settings.<key>' or 'chain.config.<key>'"
    )


def _parameter_spec(path: str, raw: Dict[str, Any]) -> ParameterSpec:
    spec_type = raw.get("type")
    if spec_type not in PARAMETER_TYPES:
        raise ValueError(f"parameter_space.{path}.type must be one of {list(PARAMETER_TYPES)}")
    if spec_type == "choice" and not raw.get("values"):
        raise ValueError(f"parameter_space.{path} of type 'choice' requires non-empty values")
    if spec_type in ("int", "float") and (raw.get("min") is None or raw.get("max") is None):
        raise ValueError(f"parameter_space.{path} of type {spec_type!r} requires min and max")
    return ParameterSpec(
        path=path,
        type=spec_type,
        min=raw.get("min"),
        max=raw.get("max"),
        values=list(raw.get("values", [])),
    )


def _object(value: Any, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _required_str(raw: Dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"policy is missing required string {key!r}")
    return value
