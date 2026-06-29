# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests that skill_example eval configs load and wire up skills correctly."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.hephaestus.runs.eval_runner import load_eval_config

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"

COMPOSITE_CONFIGS = ["eval.json"]


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_uses_composite_scorer(config_name: str) -> None:
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    assert cfg.tenant_id == "skill_example"
    scorer = cfg.scoring_profile["scorer"]
    assert scorer["class_name"] == "CompositeScorer"
    assert scorer["module_path"].endswith("composite_scorer.py")


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_has_judge_block(config_name: str) -> None:
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    judge = cfg.scoring_profile.get("judge")
    assert judge is not None
    assert judge["provider"] == "openai"
    assert judge["provider_settings"]["model"] == "gpt-5.5"
    assert "fallback_score" in judge


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_weights_are_trajectory_heavy(config_name: str) -> None:
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    weights = cfg.scoring_profile.get("composite_weights")
    assert weights is not None
    assert set(weights) == {"answer_correct", "trajectory"}
    assert weights["trajectory"] == pytest.approx(0.6)
    assert weights["answer_correct"] == pytest.approx(0.4)


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_declares_skills(config_name: str) -> None:
    """skill_example is the agentic-skills demo: skill_paths + optimization_target."""
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    chain_config = cfg.chain.config
    skill_paths = chain_config.get("skill_paths")
    assert skill_paths, "skill_example must declare skill_paths"
    assert chain_config.get("optimization_target") == "both"
    # Every declared skill file must exist on disk.
    for path in skill_paths:
        assert Path(path).exists(), f"missing skill file: {path}"


@pytest.mark.parametrize("config_name", COMPOSITE_CONFIGS)
def test_config_requires_agentic_chain(config_name: str) -> None:
    """skill optimization requires an agentic (MCP) chain — config must satisfy it."""
    cfg = load_eval_config(CONFIGS_DIR / config_name)
    assert cfg.mcp and cfg.mcp.servers
