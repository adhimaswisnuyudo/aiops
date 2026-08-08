"""Docker read-only tools — Phase 1."""

from __future__ import annotations

from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult, ToolRisk


class DockerStatusTool(BaseTool):
    """Check Docker service status."""

    name = "docker_status"
    description = "Check Docker daemon status"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "systemctl status docker --no-pager -l 2>/dev/null || "
            "docker info 2>/dev/null | head -20 || "
            "echo 'Docker not installed or not running'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout if stdout else "Docker not installed or not running",
            error=stderr if stderr else None,
        )


class DockerPS(BaseTool):
    """List Docker containers."""

    name = "docker_ps"
    description = "List all running Docker containers"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo 'Docker not available'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class DockerPSAll(BaseTool):
    """List all Docker containers (including stopped)."""

    name = "docker_ps_all"
    description = "List all Docker containers (including stopped)"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo 'Docker not available'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class DockerStats(BaseTool):
    """Show Docker container resource usage."""

    name = "docker_stats"
    description = "Show live resource usage of all running Docker containers (no-stream)"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "docker stats --no-stream 2>/dev/null || echo 'Docker not available'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class DockerImages(BaseTool):
    """List Docker images."""

    name = "docker_images"
    description = "List all Docker images"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' 2>/dev/null || echo 'Docker not available'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )


class DockerLogs(BaseTool):
    """Get Docker container logs (tail)."""

    name = "docker_logs"
    description = "Get the last N lines from a Docker container's logs"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(
        self, context: ToolContext, container: str = "", lines: int = 50, **kwargs: Any
    ) -> ToolResult:
        if not container:
            return ToolResult(success=False, error="container name is required")

        cmd = f"docker logs --tail {lines} {container} 2>/dev/null || echo 'Cannot read logs for {container}'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd, sudo=True)
        return ToolResult(
            success=True,
            output=stdout,
            error=stderr if stderr else None,
        )