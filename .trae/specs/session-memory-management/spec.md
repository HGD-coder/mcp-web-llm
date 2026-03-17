# mcp-web-llm 会话与记忆机制改进规格（Session & Memory Management）

## 背景与目标

当前 `mcp-web-llm` 是一个无状态的浏览器自动化工具。在目前的实现中，每次 MCP 请求仅根据模型名称在浏览器中寻找已有 Tab 或者新建 Tab 进行对话。
这种模式存在以下局限性：
1. **无法隔离会话 (Session Isolation)**：如果用户同时进行两个不同的任务（例如写代码和写文案），所有请求都会挤在同一个页面的同一个对话流中，导致上下文混乱。
2. **缺乏记忆留痕 (Persistence)**：除了网页版自身保存的对话列表外，本地没有结构化的记录。一旦网页刷新、DOM 变动或页面崩溃，之前的上下文很难被 MCP 客户端再次结构化获取。
3. **长对话 DOM 臃肿**：随着单个网页对话变长，DOM 节点爆炸会导致 Playwright 操作变慢、抓取失败或触发站点的反爬虫/内存限制。

**本次改进目标 (Phase 2)**：
- **Session 路由层**：引入 `session_id` 概念，实现多会话隔离。不同的 `session_id` 将映射到不同的浏览器 Tab。
- **结构化持久层**：引入本地 SQLite 数据库，将每一次的问答记录结构化保存在本地。
- **为未来的 Context 注入打基础**：通过将会话结构化存储，未来可以在发送 Query 前，通过检索 SQLite 提取前文摘要，从而不再依赖长长的网页原生 DOM 历史。

## 用户故事

1. 作为用户，我希望在让 AI 并行处理多个独立任务时，能够通过传入不同的 `session_id`，让浏览器在不同的 Tab 中开启独立的新对话，避免上下文串话。
2. 作为用户，我希望我通过 MCP 产生的所有对话记录都能在本地有一份 SQLite 备份，以便后续审计、复盘或作为长期记忆使用。

## 范围（In Scope）

### 1) Session 路由层 (短期可实现)
- 修改所有的 Tool 签名（`ask_chatgpt`, `ask_claude`, `ask_gemini` 等以及 `ask_all`），增加可选参数 `session_id: str = "default"`。
- 重构 `server.py` 中的页面分配逻辑：
  - 维护内存映射 `Map<session_id, Dict<model, Page>>`。
  - 当接收到请求时，基于 `session_id` 查找对应的 Tab。如果不存在，则创建一个新 Tab，并导航到对应模型的起始 URL（自动开启新对话）。
  - （可选/建议）增加一个 TTL 或清理机制，如果一个 session 很久没用，可以考虑手动或自动清理对应 Tab 释放内存。也可以新增一个 `clear_session` tool。

### 2) 持久化层 (SQLite)
- 引入 Python 内置的 `sqlite3`。
- 在用户的数据目录（如 `%APPDATA%\mcp-web-llm` 或配置指定的目录）下自动创建 `history.db` 数据库。
- 设计表结构 `chat_history`：
  - `id` (主键)
  - `session_id` (字符串)
  - `model` (字符串，如 "chatgpt")
  - `role` (字符串，"user" 或 "assistant")
  - `content` (文本，Prompt 或 Response 的内容)
  - `created_at` (时间戳)
- 在 `run_model_task` 执行成功后，自动将问答对插入数据库。

## 范围外（Out of Scope）

- **上下文自动拼接（RAG / Context Injection）**：本次迭代主要完成 Session 隔离与数据入库。暂时不在每次发起请求前主动去查库拼接上文（避免 Prompt 组装过于复杂，后续视需求在 Phase 3 演进）。
- **向量数据库/Embeddings**：本次仅使用 SQLite 存储文本记录，暂不引入 Chroma/FAISS 等向量检索库。

## 兼容性与约束

- 保持与现有客户端的向后兼容：`session_id` 必须是可选参数，默认值为 `"default"`。
- SQLite 文件存放路径需考虑不同操作系统（Windows/macOS/Linux）的常规路径习惯，默认可放在与 profile 相同的基础目录下，或直接放在用户家目录。

## 验收标准

- 代码提交并推送到 GitHub，包含完善的 Spec。
- 能够通过传递不同的 `session_id` 调用 `ask_chatgpt`，观察到 Chrome 浏览器开启了多个 ChatGPT Tab。
- 检查本地的 SQLite 数据库文件，确认能正确记录 `user` 和 `assistant` 的对话内容，并且区分了正确的 `session_id` 和 `model`。
- README.md 更新，详细说明 `session_id` 参数的作用以及本地缓存机制。
