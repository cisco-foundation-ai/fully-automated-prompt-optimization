# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from src.hephaestus.optimization.stats import paired_improvement


class TestPairedImprovement:
    def test_no_difference_has_no_evidence(self) -> None:
        """Identical scores give zero gain and zero probability."""
        scores = {"a": 100.0, "b": 0.0}

        assert paired_improvement(scores, dict(scores)) == (0.0, 0.0)

    def test_uniform_gain_is_certain(self) -> None:
        """When every case improves, every resample improves."""
        gain, probability = paired_improvement({"a": 100.0, "b": 100.0}, {"a": 0.0, "b": 0.0})

        assert (gain, probability) == (100.0, 1.0)

    def test_one_improved_case_out_of_three(self) -> None:
        """One improved case in three gives the expected bootstrap probability."""
        _, probability = paired_improvement(
            {"a": 100.0, "b": 0.0, "c": 0.0}, {"a": 0.0, "b": 0.0, "c": 0.0}, resamples=20000
        )

        # The mean is positive exactly when the improved case is drawn at least once.
        assert probability == pytest.approx(1 - (2 / 3) ** 3, abs=0.01)

    def test_one_improved_case_stays_below_high_confidence(self) -> None:
        """A single improved case among many cannot reach 0.8, whatever the split size."""
        incumbent = {f"case-{i}": 0.0 for i in range(300)}
        candidate = dict(incumbent, **{"case-0": 100.0})

        _, probability = paired_improvement(candidate, incumbent)

        assert probability == pytest.approx(1 - (299 / 300) ** 300, abs=0.03)
        assert probability < 0.8

    def test_offsetting_changes_are_uncertain(self) -> None:
        """Equal numbers of improved and broken cases give a probability below one half."""
        candidate = {f"case-{i}": 100.0 if i < 10 else 0.0 for i in range(20)}
        incumbent = {f"case-{i}": 0.0 if i < 10 else 100.0 for i in range(20)}

        gain, probability = paired_improvement(candidate, incumbent)

        assert gain == 0.0
        # Positive and negative means are equally likely; exact ties (C(20,10)/2^20) count for neither.
        assert probability == pytest.approx((1 - 184756 / 2**20) / 2, abs=0.04)

    def test_only_shared_cases_count(self) -> None:
        """Cases missing from either side are ignored."""
        gain, _ = paired_improvement({"a": 100.0, "extra": 0.0}, {"a": 50.0})

        assert gain == 50.0

    def test_is_deterministic_for_a_seed(self) -> None:
        """The same seed gives the same probability."""
        candidate = {f"case-{i}": float(i % 3) * 50 for i in range(30)}
        incumbent = {f"case-{i}": float(i % 2) * 50 for i in range(30)}

        assert paired_improvement(candidate, incumbent, seed="x") == paired_improvement(
            candidate, incumbent, seed="x"
        )
