"""CLI entry point for aiops-agent."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

from aiops_agent.agent.planner import AgentPlanner
from aiops_agent.config.models import AppConfig, SecurityConfig, ServerConfig
from aiops_agent.memory.store import MemoryStore
from aiops_agent.skills.registry import SkillRegistry
from aiops_agent.skills.server_status import ServerStatusSkill
from aiops_agent.skills.laravel_status import LaravelStatusSkill
from aiops_agent.skills.database_status import DatabaseStatusSkill
from aiops_agent.skills.nginx_status import NginxStatusSkill
from aiops_agent.tools.base import BaseTool
from aiops_agent.tools.docker import DockerTool
from aiops_agent.tools.git import GitTool
from aiops_agent.tools.laravel import LaravelTool
from aiops_agent.tools.mysql import MySQLTool
from aiops_agent.tools.nginx import NginxTool
from aiops_agent.tools.php import PHPTool
from aiops_agent.tools.registry import ToolRegistry
from aiops_agent.tools.ssh import SSHClientPool
from aiops_agent.tools.system import SystemTool

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def load_config(path: Path) -> AppConfig:
    """Load AppConfig from YAML file with env var overrides, or return default."""
    if path.exists():
        return AppConfig.from_yaml_with_env(path)

    # Return a minimal default config
    return AppConfig(
        servers=[
            ServerConfig(
                name="default",
                host="localhost",
                environment="staging",
            )
        ],
        security=SecurityConfig(),
    )


def build_registry(security: SecurityConfig) -> tuple[ToolRegistry, SSHClientPool]:
    """Build tool registry and SSH client pool."""
    ssh_pool = SSHClientPool(security=security)
    tool_registry = ToolRegistry(phase=1)

    tools: list[BaseTool] = [
        SystemTool(),
        NginxTool(),
        PHPTool(),
        MySQLTool(),
        LaravelTool(),
        DockerTool(),
        GitTool(),
    ]
    tool_registry.register_many(tools)

    return tool_registry, ssh_pool


def build_skill_registry(tool_registry: ToolRegistry) -> SkillRegistry:
    """Build and populate skill registry."""
    skill_registry = SkillRegistry(tool_registry)

    skills = [
        ServerStatusSkill(tool_registry),
        LaravelStatusSkill(tool_registry),
        DatabaseStatusSkill(tool_registry),
        NginxStatusSkill(tool_registry),
    ]
    skill_registry.register_all(skills)

    return skill_registry


async def run_agent(
    text: str,
    config: AppConfig,
    server_name: str,
    planner: AgentPlanner,
    ssh_pool: SSHClientPool,
    output_format: str = "text",
) -> None:
    """Run the agent with a natural language request."""
    try:
        server = config.get_server(server_name)
    except KeyError:
        names = [s.name for s in config.servers]
        print(f"Error: Server '{server_name}' not found in config", file=sys.stderr)
        print(f"Available servers: {', '.join(names)}", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to {server.name} ({server.host})...")

    # Get SSH client for this server
    ssh_client = await ssh_pool.get_client(server)

    result = await planner.execute(
        text=text,
        server_name=server.name,
        server_host=server.host,
        environment=server.environment,
    )

    if output_format == "json":
        import json

        serializable: dict[str, object] = {
            "success": result["success"],
            "skills_executed": result["skills_executed"],
            "results": result["results"],
        }
        print(json.dumps(serializable, indent=2))
    else:
        print(result["summary"])

        for skill_name, skill_result in result["results"].items():
            if not skill_result["success"]:
                print(
                    f"\n[WARN] {skill_name} had errors: {skill_result.get('error', '')}",
                    file=sys.stderr,
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="aiops-agent — LLM-powered server management agent"
    )
    parser.add_argument("request", nargs="?", help="Natural language request")
    parser.add_argument(
        "-s", "--server", default=None, help="Server name from config"
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "-f", "--format", choices=["text", "json"], default="text", help="Output format"
    )
    parser.add_argument(
        "-l", "--list-skills", action="store_true", help="List available skills"
    )
    parser.add_argument(
        "-L", "--list-tools", action="store_true", help="List available tools"
    )
    parser.add_argument(
        "-H", "--history", action="store_true", help="Show conversation history"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )
    parser.add_argument(
        "--db", default=":memory:", help="Memory database path (default: in-memory)"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Load config
    config = load_config(Path(args.config))

    # Determine target server
    if args.server:
        server_name = args.server
    elif config.default_server:
        server_name = config.default_server
    elif config.servers:
        server_name = config.servers[0].name
    else:
        print("Error: No servers configured", file=sys.stderr)
        sys.exit(1)

    # Build registries
    tool_registry, ssh_pool = build_registry(config.security)
    skill_registry = build_skill_registry(tool_registry)

    # Setup memory
    memory = MemoryStore(db_path=args.db)

    # Build planner
    planner = AgentPlanner(skill_registry=skill_registry, memory=memory)

    # Handle info commands
    if args.list_skills:
        print("Available skills:")
        for skill in skill_registry.list_skills():
            print(f"  {skill['name']:20s} — {skill['description']}")
        return

    if args.list_tools:
        print("Available tools:")
        for tool in tool_registry.list_tools():
            print(f"  {tool['name']:25s} — {tool['description']}")
        return

    if args.history:
        history = planner.get_history(server_name, limit=30)
        if not history:
            print("No conversation history.")
        else:
            for msg in history:
                role_tag = "YOU" if msg["role"] == "user" else "AGENT"
                print(f"\n[{role_tag}]: {msg['content'][:200]}...")
        return

    if args.request:
        asyncio.run(
            run_agent(
                args.request,
                config,
                server_name,
                planner,
                ssh_pool,
                args.format,
            )
        )
    else:
        # Interactive REPL mode
        from aiops_agent.cli.repl import start_repl

        asyncio.run(start_repl(config, server_name, planner, ssh_pool))


def bot() -> None:
    """Entry point: aiops bot"""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="aiops-agent bot — Telegram Bot mode"
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--token", default=None, help="Telegram bot token (overrides env var)"
    )
    parser.add_argument(
        "--webhook", action="store_true", help="Run in webhook mode (default: long polling)"
    )
    parser.add_argument(
        "--webhook-url", default=None, help="Webhook URL (e.g. https://example.com/bot<token>)"
    )
    parser.add_argument(
        "--webhook-port", type=int, default=8443, help="Webhook listen port (default: 8443)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Load config
    config = load_config(Path(args.config))

    # Get Telegram config (read from config.yaml telegram: section)
    import yaml
    raw = yaml.safe_load(Path(args.config).read_text())
    tg_raw = raw.get("telegram", {}) if isinstance(raw, dict) else {}
    from aiops_agent.config.models import TelegramConfig
    tg_config = TelegramConfig(**tg_raw) if tg_raw else TelegramConfig()

    if not tg_config.enabled:
        print("Error: Telegram bot is not enabled in config (telegram.enabled: false)", file=sys.stderr)
        print("Set telegram.enabled: true in config.yaml", file=sys.stderr)
        sys.exit(1)

    # Resolve token
    token = args.token or os.getenv(tg_config.token_env)
    if not token:
        print(
            f"Error: No Telegram bot token provided. Set {tg_config.token_env} env var or pass --token",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build registries
    tool_registry, ssh_pool = build_registry(config.security)
    skill_registry = build_skill_registry(tool_registry)
    memory = MemoryStore()
    planner = AgentPlanner(skill_registry=skill_registry, memory=memory)

    # Resolve default server
    if config.default_server:
        server_name = config.default_server
    elif config.servers:
        server_name = config.servers[0].name
    else:
        server_name = "default"

    # Build bot
    from aiops_agent.bot.telegram import TelegramBot

    bot_instance = TelegramBot(
        token=token,
        planner=planner,
        ssh_pool=ssh_pool,
        config=config,
        tg_config=tg_config,
    )

    print(f"🤖 AIOps Agent Telegram Bot starting...")
    print(f"   Mode: {'Webhook' if args.webhook else 'Long Polling'}")
    if config.servers:
        print(f"   Servers: {', '.join(s.name for s in config.servers)}")
    if tg_config.allowed_users:
        print(f"   Allowed users: {tg_config.allowed_users}")

    # Run bot
    async def run_bot():
        if args.webhook:
            webhook_url = args.webhook_url or tg_config.webhook_url
            if not webhook_url:
                print("Error: --webhook-url is required in webhook mode", file=sys.stderr)
                sys.exit(1)
            await bot_instance.start_webhook(webhook_url, args.webhook_port or tg_config.webhook_port)
        else:
            await bot_instance.start_polling()

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nBot stopped.")
    finally:
        asyncio.run(ssh_pool.disconnect_all())


if __name__ == "__main__":
    main()