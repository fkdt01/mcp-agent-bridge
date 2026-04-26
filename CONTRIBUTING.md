# Contributing to MCP Agent Bridge

感谢你对 MCP Agent Bridge 感兴趣！本文档将帮助你参与项目开发。

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/fkdt01/mcp-agent-bridge.git
cd mcp-agent-bridge

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -e ".[dev]"
```

## 代码规范

- **Python 版本**: 3.11+
- **代码风格**: 遵循 PEP 8
- **类型注解**: 所有函数必须有类型注解
- **文档字符串**: 使用 Google 风格的 docstring

## 添加新工具

1. 在 `bridge/tools/` 下创建新文件，命名遵循：
   - `oc_*.py` — OpenClaw 相关工具
   - `hermes_*.py` — Hermes 相关工具
   - `shared_*.py` — 双向共享工具

2. 实现 `register(mcp, config)` 函数：

```python
"""工具模块描述."""
from mcp.server.fastmcp import FastMCP
from typing import Any

def register(mcp: FastMCP, config: dict[str, Any]) -> None:
    """注册工具到 MCP 服务器."""
    
    @mcp.tool()
    async def my_tool(param: str) -> dict[str, Any]:
        """工具描述 — 会显示在 MCP 工具列表中.
        
        Args:
            param: 参数说明
            
        Returns:
            返回值说明
        """
        # 实现逻辑
        return {"result": "ok"}
```

3. 工具会自动被发现和注册，无需手动导入。

## 安全规范

⚠️ **绝对禁止硬编码敏感数据**：

- API Key
- 密码
- Token
- 私钥

敏感数据应通过以下方式获取：

```python
import os

# 方式1: 环境变量
api_key = os.environ.get("MY_API_KEY")

# 方式2: 配置文件 (config.yaml，已在 .gitignore 中)
api_key = config.get("my_service", {}).get("api_key")
```

## 提交规范

使用 Conventional Commits 格式：

```
feat: 添加新工具 oc_video_generate
fix: 修复 shared_memory 并发问题
docs: 更新 README 安装说明
refactor: 重构 openclaw_runner 错误处理
test: 添加 memory.py 单元测试
chore: 更新依赖版本
```

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_memory.py -v

# 测试覆盖率
pytest --cov=bridge tests/
```

## 发布流程

1. 更新版本号 (`pyproject.toml`)
2. 更新 CHANGELOG
3. 创建 Git tag: `git tag v0.x.x`
4. 推送 tag: `git push origin v0.x.x`

## 问题反馈

- Bug 报告 / 功能建议: [fkdt01@vip.qq.com](mailto:fkdt01@vip.qq.com)

## 许可证

本项目采用 MIT 许可证。贡献代码即表示你同意以相同许可证授权。
