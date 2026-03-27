from .base import ModelAdapter
import asyncio
import random
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

class GeminiAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://gemini.google.com/"

    @property
    def domain_keyword(self) -> str:
        return "gemini.google.com"

    async def send_message(self, query: str, file_paths: list[str] = None):
        candidates = [
            "div[role='textbox'][contenteditable='true']",
            "rich-textarea div[role='textbox']",
            "div[contenteditable='true'][role='textbox']",
            "div[contenteditable='true']",
            "textarea:not([readonly]):not([aria-hidden='true'])",
        ]

        input_selector = None
        for sel in candidates:
            loc = self.page.locator(sel).first
            try:
                await loc.wait_for(state="visible", timeout=8000)
                input_selector = sel
                break
            except:
                continue

        if not input_selector:
            raise Exception("Gemini input box not found. Are you logged in?")

        if file_paths:
            uploaded = False
            try:
                trigger = self.page.locator(".upload-card-button").first
                if await trigger.count() > 0 and await trigger.is_visible():
                    await trigger.click(timeout=3000)
                    await asyncio.sleep(1)
                    async with self.page.expect_file_chooser(timeout=3000) as chooser_info:
                        await self.page.get_by_text("上传文件").click()
                    chooser = await chooser_info.value
                    await chooser.set_files(file_paths)
                    uploaded = True
            except PlaywrightTimeoutError:
                uploaded = False
            except Exception:
                uploaded = False
            if not uploaded:
                attach_selectors = [
                    'button[aria-label*="插入" i]',
                    'button[aria-label*="添加" i]',
                    'button[aria-label*="上传" i]',
                    'button[aria-label*="add" i]',
                    'button[aria-label*="upload" i]',
                    'button[aria-label*="file" i]',
                    'button[aria-label*="image" i]',
                    '[data-test-id*="upload"]',
                ]
                for sel in attach_selectors:
                    btn = self.page.locator(sel).first
                    try:
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click(timeout=3000)
                            await asyncio.sleep(1)
                            break
                    except:
                        continue
                await self.upload_files(file_paths)
            await asyncio.sleep(2)

        if "contenteditable" in input_selector or "role='textbox'" in input_selector:
            await self.page.focus(input_selector)
            await self.page.keyboard.type(query, delay=random.randint(20, 60))
        else:
            await self.human_type(input_selector, query)
        await asyncio.sleep(1)
        
        clicked = False
        send_selectors = [
            'button[aria-label*="发送" i]',
            'button[aria-label*="Send" i]',
            'button[aria-label*="message" i]',
            'button[mattooltip*="Send" i]',
            'button[type="submit"]',
        ]
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

        try:
            await self.page.wait_for_function(
                """(sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return true;
                    const text = (el.value || el.textContent || '').replace(/\\u200b/g, '').trim();
                    return text === '';
                }""",
                arg=input_selector,
                timeout=5000
            )
        except:
            pass

        await asyncio.sleep(2)

    async def _get_bubbles(self):
        for sel in [
            "message-content",
            ".model-response-text",
            "model-response",
            "div[class*='response']",
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
        
        for _ in range(120):
            bubbles = await self._get_bubbles()
            if not bubbles or len(bubbles) <= min_len:
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
