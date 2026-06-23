# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAPO web UI HTTP routing helpers."""

from __future__ import annotations

from src.hephaestus.webui.server import _overview_tenant_ids, _parse_query


def test_overview_tenant_filter_distinguishes_missing_from_empty() -> None:
    assert _overview_tenant_ids(_parse_query("")) is None
    assert _overview_tenant_ids(_parse_query("tenants=")) == []


def test_overview_tenant_filter_parses_selected_tenants() -> None:
    assert _overview_tenant_ids(_parse_query("tenants=alpha,beta")) == ["alpha", "beta"]

