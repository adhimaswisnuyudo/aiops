"""Unit tests for AgentPlanner request parsing."""

from __future__ import annotations

import pytest

from aiops_agent.agent.planner import AgentPlanner, SKILL_ALIASES
from aiops_agent.skills.registry import SkillRegistry
from aiops_agent.tools.registry import ToolRegistry


@pytest.fixture
def planner() -> AgentPlanner:
    """Create a planner with empty registries (parsing only, no tool execution)."""
    tool_registry = ToolRegistry(phase=1)
    skill_registry = SkillRegistry(tool_registry)
    return AgentPlanner(skill_registry=skill_registry, memory=None)


class TestParseRequest:
    """Tests for AgentPlanner.parse_request()."""

    def test_unknown_query_defaults_to_server_status(self, planner: AgentPlanner) -> None:
        """An unknown query should default to server status."""
        result = planner.parse_request("hello")
        assert result == ["server_status"]

    def test_server_keyword(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("How is the server?")
        assert "server_status" in result

    def test_cpu_keyword(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("What is the CPU usage?")
        assert "server_status" in result

    def test_memory_keyword(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("Check memory")
        assert "server_status" in result

    def test_disk_keyword(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("Show disk usage")
        assert "server_status" in result

    def test_laravel_keyword(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("How is Laravel?")
        assert "laravel_status" in result

    def test_app_alias(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("Check the app")
        assert "laravel_status" in result

    def test_php_alias(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("PHP version?")
        assert "laravel_status" in result

    def test_database_keyword(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("How is the database?")
        assert "database_status" in result

    def test_db_alias(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("Check DB")
        assert "database_status" in result

    def test_mysql_alias(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("MySQL status")
        assert "database_status" in result

    def test_nginx_keyword(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("What is nginx doing?")
        assert "nginx_status" in result

    def test_web_alias(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("Web server status")
        assert "nginx_status" in result

    def test_all_keyword(self, planner: AgentPlanner) -> None:
        """'all' should expand to all 4 skills."""
        result = planner.parse_request("check all")
        assert result == [
            "server_status",
            "laravel_status",
            "database_status",
            "nginx_status",
        ]

    def test_status_alias_expands_to_all(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("status")
        assert result == [
            "server_status",
            "laravel_status",
            "database_status",
            "nginx_status",
        ]

    def test_full_alias_expands_to_all(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("full check")
        assert result == [
            "server_status",
            "laravel_status",
            "database_status",
            "nginx_status",
        ]

    def test_multiple_keywords_deduplicates(self, planner: AgentPlanner) -> None:
        """Server and CPU both map to server_status — should not duplicate."""
        result = planner.parse_request("server CPU")
        assert result == ["server_status"]

    def test_multiple_distinct_keywords(self, planner: AgentPlanner) -> None:
        """Laravel and DB should return both skills."""
        result = planner.parse_request("Check laravel and database")
        assert set(result) == {"laravel_status", "database_status"}

    def test_case_insensitivity(self, planner: AgentPlanner) -> None:
        result = planner.parse_request("CHECK NGINX AND MYSQL")
        assert set(result) == {"nginx_status", "database_status"}


class TestSkillAliasesIntegrity:
    """Verify all aliases map to valid skills."""

    VALID_SKILLS = {"server_status", "laravel_status", "database_status", "nginx_status", "all"}

    def test_all_aliases_map_to_known_skills(self) -> None:
        for alias, skill_name in SKILL_ALIASES.items():
            assert skill_name in self.VALID_SKILLS, f"Alias '{alias}' maps to unknown skill '{skill_name}'"