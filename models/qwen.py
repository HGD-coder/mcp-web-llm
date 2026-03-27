from .base import ModelAdapter
import asyncio
import os
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
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

    async def send_message(self, query: str, file_paths: list[str] = None):
        candidates = [
            "textarea[class*='ant-input']:not([readonly]):not([aria-hidden='true'])",
            "textarea:not([readonly]):not([aria-hidden='true'])",
            "div[contenteditable='true'][role='textbox']",
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

        if file_paths:
            uploaded = False
            try:
                trigger = self.page.locator(".mode-select .ant-dropdown-trigger").first
                if await trigger.count() > 0 and await trigger.is_visible():
                    await trigger.click(timeout=3000)
                    await asyncio.sleep(0.8)
                    async with self.page.expect_file_chooser(timeout=3000) as chooser_info:
                        await self.page.locator(".ant-dropdown-menu-item").nth(0).click()
                    chooser = await chooser_info.value
                    await chooser.set_files(file_paths)
                    uploaded = True
            except PlaywrightTimeoutError:
                uploaded = False
            except Exception:
                uploaded = False
            if not uploaded:
                attach_selectors = [
                    'button[aria-label*="Upload" i]',
                    'button[aria-label*="upload" i]',
                    'button[aria-label*="attach" i]',
                    'button[aria-label*="file" i]',
                    'button[aria-label*="image" i]',
                    '.message-input-action-button',
                    '.message-input-action-item',
                    '[data-testid*="upload"]',
                ]
                for sel in attach_selectors:
                    try:
                        loc = self.page.locator(sel)
                        count = min(await loc.count(), 5)
                        clicked = False
                        for i in range(count):
                            btn = loc.nth(i)
                            if await btn.is_visible():
                                await btn.click(timeout=3000)
                                await asyncio.sleep(1)
                                clicked = True
                                break
                        if clicked:
                            break
                    except:
                        continue
                try:
                    qwen_input = self.page.locator("#filesUpload").first
                    if await qwen_input.count() > 0:
                        await qwen_input.set_input_files(file_paths)
                        try:
                            await qwen_input.dispatch_event("input")
                            await qwen_input.dispatch_event("change")
                        except:
                            pass
                        uploaded = True
                except:
                    uploaded = False
            if not uploaded:
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
        
        send_selectors = [
            "button[type='submit']",
            "button:has-text('发送')",
            "button:has-text('Send')",
            "span[aria-label='send']",
            "button[aria-label*='send' i]",
            "button[aria-label*='发送']",
            "button:not([disabled]):has(svg)",
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

    async def _get_bubbles(self):
        for sel in [
            ".markdown-body",
            ".qwen-markdown",
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

    async def get_latest_answer(self, min_len: int = 0) -> str:
        last_text = ""
        stable_count = 0
        
        for _ in range(120):
            bubbles = await self._get_bubbles()
            if not bubbles:
                await asyncio.sleep(1)
                continue
            
            current_text = bubbles[-1].strip()
            if len(current_text) <= max(min_len, 10):
                await asyncio.sleep(1)
                continue
            
            if current_text == last_text and len(current_text) > 0:
                stable_count += 1
                if stable_count >= 3:
                    return current_text
            else:
                stable_count = 0
                last_text = current_text
            
            await asyncio.sleep(1)
            
        return f"Timeout. Partial answer: {last_text}"
