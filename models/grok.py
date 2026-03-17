from .base import ModelAdapter
import asyncio
import random

class GrokAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://grok.com/" # 或者 x.com/i/grok

    @property
    def domain_keyword(self) -> str:
        return "grok.com"

    async def ensure_logged_in(self) -> bool:
        url = (self.page.url or "").lower()
        if "login" in url or "auth" in url or "sign" in url:
            return False
        return True

    async def send_message(self, query: str):
        self._last_query = query
        candidates = [
            "textarea[placeholder*='Grok']",
            "textarea[placeholder*='Ask']",
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
            raise Exception("Grok input box not found. Are you logged in?")

        if "contenteditable" in input_selector or "role='textbox'" in input_selector:
            await self.page.focus(input_selector)
            await self.page.keyboard.type(query, delay=random.randint(30, 80))
        else:
            await self.human_type(input_selector, query)

        await asyncio.sleep(1)
        
        await self.page.keyboard.press("Enter")

    async def _get_bubbles(self):
        for sel in [
            "main div[dir='auto']",
            "main [role='listitem']",
            "main [role='article']",
            ".prose",
            "div[class*='message']",
            "div[class*='markdown']",
        ]:
            try:
                bubbles = await self.page.locator(sel).all_text_contents()
                bubbles = [b.strip() for b in bubbles if (b or "").strip()]
                if bubbles:
                    return bubbles
            except:
                continue
        return []

    async def get_latest_answer(self, min_len: int = 0) -> str:
        last_text = ""
        stable_count = 0
        last_query = getattr(self, "_last_query", "") or ""
        
        for _ in range(120):
            bubbles = await self._get_bubbles()
            if not bubbles or len(bubbles) <= min_len:
                await asyncio.sleep(1)
                continue
            
            current_text = ""
            for t in reversed(bubbles):
                if last_query and t.strip() == last_query.strip():
                    continue
                current_text = t
                break
            
            if current_text == last_text and len(current_text) > 0:
                stable_count += 1
                if stable_count >= 3:
                    return current_text
            else:
                stable_count = 0
                last_text = current_text
            
            await asyncio.sleep(1)
            
        return f"Timeout. Partial answer: {last_text}"
