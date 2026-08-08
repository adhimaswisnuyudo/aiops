"""PHP/PHP-FPM read-only tools — Phase 1."""

from __future__ import annotations

from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult, ToolRisk


class PHPStatusTool(BaseTool):
    """Check PHP-FPM service status."""

    name = "php_status"
    description = "Check PHP-FPM service status"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        # aaPanel typically uses php-fpm-XX naming
        cmd = (
            "systemctl status 'php*' --no-pager -l 2>/dev/null || "
            "systemctl list-units --type=service --state=running | grep php || "
            "ps aux | grep php-fpm | grep -v grep"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout if stdout else "PHP-FPM not found or not running",
            error=stderr if stderr else None,
        )


class PHPVersionTool(BaseTool):
    """Get PHP version."""

    name = "php_version"
    description = "Get installed PHP version"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "php -v 2>/dev/null || /usr/bin/php -v 2>/dev/null || echo 'PHP not found'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class PHPModulesTool(BaseTool):
    """List installed PHP modules."""

    name = "php_modules"
    description = "List installed PHP modules"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "php -m 2>/dev/null || echo 'PHP not found'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class PHPFPMConfigTool(BaseTool):
    """Read PHP-FPM pool configuration."""

    name = "php_fpm_config"
    description = "Show PHP-FPM pool configuration summary"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "grep -E '^(pm\\.|listen|user|group)' "
            "/www/server/php/*/etc/php-fpm.conf 2>/dev/null || "
            "grep -E '^(pm\\.|listen|user|group)' "
            "/etc/php/*/fpm/pool.d/www.conf 2>/dev/null || "
            "echo 'PHP-FPM config not found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class PHPErrorLogTool(BaseTool):
    """Read PHP error log (tail)."""

    name = "php_error_log"
    description = "Get the last N lines from PHP error log"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, lines: int = 50, **kwargs: Any) -> ToolResult:
        cmd = (
            f"tail -n {lines} /var/log/php*-fpm*.log 2>/dev/null || "
            f"tail -n {lines} /www/server/php/*/var/log/php-fpm.log 2>/dev/null || "
            "echo 'PHP error log not found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class PHPFPMProcessesTool(BaseTool):
    """Show PHP-FPM worker processes."""

    name = "php_fpm_processes"
    description = "Show active PHP-FPM worker processes"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "ps aux | grep 'php-fpm' | grep -v grep | wc -l && ps aux | grep 'php-fpm' | grep -v grep | head -10"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )