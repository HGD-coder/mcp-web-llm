from .base import ModelAdapter
import asyncio
import os
import random

class DeepSeekAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://chat.deepseek.com/"

    @property
    def domain_keyword(self) -> str:
        return "chat.deepseek.com"

    async def ensure_logged_in(self) -> bool:
        url = (self.page.url or "").lower()
        if "login" in url or "auth" in url or "sign" in url:
            return False
        return True

    async def send_message(self, query: str, file_paths: list[str] = None):
        self._last_query = query
        candidates = [
            "textarea#chat-input",
            "textarea[id='chat-input']",
            "textarea[placeholder*='DeepSeek']",
            "textarea[placeholder*='发送消息']",
            "textarea",
            "div[contenteditable='true']",
            "div[role='textbox']",
        ]

        input_selector = None
        for sel in candidates:
            loc = self.page.locator(sel).first
            try:
                await loc.wait_for(state="visible", timeout=6000)
                input_selector = sel
                break
            except:
                continue

        if not input_selector:
            raise Exception("DeepSeek input box not found. Are you logged in?")

        if file_paths:
            await self.upload_files(file_paths)
            try:
                basename = os.path.basename(file_paths[0])
                await self.page.wait_for_function(
                    """(name) => document.body && document.body.innerText.includes(name)""",
                    arg=basename,
                    timeout=10000
                )
            except:
                pass
            await asyncio.sleep(4)

        if "contenteditable" in input_selector or "role='textbox'" in input_selector:
            await self.page.focus(input_selector)
            await self.page.keyboard.type(query, delay=random.randint(30, 80))
        else:
            await self.human_type(input_selector, query)

        await asyncio.sleep(1)
        
        clicked = False
        try:
            if "textarea" in input_selector:
                ta = self.page.locator(input_selector).first
                container = ta.locator("xpath=ancestor::*[.//div[@role='button']][1]")
                btn = container.locator("div[role='button'][aria-disabled='false']:has(svg)").last
                if await btn.count() > 0:
                    await btn.click()
                    clicked = True
        except:
            pass
        if not clicked:
            try:
                btn = self.page.locator("div[role='button'][aria-disabled='false']:has(svg)").last
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    clicked = True
            except:
                pass
        if not clicked:
            await self.page.keyboard.press("Enter")

        try:
            if "textarea" in input_selector:
                await self.page.wait_for_function(
                    f"(sel) => {{ const el = document.querySelector(sel); return !el || (el.value || el.textContent || '').trim() === ''; }}",
                    arg=input_selector,
                    timeout=5000,
                )
        except:
            pass

    async def _get_bubbles(self):
        for sel in [
            ".ds-markdown",
            ".markdown-body",
            "div[class*='markdown']",
            "div[class*='message']",
            "div[class*='assistant']",
        ]:
            try:
                bubbles = await self.page.locator(sel).all_text_contents()
                bubbles = [b.strip() for b in bubbles if (b or "").strip()]
                if bubbles:
                    return bubbles
            except:
                continue
        return []

    async def get_latest_answer(self, min_len: int = 0, timeout: int = 45) -> str:
        deadline = asyncio.get_event_loop().time() + timeout
        last = ""
        while asyncio.get_event_loop().time() < deadline:
            try:
                bubbles = await self._get_bubbles()
                if bubbles:
                    current = bubbles[-1].strip()
                    if current and len(current) > max(min_len, 20):
                        if current == last:
                            return current
                        last = current
                await asyncio.sleep(1.5)
            except Exception:
                await asyncio.sleep(1.5)
        if last:
            return last
        try:
            body_text = await self.page.evaluate("() => document.body ? document.body.innerText : ''")
            last_query = getattr(self, "_last_query", "").strip()
            if body_text and last_query and last_query in body_text:
                tail = body_text.split(last_query)[-1]
                lines = [line.strip() for line in tail.splitlines() if line.strip()]
                skip_tokens = ["PNG", "JPG", "JPEG", "KB", "仅识别附件中的文字", "内容由 AI 生成", "深度思考", "智能搜索"]
                for line in lines:
                    if any(token in line for token in skip_tokens):
                        continue
                    if line.endswith(".png") or line.endswith(".jpg") or line.endswith(".jpeg"):
                        continue
                    return line
        except Exception:
            pass
        raise TimeoutError("Timeout waiting for DeepSeek answer")

    async def get_latest_answer(self, min_len: int = 0) -> str:
        last_text = ""
        stable_count = 0
        
        for _ in range(120):
            bubbles = await self._get_bubbles()
            if not bubbles or len(bubbles) <= min_len:
                await asyncio.sleep(1)
                continue
            
            current_text = bubbles[-1]
            
            if current_text == last_text and len(current_text) > 0:
                # 检查是否还有正在生成的标志 (e.g. 光标)
                is_generating = await self.page.locator(".ds-cursor").count() > 0
                if not is_generating:
                    stable_count += 1
                    if stable_count >= 3:
                        return current_text
            else:
                stable_count = 0
                last_text = current_text
            
            await asyncio.sleep(1)
            
        return f"Timeout. Partial answer: {last_text}"
