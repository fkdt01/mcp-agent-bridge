"""Shared memory tools.

Provides a durable key-value store that both Hermes and OpenClaw can
read from and write to, enabling cross-agent memory sharing.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from bridge.memory import MemoryStore

# Module-level store instance — initialised once by register().
_store: MemoryStore | None = None


def _get_store(config: dict[str, Any]) -> MemoryStore:
    global _store
    if _store is None:
        mem_cfg = config.get("memory", {})
        _store = MemoryStore(
            db_path=mem_cfg.get("db_path", "data/bridge_memory.db"),
            max_history_per_key=mem_cfg.get("max_history_per_key", 50),
        )
    return _store


def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    """Register ``shared_memory_read`` and ``shared_memory_write`` tools."""

    # Ensure store is initialised at registration time
    _get_store(config)

    @mcp.tool()
    def shared_memory_read(
        key: str,
        *,
        latest: bool = True,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Read a shared memory entry by key.

        Both Hermes and OpenClaw can read entries written by either agent.

        Parameters
        ----------
        key:
            The memory key to look up.
        latest:
            If True (default), return only the most recent entry.
            If False, return up to *limit* historical entries.
        limit:
            Maximum number of entries when *latest* is False (default 10).
        """
        store = _get_store(config)
        return store.read(key, latest=latest, limit=limit)

    @mcp.tool()
    def shared_memory_write(
        key: str,
        value: str,
        *,
        source: str = "unknown",
    ) -> dict[str, Any]:
        """Write a shared memory entry.

        Both Hermes and OpenClaw can write entries readable by the other.

        Parameters
        ----------
        key:
            The memory key (use dot-notation for namespacing,
            e.g. ``"project.math-game.pet-design"``).
        value:
            The value to store (text or JSON string).
        source:
            Identifier of the writer, e.g. ``"hermes"`` or ``"openclaw"``.
        """
        store = _get_store(config)
        return store.write(key, value, source=source)

    @mcp.tool()
    def shared_memory_list_keys(
        *,
        source: str | None = None,
        prefix: str | None = None,
    ) -> dict[str, Any]:
        """List distinct memory keys, optionally filtered by source or prefix.

        Parameters
        ----------
        source:
            Filter by writer source, e.g. ``"hermes"``.
        prefix:
            Filter by key prefix, e.g. ``"project."``.
        """
        store = _get_store(config)
        keys = store.list_keys(source=source, prefix=prefix)
        return {"keys": keys, "count": len(keys)}

    @mcp.tool()
    def shared_memory_delete(key: str) -> dict[str, Any]:
        """Delete all entries for a memory key.

        Parameters
        ----------
        key:
            The memory key to delete.
        """
        store = _get_store(config)
        deleted = store.delete(key)
        return {"key": key, "deleted_count": deleted}
