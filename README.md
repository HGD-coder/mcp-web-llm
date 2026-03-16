# MCP Web LLM Aggregator

[English](#english) | [中文](#chinese)

<a name="english"></a>

A **Zero-Cost, Non-API** MCP Server that aggregates web versions of **ChatGPT**, **Claude**, and **Gemini**.

Query multiple top-tier models in parallel directly from your AI IDE (Trae, Cursor, etc.) using your local browser sessions. **No API keys or tokens required.**

## Features

- **Multi-Model Aggregation**: The `ask_all` tool queries ChatGPT, Claude, and Gemini simultaneously and returns a consolidated JSON response.
- **No API Tokens**: Leverages the free web interfaces of these models.
- **Browser Automation**: Uses Playwright and CDP to connect to your existing Chrome instance, reusing your login state.
- **Cost Saving**: Perfect for developers who want high-quality model outputs without the API costs.

## Usage

### 1. Prerequisites

This project uses `uv` for dependency management. Run in the project root:
```bash
uv sync
```

### 2. Prepare Chrome Browser

You need a dedicated Chrome window for AI conversations. We use "Connect over CDP" mode to avoid bans and CAPTCHAs.

**Windows:**
Run in PowerShell (change path if needed):
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_profile" --disable-blink-features=AutomationControlled
```

**macOS:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome_debug_profile" --disable-blink-features=AutomationControlled
```

**After running:**
1. A new Chrome window will pop up.
2. Open and **log in** to these sites in tabs:
   - ChatGPT: [https://chatgpt.com](https://chatgpt.com)
   - Claude: [https://claude.ai](https://claude.ai)
   - Gemini: [https://gemini.google.com](https://gemini.google.com)
3. **Do not close this window!** Keep it running in the background.

### 3. Configure IDE (Trae/Cursor)

Add to your `mcp-servers.json`:

```json
{
  "mcpServers": {
    "web-llm-agent": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/mcp-web-llm",
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### 4. Start Using

In your IDE chat, use natural language:
- "Use `ask_all` to compare Vue vs React."
- "Ask Claude to write a Python script."

---

<a name="chinese"></a>

# MCP Web LLM 聚合器 (中文版)

一个 **零成本、非 API** 的 MCP 服务器，聚合了 **ChatGPT**、**Claude** 和 **Gemini** 的网页版。

在您的 AI IDE（如 Trae、Cursor）中，直接利用本地浏览器会话，并行查询多个顶级模型。**无需 API Key，无需 Token。**

## 核心功能

- **多模型聚合**：`ask_all` 工具同时询问 ChatGPT、Claude 和 Gemini，并返回汇总的 JSON 结果。
- **无需 API Token**：直接利用这些模型的免费网页版接口。
- **浏览器自动化**：使用 Playwright 和 CDP 连接到您现有的 Chrome 实例，复用您的登录状态。
- **极致省钱**：适合希望获得高质量模型输出但不想支付 API 费用的开发者。

## 使用指南

### 1. 环境准备

本项目使用 `uv` 管理依赖。请在项目根目录下运行：
```bash
uv sync
```

### 2. 准备 Chrome 浏览器

你需要一个专门用于 AI 对话的 Chrome 窗口。为了避免封号和验证码，我们使用“接管模式” (Connect over CDP)。

**Windows 用户:**
请在 PowerShell 中运行（注意修改您的 Chrome 路径）：
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_profile" --disable-blink-features=AutomationControlled
```

**macOS 用户:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome_debug_profile" --disable-blink-features=AutomationControlled
```

**运行后：**
1. 会弹出一个全新的 Chrome 窗口。
2. 在这个窗口里，分别打开以下网站并**登录你的账号**：
   - ChatGPT: [https://chatgpt.com](https://chatgpt.com)
   - Claude: [https://claude.ai](https://claude.ai)
   - Gemini: [https://gemini.google.com](https://gemini.google.com)
3. **不要关闭这个窗口！** 把它最小化放在后台即可。

### 3. 配置 IDE (Trae/Cursor)

在您的 `mcp-servers.json` 中添加以下配置：

```json
{
  "mcpServers": {
    "web-llm-agent": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "D:\\path\\to\\mcp-web-llm",
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### 4. 开始使用

在 IDE 的对话框中，直接使用自然语言调用工具：
- “请使用 `ask_all` 工具，让它们分别对比一下 Vue 和 React，并给我一个汇总建议。”
- “让 `ask_claude` 帮我写一个 Python 爬虫脚本。”

See [USAGE.md](USAGE.md) for detailed instructions on how to start Chrome and configure the MCP server.
