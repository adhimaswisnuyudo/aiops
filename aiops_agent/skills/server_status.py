"""Server status skill — comprehensive server health check."""

from __future__ import annotations

import time
from typing import Any

from aiops_agent.skills.base import BaseSkill, SkillContext, SkillResult
from aiops_agent.tools.registry import ToolRegistry


class ServerStatusSkill(BaseSkill):
    """Gather comprehensive server status: CPU, RAM, disk, uptime, and processes."""

    name = "server_status"
    description = "Comprehensive server health check — CPU, RAM, disk, load, processes"

    def __init__(self, tool_registry: ToolRegistry) -> None:
        super().__init__(tool_registry)

    async def execute(self, context: SkillContext, **kwargs: Any) -> SkillResult:
        start = time.monotonic()
        results = []
        errors = []

        # Run tools sequentially (they use the same SSH connection)
        tools_to_run = [
            ("uptime", {}),
            ("cpu_info", {}),
            ("memory", {}),
            ("disk", {}),
            ("disk_percent", {}),
            ("load_average", {}),
            ("top_processes", {}),
            ("os_info", {}),
            ("network", {}),
            ("users", {}),
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

        # Build summary output
        output_lines = ["=== SERVER STATUS REPORT ==="]
        output_lines.append(f"Server: {context.server_name}")
        output_lines.append(f"Environment: {context.environment}")
        output_lines.append("")

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