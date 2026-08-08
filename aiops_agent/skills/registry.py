"""Skill registry — discovers and stores all skills."""

from __future__ import annotations

import logging
from typing import Any

from aiops_agent.skills.base import BaseSkill
from aiops_agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry for all available skills."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tool_registry = tool_registry
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        if skill.name in self._skills:
            logger.warning("Skill %r already registered, overwriting", skill.name)
        self._skills[skill.name] = skill
        logger.debug("Registered skill: %s", skill.name)

    async def execute(
        self, name: str, context: Any, **kwargs: Any
    ) -> Any:
        if name not in self._skills:
            available = ", ".join(self._skills.keys())
            raise KeyError(f"Skill {name!r} not found. Available: {available}")

        return await self._skills[name].execute(context, **kwargs)

    def list_skills(self) -> list[dict[str, Any]]:
        return [skill.to_dict() for skill in self._skills.values()]

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def register_all(self, skills: list[BaseSkill]) -> None:
        for skill in skills:
            self.register(skill)

    def __len__(self) -> int:
        return len(self._skills)