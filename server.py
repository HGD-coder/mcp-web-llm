from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, BrowserContext, Page
import asyncio
import sys
import json

from models.chatgpt import ChatGPTAdapter
from models.claude import ClaudeAdapter
from models.gemini import GeminiAdapter

mcp = FastMCP("web-llm-agent")

async def get_browser_context(p) -> BrowserContext:
    """Connect to local Chrome instance"""
    try:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        return browser.contexts[0]
    except Exception as e:
        raise Exception(f"Failed to connect to Chrome: {e}. Please ensure Chrome is running with remote debugging port 9222.")

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_or_create_page(context: BrowserContext, adapter_cls) -> tuple[Page, bool]:
    """Find existing tab for the model or create new one"""
    # Instantiate a temp adapter just to get properties
    temp_adapter = adapter_cls(None)
    keyword = temp_adapter.domain_keyword
    start_url = temp_adapter.start_url
    
    for page in context.pages:
        if keyword in page.url:
            logger.info(f"Found existing page for {keyword}: {page.url}")
            await page.bring_to_front()
            return page, True
            
    logger.info(f"Creating new page for {keyword} with url {start_url}")
    page = await context.new_page()
    await page.goto(start_url)
    return page, False

async def run_model_task(model_name: str, query: str, context: BrowserContext):
    """Execute query on a specific model"""
    logger.info(f"Starting task for {model_name}")
    adapters = {
        "chatgpt": ChatGPTAdapter,
        "claude": ClaudeAdapter,
        "gemini": GeminiAdapter
    }
    
    if model_name not in adapters:
        return f"Error: Model {model_name} not supported."
        
    adapter_cls = adapters[model_name]
    
    try:
        page, existed = await get_or_create_page(context, adapter_cls)
        adapter = adapter_cls(page)
        
        # Check login
        if not await adapter.ensure_logged_in():
            return f"Error: Please log in to {model_name} in the opened Chrome window."
            
        logger.info(f"Sending message to {model_name}...")
        await adapter.send_message(query)
        logger.info(f"Waiting for answer from {model_name}...")
        answer = await adapter.get_latest_answer()
        logger.info(f"Got answer from {model_name}: {answer[:50]}...")
        return answer
        
    except Exception as e:
        import traceback
        err_msg = f"Error querying {model_name}: {e}\n{traceback.format_exc()}"
        logger.error(err_msg)
        return err_msg

@mcp.tool()
async def ask_chatgpt(query: str) -> str:
    """Ask a question to ChatGPT web interface."""
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("chatgpt", query, context)

@mcp.tool()
async def ask_claude(query: str) -> str:
    """Ask a question to Claude web interface."""
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("claude", query, context)

@mcp.tool()
async def ask_gemini(query: str) -> str:
    """Ask a question to Gemini web interface."""
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("gemini", query, context)

@mcp.tool()
async def ask_all(query: str) -> str:
    """
    Ask the same question to ALL supported models (ChatGPT, Claude, Gemini) in parallel.
    Returns a JSON string containing answers from all models.
    """
    async with async_playwright() as p:
        context = await get_browser_context(p)
        
        # Helper to run model task with delay
        async def delayed_start(model, q, c, delay):
            if delay > 0:
                await asyncio.sleep(delay)
            return await run_model_task(model, q, c)

        tasks = [
            delayed_start("chatgpt", query, context, 0),
            delayed_start("claude", query, context, 2),
            delayed_start("gemini", query, context, 4)
        ]
        
        # Run in parallel
        results = await asyncio.gather(*tasks)
        
        response = {
            "chatgpt": results[0],
            "claude": results[1],
            "gemini": results[2]
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run(transport='stdio')
