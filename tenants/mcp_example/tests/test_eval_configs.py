# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests that mcp_example eval configs load via load_eval_config."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.hephaestus.runs.eval_runner import load_eval_config

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"

COMPOSITE_CONFIGS = ["eval.json"]


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_uses_composite_scorer(config_name: str) -> None:
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    assert cfg.tenant_id == "mcp_example"
    scorer = cfg.scoring_profile["scorer"]
    assert scorer["class_name"] == "CompositeScorer"
    assert scorer["module_path"].endswith("composite_scorer.py")


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_has_judge_block(config_name: str) -> None:
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    judge = cfg.scoring_profile.get("judge")
    assert judge is not None
    assert judge["provider"] == "openai"
    assert "fallback_score" in judge


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_weights_present(config_name: str) -> None:
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    weights = cfg.scoring_profile.get("composite_weights")
    assert weights is not None
    assert set(weights) == {"answer_correct", "trajectory"}
