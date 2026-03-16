# MCP Web LLM Aggregator

A **Zero-Cost, Non-API** MCP Server that aggregates web versions of **ChatGPT**, **Claude**, and **Gemini**.

Query multiple top-tier models in parallel directly from your AI IDE (Trae, Cursor, etc.) using your local browser sessions. **No API keys or tokens required.**

## Features

- **Multi-Model Aggregation**: The `ask_all` tool queries ChatGPT, Claude, and Gemini simultaneously and returns a consolidated JSON response.
- **No API Tokens**: Leverages the free web interfaces of these models.
- **Browser Automation**: Uses Playwright and CDP to connect to your existing Chrome instance, reusing your login state.
- **Cost Saving**: Perfect for developers who want high-quality model outputs without the API costs.

## Usage

See [USAGE.md](USAGE.md) for detailed instructions on how to start Chrome and configure the MCP server.
