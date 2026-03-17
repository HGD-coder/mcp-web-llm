from .base import ModelAdapter
import asyncio

class GeminiAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://gemini.google.com/"

    @property
    def domain_keyword(self) -> str:
        return "gemini.google.com"

    async def send_message(self, query: str):
        # Gemini 的输入框通常在 rich-textarea 下
        input_selector = "div[role='textbox']"
        try:
            await self.page.wait_for_selector(input_selector, timeout=30000)
        except:
            raise Exception("Gemini input box not found. Are you logged in?")

        await self.human_type(input_selector, query)
        await asyncio.sleep(1)
        
        # 发送按钮
        send_button = self.page.locator('button[aria-label="Send message"]')
        if await send_button.count() > 0:
            await send_button.click()
        else:
            await self.page.keyboard.press("Enter")
        
        # 等待输入框清空，作为发送成功的标志
        try:
             await self.page.wait_for_function(
                 f"document.querySelector(\"{input_selector}\").textContent === ''",
                 timeout=5000
             )
        except:
             pass
             
        # 等待新的回答出现 (旧回答数量 + 1)
        # 或者等待 loading 状态消失
        await asyncio.sleep(2) # 简单等待一下

    async def _get_bubbles(self):
        # Gemini 的回答通常在 .model-response-text 类下或 message-content
        return await self.page.locator(".model-response-text, message-content").all_text_contents()

    async def get_content_length(self) -> int:
        bubbles = await self._get_bubbles()
        return len(bubbles)

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
