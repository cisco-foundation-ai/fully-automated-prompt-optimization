# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Paired statistics for comparing two candidates on the same cases."""

from __future__ import annotations

import random
from typing import Mapping, Tuple, Union

BOOTSTRAP_RESAMPLES = 2000


def paired_improvement(
    candidate: Mapping[str, float],
    incumbent: Mapping[str, float],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: Union[int, str] = 0,
) -> Tuple[float, float]:
    """Return the mean per-case gain and the probability that it is positive.

    Both mappings hold per-case scores keyed by case ID; only shared cases
    count. The probability is a paired bootstrap over cases: the share of
    resamples whose mean gain is strictly above zero. Resamples that tie at
    zero do not count, so one changed case cannot clear a high threshold on
    its own. Each case's gain includes the sampling noise of both runs, and
    repeats (``val_repeats``) average it down.

    Returns:
        ``(mean_gain, probability)``; ``(0.0, 0.0)`` when no case differs.
    """
    case_ids = sorted(set(candidate) & set(incumbent))
    gains = [candidate[case_id] - incumbent[case_id] for case_id in case_ids]
    if not any(gains):
        return 0.0, 0.0
    mean_gain = sum(gains) / len(gains)
    rng = random.Random(seed)
    above = sum(1 for _ in range(resamples) if sum(rng.choices(gains, k=len(gains))) > 0)
    return mean_gain, above / resamples
