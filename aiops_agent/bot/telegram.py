"""Telegram Bot — bridges Telegram messages to the AIOps Agent planner."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

from aiops_agent.agent.planner import AgentPlanner
from aiops_agent.config.models import AppConfig, TelegramConfig
from aiops_agent.tools.ssh import SSHClientPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lightweight Telegram HTTP client (no third-party dependency required)
# ---------------------------------------------------------------------------

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


class TelegramAPIError(Exception):
    """Raised when the Telegram API returns an error."""


class TelegramAPI:
    """Minimal async wrapper around the Telegram Bot API."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self, token: str) -> None:
        self._token = token
        self._base = f"{self.BASE_URL}/bot{token}"

    async def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if httpx is None:
            raise ImportError("httpx is required for Telegram bot support. Install with: pip install httpx")
        url = f"{self._base}/{method}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=params or {})
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise TelegramAPIError(data.get("description", "Unknown error"))
            return data

    async def get_me(self) -> dict[str, Any]:
        return (await self._request("getMe"))["result"]

    async def get_updates(
        self, offset: int | None = None, timeout: int = 60
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset
        return (await self._request("getUpdates", params))["result"]

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_to_message_id:
            params["reply_to_message_id"] = reply_to_message_id
        return (await self._request("sendMessage", params))["result"]

    async def set_webhook(self, url: str) -> dict[str, Any]:
        return (await self._request("setWebhook", {"url": url}))["result"]

    async def delete_webhook(self) -> dict[str, Any]:
        return (await self._request("deleteWebhook"))["result"]

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> dict[str, Any]:
        return (await self._request("sendChatAction", {"chat_id": chat_id, "action": action}))["result"]


# ---------------------------------------------------------------------------
# Telegram Bot
# ---------------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 4000  # Telegram limit is 4096 — leave some buffer
START_MESSAGE = """🤖 *AIOps Agent* — AI-powered DevOps assistant

I can check your servers via SSH. Just send me a message like:

• `check all` — run all checks
• `check server` — CPU, memory, disk
• `check laravel` — Laravel status
• `check database` — MySQL status
• `check nginx` — Nginx status

*Commands:*
/status — same as `check all`
/servers — list configured servers
/server <name> — switch to a different server
/help — show this message"""

HELP_TEXT = """📖 *AIOps Agent Help*

*Natural language queries:*
• `check all` or `status` — run every skill
• `check server` — system health (uptime, CPU, memory, disk)
• `check laravel` — Laravel + PHP info
• `check database` — MySQL process list, slow queries
• `check nginx` — status, config test, error logs
• `How is the server?` — same as `check server`
• Combine: `Check laravel and database`

*Commands:*
/status — full system check
/servers — list servers
/server <name> — switch server
/help — show this message"""


class TelegramBot:
    """Long-running Telegram bot that bridges chat messages to the agent."""

    def __init__(
        self,
        token: str,
        planner: AgentPlanner,
        ssh_pool: SSHClientPool,
        config: AppConfig,
        tg_config: TelegramConfig,
    ) -> None:
        self._api = TelegramAPI(token)
        self._planner = planner
        self._ssh_pool = ssh_pool
        self._config = config
        self._tg_config = tg_config

        # Per-chat state
        self._server_name: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _is_allowed(self, user_id: int) -> bool:
        allowed = self._tg_config.allowed_users
        if not allowed:  # empty = allow everyone
            return True
        return user_id in allowed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_server_name(self, chat_id: int) -> str:
        """Resolve server name for a chat, falling back to default."""
        if chat_id in self._server_name:
            return self._server_name[chat_id]
        if self._config.default_server:
            return self._config.default_server
        if self._config.servers:
            return self._config.servers[0].name
        return "default"

    def _truncate(self, text: str, max_len: int = MAX_MESSAGE_LENGTH) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "…"

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def _handle_message(self, msg: dict[str, Any]) -> list[tuple[int, str]]:
        user = msg.get("from", {})
        chat = msg.get("chat", {})
        chat_id = chat.get("id", 0)
        user_id = user.get("id", 0)
        text = (msg.get("text") or "").strip()

        responses: list[tuple[int, str]] = []

        if not self._is_allowed(user_id):
            responses.append((chat_id, "⛔ You are not authorized to use this bot."))
            return responses

        if not text:
            return responses

        # --- Slash commands ---
        if text.startswith("/"):
            responses = await self._handle_command(chat_id, user_id, text)
            return responses

        # --- Natural language query ---
        responses = await self._handle_query(chat_id, text)
        return responses

    async def _handle_command(
        self, chat_id: int, user_id: int, text: str
    ) -> list[tuple[int, str]]:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().lstrip("/")
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "start":
            return [(chat_id, START_MESSAGE)]

        elif cmd == "help":
            return [(chat_id, HELP_TEXT)]

        elif cmd == "servers":
            lines = ["🖥 *Configured Servers:*"]
            current = self._get_server_name(chat_id)
            for s in self._config.servers:
                marker = "  ← current" if s.name == current else ""
                lines.append(f"  • `{s.name}` — {s.host} ({s.environment}){marker}")
            return [(chat_id, "\n".join(lines))]

        elif cmd == "server":
            if not arg:
                current = self._get_server_name(chat_id)
                names = [s.name for s in self._config.servers]
                return [(chat_id, f"Current: `{current}`\nAvailable: {', '.join(f'`{n}`' for n in names)}\nUsage: `/server <name>`")]
            try:
                server = self._config.get_server(arg)
                self._server_name[chat_id] = arg
                return [(chat_id, f"✅ Switched to *{server.name}* ({server.host}) [{server.environment}]")]
            except KeyError:
                names = [s.name for s in self._config.servers]
                return [(chat_id, f"❌ Server `{arg}` not found.\nAvailable: {', '.join(f'`{n}`' for n in names)}")]

        elif cmd == "status":
            return await self._handle_query(chat_id, "check all")

        else:
            return [(chat_id, f"Unknown command: `/{cmd}`. Type /help for available commands.")]

    async def _handle_query(
        self, chat_id: int, text: str
    ) -> list[tuple[int, str]]:
        server_name = self._get_server_name(chat_id)

        try:
            server = self._config.get_server(server_name)
        except KeyError:
            return [(chat_id, "❌ No server configured. Add servers to `config.yaml` first.")]

        ssh_client = await self._ssh_pool.get_client(server)
        try:
            result = await self._planner.execute(
                text=text,
                server_name=server.name,
                server_host=server.host,
                environment=server.environment,
                ssh_client=ssh_client,
            )
        except Exception as exc:
            logger.exception("Agent execution failed")
            return [(chat_id, f"❌ Error: {exc}")]

        # Build response
        header = f"📊 *{server.display_name}*"
        skills_ran = ", ".join(f"`{s}`" for s in result["skills_executed"])

        response_parts = [header, f"_Skills: {skills_ran}_", "", result["summary"]]

        # Append per-skill error summary
        errors = [
            f"⚠️ `{sn}`: {sr.get('error', 'unknown')}"
            for sn, sr in result["results"].items()
            if not sr["success"]
        ]
        if errors:
            response_parts.append("\n" + "\n".join(errors))

        full_response = "\n".join(response_parts)
        truncated = self._truncate(full_response)

        return [(chat_id, truncated)]

    # ------------------------------------------------------------------
    # Polling loop
    # ------------------------------------------------------------------

    async def start_polling(self) -> None:
        """Start long-polling loop (runs until cancelled)."""
        me = await self._api.get_me()
        logger.info("Bot started: @%s (ID: %s)", me.get("username"), me.get("id"))

        # Clear any existing webhook
        await self._api.delete_webhook()
        logger.info("Webhook cleared, entering polling mode")

        offset: int | None = None

        while True:
            try:
                updates = await self._api.get_updates(offset=offset, timeout=60)
                for update in updates:
                    offset = update["update_id"] + 1
                    if "message" not in update:
                        continue

                    msg = update["message"]
                    chat_id = msg.get("chat", {}).get("id", 0)

                    # Show typing indicator
                    try:
                        await self._api.send_chat_action(chat_id, "typing")
                    except Exception:
                        pass

                    responses = await self._handle_message(msg)
                    for resp_chat_id, text in responses:
                        try:
                            await self._api.send_message(
                                resp_chat_id, text, parse_mode="Markdown"
                            )
                        except TelegramAPIError:
                            # Retry without Markdown if parsing fails
                            await self._api.send_message(resp_chat_id, text)

            except asyncio.CancelledError:
                logger.info("Polling cancelled, shutting down")
                break
            except TelegramAPIError as e:
                logger.error("Telegram API error: %s", e)
                await asyncio.sleep(5)
            except Exception:
                logger.exception("Unexpected error in polling loop")
                await asyncio.sleep(5)

    async def start_webhook(self, url: str, port: int) -> None:
        """Webhook mode — requires a reverse proxy or direct TLS termination."""
        if httpx is None:
            raise ImportError("httpx is required for webhook mode")

        me = await self._api.get_me()
        logger.info("Bot started: @%s (ID: %s)", me.get("username"), me.get("id"))

        await self._api.set_webhook(url)
        logger.info("Webhook set to %s", url)

        # Minimal aiohttp-based webhook server
        try:
            from aiohttp import web  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "aiohttp is required for webhook mode. Install: pip install aiohttp"
            )
            raise

        async def handle_webhook(request: web.Request) -> web.Response:
            try:
                update = await request.json()
            except Exception:
                return web.Response(status=400, text="Bad Request")

            if "message" in update:
                msg = update["message"]
                chat_id = msg.get("chat", {}).get("id", 0)

                try:
                    await self._api.send_chat_action(chat_id, "typing")
                except Exception:
                    pass

                responses = await self._handle_message(msg)
                for resp_chat_id, text in responses:
                    try:
                        await self._api.send_message(
                            resp_chat_id, text, parse_mode="Markdown"
                        )
                    except TelegramAPIError:
                        await self._api.send_message(resp_chat_id, text)

            return web.Response(status=200, text="ok")

        app = web.Application()
        app.router.add_post(f"/bot{self._api._token}", handle_webhook)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        logger.info("Webhook server listening on port %s", port)
        await site.start()

        # Keep alive
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Webhook server shutting down")
        finally:
            await runner.cleanup()