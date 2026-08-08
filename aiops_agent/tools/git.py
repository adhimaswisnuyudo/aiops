"""Git read-only tools — Phase 1."""

from __future__ import annotations

from typing import Any

from aiops_agent.tools.base import BaseTool, ToolContext, ToolResult, ToolRisk


class GitStatusTool(BaseTool):
    """Check Git status in project directories."""

    name = "git_status"
    description = "Show git status for project directories"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "find /www/wwwroot -maxdepth 3 -name .git -type d 2>/dev/null | "
            "while read gitdir; do "
            "  repo=$(dirname \"$gitdir\"); "
            "  echo \"=== $repo ===\"; "
            "  cd \"$repo\" && git status --short 2>/dev/null && "
            "  git log --oneline -3 2>/dev/null; "
            "  echo; "
            "done || echo 'No git repositories found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No git repositories found",
            error=stderr if stderr else None,
        )


class GitBranchTool(BaseTool):
    """Show current Git branch."""

    name = "git_branch"
    description = "Show current Git branch for project directories"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "find /www/wwwroot -maxdepth 3 -name .git -type d 2>/dev/null | "
            "while read gitdir; do "
            "  repo=$(dirname \"$gitdir\"); "
            "  echo \"$repo: $(cd \"$repo\" && git rev-parse --abbrev-ref HEAD 2>/dev/null)\"; "
            "done || echo 'No git repositories found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No git repositories found",
            error=stderr if stderr else None,
        )


class GitLogTool(BaseTool):
    """Show recent Git commits."""

    name = "git_log"
    description = "Show recent git commit history for project directories"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, count: int = 10, **kwargs: Any) -> ToolResult:
        cmd = (
            f"find /www/wwwroot -maxdepth 3 -name .git -type d 2>/dev/null | "
            "while read gitdir; do "
            "  repo=$(dirname \"$gitdir\"); "
            f"  echo \"=== $repo ===\"; "
            f"  cd \"$repo\" && git log --oneline -{count} 2>/dev/null; "
            "  echo; "
            "done || echo 'No git repositories found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No git repositories found",
            error=stderr if stderr else None,
        )


class GitRemoteTool(BaseTool):
    """Show Git remote URLs."""

    name = "git_remote"
    description = "Show git remote URLs for project directories"
    risk = ToolRisk.READ_ONLY
    read_only = True

    async def execute(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        cmd = (
            "find /www/wwwroot -maxdepth 3 -name .git -type d 2>/dev/null | "
            "while read gitdir; do "
            "  repo=$(dirname \"$gitdir\"); "
            "  echo \"$repo: $(cd \"$repo\" && git remote get-url origin 2>/dev/null)\"; "
            "done || echo 'No git repositories found'"
        )
        stdout, stderr, code = await self._run_ssh(self.ssh_client, cmd)
        return ToolResult(
            success=True,
            output=stdout if stdout else "No git repositories found",
            error=stderr if stderr else None,
        )