# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for deterministic guideline applicability contracts."""

from __future__ import annotations

from typing import Any

from src.hephaestus.evaluation_assets.stage_three_contract import (
    APPLICABILITY_CONTRACT_SCHEMA_VERSION,
    EpisodeFacts,
    evaluate_applicability_contract,
    extract_episode_facts,
    normalize_applicability_contract,
)


def _contract(*, deterministic_accept: bool = True) -> dict[str, Any]:
    return {
        "schema_version": APPLICABILITY_CONTRACT_SCHEMA_VERSION,
        "requires": [
            {
                "dimension": "action",
                "any_of": ["action:exchange"],
                "on_known_absence": "not_applicable",
            },
            {
                "dimension": "state",
                "any_of": ["state:delivered"],
                "on_known_absence": "unknown",
            },
        ],
        "excludes": [
            {
                "dimension": "action",
                "any_of": ["action:reverse_cancellation"],
                "on_known_absence": "unknown",
            }
        ],
        "deterministic_accept": deterministic_accept,
    }


def test_extract_episode_facts_preserves_user_and_tool_evidence() -> None:
    """Fact extraction links matching tags to observable evidence pointers."""
    facts = extract_episode_facts(
        {
            "user_messages": [
                "Please exchange this item and tell me the price difference."
            ],
            "tool_observations": [
                {
                    "pointer": "episode.events[4]",
                    "name": "get_resource_details",
                    "outcome_status": "result_returned",
                    "result_state": {"status": "delivered"},
                }
            ],
        }
    )

    assert "action:exchange" in facts.tags
    assert "action:factual_question" in facts.tags
    assert "state:delivered" in facts.tags
    assert facts.evidence_by_tag["state:delivered"] == ("episode.events[4]",)
    assert "tool_outcome:get_resource_details:result_returned" in facts.tags


def test_extract_episode_facts_distinguishes_requests_from_acknowledgements() -> None:
    """Return instructions and payment swaps do not become item actions."""
    facts = extract_episode_facts(
        {
            "user_messages": [
                "I'll keep an eye out for the return instructions.",
                "Why can't you just swap the original payment methods?",
            ],
            "tool_observations": [],
        }
    )

    assert "request:return_items" not in facts.tags
    assert "request:partial_order_removal" not in facts.tags
    assert "action:exchange" not in facts.tags


def test_extract_episode_facts_captures_reviewed_request_scopes() -> None:
    """Narrow request tags support deterministic applicability contracts."""
    facts = extract_episode_facts(
        {
            "user_messages": [
                "Please update my default address for future orders.",
                "Change the shipping address for my pending order.",
                "Return only the desk lamp and tell me the total amount.",
                "What will my gift card balance be after the change?",
                "I received the boots and want to swap them for a larger size.",
            ],
            "tool_observations": [],
        }
    )

    assert {
        "request:update_default_address",
        "request:update_order_address",
        "request:partial_order_removal",
        "request:return_items",
        "request:exact_factual_value",
        "topic:gift_card_balance",
        "scope:pending_request",
        "scope:delivered_request",
        "action:exchange",
    } <= facts.tags


def test_extract_episode_facts_detects_lookup_recovery() -> None:
    """A failed lookup followed by success is distinct from any tool error."""
    facts = extract_episode_facts(
        {
            "user_messages": ["Please show my latest order total."],
            "tool_observations": [
                {
                    "pointer": "episode.events[1]",
                    "name": "find_user_by_email",
                    "outcome_status": "error_returned",
                },
                {
                    "pointer": "episode.events[3]",
                    "name": "find_user_by_email",
                    "outcome_status": "result_returned",
                },
            ],
        }
    )

    assert "condition:lookup_recovered" in facts.tags
    assert facts.evidence_by_tag["condition:lookup_recovered"] == (
        "episode.events[1]",
        "episode.events[3]",
    )


def test_contract_accepts_when_all_reviewed_requirements_match() -> None:
    """Reviewed contracts deterministically accept complete matching facts."""
    facts = EpisodeFacts(
        tags=frozenset({"action:exchange", "state:delivered"}),
        known_dimensions=frozenset({"action", "state"}),
        evidence_by_tag={
            "action:exchange": ("user_messages[0]",),
            "state:delivered": ("episode.events[4]",),
        },
    )

    decision = evaluate_applicability_contract(facts, _contract())

    assert decision.status == "applicable"
    assert decision.evidence_pointers == (
        "user_messages[0]",
        "episode.events[4]",
    )


def test_contract_rejects_known_action_mismatch() -> None:
    """A known incompatible action is rejected before LLM fallback."""
    facts = EpisodeFacts(
        tags=frozenset({"action:return", "state:delivered"}),
        known_dimensions=frozenset({"action", "state"}),
        evidence_by_tag={},
    )

    decision = evaluate_applicability_contract(facts, _contract())

    assert decision.status == "not_applicable"
    assert "known action facts" in decision.reason


def test_contract_defers_when_required_state_is_unknown() -> None:
    """Missing state evidence defers to the semantic fallback."""
    facts = EpisodeFacts(
        tags=frozenset({"action:exchange"}),
        known_dimensions=frozenset({"action"}),
        evidence_by_tag={"action:exchange": ("user_messages[0]",)},
    )

    decision = evaluate_applicability_contract(facts, _contract())

    assert decision.status == "unknown"
    assert "unresolved dimensions: state" in decision.reason


def test_unreviewed_contract_never_deterministically_accepts() -> None:
    """Automatically inferred contracts prune but do not accept guidelines."""
    facts = EpisodeFacts(
        tags=frozenset({"action:exchange", "state:delivered"}),
        known_dimensions=frozenset({"action", "state"}),
        evidence_by_tag={},
    )

    decision = evaluate_applicability_contract(
        facts,
        _contract(deterministic_accept=False),
    )

    assert decision.status == "unknown"


def test_contract_schema_rejects_empty_required_clauses() -> None:
    """Contracts require at least one positive applicability condition."""
    try:
        normalize_applicability_contract(
            {
                "schema_version": APPLICABILITY_CONTRACT_SCHEMA_VERSION,
                "requires": [],
            }
        )
    except ValueError as exc:
        assert "requires" in str(exc)
    else:
        raise AssertionError("empty applicability contract was accepted")
