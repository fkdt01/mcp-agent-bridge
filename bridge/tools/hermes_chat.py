"""Hermes chat tool.

Delegates a task or question to Hermes's AI agent for processing,
returning the full response.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    """Register the ``hermes_chat`` tool."""

    @mcp.tool()
    async def hermes_chat(
        message: str,
        *,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a message to Hermes's AI agent and get a response.

        Use this to delegate complex reasoning, coding tasks, or any
        question that benefits from Hermes's planning capabilities and
        tool access (terminal, files, web search, etc.).

        Parameters
        ----------
        message:
            The task or question to send to Hermes.
        system_prompt:
            Optional system prompt to set Hermes's behaviour for this request.
        max_tokens:
            Maximum tokens in the response (default 4096).
        """
        hermes_cfg = config.get("hermes", {})
        api_url = hermes_cfg.get("api_url", "http://127.0.0.1:8888")
        api_key = hermes_cfg.get("api_key", "")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": "hermes-agent",
            "messages": messages,
            "max_tokens": max_tokens,
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("Hermes API error %d: %s", resp.status, body[:300])
                        return {"status": "error", "code": resp.status, "detail": body[:500]}

                    data = await resp.json()
                    reply = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    return {"status": "ok", "response": reply}

        except aiohttp.ClientError as exc:
            logger.exception("Failed to reach Hermes API")
            return {"status": "error", "detail": str(exc)}
