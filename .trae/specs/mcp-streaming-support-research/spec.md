# MCP Tool Streaming Support Research Spec

## Why
用户希望了解 Cursor 和 Trae 等主流 AI IDE 当前对 MCP Tool 流式渲染（Streaming）的支持情况，以便决定是否对 `ask_all` 工具进行深度的流式改造。目前 `ask_all` 使用一次性返回（Request-Response），用户体验存在长时间等待的卡顿感。

## What Changes
- 本次任务为调研性质，不涉及代码变更。
- 输出一份调研报告 `MCP_Streaming_Support_Report.md`，涵盖 Cursor 和 Trae 对 MCP `progress` 通知、`content_block_delta` 流式内容的渲染支持情况。

## Impact
- Affected specs: 无（调研任务）
- Affected code: 无（产出文档）

## ADDED Requirements
### Requirement: 调研报告
系统需要通过网络搜索和官方文档查阅，回答以下问题：
1. **Cursor 支持情况**：Cursor 是否支持显示 MCP Tool 的实时进度（`notifications/progress`）？是否支持流式显示 Tool 返回的文本内容？
2. **Trae 支持情况**：Trae 对 MCP 流式协议的支持程度如何？
3. **最佳实践**：在当前 IDE 版本下，实现“打字机”效果的最佳 MCP 协议实现方式是什么（Tool vs Resource vs Prompt）？

#### Scenario: Success case
- **WHEN** 用户阅读报告
- **THEN** 用户能明确知道当前是否值得投入精力开发流式功能，以及预期的 UI 效果是什么。
