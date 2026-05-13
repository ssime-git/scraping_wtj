from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import urlparse
from collections.abc import Callable

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
    for label in ("OK pour moi", "Non merci", "Je choisis"):
        button = page.get_by_role("button", name=label).first
        if await button.count():
            await button.click(timeout=5_000)
            return


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


async def _wait_for_matches_ready(page: Page, *, timeout: int = 120_000) -> None:
    await page.get_by_text("Vos préférences", exact=True).first.wait_for(state="visible", timeout=timeout)
    await page.get_by_text("Enregistrer", exact=True).first.wait_for(state="visible", timeout=timeout)


async def _first_visible_locator(
    candidates: list[Callable[[], object]],
    *,
    description: str,
):
    for _ in range(15):
        for candidate in candidates:
            locator = candidate()
            if await locator.count():
                return locator.first
        await asyncio.sleep(1)
    raise RuntimeError(f"Could not find visible {description}")


async def login_to_matches(
    context: BrowserContext,
    login_url: str,
    matches_url: str,
    email: str,
    password: str,
    logger: logging.Logger,
    auth_state_path: Path | None = None,
) -> Page:
    page = await context.new_page()
    try:
        await page.goto(matches_url, wait_until="domcontentloaded", timeout=30_000)
        if page.url.startswith(matches_url):
            await _wait_for_matches_ready(page, timeout=10_000)
            if auth_state_path is not None:
                await page.context.storage_state(path=str(auth_state_path))
            logger.info("Reused existing authenticated session on jobs-matches")
            return page
    except (PlaywrightTimeoutError, PlaywrightError):
        logger.info("Existing session did not open jobs-matches cleanly; falling back to login")
    await page.goto(login_url, wait_until="domcontentloaded", timeout=120_000)
    await _dismiss_cookie_overlay(page)
    try:
        email_field = await _first_visible_locator(
            [
                lambda: page.locator('input[type="email"]'),
                lambda: page.locator('input[name="email"]'),
                lambda: page.locator('input[autocomplete="email"]'),
                lambda: page.locator('input[placeholder*="mail" i]'),
                lambda: page.get_by_label("E-mail"),
                lambda: page.get_by_label("Email"),
            ],
            description="email field",
        )
        password_field = await _first_visible_locator(
            [
                lambda: page.locator('input[type="password"]'),
                lambda: page.locator('input[name="password"]'),
                lambda: page.locator('input[autocomplete="current-password"]'),
                lambda: page.locator('input[placeholder*="password" i]'),
                lambda: page.locator('input[placeholder*="mot de passe" i]'),
                lambda: page.get_by_label("Mot de passe"),
                lambda: page.get_by_label("Password"),
            ],
            description="password field",
        )
        login_button = await _first_visible_locator(
            [
                lambda: page.get_by_role("button", name="Se connecter"),
                lambda: page.get_by_role("button", name="Sign in"),
                lambda: page.get_by_role("button", name="Login"),
                lambda: page.get_by_role("button", name="Continue"),
                lambda: page.get_by_role("button", name="Log in"),
            ],
            description="sign in button",
        )
    except RuntimeError:
        await _write_debug_artifacts(page, logger)
        await page.close()
        raise
    await email_field.fill(email)
    await password_field.fill(password)
    await login_button.click()
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
        await _dismiss_cookie_overlay(page)
        await _wait_for_matches_ready(page)
        if auth_state_path is not None:
            await page.context.storage_state(path=str(auth_state_path))
    except (PlaywrightTimeoutError, PlaywrightError) as exc:
        await _write_debug_artifacts(page, logger)
        await page.close()
        raise RuntimeError(f"Login did not reach jobs-matches: {matches_url}") from exc
    logger.info("Authenticated on jobs-matches")
    return page
