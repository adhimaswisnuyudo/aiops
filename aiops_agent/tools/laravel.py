"""Laravel read-only tools — Phase 1."""

from __future__ import annotations

from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult, ToolRisk


class LaravelVersionTool(BaseTool):
    """Show Laravel version."""

    name = "laravel_version"
    description = "Show Laravel framework version from artisan"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "cd /www/wwwroot 2>/dev/null && "
            "php artisan --version 2>/dev/null || "
            "grep '\"laravel/framework\"' /www/wwwroot/*/composer.json 2>/dev/null || "
            "echo 'No Laravel project found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No Laravel project found",
            error=stderr if stderr else None,
        )


class LaravelLogTool(BaseTool):
    """Read Laravel log (tail)."""

    name = "laravel_log"
    description = "Get the last N lines from Laravel storage/logs/laravel.log"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, lines: int = 50, **kwargs: Any) -> ToolResult:
        cmd = (
            f"tail -n {lines} /www/wwwroot/*/storage/logs/laravel.log 2>/dev/null || "
            f"find /www/wwwroot -name laravel.log -exec tail -n {lines} {{}} \\; 2>/dev/null || "
            "echo 'Laravel log not found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class LaravelRoutesTool(BaseTool):
    """Show Laravel routes."""

    name = "laravel_routes"
    description = "List all registered Laravel routes via artisan route:list"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "cd /www/wwwroot/*/ 2>/dev/null && "
            "php artisan route:list 2>/dev/null || "
            "echo 'Cannot list routes'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No Laravel project or routes found",
            error=stderr if stderr else None,
        )


class LaravelEnvTool(BaseTool):
    """Read Laravel .env (sanitised)."""

    name = "laravel_env"
    description = "Show Laravel .env key settings (passwords redacted)"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "cat /www/wwwroot/*/.env 2>/dev/null | "
            "grep -v 'PASSWORD\\|SECRET\\|KEY\\|TOKEN' || "
            "echo 'No .env found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No .env found",
            error=stderr if stderr else None,
        )


class LaravelScheduleTool(BaseTool):
    """Show Laravel scheduled tasks."""

    name = "laravel_schedule"
    description = "Show registered Laravel scheduled tasks"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "cd /www/wwwroot/*/ 2>/dev/null && "
            "php artisan schedule:list 2>/dev/null || "
            "echo 'Cannot list scheduled tasks'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No scheduled tasks found or no Laravel project",
            error=stderr if stderr else None,
        )


class JournalCtlTool(BaseTool):
    """Read systemd journal logs."""

    name = "journalctl"
    description = "Read systemd journal logs for a specific service"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(
        self, context: ToolContext, service: str = "", lines: int = 50, **kwargs: Any
    ) -> ToolResult:
        if service:
            cmd = f"journalctl -u {service} --no-pager -n {lines} 2>/dev/null || echo 'No logs for {service}'"
        else:
            cmd = f"journalctl --no-pager -n {lines} 2>/dev/null || echo 'Cannot read journal'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )