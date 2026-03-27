from .base import ModelAdapter
import asyncio
import random
import logging

class ClaudeAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://claude.ai/"

    @property
    def domain_keyword(self) -> str:
        return "claude.ai"

    async def send_message(self, query: str, file_paths: list[str] = None):
        candidates = [
            "textarea[data-testid='chat-input-ssr']",
            ".ProseMirror",
            "[contenteditable='true'][role='textbox']",
            "[contenteditable='true']",
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
            raise Exception("Claude input box not found. Are you logged in?")

        if file_paths:
            # Claude: try clicking attach button first to initialize the file input
            try:
                attach_selectors = [
                    'button[aria-label*="attach" i]',
                    'button[aria-label*="Attach"]',
                    'button[aria-label*="file" i]',
                    'button[data-testid="attach-file"]',
                    'button[data-testid="file-upload-button"]',
                    '[aria-label*="attach" i]',
                ]
                for sel in attach_selectors:
                    btn = self.page.locator(sel).first
                    if await btn.count() > 0:
                        await btn.click(timeout=3000)
                        await asyncio.sleep(1)
                        logging.info(f"Claude: clicked attach button {sel}")
                        break
            except Exception as e:
                logging.warning(f"Claude: failed to click attach button: {e}")
            
            await self.upload_files(file_paths)
            # upload_files already waits 5s internally

        if "contenteditable" in input_selector or "ProseMirror" in input_selector:
            await self.page.focus(input_selector)
            await self.page.keyboard.type(query, delay=random.randint(30, 80))
        else:
            await self.human_type(input_selector, query)
        
        import asyncio
        await asyncio.sleep(1)
        
        # 查找发送按钮或直接回车
        await self.page.keyboard.press("Enter")
        
        # 确认输入框已清空 (发送成功)
        try:
            await self.page.wait_for_function(
                f"document.querySelector(\"{input_selector}\").textContent === '' || document.querySelector(\"{input_selector}\").value === ''",
                timeout=5000
            )
        except:
            # 如果没清空，可能是需要点击发送按钮
            pass

    async def _get_bubbles(self):
        # Claude 的回答通常在 .font-claude-response 
        return await self.page.locator(".font-claude-response, div[data-is-streaming='false']").all_text_contents()

    async def get_latest_answer(self, min_len: int = 0) -> str:
        last_text = ""
        stable_count = 0
        
        for _ in range(120):
            bubbles = await self._get_bubbles()
            if not bubbles or len(bubbles) <= min_len:
                await asyncio.sleep(1)
                continue
            
            # Claude 的页面结构比较复杂，通常最后一条是 AI 回复
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
