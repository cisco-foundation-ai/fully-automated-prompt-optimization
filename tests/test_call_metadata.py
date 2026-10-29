# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.hephaestus.providers.call_metadata import provider_response_metadata, sanitize_call_metadata


def _response(**overrides: object) -> SimpleNamespace:
    fields = {
        "id": "resp-1",
        "_request_id": "req-1",
        "model": "model-x",
        "system_fingerprint": "fp-1",
        "usage": SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


class TestProviderResponseMetadata:
    def test_projects_identity_and_usage(self) -> None:
        """A response's IDs, model, and token usage are projected into one row."""
        row = provider_response_metadata(
            _response(), transport_ordinal=2, retry_count=1, output_tokens_not_applicable=False
        )

        assert row == {
            "transport_ordinal": 2,
            "response_id": "resp-1",
            "request_id": "req-1",
            "model": "model-x",
            "system_fingerprint": "fp-1",
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            "retry_count": 1,
        }

    def test_secret_like_values_are_replaced(self) -> None:
        """Values that look like credentials never reach the metadata row."""
        row = provider_response_metadata(
            _response(model="sk-secretvalue"), transport_ordinal=1, retry_count=0,
            output_tokens_not_applicable=False,
        )

        assert row["model"] == {"status": "unavailable", "reason": "metadata_failed_validation"}

    def test_missing_output_tokens_can_be_not_applicable(self) -> None:
        """Embedding responses without output tokens record a not-applicable marker."""
        usage = SimpleNamespace(prompt_tokens=4, total_tokens=4)
        row = provider_response_metadata(
            _response(usage=usage), transport_ordinal=1, retry_count=0, output_tokens_not_applicable=True
        )

        assert row["usage"]["output_tokens"] == {
            "status": "not_applicable",
            "reason": "provider_does_not_expose_field",
        }


class TestSanitizeCallMetadata:
    def test_rejects_non_contiguous_ordinals(self) -> None:
        """Transport ordinals must start at 1 and be contiguous."""
        with pytest.raises(ValueError, match="contiguous"):
            sanitize_call_metadata([{"transport_ordinal": 2}])

    def test_drops_unknown_fields(self) -> None:
        """Unknown fields are discarded and missing ones become markers."""
        [row] = sanitize_call_metadata([{"transport_ordinal": 1, "secret": "x"}])

        assert "secret" not in row
        assert row["model"] == {"status": "unavailable", "reason": "provider_does_not_expose_field"}
