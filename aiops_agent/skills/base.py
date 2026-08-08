"""Base classes for skills."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from aiops_agent.tools.base import ToolResult
from aiops_agent.tools.registry import ToolRegistry


@dataclass
class SkillResult:
    """Result of a skill execution."""

    success: bool
    output: str = ""
    error: str | None = None
    tool_results: list[ToolResult] = field(default_factory=list)
    execution_time_ms: float = 0.0


@dataclass
class SkillContext:
    """Context passed to every skill execution."""

    server_name: str
    server_host: str
    environment: str = "staging"


class BaseSkill(ABC):
    """Abstract base class for skills.

    A skill orchestrates multiple tools to accomplish a higher-level task.
    """

    name: str = "base_skill"
    description: str = "Base skill"

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tools = tool_registry

    @abstractmethod
    async def execute(self, context: SkillContext, **kwargs: Any) -> SkillResult:
        """Execute the skill workflow."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serialise skill metadata."""
        return {
            "name": self.name,
            "description": self.description,
        }

    async def _run_tool(
        self, name: str, context: Any, ssh_client: Any = None, **kwargs: Any
    ) -> ToolResult:
        """Convenience method to run a registered tool."""
        from aiops_agent.tools.base import ToolContext

        tool_ctx = ToolContext(
            server_name=context.server_name,
            server_host=context.server_host,
            environment=context.environment,
        )
        return await self._tools.execute(name, tool_ctx, ssh_client=ssh_client, **kwargs)

    def __repr__(self) -> str:
        return f"<Skill name={self.name!r}>"