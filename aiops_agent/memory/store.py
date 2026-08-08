"""Memory store — persistent key-value context with TTL via SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryStore:
    """Simple persistent key-value store backed by SQLite.

    Used for:
    - Session context persistence
    - Conversation history
    - Server-specific state
    - Tool execution history
    """

    _instance: MemoryStore | None = None

    def __new__(cls, db_path: str | Path = ":memory:") -> MemoryStore:
        if cls._instance is None:
            instance = super().__new__(cls)
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL,
                        server TEXT DEFAULT ''
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp REAL NOT NULL
                    )
                """)
                conn.commit()
            instance._db_path = str(db_path)
            instance._conn = None
            cls._instance = instance
        return cls._instance

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def set(self, key: str, value: Any, ttl: int | None = None, server: str = "") -> None:
        """Set a key with optional TTL (seconds)."""
        conn = self._get_conn()
        now = time.time()
        expires_at = now + ttl if ttl else None

        conn.execute(
            """
            INSERT OR REPLACE INTO memory (key, value, created_at, expires_at, server)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, json.dumps(value), now, expires_at, server),
        )
        conn.commit()
        logger.debug("Memory set: %s", key)

    def get(self, key: str) -> Any | None:
        """Get a key value, respecting TTL."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value, expires_at FROM memory WHERE key = ?", (key,)
        ).fetchone()

        if row is None:
            return None

        if row["expires_at"] and row["expires_at"] < time.time():
            conn.execute("DELETE FROM memory WHERE key = ?", (key,))
            conn.commit()
            return None

        return json.loads(row["value"])

    def delete(self, key: str) -> None:
        """Delete a key."""
        self._get_conn().execute("DELETE FROM memory WHERE key = ?", (key,))
        self._get_conn().commit()

    def get_by_server(self, server: str) -> list[dict[str, Any]]:
        """Get all keys for a specific server."""
        rows = self._get_conn().execute(
            "SELECT key, value, created_at FROM memory WHERE server = ?", (server,)
        ).fetchall()

        result = []
        for row in rows:
            if json.loads(row["value"]):
                result.append({
                    "key": row["key"],
                    "value": json.loads(row["value"]),
                    "created_at": row["created_at"],
                })
        return result

    def add_history(self, server: str, role: str, content: str) -> None:
        """Add a message to the session conversation history."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO session_history (server, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (server, role, content, time.time()),
        )
        conn.commit()

    def get_history(
        self, server: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get recent conversation history for a server."""
        rows = self._get_conn().execute(
            "SELECT role, content, timestamp FROM session_history WHERE server = ? ORDER BY id DESC LIMIT ?",
            (server, limit),
        ).fetchall()

        return [
            {"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in reversed(rows)
        ]

    def clear_server(self, server: str) -> None:
        """Clear all memory and history for a server."""
        conn = self._get_conn()
        conn.execute("DELETE FROM memory WHERE server = ?", (server,))
        conn.execute("DELETE FROM session_history WHERE server = ?", (server,))
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None