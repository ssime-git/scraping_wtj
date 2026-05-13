from contextlib import asynccontextmanager
from pathlib import Path
import subprocess
import sys
from typing import AsyncGenerator

from playwright.async_api import BrowserContext, Error, async_playwright

_PLAYWRIGHT_INSTALL_COMMAND = [sys.executable, "-m", "playwright", "install", "chromium"]
_DEFAULT_VIEWPORT = {"width": 1440, "height": 900}
_DEFAULT_LOCALE = "fr-FR"
_DEFAULT_TIMEZONE = "Europe/Paris"


def _missing_browser_error(error: Exception) -> bool:
    message = str(error)
    return "Executable doesn't exist" in message or "playwright install" in message.lower()


def _install_chromium() -> None:
    subprocess.run(_PLAYWRIGHT_INSTALL_COMMAND, check=True)


async def _launch_chromium(playwright, headless: bool):
    try:
        return await playwright.chromium.launch(headless=headless)
    except Error as error:
        if not _missing_browser_error(error):
            raise
        _install_chromium()
        return await playwright.chromium.launch(headless=headless)


async def _launch_with_retry(launch_fn):
    try:
        return await launch_fn()
    except Error as error:
        if not _missing_browser_error(error):
            raise
        _install_chromium()
        return await launch_fn()


def _context_kwargs() -> dict[str, object]:
    return {
        "locale": _DEFAULT_LOCALE,
        "timezone_id": _DEFAULT_TIMEZONE,
        "viewport": _DEFAULT_VIEWPORT,
    }


@asynccontextmanager
async def browser_context(
    headless: bool = True,
    *,
    profile_dir: Path | None = None,
    storage_state_path: Path | None = None,
) -> AsyncGenerator[BrowserContext, None]:
    async with async_playwright() as p:
        if profile_dir is not None:
            profile_dir.mkdir(parents=True, exist_ok=True)

            async def _launch_persistent():
                return await p.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=headless,
                    **_context_kwargs(),
                )

            context = await _launch_with_retry(_launch_persistent)
            try:
                yield context
            finally:
                await context.close()
            return

        browser = await _launch_chromium(p, headless)
        context_kwargs = _context_kwargs()
        if storage_state_path is not None and storage_state_path.exists():
            context_kwargs["storage_state"] = str(storage_state_path)
        context = await browser.new_context(**context_kwargs)
        try:
            yield context
        finally:
            await context.close()
            await browser.close()
