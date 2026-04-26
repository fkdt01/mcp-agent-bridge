# MCP Agent Bridge

A lightweight MCP (Model Context Protocol) bridge server that enables **Hermes Agent** and **OpenClaw** to share tools and memory, forming a cooperative multi-agent system.

## Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Hermes     │  MCP    │  Agent Bridge    │  CLI/   │  OpenClaw    │
│   Agent     │◄───────►│  (FastMCP SSE)   │◄───────►│    CLI      │
│              │  client │  Port :18900     │  HTTP   │              │
│  Feishu/WX   │         │                  │         │  Image/Web   │
│  Memory/Plan │         │  Shared Memory   │         │  TTS/Video   │
└─────────────┘         └──────────────────┘         └─────────────┘
```

**Hermes** contributes messaging channels (Feishu, WeChat, Telegram…) and its planning/reasoning capabilities.

**OpenClaw** contributes AI image generation, web search, TTS, and video generation.

**The Bridge** makes each agent's strengths available to the other through standard MCP tool calls, plus a shared SQLite-backed memory store.

## Exposed Tools

| Tool | Direction | Description |
|------|-----------|-------------|
| `oc_image_generate` | OC → Hermes | AI image generation via OpenClaw |
| `oc_web_search` | OC → Hermes | Web search via OpenClaw |
| `oc_web_fetch` | OC → Hermes | URL content extraction via OpenClaw |
| `oc_tts_convert` | OC → Hermes | Text-to-speech via OpenClaw |
| `hermes_send_message` | Hermes → OC | Send messages through Hermes's platforms |
| `hermes_chat` | Hermes → OC | Delegate tasks to Hermes's AI agent |
| `shared_memory_read` | Bidirectional | Read from shared key-value store |
| `shared_memory_write` | Bidirectional | Write to shared key-value store |
| `shared_memory_list_keys` | Bidirectional | List memory keys with optional filters |
| `shared_memory_delete` | Bidirectional | Delete a memory key |
| `bridge_health` | — | Health check and registered module list |

## Quick Start

### Prerequisites

- Python 3.11+
- [Hermes Agent](https://github.com/nicepkg/hermes-agent) with API Server enabled
- [OpenClaw](https://github.com/nicepkg/openclaw) CLI installed and configured
- `pip install "mcp[cli]>=1.0" aiohttp pyyaml`

### Install

```bash
git clone https://github.com/fkdt01/mcp-agent-bridge.git
cd mcp-agent-bridge
pip install -e .
```

### Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml — fill in your API keys and paths
```

Key settings:

```yaml
openclaw:
  cli_path: "openclaw"          # or full path like /usr/local/bin/openclaw
  image_provider: "openai"       # default image gen provider
  web_search_provider: "duckduckgo"

hermes:
  api_url: "http://127.0.0.1:8888"
  api_key: ""                    # or set HERMES_API_KEY env var
  default_channel: "feishu"

memory:
  backend: "sqlite"
  db_path: "data/bridge_memory.db"
```

### Run

```bash
# Start the bridge server
python -m bridge.server

# With custom options
python -m bridge.server --config /path/to/config.yaml --port 18900 --log-level DEBUG
```

### Connect Hermes

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  agent-bridge:
    transport: sse
    url: http://127.0.0.1:18900/sse
```

### Connect OpenClaw

Add to `~/.openclaw/openclaw.json` → `mcpServers`:

```json
{
  "mcpServers": {
    "agent-bridge": {
      "transport": "sse",
      "url": "http://127.0.0.1:18900/sse"
    }
  }
}
```

## Usage Examples

### Hermes generates an image via OpenClaw

When Hermes needs to generate an image (e.g. from a Feishu chat), it calls:

```
oc_image_generate({
  prompt: "A futuristic city at sunset, cyberpunk style",
  aspect_ratio: "16:9",
  model: "openai"
})
```

→ Bridge runs `openclaw capability image generate --prompt "..." --json`
→ Returns image path/metadata to Hermes
→ Hermes delivers the image to the user

### OpenClaw sends a Feishu message via Hermes

```
hermes_send_message({
  message: "✅ Image generation complete!",
  target: "feishu"
})
```

→ Bridge POSTs to Hermes API `/v1/chat/completions`
→ Hermes delivers the message to the Feishu channel

### Shared memory between agents

Hermes writes project context:
```
shared_memory_write({
  key: "project.math-game.pet-design",
  value: "算术小喵: 草原主题, 绿色配色",
  source: "hermes"
})
```

OpenClaw reads it later:
```
shared_memory_read({ key: "project.math-game.pet-design" })
→ { value: "算术小喵: 草原主题, 绿色配色", source: "hermes", updated_at: 1745631000 }
```

## Adding Custom Tools

Create a new file in `bridge/tools/` following the naming convention:

- `oc_*.py` — OpenClaw-backed tools
- `hermes_*.py` — Hermes-backed tools
- `shared_*.py` — Shared/bidirectional tools

Each module must expose a `register(mcp, config)` function:

```python
"""My custom tool."""
from mcp.server.fastmcp import FastMCP
from typing import Any

def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    @mcp.tool()
    async def my_custom_tool(param: str) -> dict[str, Any]:
        """Tool description — this becomes the MCP tool description."""
        # Your implementation here
        return {"result": "ok"}
```

The tool is auto-discovered and registered on server startup.

## Running as a systemd Service

```bash
cat > ~/.config/systemd/user/mcp-agent-bridge.service << 'EOF'
[Unit]
Description=MCP Agent Bridge Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/mcp-agent-bridge
ExecStart=/usr/bin/python -m bridge.server
Restart=on-failure
RestartSec=5
Environment=HERMES_API_KEY=your_key_here

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now mcp-agent-bridge
```

## Project Structure

```
mcp-agent-bridge/
├── bridge/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py              # FastMCP server entry point
│   ├── config.py              # YAML + env-var config loader
│   ├── openclaw_runner.py     # Shared async CLI subprocess runner
│   ├── memory.py              # SQLite-backed shared memory store
│   └── tools/
│       ├── __init__.py         # Auto-discovery & registration
│       ├── oc_image.py         # Image generation
│       ├── oc_web.py           # Web search & fetch
│       ├── oc_tts.py           # Text-to-speech
│       ├── hermes_messaging.py # Message sending
│       ├── hermes_chat.py      # Task delegation
│       └── shared_memory.py    # Shared memory tools
├── config.example.yaml
├── .gitignore
├── LICENSE
├── README.md
└── pyproject.toml
```

## License

MIT