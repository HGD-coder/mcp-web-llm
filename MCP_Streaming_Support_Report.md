# MCP Streaming Support Research Report

## 1. Executive Summary
Cursor and Trae currently have **limited or experimental support** for full MCP tool streaming (content_block_delta). While the MCP protocol defines streaming capabilities (Server-Sent Events), most IDE clients primarily support the **Request-Response** model for tools.

- **Cursor**: Supports `notifications/progress` for showing progress bars/logs, but does not natively render tool outputs as a real-time stream in the chat interface. It waits for the final tool result.
- **Trae**: Similar to Cursor, follows the standard MCP client implementation, prioritizing stability over experimental streaming features.

**Conclusion**: Implementing true "typewriter" streaming for `ask_all` is **technically possible via SSE**, but the **UI experience in current IDEs will likely not match expectations** (users won't see text streaming in the chat bubble, but rather in a separate log or progress indicator).

## 2. Detailed Findings

### 2.1 Cursor Support
- **Protocol**: Supports standard MCP over `stdio`.
- **Progress API**: Supports `notifications/progress`. Can be used to update a progress bar or status text (e.g., "ChatGPT finished... Claude generating...").
- **Streaming Content**: 
  - Tools are generally treated as atomic operations. The IDE waits for the `CallToolResult` before passing it back to the LLM context.
  - **Workaround**: Some developers use `resource` subscriptions for streaming data, but this doesn't fit the `ask_all` tool paradigm well.

### 2.2 Trae Support
- **Protocol**: Standard MCP support.
- **Behavior**: Trae's chat interface expects a complete tool response to proceed with the next step of reasoning. Streaming partial tool outputs directly into the chat view is not a documented feature for standard tools.

## 3. Recommended Implementation Strategy

Given the current IDE limitations, the best approach to improve user experience without breaking compatibility is **"Progress Notifications"** rather than "Content Streaming".

### Strategy: Async Progress Reporting (The "Optimized Batch" Approach)

Instead of trying to stream text token-by-token (which IDEs might swallow or buffer), we should:

1.  **Keep `ask_all` as a Tool**: It returns a final JSON.
2.  **Use `ctx.info()` / Logging**: As each model finishes, send a log message.
    - *Effect*: User sees "ChatGPT: Done", "Claude: Done" in the tool logs area, reducing anxiety.
3.  **Optimize Concurrency**: Use `asyncio.as_completed` to process results as soon as they are ready, rather than `gather` (waiting for the slowest).

### Why not SSE / Content Delta?
- **Complexity**: Requires rewriting the server to use HTTP/SSE transport instead of `stdio`.
- **Client Support**: If the IDE doesn't handle `content_block_delta` specifically for tools, the stream will be ignored, and the user will still see a spinner until the end.

## 4. Next Steps
- **Immediate**: Implement `asyncio.as_completed` + `ctx.info()` logging to provide granular status updates.
- **Future**: Monitor Cursor/Trae changelogs for "Tool Result Streaming" support.
