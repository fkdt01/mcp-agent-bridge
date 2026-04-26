"""MCP Agent Bridge — Shared CLI subprocess runner for OpenClaw.

All OC-backed tools delegate here so subprocess logic is centralised.
Includes auto-sync: successful OC call results are written to shared memory
so both Hermes and OpenClaw can recall past OC tool usage.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from typing import Any

logger = logging.getLogger(__name__)


# ── Auto-sync to shared memory ──────────────────────────────────────

def _sync_result_to_memory(
    config: dict[str, Any],
    tool_name: str,
    args: list[str],
    result: dict[str, Any],
) -> None:
    """Write OC tool call result to shared memory (best-effort, non-blocking)."""
    try:
        from bridge.memory import MemoryStore

        mem_cfg = config.get("memory", {})
        db_path = mem_cfg.get("db_path", "data/bridge_memory.db")
        mem = MemoryStore(db_path)

        # Build key: oc_result.<tool_name>.<timestamp_short>
        ts = int(time.time())
        key = f"oc_result.{tool_name}.{ts}"

        # Summarise — store the query/prompt + status, not the full blob
        summary = {
            "tool": tool_name,
            "args_summary": " ".join(args[:6]),  # first 6 tokens
            "status": result.get("status", "unknown"),
            "timestamp": ts,
        }
        # For search: keep result count; for image: keep path; for tts: keep path
        if "results" in result:
            summary["result_count"] = len(result["results"])
        if "output" in result:
            summary["output"] = str(result["output"])[:200]
        if "image_url" in result:
            summary["image_url"] = result["image_url"]
        if "audio_path" in result:
            summary["audio_path"] = result["audio_path"]

        mem.write(key, json.dumps(summary, ensure_ascii=False), source=f"oc-auto:{tool_name}")
        logger.debug("Auto-synced OC result → %s", key)
    except Exception:
        # Never let memory sync failures break the actual tool call
        logger.warning("Failed to auto-sync OC result to shared memory", exc_info=True)


async def run_openclaw(
    args: list[str],
    config: dict[str, Any],
    *,
    timeout: int | None = None,
    tool_name: str = "unknown",
) -> dict[str, Any]:
    """Run an ``openclaw`` CLI subcommand and return parsed JSON output.

    On success the result is automatically synced to shared memory
    (key ``oc_result.<tool_name>.<timestamp>``) so both Hermes and
    OpenClaw can recall past OC tool usage.

    Parameters
    ----------
    args:
        CLI arguments *after* the ``openclaw`` command itself,
        e.g. ``["capability", "web", "search", "--query", "cat"]``.
    config:
        Bridge configuration dict (reads ``openclaw.cli_path`` and
        ``openclaw.timeout``).
    timeout:
        Override timeout in seconds.  Falls back to ``config``.
    tool_name:
        Logical tool name for auto-sync, e.g. ``"oc_web_search"``.

    Returns
    -------
    dict
        Parsed JSON stdout from the subprocess.

    Raises
    ------
    RuntimeError
        If the subprocess exits non-zero or times out.
    """
    oc_cfg = config.get("openclaw", {})
    cli_path = oc_cfg.get("cli_path", "openclaw")
    actual_timeout = timeout or oc_cfg.get("timeout", 60)

    # Ensure the binary is available
    if "/" not in cli_path and not shutil.which(cli_path):
        raise RuntimeError(f"openclaw binary not found in PATH: {cli_path}")

    # Always request JSON output
    if "--json" not in args:
        args.append("--json")

    cmd = [cli_path] + args
    logger.debug("Running: %s (timeout=%ds)", " ".join(cmd), actual_timeout)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=actual_timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"openclaw timed out after {actual_timeout}s: {' '.join(args)}") from None

    stdout = stdout_bytes.decode().strip()
    stderr = stderr_bytes.decode().strip()

    if proc.returncode != 0:
        logger.error("openclaw stderr: %s", stderr)
        raise RuntimeError(
            f"openclaw exited {proc.returncode}: {stderr[:500]}"
        )

    # Parse result
    if not stdout:
        result = {"status": "ok", "raw": False}
    else:
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            result = {"status": "ok", "output": stdout}

    # Auto-sync to shared memory (best-effort)
    _sync_result_to_memory(config, tool_name, args, result)

    return result
