"""Base classes for all tools."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolRisk(str, Enum):
    """Risk level classification for tools."""

    READ_ONLY = "read_only"  # Only reads data, no side effects
    SAFE = "safe"  # Well-known safe actions (restart services, clear cache)
    CAUTIOUS = "cautious"  # Needs approval (composer install, migrate)
    DANGEROUS = "dangerous"  # Forbidden unless explicitly allowed


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


@dataclass
class ToolContext:
    """Context passed to every tool execution."""

    server_name: str
    server_host: str
    environment: str = "staging"
    request_approval: bool = False


class BaseTool(ABC):
    """Abstract base class for all tools.

    Each tool wraps a specific system command or API call.
    Tools are stateless — context is injected per execution.
    """

    # --- Subclass overrides ---

    name: str = "base"
    description: str = "Base tool"
    risk: ToolRisk = ToolRisk.READ_ONLY
    read_only: bool = True  # True = no mutations allowed

    @abstractmethod
    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        """Execute the tool with given context and arguments.

        Subclasses should:
        1. Validate input
        2. Build the command
        3. Execute via SSH (injected via dependency)
        4. Parse output
        5. Return ToolResult
        """
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serialise tool metadata for LLM function-calling."""
        return {
            "name": self.name,
            "description": self.description,
            "risk": self.risk.value,
            "read_only": self.read_only,
        }

    async def _run_ssh(
        self, ssh_client: Any, command: str, timeout: int = 30, sudo: bool = False
    ) -> tuple[str, str, int]:
        """Convenience method to run an SSH command through the injected client.

        Returns (stdout, stderr, exit_code).
        """
        start = time.monotonic()
        try:
            result = await ssh_client.run(command, timeout=timeout, sudo=sudo)
            elapsed = (time.monotonic() - start) * 1000
            return result.stdout, result.stderr, result.exit_code
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return "", str(e), -1

    def __repr__(self) -> str:
        return f"<Tool name={self.name!r} risk={self.risk.value}>"