from .base import ModelAdapter
import asyncio
import random

class QwenAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://chat.qwen.ai/"

    @property
    def domain_keyword(self) -> str:
        return "chat.qwen.ai"

    @property
    def domain_keywords(self) -> list[str]:
        return ["chat.qwen.ai", "chat.qwenlm.ai", "qwen.ai", "qwenlm.ai"]

    async def ensure_logged_in(self) -> bool:
        url = (self.page.url or "").lower()
        if "login" in url or "auth" in url or "sign" in url:
            return False
        return True

    async def send_message(self, query: str):
        candidates = [
            "textarea[class*='ant-input']",
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
            raise Exception("Qwen input box not found. Are you logged in?")

        if "contenteditable" in input_selector or "role='textbox'" in input_selector:
            await self.page.focus(input_selector)
            await self.page.keyboard.type(query, delay=random.randint(30, 80))
        else:
            await self.human_type(input_selector, query)

        await asyncio.sleep(1)
        
        send_selectors = [
            "button[type='submit']",
            "button:has-text('发送')",
            "span[aria-label='send']",
            "button[aria-label*='send']",
            "button:has(svg)",
        ]
        clicked = False
        for sel in send_selectors:
            btn = self.page.locator(sel).first
            try:
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    clicked = True
                    break
            except:
                continue
        if not clicked:
            await self.page.keyboard.press("Enter")

    async def get_latest_answer(self) -> str:
        last_text = ""
        stable_count = 0
        
        for _ in range(120):
            bubbles = await self.page.locator(".markdown-body, div[class*='markdown']").all_text_contents()
            if not bubbles:
                await asyncio.sleep(1)
                continue
            
            current_text = bubbles[-1]
            
            if current_text == last_text and len(current_text) > 0:
                stable_count += 1
                if stable_count >= 3:
                    return current_text
            else:
                stable_count = 0
                last_text = current_text
            
            await asyncio.sleep(1)
            
        return f"Timeout. Partial answer: {last_text}"
