from abc import ABC, abstractmethod
from playwright.async_api import Page
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

    async def ensure_logged_in(self) -> bool:
        """Check if user is logged in, return False if not"""
        # Default implementation: check if URL redirects to login
        if "login" in self.page.url or "auth" in self.page.url:
            return False
        return True

    async def human_type(self, selector: str, text: str):
        """Simulate human typing with random delays"""
        await self.page.click(selector)
        input_box = self.page.locator(selector)
        await input_box.fill("") # Clear first
        
        for char in text:
            await input_box.type(char, delay=random.randint(30, 80))
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.1, 0.3))

    @abstractmethod
    async def send_message(self, query: str):
        """Input query and click send"""
        pass

    @abstractmethod
    async def get_latest_answer(self) -> str:
        """Wait for and retrieve the generated answer"""
        pass
