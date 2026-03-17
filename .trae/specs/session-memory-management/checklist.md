# 验收清单：会话与记忆机制改进

## 基础功能验证
- [ ] 代码中所有工具（`ask_*`）都能接受可选的 `session_id` 参数而不报错。
- [ ] 默认不传 `session_id` 时，行为与以前一致（所有模型都在 `default` 会话下进行）。

## Session 隔离验证
- [ ] 调用 `ask_chatgpt(query="你好", session_id="task-A")`。
- [ ] 观察到 Chrome 开启了一个新的 ChatGPT Tab 并发送了 "你好"。
- [ ] 调用 `ask_chatgpt(query="我是谁", session_id="task-A")`。
- [ ] 观察到在 **同一个** Tab 中继续追问了 "我是谁"。
- [ ] 调用 `ask_chatgpt(query="开始新话题", session_id="task-B")`。
- [ ] 观察到 Chrome 开启了 **另一个全新** 的 ChatGPT Tab 并发送了 "开始新话题"，与 `task-A` 互不干扰。

## SQLite 存储验证
- [ ] 确认在用户目录下（或项目根目录下）成功生成了 `history.db` 文件。
- [ ] 使用 SQLite 工具（如 DB Browser 或命令行）打开数据库。
- [ ] 确认表中包含字段：`session_id`, `model`, `role`, `content`, `created_at`。
- [ ] 验证表中准确记录了刚才发出的所有 `query`（role: user）和对应的 `answer`（role: assistant），并且 `session_id` 分配正确。

## 鲁棒性验证
- [ ] 在模型超时或报错时，`user` 的 query 仍然能被记录（或明确设计为成对记录，确保数据一致性）。
- [ ] (如果实现了) 调用 `clear_session(session_id="task-A")`，对应的 Chrome Tab 被成功关闭，字典中不再保留引用。

## 文档验证
- [ ] README.md 中已包含 `session_id` 的说明。
- [ ] README_zh.md 中已包含 SQLite 和会话隔离机制的介绍。
