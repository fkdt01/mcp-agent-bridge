"""MCP Agent Bridge — Configuration loader.

Search order: ``config.yaml`` in the project root, then environment variables.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file with env-var overrides.

    Environment variables take precedence over the YAML file:
      ``BRIDGE_SERVER_PORT`` → server.port
      ``BRIDGE_OPENCLAW_CLI`` → openclaw.cli_path
      ``BRIDGE_HERMES_API_URL`` → hermes.api_url
      ``HERMES_API_KEY`` → hermes.api_key
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH

    if config_path.exists():
        with open(config_path) as f:
            config: dict[str, Any] = yaml.safe_load(f) or {}
        logger.info("Loaded config from %s", config_path)
    else:
        config = {}
        logger.warning("Config file not found at %s — using defaults + env vars", config_path)

    # Defaults
    config.setdefault("server", {})
    config["server"].setdefault("host", "127.0.0.1")
    config["server"].setdefault("port", 18900)

    config.setdefault("openclaw", {})
    config["openclaw"].setdefault("cli_path", "openclaw")
    config["openclaw"].setdefault("timeout", 60)
    config["openclaw"].setdefault("image_provider", "openai")
    config["openclaw"].setdefault("web_search_provider", "duckduckgo")

    config.setdefault("hermes", {})
    config["hermes"].setdefault("api_url", "http://127.0.0.1:8888")
    config["hermes"].setdefault("api_key", "")
    config["hermes"].setdefault("default_channel", "feishu")

    config.setdefault("memory", {})
    config["memory"].setdefault("backend", "sqlite")
    config["memory"].setdefault("db_path", str(PROJECT_ROOT / "data" / "bridge_memory.db"))
    config["memory"].setdefault("max_history_per_key", 50)

    # Environment variable overrides
    if v := os.getenv("BRIDGE_SERVER_PORT"):
        config["server"]["port"] = int(v)
    if v := os.getenv("BRIDGE_OPENCLAW_CLI"):
        config["openclaw"]["cli_path"] = v
    if v := os.getenv("BRIDGE_HERMES_API_URL"):
        config["hermes"]["api_url"] = v
    if v := os.getenv("HERMES_API_KEY"):
        config["hermes"]["api_key"] = v

    return config
