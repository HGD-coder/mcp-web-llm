# Tasks
- [x] Task 1: 引入环境变量配置支持
  - [x] SubTask 1.1: 在 `pyproject.toml` 中添加 `python-dotenv` 依赖
  - [x] SubTask 1.2: 修改 `server.py`，使用 `python-dotenv` 加载环境变量，替换硬编码的 CDP_ENDPOINT 和路径参数
- [x] Task 2: 增强代码健壮性与错误处理
  - [x] SubTask 2.1: 在 `server.py` 的 `get_or_create_page` 中增加对 `page.goto` 超时的 `try-except` 逻辑，增加重试机制或更友好的错误提示
  - [x] SubTask 2.2: 在 `models/base.py` 及其子类中，优化 `locator` 相关操作的异常捕获，避免出现底层 TimeoutError 直接抛出到用户端
- [x] Task 3: 完善项目文档
  - [x] SubTask 3.1: 在 `README.md` 中增加架构说明 (Architecture) 和贡献指南 (Contributing) 简述
  - [x] SubTask 3.2: 在 `README_zh.md` 中增加对应的架构说明和贡献指南

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] can be executed in parallel with [Task 1] and [Task 2]