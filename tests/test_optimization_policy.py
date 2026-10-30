# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from src.hephaestus.optimization.policy import ParameterSpec, load_policy


def _write_policy(tmp_path: Path, **overrides: Any) -> Path:
    policy: Dict[str, Any] = {
        "base_config": "base.json",
        "datasets": {"train": "train.jsonl", "val": "val.jsonl"},
    }
    policy.update(overrides)
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    return path


class TestLoadPolicy:
    def test_defaults(self, tmp_path: Path) -> None:
        """A minimal policy gets prompt-only scope and conservative acceptance defaults."""
        policy = load_policy(_write_policy(tmp_path))

        assert policy.levels == ["prompt"]
        assert policy.val_dataset == "val.jsonl"
        assert policy.test_dataset is None
        assert (policy.acceptance.min_val_delta, policy.acceptance.confidence) == (0.0, 0.8)
        assert (policy.search.candidates, policy.search.parent_selection, policy.search.merge) == (
            3,
            "pareto",
            True,
        )
        assert (policy.selection.finalists, policy.selection.repeats) == (3, 1)
        assert policy.budget.max_iterations == 10
        assert policy.llm_review is True
        assert policy.acceptance.train_tiebreak is True
        assert (policy.max_failures_shown, policy.train_overview_limit) == (20, 200)

    def test_full_policy(self, tmp_path: Path) -> None:
        """Every section is parsed into its dataclass."""
        policy = load_policy(
            _write_policy(
                tmp_path,
                levels=["prompt", "parameter"],
                prompt_modules=["answer"],
                parameter_space={
                    "provider_settings.temperature": {"type": "float", "min": 0.0, "max": 1.0},
                    "chain.config.retrieval_k": {"type": "int", "min": 3, "max": 20},
                    "chain.config.rerank": {"type": "bool"},
                },
                acceptance={
                    "min_train_delta": -1.0,
                    "min_val_delta": 3.0,
                    "val_repeats": 2,
                    "train_tiebreak": False,
                },
                train_overview_limit=0,
                budget={"max_iterations": 4, "plateau_patience": 2, "target_score": 80},
                roles={"model": "role-model", "llm_review": False},
            )
        )

        expected = ParameterSpec("chain.config.retrieval_k", "int", 3, 20)
        assert policy.parameter("chain.config.retrieval_k") == expected
        assert policy.parameter("chain.config.missing") is None
        assert policy.acceptance.val_repeats == 2
        assert (policy.acceptance.train_tiebreak, policy.train_overview_limit) == (False, 0)
        assert policy.budget.target_score == 80.0
        assert (policy.role_model, policy.llm_review) == ("role-model", False)

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"levels": ["structural"]}, "unsupported optimization levels"),
            ({"levels": []}, "at least one"),
            ({"levels": ["parameter"]}, "requires a non-empty parameter_space"),
            (
                {"parameter_space": {"provider_settings.api_key": {"type": "choice", "values": ["x"]}}},
                "is not tunable",
            ),
            (
                {"parameter_space": {"chain.config.prompt_paths": {"type": "choice", "values": [{}]}}},
                "owned by the prompt level",
            ),
            ({"parameter_space": {"chain.path": {"type": "bool"}}}, "must be 'provider_settings"),
            ({"parameter_space": {"chain.config.k": {"type": "int"}}}, "requires min and max"),
            ({"parameter_space": {"chain.config.k": {"type": "choice"}}}, "requires non-empty values"),
            ({"parameter_space": {"chain.config.k": {"type": "text"}}}, "type must be one of"),
            ({"datasets": {"train": "a.jsonl", "val": "a.jsonl"}}, "must be distinct"),
            ({"datasets": {"val": "a.jsonl"}}, "missing required string 'train'"),
            ({"acceptance": {"val_repeats": 0}}, "val_repeats"),
            ({"acceptance": {"confidence": 1.5}}, "confidence must be between 0 and 1"),
            ({"search": {"candidates": 0}}, "candidates must be between 1 and 26"),
            ({"search": {"parent_selection": "random"}}, "parent_selection must be one of"),
            ({"selection": {"finalists": 0}}, "finalists must be >= 1"),
            ({"selection": {"repeats": 0}}, "selection.repeats must be >= 1"),
            ({"budget": {"plateau_patience": 0}}, "plateau_patience"),
            ({"train_overview_limit": -1}, "train_overview_limit"),
        ],
    )
    def test_rejects_invalid_policy(self, tmp_path: Path, overrides: Dict[str, Any], message: str) -> None:
        """Invalid or out-of-scope policies fail at load time."""
        with pytest.raises(ValueError, match=message):
            load_policy(_write_policy(tmp_path, **overrides))


class TestParameterSpec:
    @pytest.mark.parametrize(
        ("spec", "value", "error"),
        [
            (ParameterSpec("p", "int", 1, 5), 3, None),
            (ParameterSpec("p", "int", 1, 5), 3.0, None),
            (ParameterSpec("p", "int", 1, 5), 2.5, "must be an integer"),
            (ParameterSpec("p", "int", 1, 5), 0, "must be >= 1"),
            (ParameterSpec("p", "float", 0.0, 1.0), 1.5, "must be <= 1.0"),
            (ParameterSpec("p", "float", 0.0, 1.0), True, "must be a number"),
            (ParameterSpec("p", "float", 0.0, 1.0), "0.5", "must be a number"),
            (ParameterSpec("p", "bool"), False, None),
            (ParameterSpec("p", "bool"), 0, "must be a boolean"),
            (ParameterSpec("p", "choice", values=["a", "b"]), "b", None),
            (ParameterSpec("p", "choice", values=["a", "b"]), "c", "must be one of"),
        ],
    )
    def test_validate(self, spec: ParameterSpec, value: Any, error: str | None) -> None:
        """Values are checked against type, bounds, and choices."""
        result = spec.validate(value)
        if error is None:
            assert result is None
        else:
            assert error in result
