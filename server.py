from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import asyncio
import sys
import json
import os
import subprocess
import platform
import urllib.request
from dotenv import load_dotenv

load_dotenv()

from models.chatgpt import ChatGPTAdapter
from models.claude import ClaudeAdapter
from models.gemini import GeminiAdapter
from models.deepseek import DeepSeekAdapter
from models.grok import GrokAdapter
from models.qwen import QwenAdapter

mcp = FastMCP("web-llm-agent")

cdp_port = os.getenv("MCP_WEB_LLM_CDP_PORT", "9222")
CDP_ENDPOINT = f"http://127.0.0.1:{cdp_port}"
DEFAULT_PROFILE_DIR_WIN = r"C:\chrome_debug_profile"

def find_chrome_executable() -> str | None:
    env_chrome_path = os.getenv("MCP_WEB_LLM_CHROME_PATH")
    if env_chrome_path and os.path.exists(env_chrome_path):
        return env_chrome_path

    candidates = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(os.path.join(local_appdata, "Google", "Chrome", "Application", "chrome.exe"))
    candidates.extend(
        [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    )
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

def launch_chrome_with_cdp(urls: list[str]) -> None:
    if platform.system().lower().startswith("win"):
        chrome = find_chrome_executable()
        cdp_port = os.getenv("MCP_WEB_LLM_CDP_PORT", "9222")
        if not chrome:
            raise Exception(f"chrome.exe not found. Please install Google Chrome or start Chrome with --remote-debugging-port={cdp_port} manually.")
        profile_dir = os.environ.get("MCP_WEB_LLM_PROFILE_DIR", DEFAULT_PROFILE_DIR_WIN)
        args = [
            chrome,
            "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={cdp_port}",
            f'--user-data-dir={profile_dir}',
            "--disable-blink-features=AutomationControlled",
            "--new-window",
            *urls,
        ]
        creationflags = 0
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creationflags |= subprocess.DETACHED_PROCESS
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(args, close_fds=True, creationflags=creationflags)
        return

    cdp_port = os.getenv("MCP_WEB_LLM_CDP_PORT", "9222")
    raise Exception(f"Auto-launch is currently supported on Windows only. Please start Chrome with --remote-debugging-port={cdp_port} manually.")

async def wait_for_cdp(p, timeout_s: float = 15.0) -> BrowserContext:
    deadline = asyncio.get_event_loop().time() + timeout_s
    last_err: Exception | None = None
    while asyncio.get_event_loop().time() < deadline:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_ENDPOINT)
            return browser.contexts[0]
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.5)
    raise Exception(f"Failed to connect to Chrome at {CDP_ENDPOINT}: {last_err}")

async def get_browser_context(p) -> BrowserContext:
    """Connect to local Chrome instance"""
    try:
        return await wait_for_cdp(p, timeout_s=2.0)
    except Exception as e:
        urls = [
            "https://chatgpt.com/",
            "https://claude.ai/",
            "https://gemini.google.com/",
            "https://chat.deepseek.com/",
            "https://grok.com/",
            "https://chat.qwen.ai/",
        ]
        launch_chrome_with_cdp(urls)
        return await wait_for_cdp(p, timeout_s=20.0)

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)

def doctor_report() -> dict:
    report: dict = {
        "project": "mcp-web-llm",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cdp_endpoint": CDP_ENDPOINT,
        "cdp_reachable": False,
        "chrome_executable": find_chrome_executable(),
        "profile_dir": os.environ.get("MCP_WEB_LLM_PROFILE_DIR", DEFAULT_PROFILE_DIR_WIN),
        "open_tabs": [],
        "env": {
            "MCP_WEB_LLM_PROFILE_DIR": os.environ.get("MCP_WEB_LLM_PROFILE_DIR"),
        },
    }
    try:
        with urllib.request.urlopen(f"{CDP_ENDPOINT}/json/version", timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            report["cdp_reachable"] = True
            report["cdp_browser"] = data.get("Browser")
    except Exception as e:
        report["cdp_error"] = str(e)
        return report

    try:
        with urllib.request.urlopen(f"{CDP_ENDPOINT}/json/list", timeout=2) as resp:
            tabs = json.loads(resp.read().decode("utf-8"))
            report["open_tabs"] = [t.get("url") for t in tabs if isinstance(t, dict) and t.get("url")]
    except Exception as e:
        report["tabs_error"] = str(e)

    return report

def doctor_cli() -> int:
    print(json.dumps(doctor_report(), indent=2, ensure_ascii=False))
    return 0

def cli_main() -> None:
    args = sys.argv[1:]
    if args and args[0] in {"doctor", "diag", "diagnose"}:
        raise SystemExit(doctor_cli())
    if args and args[0] in {"-h", "--help", "help"}:
        print("Usage:\n  mcp-web-llm            Start MCP server over stdio\n  mcp-web-llm doctor     Show diagnostics", file=sys.stderr)
        return
    mcp.run(transport="stdio")

async def get_or_create_page(context: BrowserContext, adapter_cls) -> tuple[Page, bool]:
    """Find existing tab for the model or create new one"""
    # Instantiate a temp adapter just to get properties
    temp_adapter = adapter_cls(None)
    keywords = temp_adapter.domain_keywords
    start_url = temp_adapter.start_url
    
    for page in context.pages:
        page_url = page.url or ""
        if any(k in page_url for k in keywords):
            logger.info(f"Found existing page for {keywords}: {page.url}")
            await page.bring_to_front()
            return page, True
            
    logger.info(f"Creating new page for {keywords} with url {start_url}")
    page = await context.new_page()
    try:
        await page.goto(start_url)
    except PlaywrightTimeoutError:
        logger.warning(f"Timeout when loading {start_url}, retrying once...")
        try:
            await page.goto(start_url)
        except PlaywrightTimeoutError as e:
            raise Exception(f"Failed to load {start_url} due to network timeout. Please check your connection or try again later.") from e
    return page, False

async def run_model_task(model_name: str, query: str, context: BrowserContext):
    """Execute query on a specific model"""
    logger.info(f"Starting task for {model_name}")
    adapters = {
        "chatgpt": ChatGPTAdapter,
        "claude": ClaudeAdapter,
        "gemini": GeminiAdapter,
        "deepseek": DeepSeekAdapter,
        "grok": GrokAdapter,
        "qwen": QwenAdapter
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
        
        # Snapshot current state
        try:
            prev_len = await adapter.get_content_length()
        except:
            prev_len = 0
            
        await adapter.send_message(query)
        logger.info(f"Waiting for answer from {model_name}...")
        answer = await adapter.get_latest_answer(min_len=prev_len)
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
async def ask_deepseek(query: str) -> str:
    """Ask a question to DeepSeek web interface."""
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("deepseek", query, context)

@mcp.tool()
async def ask_grok(query: str) -> str:
    """Ask a question to Grok web interface."""
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("grok", query, context)

@mcp.tool()
async def ask_qwen(query: str) -> str:
    """Ask a question to Qwen web interface."""
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("qwen", query, context)

@mcp.tool()
async def ask_all(query: str) -> str:
    """
    Ask the same question to ALL supported models (ChatGPT, Claude, Gemini, DeepSeek, Grok, Qwen) in parallel.
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
            delayed_start("gemini", query, context, 4),
            delayed_start("deepseek", query, context, 6),
            delayed_start("grok", query, context, 8),
            delayed_start("qwen", query, context, 10),
        ]
        
        # Run in parallel
        results = await asyncio.gather(*tasks)
        
        response = {
            "chatgpt": results[0],
            "claude": results[1],
            "gemini": results[2],
            "deepseek": results[3],
            "grok": results[4],
            "qwen": results[5],
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    cli_main()
