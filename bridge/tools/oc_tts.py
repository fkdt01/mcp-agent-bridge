"""OpenClaw text-to-speech tool.

Converts text to speech via OpenClaw's configured TTS providers.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from bridge.openclaw_runner import run_openclaw


def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    """Register ``oc_tts_convert`` tool."""

    @mcp.tool()
    async def oc_tts_convert(
        text: str,
        *,
        voice: str | None = None,
        model: str | None = None,
        output: str | None = None,
    ) -> dict[str, Any]:
        """Convert text to speech using OpenClaw's TTS capability.

        Parameters
        ----------
        text:
            The text to convert to speech.
        voice:
            Voice identifier hint.
        model:
            Model override, e.g. ``"microsoft"``, ``"openai"``.
        output:
            Output file path for the audio.
        """
        oc_cfg = config.get("openclaw", {})
        args = [
            "capability", "tts", "convert",
            "--text", text,
            "--model", model or oc_cfg.get("tts_provider", "microsoft"),
            "--json",
        ]
        if voice:
            args.extend(["--voice", voice])
        if output:
            args.extend(["--output", output])
        return await run_openclaw(args, config, timeout=60, tool_name="oc_tts_convert")
