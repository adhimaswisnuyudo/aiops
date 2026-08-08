"""Nginx read-only tools — Phase 1."""

from __future__ import annotations

from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult, ToolRisk


class NginxStatusTool(BaseTool):
    """Check Nginx service status."""

    name = "nginx_status"
    description = "Check if Nginx is running via systemctl status"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "systemctl status nginx --no-pager -l 2>/dev/null || service nginx status 2>/dev/null"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,  # status command returns non-zero sometimes — still valid info
            output=stdout,
            error=stderr if stderr else None,
        )


class NginxAccessLogTool(BaseTool):
    """Read Nginx access log (tail)."""

    name = "nginx_access_log"
    description = "Get the last N lines from Nginx access log"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, lines: int = 50, **kwargs: Any) -> ToolResult:
        cmd = f"tail -n {lines} /var/log/nginx/access.log 2>/dev/null || tail -n {lines} /www/wwwlogs/access.log 2>/dev/null || echo 'Access log not found'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class NginxErrorLogTool(BaseTool):
    """Read Nginx error log (tail)."""

    name = "nginx_error_log"
    description = "Get the last N lines from Nginx error log"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, lines: int = 50, **kwargs: Any) -> ToolResult:
        cmd = f"tail -n {lines} /var/log/nginx/error.log 2>/dev/null || tail -n {lines} /www/wwwlogs/error.log 2>/dev/null || echo 'Error log not found'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class NginxConfigTestTool(BaseTool):
    """Test Nginx configuration."""

    name = "nginx_config_test"
    description = "Test Nginx configuration syntax with nginx -t"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "nginx -t 2>&1"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        combined = f"{stdout}\n{stderr}" if stderr else stdout
        return ToolResult(
            success=code == 0,
            output=combined,
            error=None if code == 0 else combined,
        )