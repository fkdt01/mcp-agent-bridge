"""MCP Agent Bridge — Main entry point.

Starts a FastMCP server over SSE transport, auto-discovers tool plugins,
and serves them to both Hermes and OpenClaw as MCP clients.

Usage:
    python -m bridge.server          # default config
    python -m bridge.server --config /path/to/config.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from bridge.config import load_config
from bridge.tools import discover_and_register

logger = logging.getLogger("bridge")


def build_server(config: dict[str, Any]) -> FastMCP:
    """Build the FastMCP server instance with all tool plugins registered."""
    srv_cfg = config.get("server", {})
    mcp = FastMCP(
        name="mcp-agent-bridge",
        host=srv_cfg.get("host", "127.0.0.1"),
        port=srv_cfg.get("port", 18900),
        log_level="DEBUG" if logging.getLogger().isEnabledFor(logging.DEBUG) else "INFO",
    )

    # Attach config so tools can access it at call time
    mcp._bridge_config = config  # type: ignore[attr-defined]

    # Health-check tool (always available)
    @mcp.tool()
    def bridge_health() -> dict[str, Any]:
        """Check Bridge Server status and list registered tool modules."""
        return {
            "status": "ok",
            "registered_modules": getattr(mcp, "_registered_modules", []),
        }

    # Auto-discover and register tool plugins
    registered = discover_and_register(mcp, config)
    mcp._registered_modules = registered  # type: ignore[attr-defined]
    logger.info("Registered %d tool modules: %s", len(registered), registered)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP Agent Bridge Server")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--host", type=str, default=None, help="Override bind host")
    parser.add_argument("--port", type=int, default=None, help="Override bind port")
    parser.add_argument("--log-level", type=str, default="INFO", help="Log level")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = load_config(args.config)

    # CLI overrides
    if args.host:
        config["server"]["host"] = args.host
    if args.port:
        config["server"]["port"] = args.port

    logger.info(
        "Starting MCP Agent Bridge on %s:%d",
        config["server"]["host"],
        config["server"]["port"],
    )

    server = build_server(config)
    server.run(transport="sse")


if __name__ == "__main__":
    main()
