# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Label scorer for the software-name categorization challenge."""

from __future__ import annotations

import re
from typing import Any, Dict

from src.hephaestus.scoring.scorer import Scorer as BaseScorer
from src.hephaestus.types import EvalCase

ALLOWED_LABELS = {
    "network_and_remote_access",
    "exposure_testing",
    "data_transfer_and_sync",
    "runtime_and_server_stack",
    "user_endpoint_clients",
    "sensitive_key_material",
    "security_posture_changes",
    "general_utility_other",
}


def _normalize_label(text: str) -> str:
    value = text.strip()
    value = re.sub(r"^```(?:text|json|markdown)?", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"```$", "", value).strip()
    value = value.strip("`'\" \t\r\n.,;:")
    value = re.sub(r"[\s-]+", "_", value)
    return value.lower()


def _extract_candidate(output_text: str) -> str:
    lines = [line.strip() for line in output_text.splitlines() if line.strip()]
    if not lines:
        return ""
    return _normalize_label(lines[-1])


class Scorer(BaseScorer):
    def validate_case(self, case: EvalCase, scoring_profile: Dict[str, Any]) -> None:
        if "category" not in case.expected:
            raise ValueError(f"Case {case.case_id} missing expected.category")
        expected = str(case.expected["category"])
        if expected not in ALLOWED_LABELS:
            raise ValueError(
                f"Case {case.case_id} has unknown expected.category: {expected}"
            )
        if set(case.context) != {"software_name"}:
            raise ValueError(
                f"Case {case.case_id} must expose only context.software_name"
            )

    def score_case(
        self,
        case: EvalCase,
        output_text: str,
        scoring_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        expected = str(case.expected["category"])
        actual = _extract_candidate(output_text)
        exact_match = 100.0 if actual == expected else 0.0
        valid_label = 100.0 if actual in ALLOWED_LABELS else 0.0
        strict_format = 100.0 if _normalize_label(output_text) == actual else 0.0

        return {
            "composite_score": exact_match,
            "score_breakdown": {
                "f1": exact_match,
                "exact_match": exact_match,
                "valid_label": valid_label,
                "strict_format": strict_format,
            },
            "diagnostics": [
                f"expected={expected}",
                f"actual={actual or '<empty>'}",
            ],
        }
