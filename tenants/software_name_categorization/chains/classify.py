# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Single-node software-name categorization chain."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from src.hephaestus.chains.nodes import make_llm_node
from src.hephaestus.providers.base import ProviderClient


def build_chain(provider: ProviderClient, config: Dict[str, Any]) -> Any:
    """Build a one-step classification chain."""
    prompt_path = Path(config["prompt_paths"]["classify"])
    graph = StateGraph(dict)
    graph.add_node("classify", make_llm_node(provider, prompt_path))
    graph.set_entry_point("classify")
    graph.add_edge("classify", END)
    return graph.compile()

