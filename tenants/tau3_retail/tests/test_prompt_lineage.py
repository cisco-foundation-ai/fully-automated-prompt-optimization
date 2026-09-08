# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Integrity checks for exact V3 prompt lineages."""

from __future__ import annotations

import hashlib
from pathlib import Path


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts/v3"


def _digest(relative: str) -> str:
    return hashlib.sha256((PROMPT_ROOT / relative).read_bytes()).hexdigest()


def test_all_recorded_prompt_variants_are_present() -> None:
    assert len(list((PROMPT_ROOT / "trusted").glob("variant-t*.txt"))) == 11
    assert len(list((PROMPT_ROOT / "mixed").glob("m*.txt"))) == 8
    assert len(list((PROMPT_ROOT / "staged/inferred").glob("s*.txt"))) == 17
    assert len(list((PROMPT_ROOT / "staged/trusted").glob("t*.txt"))) == 5


def test_winner_hashes_match_the_recorded_experiment() -> None:
    assert _digest("trusted/variant-t008.txt") == (
        "7dfa48cf9c8857b02bb9fb3647b1d6d1d5fe86e1df7cbfe65a0b17ede104dafd"
    )
    assert _digest("mixed/m004.txt") == (
        "492d414fc5b99a802cffb42deecb7de60bdc154abfd89a0707cecb2ceb293ca8"
    )
    assert _digest("staged/trusted/t001.txt") == (
        "1f84c4605f86f107942d1432613ce31a3f6208f74de99952341ddb3737aa6447"
    )
