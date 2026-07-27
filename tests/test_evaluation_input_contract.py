# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the vendor-neutral evaluation input contract."""

from pathlib import Path

import pytest

from src.hephaestus.evaluation_assets.input_contract import (
    SCHEMA_VERSION,
    input_contract_document,
    validate_input_records,
)


def _record(record_id: str = "record-1") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "group_id": "conversation-1",
        "task_type": "general_assistant",
        "user_input": "Process the supplied input.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }


def test_canonical_labeled_and_unlabeled_records_validate() -> None:
    labeled = {
        **_record(),
        "assistant_output": "The input was processed.",
        "feedback": {
            "polarity": "positive",
            "rationale": "The response satisfied the stated requirement.",
        },
    }

    validate_input_records(
        [labeled],
        labeled=True,
        path=Path("labeled.jsonl"),
    )
    validate_input_records(
        [_record("record-2")],
        labeled=False,
        path=Path("unlabeled.jsonl"),
    )


def test_contract_rejects_vendor_shaped_or_ambiguous_records() -> None:
    with pytest.raises(ValueError, match="missing required field 'schema_version'"):
        validate_input_records(
            [{"id": "run-1", "inputs": {}, "outputs": {}}],
            labeled=False,
            path=Path("unlabeled.jsonl"),
        )

    invalid_feedback = {
        **_record(),
        "assistant_output": "A response",
        "feedback": {"polarity": "thumbs_down", "rationale": "Incorrect"},
    }
    with pytest.raises(ValueError, match="feedback.polarity"):
        validate_input_records(
            [invalid_feedback],
            labeled=True,
            path=Path("labeled.jsonl"),
        )


def test_contract_document_is_versioned_and_explicit() -> None:
    contract = input_contract_document()

    assert contract["schema_version"] == SCHEMA_VERSION
    assert "group_id" in contract["common_required_fields"]
    assert contract["labeled_required_fields"] == [
        "assistant_output",
        "feedback",
    ]
