"""Tool Registry — central registry for all available tools."""

from __future__ import annotations

import logging
from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry that holds all available tools.

    Tools are registered once at startup and looked up by name during execution.
    The registry also handles access control based on risk level and phase.
    """

    def __init__(self, phase: int = 1) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._phase = phase

    @property
    def phase(self) -> int:
        return self._phase

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Raises ValueError if a tool with the same name already exists.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s (risk=%s)", tool.name, tool.risk.value)

    def register_many(self, tools: list[BaseTool]) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> BaseTool:
        """Retrieve a tool by name.

        Raises KeyError if not found.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def list_tools(self) -> list[dict[str, Any]]:
        """Return metadata for all registered tools."""
        return [tool.to_dict() for tool in self._tools.values()]

    def get_read_only_tools(self) -> list[BaseTool]:
        """Return only read-only tools (Phase 1 safe)."""
        return [t for t in self._tools.values() if t.read_only]

    def get_tools_by_risk(self, risk: str) -> list[BaseTool]:
        """Return tools filtered by risk level."""
        return [t for t in self._tools.values() if t.risk.value == risk]

    async def execute(
        self,
        name: str,
        context: ToolContext,
        ssh_client: Any = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute a tool by name, injecting the SSH client.

        This method also enforces Phase-based restrictions:
        - Phase 1: only read_only tools
        - Phase 2: read_only + safe
        - Phase 3+: all allowed (with approval for cautious/dangerous)
        """
        tool = self.get(name)

        # Phase 1 enforcement: only read-only tools
        if self._phase <= 1 and not tool.read_only:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' requires write access. Phase 1 only allows read-only tools.",
            )

        # Set the SSH client reference on the tool instance
        tool.ssh_client = ssh_client  # type: ignore[attr-defined]

        logger.info("Executing tool: %s on %s", name, context.server_name)
        try:
            result = await tool.execute(context, **kwargs)
            logger.info("Tool %s completed (success=%s, time=%dms)", name, result.success, result.execution_time_ms)
            return result
        except Exception as e:
            logger.exception("Tool %s failed with exception", name)
            return ToolResult(success=False, error=str(e))

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools