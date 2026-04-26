"""MCP Agent Bridge — Tool plugin system.

Tools are auto-discovered from the ``bridge/tools/`` directory.
Each tool module must expose a ``register(mcp, config)`` function.

Convention:
  - File name ``oc_*.py``  → OpenClaw-backed tools
  - File name ``hermes_*.py`` → Hermes-backed tools
  - File name ``shared_*.py`` → Shared / bidirectional tools
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ``bridge/tools/`` is both this package and the discovery directory.
TOOLS_DIR = Path(__file__).resolve().parent


def discover_and_register(mcp: FastMCP, config: dict[str, Any]) -> list[str]:
    """Scan ``bridge/tools/`` and register every tool module.

    Returns a list of registered module names for diagnostics.
    """
    registered: list[str] = []

    if not TOOLS_DIR.is_dir():
        logger.warning("Tools directory not found: %s", TOOLS_DIR)
        return registered

    for py_file in sorted(TOOLS_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        module_name = f"bridge.tools.{py_file.stem}"
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            logger.exception("Failed to import tool module: %s", module_name)
            continue

        register_fn = getattr(mod, "register", None)
        if not callable(register_fn):
            logger.warning("Module %s has no register(mcp, config) function — skipping", module_name)
            continue

        try:
            register_fn(mcp, config)
            registered.append(py_file.stem)
            logger.info("Registered tool module: %s", py_file.stem)
        except Exception:
            logger.exception("Error registering tool module: %s", module_name)

    return registered
