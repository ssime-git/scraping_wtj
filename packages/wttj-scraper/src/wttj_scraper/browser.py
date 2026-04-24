from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import BrowserContext, async_playwright

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@asynccontextmanager
async def browser_context(headless: bool = True) -> AsyncGenerator[BrowserContext, None]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=_USER_AGENT)
        try:
            yield context
        finally:
            await context.close()
            await browser.close()
