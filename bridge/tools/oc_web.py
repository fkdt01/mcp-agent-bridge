"""OpenClaw web search and fetch tools.

Provides internet search and URL fetching via OpenClaw's CLI.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from bridge.openclaw_runner import run_openclaw


def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    """Register ``oc_web_search`` and ``oc_web_fetch`` tools."""

    @mcp.tool()
    async def oc_web_search(
        query: str,
        *,
        limit: int = 5,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Search the web using OpenClaw's search capability.

        Parameters
        ----------
        query:
            Search query string.
        limit:
            Maximum number of results (default 5).
        provider:
            Search provider override, e.g. ``"duckduckgo"``, ``"perplexity"``.
        """
        oc_cfg = config.get("openclaw", {})
        args = [
            "capability", "web", "search",
            "--query", query,
            "--limit", str(limit),
            "--provider", provider or oc_cfg.get("web_search_provider", "duckduckgo"),
            "--json",
        ]
        return await run_openclaw(args, config, tool_name="oc_web_search")

    @mcp.tool()
    async def oc_web_fetch(
        url: str,
        *,
        format: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Fetch and extract content from a URL using OpenClaw.

        Parameters
        ----------
        url:
            The URL to fetch.
        format:
            Format hint for the output (e.g. ``"markdown"``, ``"text"``).
        provider:
            Fetch provider override.
        """
        args = [
            "capability", "web", "fetch",
            "--url", url,
            "--json",
        ]
        if format:
            args.extend(["--format", format])
        if provider:
            args.extend(["--provider", provider])
        return await run_openclaw(args, config, timeout=90, tool_name="oc_web_fetch")
