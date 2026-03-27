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
            
            # Use fill for instant typing (faster/stable), fallback to type if needed
            try:
                await input_box.fill(text)
            except:
                # Fallback to character-by-character if fill fails (e.g. some rich text editors)
                await input_box.fill("") 
                await input_box.type(text, delay=random.randint(1, 10))
                
        except PlaywrightTimeoutError as e:
            raise Exception(f"Timeout waiting for element '{selector}'. The page might be loading slowly or the layout changed. Please try again.") from e

    @abstractmethod
    async def send_message(self, query: str, file_paths: list[str] = None):
        """Input query, optionally upload files, and click send"""
        pass

    async def upload_files(self, file_paths: list[str], drop_zone_selector: str = 'body'):
        """Upload files using a 3-step approach:
        1. Click attach button to mount the hidden file input
        2. Set files on the now-active input
        3. Wait for upload to complete
        """
        if not file_paths:
            return
            
        try:
            import os
            import base64
            import mimetypes
            import asyncio
            import logging
            
            abs_paths = [os.path.abspath(p) for p in file_paths if os.path.exists(p)]
            
            if not abs_paths:
                return

            # ==== STEP 1: Try clicking attach/upload button first ====
            # This activates the hidden input[type=file] in modern web apps
            attach_selectors = [
                'button[aria-label*="attach" i]',
                'button[aria-label*="upload" i]',
                'button[aria-label*="Add file"]',
                'button[aria-label*="Add image"]',
                'button[aria-label*="file"]',
                'button[aria-label*="image"]',
                'button[data-testid*="attach"]',
                'button[data-testid*="upload"]',
                '[aria-label*="attach" i]',
                '[aria-label*="Upload file" i]',
                '[aria-label*="Add files" i]',
                # Grok specific
                'button[aria-label*="Grok"]',
            ]
            
            attach_clicked = False
            for sel in attach_selectors:
                try:
                    btn = self.page.locator(sel).first
                    if await btn.count() > 0:
                        await btn.click(timeout=3000)
                        attach_clicked = True
                        logging.info(f"Clicked attach button: {sel}")
                        await asyncio.sleep(1)  # Let DOM mount the input
                        break
                except:
                    continue
            
            # ==== STEP 2: Find and set files on the input ====
            # Try multiple strategies
            upload_success = False
            
            # Strategy A: Find visible/enabled file input
            all_file_inputs = self.page.locator('input[type="file"]')
            input_count = await all_file_inputs.count()
            logging.info(f"Found {input_count} input[type=file] elements")
            
            for i in range(input_count):
                try:
                    inp = all_file_inputs.nth(i)
                    is_disabled = await inp.is_disabled()
                    if is_disabled:
                        continue
                    accept_attr = await inp.get_attribute("accept")
                    multiple_attr = await inp.get_attribute("multiple")
                    logging.info(f"Trying input index {i}, accept={accept_attr}, multiple={multiple_attr}")
                    await inp.set_input_files(abs_paths)
                    files_len = await inp.evaluate("(el) => (el.files && el.files.length) || 0")
                    if files_len > 0:
                        upload_success = True
                        logging.info(f"Successfully set files on input index {i} with {files_len} file(s)")
                        break
                except Exception as e:
                    logging.warning(f"Failed on input index {i}: {e}")
                    continue
            
            # Strategy B: If no input found or all disabled, try JS DataTransfer drop
            if not upload_success:
                logging.info("Falling back to DataTransfer drag-and-drop")
                
                files_data = []
                for path in abs_paths:
                    mime_type, _ = mimetypes.guess_type(path)
                    mime_type = mime_type or 'application/octet-stream'
                    
                    with open(path, 'rb') as f:
                        file_content = f.read()
                        base64_content = base64.b64encode(file_content).decode('utf-8')
                        
                    files_data.append({
                        'name': os.path.basename(path),
                        'type': mime_type,
                        'data': base64_content
                    })
    
                js_script = """
                ([filesData, selector]) => {
                    const target = document.querySelector(selector) || document.body;
                    
                    const dataTransfer = new DataTransfer();
                    
                    filesData.forEach(file => {
                        const byteCharacters = atob(file.data);
                        const byteNumbers = new Array(byteCharacters.length);
                        for (let i = 0; i < byteCharacters.length; i++) {
                            byteNumbers[i] = byteCharacters.charCodeAt(i);
                        }
                        const byteArray = new Uint8Array(byteNumbers);
                        const blob = new Blob([byteArray], { type: file.type });
                        const fileObj = new File([blob], file.name, { type: file.type });
                        dataTransfer.items.add(fileObj);
                    });
                    
                    ['dragenter', 'dragover', 'drop'].forEach(eventType => {
                        const event = new DragEvent(eventType, {
                            bubbles: true,
                            cancelable: true,
                            dataTransfer: dataTransfer
                        });
                        target.dispatchEvent(event);
                    });
                }
                """
                
                await self.page.evaluate(js_script, [files_data, drop_zone_selector])
                upload_success = True
                logging.info("DataTransfer drop executed")
            
            # ==== STEP 3: Wait for upload to process ====
            await asyncio.sleep(5)  # Wait for file preview to appear
            
        except Exception as e:
            import logging
            logging.error(f"Failed to upload files {file_paths}: {e}")

    @abstractmethod
    async def get_latest_answer(self, min_len: int = 0) -> str:
        """Wait for and retrieve the generated answer"""
        pass

    async def get_content_length(self) -> int:
        """Get the number of message bubbles"""
        try:
            return len(await self._get_bubbles())
        except:
            return 0

    @abstractmethod
    async def _get_bubbles(self) -> list[str]:
        """Get all message bubbles to track conversation length"""
        pass
