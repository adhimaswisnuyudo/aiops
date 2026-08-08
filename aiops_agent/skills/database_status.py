"""Database status skill."""

from __future__ import annotations

import time
from typing import Any

from aiops_agent.skills.base import BaseSkill, SkillContext, SkillResult
from aiops_agent.tools.base import ToolResult
from aiops_agent.tools.registry import ToolRegistry


class DatabaseStatusSkill(BaseSkill):
    """Check database health: MySQL status, process list, status vars, size, slow queries."""

    name = "database_status"
    description = "Comprehensive database health check — MySQL status, connections, size, slow queries"

    def __init__(self, tool_registry: ToolRegistry) -> None:
        super().__init__(tool_registry)

    async def execute(self, context: SkillContext, **kwargs: Any) -> SkillResult:
        start = time.monotonic()
        results = []
        errors = []

        tools_to_run = [
            ("mysql_status", {}),
            ("mysql_status_vars", {}),
            ("mysql_processlist", {}),
            ("database_size", {}),
            ("mysql_slow_query", {}),
            ("mysql_error_log", {"lines": 30}),
        ]

        for tool_name, tool_kwargs in tools_to_run:
            try:
                result = await self._run_tool(tool_name, context, **tool_kwargs)
                results.append(result)
                if result.error:
                    errors.append(f"[{tool_name}] {result.error}")
            except Exception as e:
                results.append(ToolResult(success=False, error=str(e)))
                errors.append(f"[{tool_name}] {e}")

        elapsed = (time.monotonic() - start) * 1000

        output_lines = [f"=== DATABASE STATUS: {context.server_name} ===", ""]
        for result in results:
            if result.output:
                output_lines.append(result.output.strip())
                output_lines.append("")

        return SkillResult(
            success=len(errors) == 0,
            output="\n".join(output_lines),
            error="\n".join(errors) if errors else None,
            tool_results=results,
            execution_time_ms=round(elapsed, 2),
        )