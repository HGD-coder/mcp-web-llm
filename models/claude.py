from .base import ModelAdapter
import asyncio
import random

class ClaudeAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://claude.ai/"

    @property
    def domain_keyword(self) -> str:
        return "claude.ai"

    async def send_message(self, query: str):
        # Claude 可能使用 textarea 或者 ProseMirror
        input_selector = "textarea[data-testid='chat-input-ssr'], .ProseMirror, [contenteditable='true']"
        try:
            # 强制等待，因为可能被遮挡
            await self.page.wait_for_selector(input_selector, timeout=10000, state="attached")
        except:
            raise Exception("Claude input box not found. Are you logged in?")

        # 尝试使用键盘直接输入（先聚焦）
        await self.page.focus(input_selector)
        await self.page.keyboard.type(query, delay=random.randint(30, 80))
        
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
