# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""MCP server lifecycle management with full protocol implementation.

Design note — why a dedicated background thread + single lifecycle task:

The MCP SDK (via anyio) sets up cancel scopes inside ``stdio_client`` and
``ClientSession``. anyio requires that the scope be entered and exited in the
*same* asyncio task. If we open the session in one ``run_until_complete`` call,
call tools in separate calls, and close in yet another, each of those is a
different task on the loop — anyio then raises::

    Attempted to exit cancel scope in a different task than it was entered in

To respect that invariant we run the WHOLE lifecycle (open → serve calls →
close) inside one coroutine (``_lifecycle``) on a background thread's event
loop. The sync API (start/stop/call) hands work to that task through a queue
and blocks on a ``concurrent.futures.Future``.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import threading
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.hephaestus.mcp.types import MCPConfig, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)

# Sentinel pushed onto the command queue to tell the lifecycle task to shut down.
_SHUTDOWN = object()


class MCPServerManager:
    """Manages lifecycle of MCP servers for a tenant.

    All MCP protocol work runs on a single long-lived task on a background
    thread (see module docstring). Public methods are synchronous and safe to
    call from the eval runner's threads.

    Usage:
        manager = MCPServerManager(tenant_id="my_tenant", config=mcp_config)
        try:
            manager.start_servers()
            tools = manager.list_tools()
            # ... use tools ...
        finally:
            manager.stop_servers()
    """

    def __init__(
        self,
        tenant_id: str,
        config: Optional[MCPConfig] = None,
        config_path: Optional[Path] = None,
    ):
        """Initialize MCP server manager.

        Args:
            tenant_id: Tenant identifier
            config: MCPConfig object (takes precedence over config_path)
            config_path: Path to mcp_servers.json config file
        """
        self.tenant_id = tenant_id
        self.tools: Dict[str, MCPTool] = {}
        self._server_configs: List[MCPServerConfig] = []
        self._sessions: Dict[str, ClientSession] = {}

        # Background-thread machinery
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._command_queue: "Optional[asyncio.Queue]" = None
        self._ready: Optional[concurrent.futures.Future] = None
        self._stopped: Optional[concurrent.futures.Future] = None

        if config:
            self._server_configs = config.servers
        elif config_path and config_path.exists():
            self._load_config_from_file(config_path)

    def _load_config_from_file(self, config_path: Path) -> None:
        """Load MCP server configs from JSON file."""
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            servers_data = raw.get("servers", [])

            for srv in servers_data:
                self._server_configs.append(
                    MCPServerConfig(
                        name=srv["name"],
                        command=srv["command"],
                        args=srv.get("args", []),
                        env=srv.get("env", {}),
                        enabled=srv.get("enabled", True),
                        timeout_seconds=srv.get("timeout_seconds", 30),
                    )
                )
            logger.info(f"Loaded {len(self._server_configs)} MCP server configs from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load MCP config from {config_path}: {e}")
            raise

    # ------------------------------------------------------------------
    # Public sync API
    # ------------------------------------------------------------------

    def start_servers(self) -> None:
        """Start all enabled MCP servers and block until ready.

        Spins up the background thread that owns the event loop and the single
        lifecycle task. Raises if startup fails.
        """
        if self._thread is not None:
            logger.warning("start_servers() called but servers already started")
            return

        self._ready = concurrent.futures.Future()
        self._stopped = concurrent.futures.Future()
        self._thread = threading.Thread(
            target=self._thread_main,
            name=f"mcp-manager-{self.tenant_id}",
            daemon=True,
        )
        self._thread.start()

        # Block until the lifecycle task finishes startup (or errors).
        # Use a generous ceiling so slow server boots don't false-timeout.
        startup_timeout = max(
            (c.timeout_seconds for c in self._server_configs if c.enabled),
            default=30,
        ) + 30
        self._ready.result(timeout=startup_timeout)

    def stop_servers(self) -> None:
        """Stop all running MCP servers and join the background thread."""
        if self._thread is None:
            return

        # Ask the lifecycle task to shut down (teardown happens in-task).
        if self._loop is not None and self._command_queue is not None:
            try:
                self._loop.call_soon_threadsafe(self._command_queue.put_nowait, _SHUTDOWN)
            except RuntimeError:
                # Loop already closed; nothing to do.
                pass

        # Wait for the lifecycle coroutine to finish its teardown.
        if self._stopped is not None:
            try:
                self._stopped.result(timeout=30)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error during MCP shutdown: {e}")

        # Join the thread so the loop is fully torn down.
        self._thread.join(timeout=10)

        self._thread = None
        self._loop = None
        self._command_queue = None
        self._ready = None
        self._stopped = None
        self._sessions.clear()
        self.tools.clear()
        logger.info("All MCP servers stopped")

    def run_coro(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        timeout: float = 60.0,
    ) -> Any:
        """Run an awaitable on the lifecycle task and return its result.

        The coroutine is executed *inside* the single lifecycle task, so any
        MCP session calls it makes share that task's cancel scope. Blocks the
        calling (sync) thread until the result is available.

        Args:
            coro_factory: Zero-arg callable returning the awaitable to run.
                Passed as a factory (not a coroutine) so it is created on the
                loop thread.
            timeout: Seconds to wait before giving up on the calling side.

        Returns:
            Whatever the awaitable returns.

        Raises:
            RuntimeError: If the lifecycle task is not running.
            Exception: Re-raises any exception from the awaitable.
        """
        if self._loop is None or self._command_queue is None:
            raise RuntimeError("MCP lifecycle task is not running; call start_servers() first")

        fut: concurrent.futures.Future = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(
            self._command_queue.put_nowait, (coro_factory, fut)
        )
        return fut.result(timeout=timeout)

    # ------------------------------------------------------------------
    # Background thread + lifecycle task
    # ------------------------------------------------------------------

    def _thread_main(self) -> None:
        """Entry point for the background thread: own a fresh event loop."""
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._lifecycle())
        except Exception as e:  # noqa: BLE001
            logger.error(f"MCP lifecycle task crashed: {e}")
            if self._ready is not None and not self._ready.done():
                self._ready.set_exception(e)
            if self._stopped is not None and not self._stopped.done():
                self._stopped.set_exception(e)
        finally:
            try:
                loop.close()
            except Exception:  # noqa: BLE001
                pass

    async def _lifecycle(self) -> None:
        """Single task that owns setup, command serving, and teardown.

        Critically, the AsyncExitStack is entered and exited within this one
        coroutine, satisfying anyio's same-task cancel-scope requirement.
        """
        self._command_queue = asyncio.Queue()
        startup_error: Optional[Exception] = None

        try:
            async with AsyncExitStack() as stack:
                # --- setup: open every enabled server in THIS task ---
                for config in self._server_configs:
                    if not config.enabled:
                        logger.info(f"Skipping disabled MCP server: {config.name}")
                        continue
                    try:
                        await self._open_server(stack, config)
                    except Exception as e:  # noqa: BLE001
                        logger.error(f"Failed to start MCP server '{config.name}': {e}")
                        # Continue starting other servers.

                logger.info(
                    f"Started {len(self._sessions)} MCP servers with {len(self.tools)} tools"
                )

                # Signal the sync caller that startup is done.
                if self._ready is not None and not self._ready.done():
                    self._ready.set_result(True)

                # --- serve commands until shutdown ---
                while True:
                    command = await self._command_queue.get()
                    if command is _SHUTDOWN:
                        break

                    coro_factory, fut = command
                    if fut.cancelled():
                        continue
                    try:
                        result = await coro_factory()
                        fut.set_result(result)
                    except Exception as e:  # noqa: BLE001
                        fut.set_exception(e)
            # AsyncExitStack closes here — same task that opened it. ✅
        except Exception as e:  # noqa: BLE001
            startup_error = e
            if self._ready is not None and not self._ready.done():
                self._ready.set_exception(e)
        finally:
            self._sessions.clear()
            if self._stopped is not None and not self._stopped.done():
                if startup_error is not None:
                    self._stopped.set_exception(startup_error)
                else:
                    self._stopped.set_result(True)

    async def _open_server(self, stack: AsyncExitStack, config: MCPServerConfig) -> None:
        """Open a single MCP server's session and discover its tools.

        Must be called from within the lifecycle task so the session's cancel
        scope is bound to that task.
        """
        # Expand environment variables in env dict (supports ${VAR_NAME}).
        expanded_env = os.environ.copy()
        for key, value in config.env.items():
            if value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                expanded_value = os.environ.get(env_var, "")
                if not expanded_value:
                    logger.warning(f"MCP server '{config.name}': env var '{env_var}' not set")
                expanded_env[key] = expanded_value
            else:
                expanded_env[key] = value

        logger.info(
            f"Starting MCP server '{config.name}': {config.command} {' '.join(config.args)}"
        )

        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=expanded_env,
        )

        # Enter both contexts on the stack so they unwind in this same task.
        read_stream, write_stream = await stack.enter_async_context(
            stdio_client(server_params)
        )
        session = await stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._sessions[config.name] = session
        logger.info(f"MCP server '{config.name}' connected and initialized")

        await self._discover_tools(config.name, session)

    async def _discover_tools(self, server_name: str, session: ClientSession) -> None:
        """Discover and register tools exposed by a connected server."""
        try:
            tools_result = await session.list_tools()
            for tool_info in tools_result.tools:
                self.tools[tool_info.name] = MCPTool(
                    name=tool_info.name,
                    description=tool_info.description or "",
                    input_schema=tool_info.inputSchema,
                    server_name=server_name,
                )
                logger.debug(f"Discovered tool '{tool_info.name}' from server '{server_name}'")
            logger.info(
                f"Discovered {len(tools_result.tools)} tools from MCP server '{server_name}'"
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to discover tools from server '{server_name}': {e}")

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def list_tools(self) -> List[MCPTool]:
        """Return all available tools from connected servers."""
        return list(self.tools.values())

    def add_tool(self, tool: MCPTool) -> None:
        """Manually register a tool (for testing or manual configuration)."""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool '{tool.name}' from server '{tool.server_name}'")

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get tool by name, or None if not found."""
        return self.tools.get(tool_name)

    def get_session(self, server_name: str) -> Optional[ClientSession]:
        """Get the active MCP session for a server, or None."""
        return self._sessions.get(server_name)
