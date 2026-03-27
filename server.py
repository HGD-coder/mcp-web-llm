from mcp.server.fastmcp import FastMCP, Context
from playwright.async_api import async_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import asyncio
import sys
import json
import os
import re
import base64
import binascii
import subprocess
import platform
import tempfile
import urllib.request
import uuid
from dotenv import load_dotenv

from memory import save_message

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

def materialize_base64_images(images_base64: list[str] | None = None) -> list[str]:
    if not images_base64:
        return []

    temp_dir = os.path.join(tempfile.gettempdir(), "mcp-web-llm-inline")
    os.makedirs(temp_dir, exist_ok=True)

    created_paths: list[str] = []
    for idx, raw in enumerate(images_base64):
        if not raw:
            continue
        payload = raw.strip()
        ext = ".png"

        data_uri_match = re.match(r"^data:(image/[\w.+-]+);base64,(.+)$", payload, re.IGNORECASE | re.DOTALL)
        if data_uri_match:
            mime_type = data_uri_match.group(1).lower()
            payload = data_uri_match.group(2).strip()
            if "jpeg" in mime_type or "jpg" in mime_type:
                ext = ".jpg"
            elif "webp" in mime_type:
                ext = ".webp"
            elif "gif" in mime_type:
                ext = ".gif"
        try:
            binary = base64.b64decode(payload, validate=True)
        except binascii.Error:
            continue

        if binary.startswith(b"\xff\xd8\xff"):
            ext = ".jpg"
        elif binary.startswith(b"GIF87a") or binary.startswith(b"GIF89a"):
            ext = ".gif"
        elif binary.startswith(b"RIFF") and b"WEBP" in binary[:16]:
            ext = ".webp"
        elif binary.startswith(b"\x89PNG\r\n\x1a\n"):
            ext = ".png"

        file_name = f"inline_{uuid.uuid4().hex}_{idx}{ext}"
        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(binary)
        created_paths.append(file_path)

    return created_paths

def resolve_query_and_files(
    query: str,
    file_paths: list[str] | None = None,
    images_base64: list[str] | None = None,
) -> tuple[str, list[str] | None]:
    resolved_paths: list[str] = []
    seen: set[str] = set()

    for path in materialize_base64_images(images_base64):
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and abs_path not in seen:
            resolved_paths.append(abs_path)
            seen.add(abs_path)

    for path in file_paths or []:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and abs_path not in seen:
            resolved_paths.append(abs_path)
            seen.add(abs_path)

    raw_matches: list[str] = []
    patterns = [
        r"`([A-Za-z]:[\\/][^`\r\n]+)`",
        r'"([A-Za-z]:[\\/][^"\r\n]+)"',
        r"'([A-Za-z]:[\\/][^'\r\n]+)'",
        r"([A-Za-z]:\\[^\s<>|?*]+(?:\.[A-Za-z0-9]+)?)",
        r"([A-Za-z]:/[^\s<>|?*]+(?:\.[A-Za-z0-9]+)?)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, query):
            candidate = match.group(1).strip()
            if os.path.exists(candidate):
                abs_path = os.path.abspath(candidate)
                if abs_path not in seen:
                    resolved_paths.append(abs_path)
                    seen.add(abs_path)
                raw_matches.append(match.group(0))

    cleaned_query = query
    for raw in sorted(set(raw_matches), key=len, reverse=True):
        cleaned_query = cleaned_query.replace(raw, " ")

    cleaned_query = re.sub(r"\s+", " ", cleaned_query).strip()
    if not cleaned_query:
        cleaned_query = "请读取我刚上传的文件或图片内容，并准确描述你看到的内容。"

    return cleaned_query, (resolved_paths or None)

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

async def run_model_task(model_name: str, query: str, context: BrowserContext, file_paths: list[str] = None):
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
            
        # Save user query to DB
        save_message(model_name, "user", query)
            
        await adapter.send_message(query, file_paths)
        logger.info(f"Waiting for answer from {model_name}...")
        answer = await adapter.get_latest_answer(min_len=prev_len)
        logger.info(f"Got answer from {model_name}: {answer[:50]}...")
        
        # Save assistant answer to DB
        save_message(model_name, "assistant", answer)
        
        return answer
        
    except Exception as e:
        import traceback
        err_msg = f"Error querying {model_name}: {e}\n{traceback.format_exc()}"
        logger.error(err_msg)
        return err_msg

@mcp.tool()
async def ask_chatgpt(query: str, file_paths: list[str] = None, images_base64: list[str] = None) -> str:
    """Ask a question to ChatGPT web interface."""
    query, file_paths = resolve_query_and_files(query, file_paths, images_base64)
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("chatgpt", query, context, file_paths)

@mcp.tool()
async def ask_claude(query: str, file_paths: list[str] = None, images_base64: list[str] = None) -> str:
    """Ask a question to Claude web interface."""
    query, file_paths = resolve_query_and_files(query, file_paths, images_base64)
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("claude", query, context, file_paths)

@mcp.tool()
async def ask_gemini(query: str, file_paths: list[str] = None, images_base64: list[str] = None) -> str:
    """Ask a question to Gemini web interface."""
    query, file_paths = resolve_query_and_files(query, file_paths, images_base64)
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("gemini", query, context, file_paths)

@mcp.tool()
async def ask_deepseek(query: str, file_paths: list[str] = None, images_base64: list[str] = None) -> str:
    """Ask a question to DeepSeek web interface."""
    query, file_paths = resolve_query_and_files(query, file_paths, images_base64)
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("deepseek", query, context, file_paths)

@mcp.tool()
async def ask_grok(query: str, file_paths: list[str] = None, images_base64: list[str] = None) -> str:
    """Ask a question to Grok web interface."""
    query, file_paths = resolve_query_and_files(query, file_paths, images_base64)
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("grok", query, context, file_paths)

@mcp.tool()
async def ask_qwen(query: str, file_paths: list[str] = None, images_base64: list[str] = None) -> str:
    """Ask a question to Qwen web interface."""
    query, file_paths = resolve_query_and_files(query, file_paths, images_base64)
    async with async_playwright() as p:
        context = await get_browser_context(p)
        return await run_model_task("qwen", query, context, file_paths)

@mcp.tool()
async def ask_all(
    query: str,
    ctx: Context,
    file_paths: list[str] = None,
    images_base64: list[str] = None,
) -> str:
    """
    Ask the same question to ALL supported models (ChatGPT, Claude, Gemini, DeepSeek, Grok, Qwen) in parallel.
    Returns a JSON string containing answers from all models.
    """
    query, file_paths = resolve_query_and_files(query, file_paths, images_base64)
    async with async_playwright() as p:
        context = await get_browser_context(p)
        
        # Helper to run model task with delay
        async def delayed_start(model, q, c, delay, files):
            if delay > 0:
                await asyncio.sleep(delay)
            return model, await run_model_task(model, q, c, files)

        tasks = [
            delayed_start("chatgpt", query, context, 0, file_paths),
            delayed_start("claude", query, context, 1, file_paths),
            delayed_start("gemini", query, context, 2, file_paths),
            delayed_start("deepseek", query, context, 3, file_paths),
            delayed_start("grok", query, context, 4, file_paths),
            delayed_start("qwen", query, context, 5, file_paths),
        ]
        
        # Run in parallel and process as they complete
        results = {}
        total = len(tasks)
        completed = 0
        
        await ctx.info(f"Starting {total} models...")
        
        for coro in asyncio.as_completed(tasks):
            model_name, answer = await coro
            results[model_name] = answer
            completed += 1
            await ctx.info(f"[{completed}/{total}] {model_name} finished.")
            
        # Sort results to maintain consistent order in JSON if needed, or just dump
        # To match previous behavior, we might want to ensure keys exist, but here we just dump what we got.
        return json.dumps(results, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    cli_main()
