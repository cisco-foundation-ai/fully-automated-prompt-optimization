# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Build settings for one evaluation asset."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from src.hephaestus.datasets.rubric_providers import DEFAULT_OPENAI_RUBRIC_MODEL

_SIMPLE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass
class TraceSettings:
    """How tool results are compacted before they reach the model.

    Attributes:
        result_keys: Optional regex. When set, a tool result keeps only the
            keys that match it, plus nested objects that contain a match.
        drop_keys: Result keys removed entirely, such as bulky listings.
    """

    result_keys: Optional[str] = None
    drop_keys: List[str] = field(default_factory=list)


@dataclass
class AssetConfig:
    """Settings for one evaluation-asset build.

    Every field except ``workers`` determines the asset's content, so a build
    cannot resume with different values.
    """

    tenant_id: str
    asset_id: str
    feedback: str
    unlabeled: Optional[str] = None
    model: str = DEFAULT_OPENAI_RUBRIC_MODEL
    split_seed: int = 0
    regression_split: bool = False
    observe_traces: bool = False
    redact: bool = True
    batch_size: int = 5
    min_lesson_confidence: float = 0.3
    min_guideline_support: int = 1
    workers: int = 4
    trace: TraceSettings = field(default_factory=TraceSettings)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> AssetConfig:
        """Parse and validate a config object.

        Raises:
            ValueError: If a key is unknown or a value is invalid.
        """
        if not isinstance(raw, Mapping):
            raise ValueError("asset config must be a JSON object")
        values = dict(raw)
        trace = values.pop("trace", None) or {}
        if not isinstance(trace, Mapping):
            raise ValueError("trace must be an object")
        _reject_unknown(values, {f.name for f in fields(cls)} - {"trace"}, "asset config")
        _reject_unknown(trace, {f.name for f in fields(TraceSettings)}, "trace")
        try:
            config = cls(**values, trace=TraceSettings(**trace))
        except TypeError as exc:
            raise ValueError(f"asset config is incomplete: {exc}") from exc
        config.validate()
        return config

    def validate(self) -> None:
        """Raise ``ValueError`` if any setting is invalid."""
        for name in ("tenant_id", "asset_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SIMPLE_NAME.fullmatch(value):
                raise ValueError(f"{name} must be a simple name (letters, digits, '.', '_', '-')")
        if not isinstance(self.feedback, str) or not self.feedback:
            raise ValueError("feedback must be a path")
        if self.unlabeled is not None and (not isinstance(self.unlabeled, str) or not self.unlabeled):
            raise ValueError("unlabeled must be a path or null")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError("model must be a non-empty string")
        for name in ("regression_split", "observe_traces", "redact"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be true or false")
        for name, minimum in (
            ("split_seed", 0),
            ("batch_size", 1),
            ("min_guideline_support", 1),
            ("workers", 1),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        confidence = self.min_lesson_confidence
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            raise ValueError("min_lesson_confidence must be between 0 and 1")
        if self.trace.result_keys is not None:
            if not isinstance(self.trace.result_keys, str):
                raise ValueError("trace.result_keys must be a regex string or null")
            try:
                re.compile(self.trace.result_keys)
            except re.error as exc:
                raise ValueError(f"trace.result_keys is not a valid regex: {exc}") from exc
        if not isinstance(self.trace.drop_keys, list) or not all(
            isinstance(key, str) for key in self.trace.drop_keys
        ):
            raise ValueError("trace.drop_keys must be a list of strings")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def content_settings(self) -> Dict[str, Any]:
        """Return the settings that determine the asset's content."""
        settings = self.to_dict()
        for name in ("workers", "feedback", "unlabeled"):
            settings.pop(name)
        return settings

    def asset_root(self, repository_root: Path) -> Path:
        return repository_root / "tenants" / self.tenant_id / "evaluation_assets" / self.asset_id


def _reject_unknown(values: Mapping[str, Any], known: set[str], scope: str) -> None:
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"unknown {scope} keys: {', '.join(unknown)}")
