from abc import ABC, abstractmethod
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
import random
import asyncio

class ModelAdapter(ABC):
    """Base adapter for web-based LLM interfaces"""
    
    def __init__(self, page: Page):
        self.page = page

    @property
    @abstractmethod
    def start_url(self) -> str:
        pass

    @property
    @abstractmethod
    def domain_keyword(self) -> str:
        """Keyword to identify this model's tab URL"""
        pass

    @property
    def domain_keywords(self) -> list[str]:
        return [self.domain_keyword]

    async def ensure_logged_in(self) -> bool:
        """Check if user is logged in, return False if not"""
        # Default implementation: check if URL redirects to login
        if "login" in self.page.url or "auth" in self.page.url:
            return False
        return True

    async def human_type(self, selector: str, text: str):
        """Simulate human typing with random delays"""
        try:
            await self.page.click(selector)
            input_box = self.page.locator(selector)
            await input_box.fill("") # Clear first
            
            for char in text:
                await input_box.type(char, delay=random.randint(30, 80))
                if random.random() < 0.05:
                    await asyncio.sleep(random.uniform(0.1, 0.3))
        except PlaywrightTimeoutError as e:
            raise Exception(f"Timeout waiting for element '{selector}'. The page might be loading slowly or the layout changed. Please try again.") from e

    @abstractmethod
    async def send_message(self, query: str):
        """Input query and click send"""
        pass

    @abstractmethod
    async def get_latest_answer(self) -> str:
        """Wait for and retrieve the generated answer"""
        pass
