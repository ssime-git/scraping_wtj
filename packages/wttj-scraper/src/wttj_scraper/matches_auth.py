from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeoutError


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


async def _write_debug_artifacts(page: Page, logger: logging.Logger) -> None:
    debug_dir = os.getenv("WTTJ_DEBUG_DIR")
    if not debug_dir:
        return
    target = Path(debug_dir)
    target.mkdir(parents=True, exist_ok=True)
    try:
        screenshot_path = target / "login_failure.png"
        html_path = target / "login_failure.html"
        text_path = target / "login_failure.txt"
        metadata_path = target / "login_failure_meta.txt"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(await page.content(), encoding="utf-8")
        body_text = await page.locator("body").inner_text()
        text_path.write_text(body_text, encoding="utf-8")
        metadata_path.write_text(
            "\n".join(
                [
                    f"url={page.url}",
                    f"title={await page.title()}",
                ]
            ),
            encoding="utf-8",
        )
        logger.warning("Wrote WTTJ debug artifacts to %s", target)
    except Exception as exc:
        logger.warning("Failed to write WTTJ debug artifacts: %s", exc)


async def login_to_matches(
    context: BrowserContext,
    login_url: str,
    matches_url: str,
    email: str,
    password: str,
    logger: logging.Logger,
) -> Page:
    page = await context.new_page()
    await page.goto(login_url, wait_until="domcontentloaded", timeout=120_000)
    await _dismiss_cookie_overlay(page)
    email_locator = page.locator('input[type="email"], input[name="email"]')
    password_locator = page.locator('input[type="password"], input[name="password"]')
    login_button = page.get_by_role("button", name="Se connecter")
    await email_locator.first.wait_for(state="visible", timeout=120_000)
    await password_locator.first.wait_for(state="visible", timeout=120_000)
    await email_locator.first.fill(email)
    await password_locator.first.fill(password)
    await login_button.first.click()
    matches_pattern = _wait_pattern_from_url(matches_url)
    try:
        await page.wait_for_url(matches_pattern, timeout=30_000)
    except PlaywrightTimeoutError:
        logger.info("Login did not auto-redirect to jobs-matches; opening matches page explicitly")
    try:
        if not page.url.startswith(matches_url):
            try:
                await page.goto(matches_url, wait_until="domcontentloaded", timeout=120_000)
            except PlaywrightError as exc:
                if "ERR_ABORTED" not in str(exc):
                    raise
                logger.info("Matches navigation was interrupted by an in-flight redirect; waiting for final URL")
        await page.wait_for_url(matches_pattern, timeout=120_000)
        await page.locator('input[name="futureRole"]').first.wait_for(state="visible", timeout=120_000)
    except (PlaywrightTimeoutError, PlaywrightError) as exc:
        await _write_debug_artifacts(page, logger)
        await page.close()
        raise RuntimeError(f"Login did not reach jobs-matches: {matches_url}") from exc
    await _dismiss_cookie_overlay(page)
    logger.info("Authenticated on jobs-matches")
    return page
