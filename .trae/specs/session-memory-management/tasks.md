# 任务列表：会话与记忆机制改进

## 1. 设计并实现 SQLite 存储模块
- [ ] 创建 `db.py` (或 `memory.py`) 文件。
- [ ] 实现 `init_db()` 函数：
  - 确定数据库文件存放路径（建议利用环境变量 `MCP_WEB_LLM_DATA_DIR`，默认放在 `~/.mcp-web-llm/history.db`）。
  - 创建 `chat_history` 表：`id` (INTEGER PRIMARY KEY), `session_id` (TEXT), `model` (TEXT), `role` (TEXT), `content` (TEXT), `created_at` (DATETIME DEFAULT CURRENT_TIMESTAMP)。
- [ ] 实现 `save_message(session_id, model, role, content)` 函数：
  - 执行 `INSERT` 操作将单条消息存入数据库。
  - 处理并发写入的线程安全（SQLite 默认支持，但需要注意 connection 的使用方式）。

## 2. Session 路由层重构
- [ ] 在 `server.py` 中引入 `session_id` 的概念。
- [ ] 重构 `get_or_create_page` 逻辑：
  - 现有的逻辑是遍历 `context.pages` 找 URL 匹配的页面。
  - **新逻辑**：
    - 需要一种机制在 Page 对象上附加或关联 `session_id`。
    - 可以维护一个全局字典：`active_sessions = { "session_id": { "chatgpt": Page, "claude": Page } }`。
    - 或者利用 Playwright 页面关闭事件清理字典。
    - 如果该 `session_id` 对应的 model Tab 尚未创建，则 `context.new_page()` 并跳转，记录进字典。
    - 如果已存在，则直接 `bring_to_front()` 该 Page。

## 3. Tool 签名与业务流更新
- [ ] 修改 `ask_chatgpt`, `ask_claude`, `ask_gemini`, `ask_deepseek`, `ask_grok`, `ask_qwen` 的参数，增加 `session_id: str = "default"`。
- [ ] 修改 `ask_all` 的参数，增加 `session_id: str = "default"`。
- [ ] 在 `run_model_task` 的执行流程中：
  - 将 `session_id` 传递给 `get_or_create_page`。
  - 在发送 `query` 之前，调用 `save_message(session_id, model_name, "user", query)`。
  - 在成功获取 `answer` 之后，调用 `save_message(session_id, model_name, "assistant", answer)`。

## 4. (可选) 新增会话管理工具
- [ ] 新增 tool `clear_session(session_id: str)`：
  - 在全局字典中查找对应的 Pages 并调用 `page.close()`。
  - 从字典中移除该 `session_id`，释放浏览器内存。

## 5. 文档更新
- [ ] 更新 `README.md` (English)：
  - 在 Features 中增加 Local SQLite History 和 Multi-Session Support。
  - 在 Usage/Tools 中更新各个工具的签名，说明 `session_id` 的用法。
- [ ] 更新 `README_zh.md` (中文)：
  - 对应增加“多会话隔离”与“本地 SQLite 留痕”的说明。
