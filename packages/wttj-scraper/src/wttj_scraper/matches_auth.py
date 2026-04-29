from __future__ import annotations

import logging
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError


def _wait_pattern_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    leaf = path.rsplit("/", 1)[-1] if path else ""
    return f"**/{leaf}" if leaf else "**/*"


async def _dismiss_cookie_overlay(page: Page) -> None:
    for button_id in ("axeptio_btn_dismiss", "axeptio_btn_acceptAll", "axeptio_main_button"):
        button = page.locator(f"#{button_id}").first
        if await button.count():
            await button.click(timeout=5_000)
            break


async def login_to_matches(
    context: BrowserContext,
    login_url: str,
    matches_url: str,
    email: str,
    password: str,
    logger: logging.Logger,
) -> Page:
    page = await context.new_page()
    await page.goto(login_url, wait_until="networkidle", timeout=120_000)
    email_locator = page.locator('input[type="email"], input[name="email"]')
    password_locator = page.locator('input[type="password"], input[name="password"]')
    login_button = page.get_by_role("button", name="Se connecter")
    await email_locator.first.fill(email)
    await password_locator.first.fill(password)
    await login_button.first.click()
    try:
        await page.wait_for_url(_wait_pattern_from_url(matches_url), timeout=120_000)
    except PlaywrightTimeoutError as exc:
        await page.close()
        raise RuntimeError(f"Login did not reach jobs-matches: {matches_url}") from exc
    await page.wait_for_load_state("networkidle", timeout=120_000)
    await _dismiss_cookie_overlay(page)
    logger.info("Authenticated on jobs-matches")
    return page
