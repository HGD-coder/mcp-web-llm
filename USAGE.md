# Multi-LLM Web Agent 使用指南

欢迎使用 Multi-LLM Web Agent！这是一个强大的本地工具，让你可以通过 Trae/Cursor 等 IDE，直接指挥你的 Chrome 浏览器去访问网页版 ChatGPT、Claude、Gemini 等模型，完全免费且安全。

## 🛠️ 第一步：环境准备

### 1. 安装 Python 依赖
本项目使用 `uv` 管理依赖，请在项目根目录下运行：
```bash
uv sync
```

### 2. 准备 Chrome 浏览器
你需要一个专门用于 AI 对话的 Chrome 窗口。为了避免封号和验证码，我们使用“接管模式” (Connect over CDP)。

#### Windows 用户
请复制以下命令，在 PowerShell 或 CMD 中运行（注意修改你的 Chrome 路径）：
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_profile" --disable-blink-features=AutomationControlled
```

#### Mac 用户
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome_debug_profile" --disable-blink-features=AutomationControlled
```

**运行后：**
1.  会弹出一个全新的 Chrome 窗口。
2.  在这个窗口里，分别打开以下网站并**登录你的账号**：
    *   ChatGPT: [https://chatgpt.com](https://chatgpt.com)
    *   Claude: [https://claude.ai](https://claude.ai)
    *   Gemini: [https://gemini.google.com](https://gemini.google.com)
3.  **不要关闭这个窗口！** 把它最小化放在后台即可。

---

## ⚙️ 第二步：配置 IDE (Trae)

1.  打开 Trae 设置 -> **MCP Servers**。
2.  点击编辑配置文件 (`mcp-servers.json`)。
3.  添加以下配置（请根据你的实际路径修改 `cwd`）：

```json
{
  "mcpServers": {
    "web-llm-agent": {
      "command": "uv",
      "args": [
        "run",
        "server.py"
      ],
      "cwd": "D:\\chatdev\\ChatDev\\WareHouse\\mcp_web_agent",
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```
4.  保存并重启 Trae。

---

## 🚀 第三步：开始使用

在 Trae 的对话框中，你可以直接使用自然语言调用工具：

### 1. 问单个模型
> "请用 `ask_claude` 帮我写一个 Python 爬虫脚本。"
> "让 `ask_gemini` 解释一下量子纠缠。"

### 2. 聚合查询 (Ask All)
这是最强大的功能！你可以让它同时去问所有模型，然后对比结果：
> "请使用 `ask_all` 工具，向 ChatGPT 和 Claude 询问：‘Rust 语言相比 C++ 的核心优势是什么？’，并汇总它们的观点。"

### 3. 常见问题
*   **报错 "Target closed"**：说明你的 Chrome 窗口被关闭了，请重新用命令行启动。
*   **一直卡在 "等待回答"**：可能是网页卡住了，去 Chrome 窗口里手动刷新一下页面即可。
*   **Claude 提示 "Rate limit"**：说明你网页版额度用完了，请切换到其他模型。
