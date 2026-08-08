"""Nginx status skill."""

from __future__ import annotations

import time
from typing import Any

from aiops_agent.skills.base import BaseSkill, SkillContext, SkillResult
from aiops_agent.tools.base import ToolResult
from aiops_agent.tools.registry import ToolRegistry


class NginxStatusSkill(BaseSkill):
    """Check Nginx health: service status, config test, access log, error log."""

    name = "nginx_status"
    description = "Comprehensive Nginx health check — status, config, logs"

    def __init__(self, tool_registry: ToolRegistry) -> None:
        super().__init__(tool_registry)

    async def execute(self, context: SkillContext, ssh_client: Any = None, **kwargs: Any) -> SkillResult:
        start = time.monotonic()
        results = []
        errors = []

        tools_to_run = [
            ("nginx_status", {}),
            ("nginx_config_test", {}),
            ("nginx_access_log", {"lines": 20}),
            ("nginx_error_log", {"lines": 20}),
        ]

        for tool_name, tool_kwargs in tools_to_run:
            try:
                result = await self._run_tool(tool_name, context, ssh_client, **tool_kwargs)
                results.append(result)
                if result.error:
                    errors.append(f"[{tool_name}] {result.error}")
            except Exception as e:
                results.append(ToolResult(success=False, error=str(e)))
                errors.append(f"[{tool_name}] {e}")

        elapsed = (time.monotonic() - start) * 1000

        output_lines = [f"=== NGINX STATUS: {context.server_name} ===", ""]
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