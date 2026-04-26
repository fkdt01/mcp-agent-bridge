# MCP Agent Bridge 🌉

[English](README.md) | 中文

一个轻量级 MCP (Model Context Protocol) 桥接服务器，让 **Hermes Agent** 和 **OpenClaw** 共享工具和记忆，形成协作多智能体系统。

## 架构

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Hermes     │  MCP    │  Agent Bridge    │  CLI/   │  OpenClaw    │
│   Agent     │◄───────►│  (FastMCP SSE)   │◄───────►│    CLI      │
│              │  客户端  │  端口 :18900     │  HTTP   │              │
│  飞书/微信    │         │                  │         │  图片/搜索    │
│  记忆/规划    │         │   共享记忆库      │         │  语音/视频    │
└─────────────┘         └──────────────────┘         └─────────────┘
```

**Hermes** 贡献消息通道（飞书、微信、Telegram…）和规划推理能力。

**OpenClaw** 贡献 AI 图片生成、网络搜索、语音合成、视频生成。

**Bridge** 通过标准 MCP 工具调用让两个 Agent 的能力互通，并提供 SQLite 共享记忆库。

## 工具清单

| 工具 | 方向 | 说明 |
|------|------|------|
| `oc_image_generate` | OC → Hermes | 通过 OpenClaw 生成 AI 图片 |
| `oc_web_search` | OC → Hermes | 通过 OpenClaw 搜索网络 |
| `oc_web_fetch` | OC → Hermes | 通过 OpenClaw 抓取网页内容 |
| `oc_tts_convert` | OC → Hermes | 通过 OpenClaw 文字转语音 |
| `hermes_send_message` | Hermes → OC | 通过 Hermes 发送消息 |
| `hermes_chat` | Hermes → OC | 委托任务给 Hermes |
| `shared_memory_read` | 双向 | 读取共享记忆 |
| `shared_memory_write` | 双向 | 写入共享记忆 |
| `shared_memory_list_keys` | 双向 | 列出记忆键 |
| `shared_memory_delete` | 双向 | 删除记忆键 |
| `bridge_health` | — | 健康检查 |

## 快速开始

### 前置条件

- Python 3.11+
- [Hermes Agent](https://github.com/nicepkg/hermes-agent) 已启用 API Server
- [OpenClaw](https://github.com/nicepkg/openclaw) CLI 已安装配置
- `pip install "mcp[cli]>=1.0" aiohttp pyyaml`

### 安装

```bash
git clone https://github.com/nicepkg/mcp-agent-bridge.git
cd mcp-agent-bridge
pip install -e .
```

### 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的 API Key 和路径
```

关键配置：

```yaml
openclaw:
  cli_path: "openclaw"          # 或完整路径
  image_provider: "openai"       # 图片生成提供商
  web_search_provider: "duckduckgo"

hermes:
  api_url: "http://127.0.0.1:8888"
  api_key: ""                    # 或设置 HERMES_API_KEY 环境变量
  default_channel: "feishu"

memory:
  backend: "sqlite"
  db_path: "data/bridge_memory.db"
```

### 运行

```bash
# 启动桥接服务器
python -m bridge.server

# 自定义选项
python -m bridge.server --config /path/to/config.yaml --port 18900 --log-level DEBUG
```

### 连接 Hermes

在 `~/.hermes/config.yaml` 中添加：

```yaml
mcp_servers:
  agent-bridge:
    transport: sse
    url: http://127.0.0.1:18900/sse
```

### 连接 OpenClaw

在 `~/.openclaw/openclaw.json` 的 `mcpServers` 中添加：

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

## 使用示例

### Hermes 通过 OpenClaw 生成图片

```
oc_image_generate({
  prompt: "赛博朋克风格的未来城市，日落时分",
  aspect_ratio: "16:9",
  model: "openai"
})
```

→ Bridge 执行 `openclaw capability image generate --prompt "..." --json`
→ 返回图片路径给 Hermes
→ Hermes 将图片发送给用户

### OpenClaw 通过 Hermes 发送飞书消息

```
hermes_send_message({
  message: "✅ 图片生成完成！",
  target: "feishu"
})
```

→ Bridge 调用 Hermes API
→ Hermes 发送消息到飞书频道

### Agent 间共享记忆

Hermes 写入项目上下文：
```
shared_memory_write({
  key: "project.math-game.pet-design",
  value: "算术小喵: 草原主题, 绿色配色",
  source: "hermes"
})
```

OpenClaw 稍后读取：
```
shared_memory_read({ key: "project.math-game.pet-design" })
→ { value: "算术小喵: 草原主题, 绿色配色", source: "hermes", updated_at: 1745631000 }
```

## 添加自定义工具

在 `bridge/tools/` 下创建新文件：

- `oc_*.py` — OpenClaw 相关工具
- `hermes_*.py` — Hermes 相关工具
- `shared_*.py` — 双向共享工具

每个模块必须导出 `register(mcp, config)` 函数：

```python
"""我的自定义工具."""
from mcp.server.fastmcp import FastMCP
from typing import Any

def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    @mcp.tool()
    async def my_custom_tool(param: str) -> dict[str, Any]:
        """工具描述 — 会成为 MCP 工具说明."""
        return {"result": "ok"}
```

工具会自动发现并注册。

## 作为 systemd 服务运行

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

## 项目结构

```
mcp-agent-bridge/
├── bridge/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py              # FastMCP 服务器入口
│   ├── config.py              # YAML + 环境变量配置加载
│   ├── openclaw_runner.py     # 异步 CLI 子进程运行器
│   ├── memory.py              # SQLite 共享记忆库
│   └── tools/
│       ├── __init__.py         # 自动发现和注册
│       ├── oc_image.py         # 图片生成
│       ├── oc_web.py           # 网络搜索和抓取
│       ├── oc_tts.py           # 文字转语音
│       ├── hermes_messaging.py # 消息发送
│       ├── hermes_chat.py      # 任务委托
│       └── shared_memory.py    # 共享记忆工具
├── config.example.yaml
├── .gitignore
├── LICENSE
├── README.md
└── pyproject.toml
```

## 许可证

MIT