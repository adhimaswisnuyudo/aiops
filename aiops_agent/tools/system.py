"""System-level read-only tools — Phase 1."""

from __future__ import annotations

from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult, ToolRisk


class UptimeTool(BaseTool):
    """Get server uptime."""

    name = "uptime"
    description = "Get the server's uptime and load average"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        stdout, stderr, code = await self._run_ssh(self.ssh_client, "uptime")
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class CPUInfoTool(BaseTool):
    """Get CPU information and usage."""

    name = "cpu_info"
    description = "Get CPU usage percentage and core count"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        # Get CPU usage via top in batch mode
        cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2 \"% us, \" $4 \"% sy, \" $8 \"% id\"}'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)

        # Also get core count
        cores_cmd = "nproc"
        cores_stdout, _, cores_code = await self._run_ssh(self.ssh_client, cores_cmd)

        output = f"CPU Usage: {stdout}\nCPU Cores: {cores_stdout}" if code == 0 else stdout
        return ToolResult(
            success=code == 0,
            output=output,
            error=stderr if code != 0 else None,
        )


class MemoryTool(BaseTool):
    """Get memory usage."""

    name = "memory"
    description = "Get RAM and swap usage"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "free -h | head -3"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class DiskTool(BaseTool):
    """Get disk usage."""

    name = "disk"
    description = "Get disk usage for all mounted filesystems"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "df -h --type=ext4 --type=xfs --type=btrfs 2>/dev/null || df -h"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class DiskUsagePercentTool(BaseTool):
    """Get disk usage as percentage per mount."""

    name = "disk_percent"
    description = "Get disk usage as percentage for each mounted filesystem"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "df -h --type=ext4 --type=xfs --type=btrfs 2>/dev/null | tail -n +2 | awk '{print $6, $5}' || df -h | tail -n +2 | awk '{print $6, $5}'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class LoadAverageTool(BaseTool):
    """Get load average."""

    name = "load_average"
    description = "Get the server load average (1, 5, 15 min)"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "cat /proc/loadavg | awk '{print \"1m: \"$1, \"5m: \"$2, \"15m: \"$3}'"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class UsersTool(BaseTool):
    """Get logged-in users."""

    name = "users"
    description = "Get currently logged-in users"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "who"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout if stdout else "No users logged in",
            error=stderr if code != 0 else None,
        )


class ProcessListTool(BaseTool):
    """Get top processes by CPU/memory."""

    name = "top_processes"
    description = "Get top 10 processes by CPU usage"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "ps aux --sort=-%cpu | head -11"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class OSInfoTool(BaseTool):
    """Get OS information."""

    name = "os_info"
    description = "Get OS version and kernel information"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "cat /etc/os-release 2>/dev/null || cat /etc/lsb-release 2>/dev/null || uname -a"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )


class NetworkTool(BaseTool):
    """Get network information."""

    name = "network"
    description = "Get network interfaces and listening ports"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = "ss -tlnp 2>/dev/null | head -30 || netstat -tlnp 2>/dev/null | head -30"
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=code == 0,
            output=stdout,
            error=stderr if code != 0 else None,
        )