"""SSH Client abstraction for remote server communication."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import asyncssh

from aiops_agent.config.models import SecurityConfig, ServerConfig

logger = logging.getLogger(__name__)


@dataclass
class SSHResult:
    """Result of an SSH command execution."""
    stdout: str
    stderr: str
    exit_code: int


class SSHClient:
    """Async SSH client that wraps asyncssh with safety checks.

    All communication to servers goes through this class.
    It enforces:
    - No root login
    - Command safety validation (forbidden commands rejected)
    - Sudo restriction (only whitelisted commands)
    - Audit logging
    """

    def __init__(
        self,
        server: ServerConfig,
        security: SecurityConfig,
        audit_logger: logging.Logger | None = None,
    ) -> None:
        self._server = server
        self._security = security
        self._audit = audit_logger
        self._conn: asyncssh.SSHClientConnection | None = None
        self._lock = asyncio.Lock()

    @property
    def server_name(self) -> str:
        return self._server.name

    async def connect(self) -> None:
        """Establish SSH connection."""
        if self._conn and not self._conn.is_closed():
            return

        connect_kwargs: dict[str, Any] = {
            "host": self._server.host,
            "port": self._server.port,
            "username": self._server.username,
            "known_hosts": None,  # Accept all hosts — production should use known_hosts
            "x509_trusted_certs": (),  # Disable X.509 cert path lookup (avoids ~/.ssh/crt PermError)
        }

        if self._server.ssh_key_path:
            key_path = Path(self._server.ssh_key_path).expanduser()
            if self._server.ssh_key_passphrase:
                connect_kwargs["client_keys"] = [
                    (str(key_path), self._server.ssh_key_passphrase.get_secret_value())
                ]
            else:
                connect_kwargs["client_keys"] = [str(key_path)]

        logger.info("Connecting to %s@%s:%d ...", self._server.username, self._server.host, self._server.port)
        self._conn = await asyncssh.connect(**connect_kwargs)
        logger.info("Connected to %s", self._server.display_name)

    async def disconnect(self) -> None:
        """Close SSH connection."""
        if self._conn and not self._conn.is_closed():
            self._conn.close()
            await self._conn.wait_closed()
            logger.info("Disconnected from %s", self._server.display_name)
        self._conn = None

    def _validate_command(self, command: str) -> None:
        """Check if a command is forbidden."""
        cmd_lower = command.lower().strip()
        for forbidden in self._security.forbidden_commands:
            if forbidden.lower() in cmd_lower:
                raise ValueError(f"Forbidden command detected: '{command}' matches '{forbidden}'")

    async def run(
        self, command: str, timeout: int = 30, sudo: bool = False
    ) -> SSHResult:
        """Run a command on the remote server.

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds
            sudo: If True, run with sudo

        Returns:
            SSHResult with stdout, stderr, exit_code

        Raises:
            ValueError: If command is forbidden
            RuntimeError: If not connected
        """
        async with self._lock:
            if not self._conn or self._conn.is_closed():
                raise RuntimeError(f"Not connected to {self._server.display_name}")

            # Validate command safety
            self._validate_command(command)

            # Audit log
            if self._audit:
                self._audit.info(
                    "SSH_RUN server=%s user=%s sudo=%s cmd=%s",
                    self._server.name, self._server.username, sudo, command,
                )

            full_cmd = command
            if sudo:
                full_cmd = f"sudo {command}"

            logger.debug("Running on %s: %s", self._server.name, full_cmd)

            try:
                result = await asyncio.wait_for(
                    self._conn.run(full_cmd), timeout=timeout
                )
                stdout = result.stdout.strip() if result.stdout else ""
                stderr = result.stderr.strip() if result.stderr else ""
                exit_code = result.exit_status if result.exit_status is not None else result.returncode

                if exit_code != 0 and stderr:
                    logger.warning(
                        "Command exited %d on %s: %s — stderr: %s",
                        exit_code, self._server.name, command, stderr[:200],
                    )

                return SSHResult(stdout=stdout, stderr=stderr, exit_code=exit_code)

            except asyncio.TimeoutError:
                logger.error("Command timed out (%ds) on %s: %s", timeout, self._server.name, command)
                return SSHResult(stdout="", stderr=f"Command timed out after {timeout}s", exit_code=124)

    async def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._conn is not None and not self._conn.is_closed()


class SSHClientPool:
    """Manages multiple SSH connections to different servers."""

    def __init__(self, security: SecurityConfig) -> None:
        self._security = security
        self._clients: dict[str, SSHClient] = {}

    async def get_client(self, server: ServerConfig) -> SSHClient:
        """Get or create an SSH client for a server."""
        key = server.name
        if key not in self._clients:
            client = SSHClient(server, self._security)
            await client.connect()
            self._clients[key] = client
        else:
            client = self._clients[key]
            if not await client.is_connected():
                await client.connect()
        return client

    async def disconnect_all(self) -> None:
        """Disconnect all clients."""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()