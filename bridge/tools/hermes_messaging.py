"""Hermes messaging tool.

Sends messages through Hermes's connected platforms (Feishu, WeChat, etc.)
via the Hermes API Server.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    """Register the ``hermes_send_message`` tool."""

    @mcp.tool()
    async def hermes_send_message(
        message: str,
        *,
        target: str | None = None,
    ) -> dict[str, Any]:
        """Send a message through Hermes's connected messaging platforms.

        This allows OpenClaw to send messages to users via Feishu, WeChat,
        Telegram, or any other platform Hermes is connected to.

        Parameters
        ----------
        message:
            The message text to send.
        target:
            Delivery target, e.g. ``"feishu"``, ``"weixin"``,
            ``"telegram:-1001234567890"``.  Defaults to the configured
            default channel.
        """
        hermes_cfg = config.get("hermes", {})
        api_url = hermes_cfg.get("api_url", "http://127.0.0.1:8888")
        api_key = hermes_cfg.get("api_key", "")
        channel = target or hermes_cfg.get("default_channel", "feishu")

        # Use Hermes's /v1/chat/completions endpoint as a task relay.
        # The message is sent as a user message with a system hint that
        # tells Hermes to deliver it rather than answer it.
        payload = {
            "model": "hermes-relay",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a message relay. Forward the following user "
                        "message to the user exactly as-is via your messaging "
                        "platforms. Do NOT answer or modify the message — "
                        "simply deliver it verbatim and confirm delivery."
                    ),
                },
                {"role": "user", "content": message},
            ],
            "max_tokens": 200,
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
                    timeout=aiohttp.ClientTimeout(total=30),
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
                    return {"status": "ok", "channel": channel, "reply": reply}

        except aiohttp.ClientError as exc:
            logger.exception("Failed to reach Hermes API")
            return {"status": "error", "detail": str(exc)}
