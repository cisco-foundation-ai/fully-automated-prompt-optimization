# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Compatibility re-export; the contract lives in ``data_pipeline.contract``."""

from __future__ import annotations

from src.hephaestus.data_pipeline.contract import (  # noqa: F401 - re-exported
    COMMON_REQUIRED_FIELDS,
    CORRECTNESS_SIGNAL_KINDS,
    CORRECTNESS_SIGNAL_OPTIONAL_FIELDS,
    CORRECTNESS_SIGNAL_REQUIRED_FIELDS,
    EPISODE_EVENT_TYPES,
    FEEDBACK_POLARITIES,
    SCHEMA_VERSION,
    canonical_user_intent_text,
    effective_route,
    episode_tool_names,
    episode_user_messages,
    input_contract_document,
    record_user_messages,
    redact_correctness_signals,
    validate_input_records,
)
