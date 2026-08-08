"""MySQL read-only tools — Phase 1."""

from __future__ import annotations

from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult, ToolRisk


class MySQLStatusTool(BaseTool):
    """Check MySQL/MariaDB service status."""

    name = "mysql_status"
    description = "Check MySQL/MariaDB service status"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "systemctl status mysqld --no-pager -l 2>/dev/null || systemctl status mysql --no-pager -l 2>/dev/null || systemctl status mariadb --no-pager -l 2>/dev/null || ps aux | grep mysqld | grep -v grep | head -5"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout if stdout else "MySQL/MariaDB not found or not running",
            error=stderr if stderr else None,
        )


class MySQLProcessListTool(BaseTool):
    """Show MySQL process list."""

    name = "mysql_processlist"
    description = "Show active MySQL connections and queries"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        # Try mysqladmin, otherwise skip
        cmd = (
            "mysqladmin processlist 2>/dev/null || "
            "mysql -e 'SHOW PROCESSLIST;' 2>/dev/null || "
            "echo 'Cannot connect to MySQL — check credentials'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class MySQLStatusVarsTool(BaseTool):
    """Get MySQL status variables."""

    name = "mysql_status_vars"
    description = "Show MySQL key status variables (uptime, connections, queries)"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "mysql -e \"SHOW STATUS WHERE Variable_name IN ("
            "'Uptime', 'Threads_connected', 'Threads_running', "
            "'Queries', 'Slow_queries', 'Connections', 'Max_used_connections');\" 2>/dev/null || "
            "echo 'Cannot connect to MySQL'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class MySQLSlowQueryTool(BaseTool):
    """Check MySQL slow query log status."""

    name = "mysql_slow_query"
    description = "Check slow query log status and count recent slow queries"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "mysql -e \"SHOW VARIABLES LIKE 'slow_query%'; "
            "SHOW STATUS LIKE 'Slow_queries';\" 2>/dev/null || "
            "echo 'Cannot connect to MySQL'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class DatabaseSizeTool(BaseTool):
    """Show database sizes."""

    name = "database_size"
    description = "Show size of all MySQL databases"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "mysql -e \"SELECT table_schema AS 'Database', "
            "ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' "
            "FROM information_schema.tables GROUP BY table_schema "
            "ORDER BY SUM(data_length + index_length) DESC;\" 2>/dev/null || "
            "echo 'Cannot connect to MySQL'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class MySQLErrorLogTool(BaseTool):
    """Read MySQL error log (tail)."""

    name = "mysql_error_log"
    description = "Get the last N lines from MySQL error log"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, lines: int = 50, **kwargs: Any) -> ToolResult:
        cmd = (
            f"tail -n {lines} /var/log/mysql/error.log 2>/dev/null || "
            f"tail -n {lines} /var/log/mysqld.log 2>/dev/null || "
            f"tail -n {lines} /www/server/data/*.err 2>/dev/null || "
            "echo 'MySQL error log not found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )