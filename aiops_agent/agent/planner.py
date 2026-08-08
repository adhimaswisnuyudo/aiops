"""Agent planner — natural language to action orchestration."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from aiops_agent.memory.store import MemoryStore
from aiops_agent.skills.base import SkillContext, SkillResult
from aiops_agent.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

SKILL_ALIASES: dict[str, str] = {
    "server": "server_status",
    "system": "server_status",
    "cpu": "server_status",
    "memory": "server_status",
    "ram": "server_status",
    "disk": "server_status",
    "uptime": "server_status",
    "health": "server_status",
    "laravel": "laravel_status",
    "app": "laravel_status",
    "php": "laravel_status",
    "database": "database_status",
    "db": "database_status",
    "mysql": "database_status",
    "mariadb": "database_status",
    "nginx": "nginx_status",
    "web": "nginx_status",
    "webserver": "nginx_status",
    "all": "all",
    "status": "all",
    "full": "all",
    "check": "all",
}


class AgentPlanner:
    """Parses user requests and orchestrates skill execution.

    In Phase 1, this uses simple keyword matching instead of an LLM.
    Phase 2 will integrate with an LLM provider (OpenAI/Anthropic/local).
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        memory: MemoryStore | None = None,
    ) -> None:
        self._skills = skill_registry
        self._memory = memory

    def parse_request(self, text: str) -> list[str]:
        """Parse natural language into skill names."""
        text_lower = text.lower().strip()
        matched_skills: set[str] = set()

        # Check for explicit skill mentions
        for keyword, skill_name in SKILL_ALIASES.items():
            if keyword in text_lower:
                matched_skills.add(skill_name)

        # "all" means run everything
        if "all" in matched_skills:
            return [
                "server_status",
                "laravel_status",
                "database_status",
                "nginx_status",
            ]

        # If no match, default to server status
        if not matched_skills:
            return ["server_status"]

        return list(matched_skills)

    async def execute(
        self,
        text: str,
        server_name: str,
        server_host: str,
        environment: str = "staging",
        ssh_client: Any = None,
    ) -> dict[str, Any]:
        """Parse request, run skills, return structured results."""
        skill_names = self.parse_request(text)
        context = SkillContext(
            server_name=server_name,
            server_host=server_host,
            environment=environment,
        )

        results: dict[str, Any] = {}
        all_success = True
        total_output = []

        # Save to memory for context
        if self._memory:
            self._memory.add_history(server_name, "user", text)

        for skill_name in skill_names:
            try:
                result = await self._skills.execute(skill_name, context, ssh_client=ssh_client)
                results[skill_name] = {
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                    "execution_time_ms": result.execution_time_ms,
                }
                if not result.success:
                    all_success = False
                total_output.append(result.output)
            except KeyError as e:
                results[skill_name] = {"success": False, "error": str(e)}
                all_success = False

        summary = "\n\n".join(total_output)

        if self._memory:
            self._memory.add_history(server_name, "assistant", summary)

        return {
            "success": all_success,
            "skills_executed": skill_names,
            "results": results,
            "summary": summary,
        }

    def get_available_skills(self) -> list[dict[str, Any]]:
        """Return metadata about all available skills."""
        return self._skills.list_skills()

    def get_history(self, server_name: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent conversation history for a server."""
        if self._memory:
            return self._memory.get_history(server_name, limit)
        return []