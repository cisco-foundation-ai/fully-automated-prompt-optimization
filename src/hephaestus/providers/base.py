# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.hephaestus.providers.tool_types import GenerateResponse


class ProviderClient(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate text from messages (legacy interface).

        This method is kept for backward compatibility with existing chains.
        New code should use generate_with_tools() which supports both text
        generation and tool calling.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Generated text content
        """
        raise NotImplementedError

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> GenerateResponse:
        """Generate with optional tool calling support.

        This is the enhanced interface that supports both pure text generation
        and tool calling. Subclasses override this to enable tool calling.

        The default implementation calls generate() for backward compatibility
        with providers that don't support tools.

        Args:
            messages: List of message dicts (role, content, optional tool_calls/tool_call_id)
            tools: Optional list of tool schemas in OpenAI format

        Returns:
            GenerateResponse with content and optional tool_calls
        """
        content = self.generate(messages)
        return GenerateResponse(content=content, tool_calls=None, finish_reason="stop")
