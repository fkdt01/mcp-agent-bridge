"""OpenClaw image generation tool.

Generates images via OpenClaw's configured image providers.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from bridge.openclaw_runner import run_openclaw


def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    """Register ``oc_image_generate`` tool."""

    @mcp.tool()
    async def oc_image_generate(
        prompt: str,
        *,
        model: str | None = None,
        size: str | None = None,
        output: str | None = None,
    ) -> dict[str, Any]:
        """Generate an image using OpenClaw's image generation capability.

        Parameters
        ----------
        prompt:
            Text description of the image to generate.
        model:
            Model override, e.g. ``"openai/gpt-image-2"``.
        size:
            Size hint, e.g. ``"1024x1024"``.
        output:
            Output file path for the generated image.
        """
        oc_cfg = config.get("openclaw", {})
        args = [
            "capability", "image", "generate",
            "--prompt", prompt,
            "--model", model or oc_cfg.get("image_model", "openai"),
            "--json",
        ]
        if size:
            args.extend(["--size", size])
        if output:
            args.extend(["--output", output])
        return await run_openclaw(args, config, timeout=120, tool_name="oc_image_generate")
