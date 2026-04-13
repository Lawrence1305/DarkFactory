"""
Browser Plugin - Playwright-based browser testing
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..plugin import BrowserPlugin, PluginType


@dataclass
class BrowserResult:
    """Browser action result"""
    success: bool
    screenshot: Optional[bytes] = None
    console_logs: List[str] = None
    error: Optional[str] = None
    output: str = ""


class BrowserPlugin(BrowserPlugin):
    """
    Built-in browser plugin using Playwright

    Provides browser automation for end-to-end testing.
    """

    name = "playwright-browser"
    version = "1.0.0"
    description = "Browser automation using Playwright"
    plugin_type = PluginType.BROWSER
    hooks_provided = ["browser_navigate", "browser_click", "browser_screenshot"]

    config_schema = {
        "headless": {"type": "bool", "required": False, "default": True},
        "browser": {"type": "str", "required": False, "default": "chromium"},
        "viewport": {"type": "dict", "required": False, "default": {"width": 1280, "height": 720}},
        "timeout": {"type": "int", "required": False, "default": 30000},
    }

    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser = None
        self._page = None

    async def _ensure_browser(self):
        """Ensure browser is launched"""
        if self._playwright is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
            except ImportError:
                raise ImportError(
                    "Playwright not installed. Run: pip install playwright && playwright install"
                )

        if self._browser is None:
            browser_type = self._config.get("browser", "chromium")
            headless = self._config.get("headless", True)
            self._browser = await getattr(self._playwright, browser_type).launch(
                headless=headless
            )

        if self._page is None:
            viewport = self._config.get("viewport", {"width": 1280, "height": 720})
            self._page = await self._browser.new_page(viewport=viewport)

    async def _cleanup(self):
        """Cleanup browser resources"""
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def execute_async(self, action: str, **kwargs) -> BrowserResult:
        """
        Execute browser action asynchronously

        Args:
            action: Action to perform (navigate, click, screenshot, etc.)
            **kwargs: Action-specific arguments

        Returns:
            Browser action result
        """
        try:
            await self._ensure_browser()

            if action == "navigate":
                return await self._navigate(kwargs.get("url", ""))
            elif action == "click":
                return await self._click(kwargs.get("selector", ""))
            elif action == "screenshot":
                return await self._screenshot(kwargs.get("full_page", False))
            elif action == "evaluate":
                return await self._evaluate(kwargs.get("script", ""))
            else:
                return BrowserResult(
                    success=False,
                    error=f"Unknown action: {action}",
                )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))
        finally:
            await self._cleanup()

    def execute(self, action: str, **kwargs) -> BrowserResult:
        """
        Execute browser action (sync wrapper)

        Args:
            action: Action to perform
            **kwargs: Action-specific arguments

        Returns:
            Browser action result
        """
        try:
            return asyncio.get_event_loop().run_until_complete(
                self.execute_async(action, **kwargs)
            )
        except RuntimeError:
            # No event loop, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.execute_async(action, **kwargs))
            finally:
                loop.close()

    async def _navigate(self, url: str) -> BrowserResult:
        """Navigate to URL"""
        if not url:
            return BrowserResult(success=False, error="URL required")

        timeout = self._config.get("timeout", 30000) / 1000
        response = await self._page.goto(url, timeout=timeout * 1000)

        console_logs = []
        self._page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        return BrowserResult(
            success=response.ok if response else False,
            output=f"Navigated to {url} (status: {response.status if response else 'None'})",
            console_logs=console_logs,
        )

    async def _click(self, selector: str) -> BrowserResult:
        """Click element"""
        if not selector:
            return BrowserResult(success=False, error="Selector required")

        try:
            await self._page.click(selector, timeout=self._config.get("timeout", 30000))
            return BrowserResult(success=True, output=f"Clicked {selector}")
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def _screenshot(self, full_page: bool = False) -> BrowserResult:
        """Take screenshot"""
        try:
            screenshot_bytes = await self._page.screenshot(full_page=full_page)
            return BrowserResult(
                success=True,
                screenshot=screenshot_bytes,
                output="Screenshot taken",
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def _evaluate(self, script: str) -> BrowserResult:
        """Evaluate JavaScript"""
        if not script:
            return BrowserResult(success=False, error="Script required")

        try:
            result = await self._page.evaluate(script)
            return BrowserResult(
                success=True,
                output=str(result),
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def browser_navigate(self, url: str) -> BrowserResult:
        """Hook: navigate to URL"""
        return self.execute("navigate", url=url)

    def browser_click(self, selector: str) -> BrowserResult:
        """Hook: click element"""
        return self.execute("click", selector=selector)

    def browser_screenshot(self, full_page: bool = False) -> BrowserResult:
        """Hook: take screenshot"""
        return self.execute("screenshot", full_page=full_page)
