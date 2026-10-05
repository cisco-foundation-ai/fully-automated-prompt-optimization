# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Current trust-tier identities for evaluation-asset case writers."""

from __future__ import annotations

TRUSTED_FEEDBACK = "trusted_feedback"
INFERRED_FROM_TRUSTED_FEEDBACK = "inferred_from_trusted_feedback"
SYNTHETIC_FROM_TRUSTED_RUBRIC = "synthetic_from_trusted_rubric"

CURRENT_TRUST_TIERS = frozenset(
    {
        TRUSTED_FEEDBACK,
        INFERRED_FROM_TRUSTED_FEEDBACK,
        SYNTHETIC_FROM_TRUSTED_RUBRIC,
    }
)
