from .base import ModelAdapter
import asyncio
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

    async def send_message(self, query: str):
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
        return await self.page.locator(".ds-markdown, .markdown-body, div[class*='markdown'], div[class*='message']").all_text_contents()

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
