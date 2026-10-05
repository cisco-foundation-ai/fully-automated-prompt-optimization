# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from src.hephaestus.evaluation_assets.trust_tiers import CURRENT_TRUST_TIERS


def test_current_trust_tier_allowlist_has_exactly_three_supported_tiers() -> None:
    assert CURRENT_TRUST_TIERS == frozenset(
        {
            "trusted_feedback",
            "inferred_from_trusted_feedback",
            "synthetic_from_trusted_rubric",
        }
    )


@pytest.mark.parametrize(
    ("trust_tier", "accepted"),
    [
        ("trusted_feedback", True),
        ("inferred_from_trusted_feedback", True),
        ("synthetic_from_trusted_rubric", True),
        ("synthetic", False),
        ("", False),
    ],
)
def test_current_trust_tiers_exclude_historical_spellings(
    trust_tier: str,
    accepted: bool,
) -> None:
    assert (trust_tier in CURRENT_TRUST_TIERS) is accepted
