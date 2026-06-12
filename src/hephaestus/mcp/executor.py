# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tool execution with safety controls for MCP integration.

All tool calls are dispatched onto the manager's single lifecycle task (see
``manager.py``) via ``manager.run_coro``. This keeps every MCP session call on
the same asyncio task that opened the session, satisfying anyio's cancel-scope
requirement and avoiding the "exit cancel scope in a different task" error.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List

from src.hephaestus.providers.tool_types import ToolCall, ToolResult

if TYPE_CHECKING:
    from src.hephaestus.mcp.manager import MCPServerManager

logger = logging.getLogger(__name__)


class MCPToolExecutor:
    """Executes MCP tool calls with safety controls.

    Responsibilities:
    - Execute individual tool calls via MCP protocol
    - Apply timeout and retry logic
    - Track execution metrics
    - Handle errors gracefully

    Safety features:
    - Per-tool timeout enforcement
    - Maximum tool call limits
    - Error isolation (one tool failure doesn't crash evaluation)
    """

    def __init__(
        self,
        manager: MCPServerManager,
        max_tool_calls: int = 10,
        timeout_seconds: int = 30,
    ):
        """Initialize tool executor.

        Args:
            manager: MCPServerManager for tool routing
            max_tool_calls: Maximum number of tool calls per evaluation case
            timeout_seconds: Timeout for individual tool execution
        """
        self.manager = manager
        self.max_tool_calls = max_tool_calls
        self.timeout_seconds = timeout_seconds
        self._call_count = 0

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call (sync).

        Args:
            tool_call: ToolCall to execute

        Returns:
            ToolResult with content or error
        """
        self._call_count += 1

        if self._call_count > self.max_tool_calls:
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                error=f"Exceeded max_tool_calls limit ({self.max_tool_calls})",
            )

        # Resolve tool + server up front (cheap, no async needed).
        tool = self.manager.get_tool(tool_call.name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                error=f"Tool '{tool_call.name}' not found",
            )

        session = self.manager.get_session(tool.server_name)
        if not session:
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                error=f"Server '{tool.server_name}' not connected",
            )

        logger.debug(
            f"Calling tool '{tool_call.name}' with arguments: {tool_call.arguments}"
        )

        # The actual MCP call runs INSIDE the manager's lifecycle task so the
        # session's cancel scope stays on its owning task.
        def _coro_factory():
            return asyncio.wait_for(
                session.call_tool(name=tool_call.name, arguments=tool_call.arguments),
                timeout=self.timeout_seconds,
            )

        try:
            # Give the sync side a little more than the inner timeout so the
            # inner asyncio.wait_for is what fires first on a real hang.
            result = self.manager.run_coro(
                _coro_factory, timeout=self.timeout_seconds + 5
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.error(f"Tool '{tool_call.name}' timed out after {self.timeout_seconds}s")
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                error=f"Tool execution timed out after {self.timeout_seconds}s",
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Tool '{tool_call.name}' execution failed: {e}")
            return ToolResult(
                tool_call_id=tool_call.id,
                content="",
                error=str(e),
            )

        content = self._extract_content(result)
        logger.info(
            f"Tool '{tool_call.name}' executed successfully, result length: {len(content)}"
        )
        return ToolResult(
            tool_call_id=tool_call.id,
            content=content,
            error=None,
        )

    @staticmethod
    def _extract_content(result) -> str:
        """Normalize an MCP call_tool result into a plain string."""
        content_parts: List[str] = []
        if hasattr(result, "content"):
            for item in result.content:
                if hasattr(item, "text"):
                    content_parts.append(item.text)
                elif hasattr(item, "data"):
                    content_parts.append(str(item.data))
        elif isinstance(result, list):
            for item in result:
                if hasattr(item, "text"):
                    content_parts.append(item.text)
                else:
                    content_parts.append(str(item))
        return "\n".join(content_parts) if content_parts else str(result)

    def execute_batch(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tool calls sequentially.

        Args:
            tool_calls: List of ToolCalls to execute

        Returns:
            List of ToolResults in same order as input
        """
        return [self.execute(tc) for tc in tool_calls]

    def reset_count(self) -> None:
        """Reset tool call counter (call between evaluation cases)."""
        self._call_count = 0
