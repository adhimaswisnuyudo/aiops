"""Interactive REPL for aiops-agent."""

from __future__ import annotations

import asyncio
import sys

from aiops_agent.agent.planner import AgentPlanner
from aiops_agent.config.models import AppConfig
from aiops_agent.tools.ssh import SSHClientPool

BANNER = r"""
   __    _                            
  / _\  (_) ___  _ __  ___   ___ __ _ 
  \ \   | |/ _ \| '_ \/ __| / __/ _` |
  _\ \  | | (_) | |_) \__ \| (_| (_| |
  \__/  |_|\___/| .__/|___(_)___\__,_|
                |_|                    
  AIOps Agent — Phase 1
  Type '/help' for commands, '/quit' to exit.
"""

HELP_TEXT = """
Commands:
  <any text>        — Send a natural language request to the agent
  /skills, /tools   — List available skills/tools
  /server <name>    — Switch to a different server
  /history          — Show conversation history
  /help             — Show this help
  /quit, /exit      — Exit the REPL

Examples:
  "How is the server?"
  "Check Laravel and database status"
  "Show me nginx log errors"
"""


async def start_repl(
    config: AppConfig,
    server_name: str,
    planner: AgentPlanner,
    ssh_pool: SSHClientPool,
) -> None:
    """Run the interactive REPL loop."""
    print(BANNER)

    try:
        server = config.get_server(server_name)
        print(f"Connected to: {server.display_name}")
    except KeyError:
        print(f"Warning: Server '{server_name}' not found in config")
        if config.servers:
            server_name = config.servers[0].name
            server = config.servers[0]
            print(f"Falling back to: {server.display_name}")

    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not line:
            continue

        # Handle slash commands
        if line.startswith("/"):
            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("/quit", "/exit"):
                print("Goodbye!")
                break
            elif cmd == "/help":
                print(HELP_TEXT)
            elif cmd in ("/skills", "/tools"):
                if cmd == "/skills":
                    skills = planner.get_available_skills()
                    print("Available skills:")
                    for s in skills:
                        print(f"  {s['name']:20s} — {s['description']}")
                else:
                    skills = planner.get_available_skills()
                    print("Available tools (use /skills for grouped views):")
                    for s in skills:
                        print(f"  {s['name']:20s} — {s['description']}")
            elif cmd == "/server" and arg:
                try:
                    server = config.get_server(arg)
                    server_name = arg
                    print(f"Switched to: {server.display_name}")
                except KeyError:
                    names = [s.name for s in config.servers]
                    print(f"Server '{arg}' not found. Available: {', '.join(names)}")
            elif cmd == "/server":
                names = [s.name for s in config.servers]
                print(f"Available servers: {', '.join(names)}")
                print(f"Current: {server_name}")
            elif cmd == "/history":
                history = planner.get_history(server_name, limit=20)
                if not history:
                    print("No conversation history.")
                else:
                    for msg in history:
                        role = "YOU" if msg["role"] == "user" else "AI"
                        print(f"\n--- [{role}] ---")
                        print(msg["content"][:500])
            else:
                print(f"Unknown command: {cmd}. Type /help for available commands.")
            continue

        # Send natural language request
        try:
            result = await planner.execute(
                text=line,
                server_name=server_name,
                server_host=server.host,
                environment=server.environment,
            )
            print(f"\n{result['summary']}")

            for skill_name, skill_result in result["results"].items():
                if not skill_result["success"]:
                    print(
                        f"\n[WARN] {skill_name} failed: {skill_result.get('error', '')}",
                        file=sys.stderr,
                    )
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)

    # Cleanup
    await ssh_pool.disconnect_all()