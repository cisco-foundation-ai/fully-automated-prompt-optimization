# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests that every published Tau recipe config follows the FAPO contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.hephaestus.runs.eval_runner import load_eval_config


TENANT_ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [TENANT_ROOT / "configs" / name for name in ("train.json", "eval.json", "test.json")]
CONFIGS += sorted((TENANT_ROOT / "recipe/configs").glob("*.json"))


@pytest.mark.parametrize("path", CONFIGS, ids=lambda path: path.name)
def test_recipe_config_loads_and_is_tenant_scoped(path: Path) -> None:
    config = load_eval_config(path)

    assert config.tenant_id == "tau3_retail"
    assert config.provider == "openai"
    assert config.dataset_path.startswith(
        "tenants/tau3_retail/evaluation_assets/fafo-v3-luna-v1/"
    )
    assert config.chain.path == "tenants/tau3_retail/chains/tau_episode.py"
    assert config.chain.config["tau_runtime_path"] == "../tau2-bench"
    prompt_path = config.chain.config["prompt_paths"]["agent"]
    assert (TENANT_ROOT.parents[1] / prompt_path).is_file()
    assert config.output_dir.startswith("tenants/tau3_retail/evals/")


def test_recipe_exposes_all_training_views() -> None:
    names = {path.name for path in TENANT_ROOT.glob("recipe/configs/*.json")}
    assert {"trusted-train.json", "inferred-train.json", "mixed-train.json"} <= names
