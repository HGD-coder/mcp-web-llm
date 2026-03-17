# IDE Web AI Plugin Research Spec

## Why

用户希望在 Cursor、Trae、Claude Code 等 AI 驱动的 IDE 中，能够直接访问并使用网页版 Gemini、ChatGPT 或 Claude 的免费/日常对话额度。这样可以有效节省 IDE 原生的 API Token 或订阅消耗，实现仅通过输入输出的代理来完成代码辅助。我们需要调研当前市面上是否存在满足这一需求的插件或解决方案。

## What Changes

* 针对主流代码编辑器及 AI IDE（VSCode, Cursor, Trae 等），全面调研是否存在支持桥接网页版 AI Session 的插件。

* 收集开源社区（如 GitHub）中用于将网页版 AI 逆向或转换为兼容 OpenAI API 格式的本地代理工具。

* 撰写并输出一份详细的调研报告，列出可行的工具、插件名称及配置思路。

## Impact

* Affected specs: 这是一个纯调研与分析任务，不修改现有项目代码。

* Affected code: 最终将新增一份调研报告文件 `IDE_Web_AI_Plugin_Research.md`。

## ADDED Requirements

### Requirement: 网页版 AI 接入方案调研

系统（Agent）需要搜索并整理以下信息：

1. **现有插件**：在 VSCode 等插件市场中，是否存在能够读取浏览器 Cookie/Session 直接对话网页版大模型的扩展。
2. **反向代理方案**：开源社区中将 Web 网页版 AI 转化为标准 API 接口（如 `http://localhost:xxxx/v1`）的方案（如 FreeGPT, Claude-to-API 等），以便在 Cursor/Trae 的自定义模型配置中使用。
3. **操作可行性**：总结这些方案的优缺点（如稳定性、封号风险等）。

