# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from src.hephaestus.data_pipeline.config import AssetConfig

BASE = {"tenant_id": "demo", "asset_id": "v1", "feedback": "feedback.jsonl"}


class TestAssetConfig:
    def test_defaults(self) -> None:
        """A minimal config fills in every default."""
        config = AssetConfig.from_dict(BASE)

        assert config.unlabeled is None
        assert config.regression_split is False
        assert config.observe_traces is False
        assert config.redact is True
        assert config.trace.result_keys is None

    def test_asset_root(self) -> None:
        """Assets live under the tenant's evaluation_assets directory."""
        config = AssetConfig.from_dict(BASE)

        assert config.asset_root(Path("/repo")) == Path("/repo/tenants/demo/evaluation_assets/v1")

    @pytest.mark.parametrize(
        "override, message",
        [
            ({"surprise": 1}, "unknown asset config keys: surprise"),
            ({"trace": {"surprise": 1}}, "unknown trace keys: surprise"),
            ({"asset_id": "../escape"}, "asset_id must be a simple name"),
            ({"batch_size": 0}, "batch_size must be an integer >= 1"),
            ({"workers": True}, "workers must be an integer >= 1"),
            ({"regression_split": "yes"}, "regression_split must be true or false"),
            ({"min_lesson_confidence": 2}, "min_lesson_confidence must be between 0 and 1"),
            ({"trace": {"result_keys": "("}}, "trace.result_keys is not a valid regex"),
        ],
    )
    def test_rejects_invalid_values(self, override: dict, message: str) -> None:
        """Unknown keys and invalid values fail with a precise message."""
        with pytest.raises(ValueError, match=message.replace("(", r"\(")):
            AssetConfig.from_dict({**BASE, **override})

    def test_missing_required_key(self) -> None:
        """A config without feedback is incomplete."""
        with pytest.raises(ValueError, match="incomplete"):
            AssetConfig.from_dict({"tenant_id": "demo", "asset_id": "v1"})

    def test_content_settings_exclude_workers_and_paths(self) -> None:
        """Concurrency and input paths do not change an asset's identity."""
        settings = AssetConfig.from_dict({**BASE, "workers": 9}).content_settings()

        assert "workers" not in settings
        assert "feedback" not in settings
        assert settings["model"]
