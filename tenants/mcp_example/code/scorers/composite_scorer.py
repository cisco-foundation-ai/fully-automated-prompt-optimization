# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Composite scorer for mcp_example tenant.

Combines the trajectory evaluator (deterministic, argument/order-aware) with
the LLM-as-judge answer evaluator into a single weighted score. This is the
LangSmith-style pattern of running several evaluators and aggregating their
feedback.

Weights are configurable via ``scoring_profile.composite_weights``:

    "composite_weights": {
        "answer_correct": 0.60,   # from the LLM judge
        "trajectory":     0.40    # from the trajectory scorer
    }

Weights are normalized, so they need not sum to 1.0. The full sub-metric
breakdowns from both child scorers are flattened into ``score_breakdown`` so
nothing is lost.
"""

from typing import Any, Dict, List, Optional

from src.hephaestus.scoring.scorer import Scorer as BaseScorer

from .llm_judge_scorer import LLMJudgeScorer
from .trajectory_scorer import TrajectoryScorer

DEFAULT_WEIGHTS = {
    "answer_correct": 0.60,
    "trajectory": 0.40,
}


class CompositeScorer(BaseScorer):
    """Aggregate LLM-judge answer correctness + trajectory into one score."""

    def __init__(self):
        self._trajectory = TrajectoryScorer()
        self._judge = LLMJudgeScorer()

    def validate_case(self, case, scoring_profile):
        self._trajectory.validate_case(case, scoring_profile)
        self._judge.validate_case(case, scoring_profile)

    def score_case(self, case, output_text, scoring_profile):
        return self.score_pipeline_case(
            case, {}, scoring_profile, output_text=output_text, tool_call_history=None
        )

    def score_pipeline_case(
        self,
        case,
        step_outputs: Dict[str, str],
        scoring_profile: Dict[str, Any],
        output_text: Optional[str] = None,
        tool_call_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        output_text = output_text or ""

        # 1. Trajectory evaluator (deterministic).
        traj = self._trajectory.score_pipeline_case(
            case, step_outputs, scoring_profile,
            output_text=output_text, tool_call_history=tool_call_history,
        )
        trajectory_score = traj["composite_score"]

        # 2. LLM-as-judge answer correctness.
        judged = self._judge.score_pipeline_case(
            case, step_outputs, scoring_profile,
            output_text=output_text, tool_call_history=tool_call_history,
        )
        answer_correct = judged["composite_score"]

        # Weighted, normalized composite.
        weights = self._resolve_weights(scoring_profile)
        components = {
            "answer_correct": answer_correct,
            "trajectory": trajectory_score,
        }
        total_weight = sum(weights.values()) or 1.0
        composite = sum(
            weights[name] * components[name] for name in components
        ) / total_weight

        # Flatten child breakdowns with prefixes so every sub-metric survives.
        breakdown: Dict[str, float] = {
            "answer_correct": answer_correct,
            "trajectory": trajectory_score,
        }
        for key, val in traj["score_breakdown"].items():
            breakdown[f"traj_{key}"] = val
        for key, val in judged["score_breakdown"].items():
            breakdown[f"judge_{key}"] = val

        return {
            "composite_score": composite,
            "score_breakdown": breakdown,
        }

    @staticmethod
    def _resolve_weights(scoring_profile: Dict[str, Any]) -> Dict[str, float]:
        configured = scoring_profile.get("composite_weights") or {}
        weights = dict(DEFAULT_WEIGHTS)
        for key in weights:
            if key in configured:
                weights[key] = float(configured[key])
        return weights
