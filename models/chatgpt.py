from .base import ModelAdapter
import asyncio

class ChatGPTAdapter(ModelAdapter):
    @property
    def start_url(self) -> str:
        return "https://chatgpt.com/"

    @property
    def domain_keyword(self) -> str:
        return "chatgpt.com"

    async def send_message(self, query: str):
        input_selector = "#prompt-textarea"
        try:
            await self.page.wait_for_selector(input_selector, timeout=10000)
        except:
            raise Exception("ChatGPT input box not found. Are you logged in?")

        await self.human_type(input_selector, query)
        await asyncio.sleep(1)
        
        send_button = self.page.locator('[data-testid="send-button"]')
        if await send_button.count() > 0:
            await send_button.click()
        else:
            await self.page.keyboard.press("Enter")

    async def _get_bubbles(self):
        # We need to exclude the user's prompt which might be caught in some selectors
        bubbles = await self.page.locator("div[data-message-author-role='assistant']").all_text_contents()
        if not bubbles:
            # Fallback to older class if assistant role is not found
            bubbles = await self.page.locator(".markdown").all_text_contents()
        return bubbles

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
