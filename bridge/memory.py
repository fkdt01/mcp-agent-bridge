"""MCP Agent Bridge — Shared memory backend (SQLite).

Provides a durable key-value store with source tagging and timestamps,
accessible by both Hermes and OpenClaw through the Bridge Server.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryStore:
    """Thread-safe SQLite-backed shared memory."""

    def __init__(self, db_path: str | Path, max_history_per_key: int = 50) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_history = max_history_per_key
        self._init_db()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    key       TEXT    NOT NULL,
                    value     TEXT    NOT NULL,
                    source    TEXT    NOT NULL DEFAULT 'unknown',
                    created_at REAL   NOT NULL,
                    UNIQUE(key, id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source)"
            )

    def _prune(self, conn: sqlite3.Connection, key: str) -> None:
        """Keep only the latest *max_history* entries for a key."""
        conn.execute(
            """
            DELETE FROM memories
            WHERE key = ? AND id NOT IN (
                SELECT id FROM memories WHERE key = ?
                ORDER BY created_at DESC LIMIT ?
            )
            """,
            (key, key, self.max_history),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, key: str, value: str, source: str = "unknown") -> dict[str, Any]:
        """Write a memory entry.  Returns the stored record."""
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO memories (key, value, source, created_at) VALUES (?, ?, ?, ?)",
                (key, value, source, now),
            )
            self._prune(conn, key)
            conn.commit()

        return {"key": key, "source": source, "updated_at": now}

    def read(
        self,
        key: str,
        *,
        latest: bool = True,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Read memory entries for a key.

        Parameters
        ----------
        key:
            Memory key to look up.
        latest:
            If True, return only the most recent entry.
        limit:
            Maximum number of entries to return (when *latest* is False).
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if latest:
                row = conn.execute(
                    "SELECT value, source, created_at FROM memories WHERE key = ? ORDER BY created_at DESC LIMIT 1",
                    (key,),
                ).fetchone()
                if row is None:
                    return {"key": key, "found": False}
                return {
                    "key": key,
                    "found": True,
                    "value": row["value"],
                    "source": row["source"],
                    "updated_at": row["created_at"],
                }
            else:
                rows = conn.execute(
                    "SELECT value, source, created_at FROM memories WHERE key = ? ORDER BY created_at DESC LIMIT ?",
                    (key, limit),
                ).fetchall()
                return {
                    "key": key,
                    "found": len(rows) > 0,
                    "entries": [
                        {
                            "value": r["value"],
                            "source": r["source"],
                            "updated_at": r["created_at"],
                        }
                        for r in rows
                    ],
                }

    def list_keys(self, source: str | None = None, prefix: str | None = None) -> list[str]:
        """List distinct memory keys, optionally filtered by source or prefix."""
        with self._connect() as conn:
            query = "SELECT DISTINCT key FROM memories WHERE 1=1"
            params: list[str] = []
            if source:
                query += " AND source = ?"
                params.append(source)
            if prefix:
                query += " AND key LIKE ?"
                params.append(f"{prefix}%")
            query += " ORDER BY key"
            return [r[0] for r in conn.execute(query, params).fetchall()]

    def delete(self, key: str) -> int:
        """Delete all entries for a key.  Returns count of deleted rows."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
            return cur.rowcount
