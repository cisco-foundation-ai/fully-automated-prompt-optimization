# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ChainState(TypedDict, total=False):
    """Base state protocol for Hephaestus chains.

    Required:
        context: Input from case.context — the eval runner populates this
        output_text: Final output — the eval runner reads this for scoring

    Optional:
        step_outputs: Intermediate outputs — pipeline-aware scorers can inspect these
        diagnostics: Generic debug messages that any chain node or tenant code can write to

    Agentic workflow fields (MCP integration):
        tool_call_history: All tool calls made during chain execution
        mcp_servers: Names of active MCP servers for this chain
    """

    context: Dict[str, str]
    output_text: str
    step_outputs: Dict[str, str]
    diagnostics: List[str]

    # Agentic workflow tracking
    tool_call_history: List[Dict[str, Any]]
    mcp_servers: Optional[List[str]]
