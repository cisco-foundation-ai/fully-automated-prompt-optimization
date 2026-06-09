# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.hephaestus.types import EvalCase


class Scorer(ABC):
    @abstractmethod
    def validate_case(self, case: EvalCase, scoring_profile: Dict[str, Any]) -> None:
        """Validate a case before scoring."""

    @abstractmethod
    def score_case(self, case: EvalCase, output_text: str, scoring_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Score a model response for a case."""

    def score_pipeline_case(
        self,
        case: EvalCase,
        step_outputs: Dict[str, str],
        scoring_profile: Dict[str, Any],
        output_text: Optional[str] = None,
        tool_call_history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Score a chain result with access to intermediate step outputs and tool calls.

        Default: score output_text (if provided) via score_case(), falling back
        to the last value in step_outputs for backwards compatibility.
        Override in chain-aware scorers that need intermediate outputs or tool history.

        Args:
            case: The evaluation case
            step_outputs: Outputs from each chain step
            scoring_profile: Scoring configuration
            output_text: Final output text (optional)
            tool_call_history: List of tool calls made (optional, for agentic chains)
        """
        if output_text is None:
            if not step_outputs:
                raise ValueError("score_pipeline_case called with empty step_outputs and no output_text")
            output_text = list(step_outputs.values())[-1]
        return self.score_case(case, output_text, scoring_profile)
