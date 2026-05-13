from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from playwright.async_api import Error

from wttj_scraper.browser import browser_context


@pytest.mark.asyncio
async def test_browser_context_yields_context():
    mock_browser = AsyncMock()
    mock_ctx = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_ctx)

    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch("wttj_scraper.browser.async_playwright", return_value=mock_playwright):
        async with browser_context() as ctx:
            assert ctx is mock_ctx

    mock_ctx.close.assert_awaited_once()
    mock_browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_context_closes_on_exception():
    mock_browser = AsyncMock()
    mock_ctx = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_ctx)

    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch("wttj_scraper.browser.async_playwright", return_value=mock_playwright):
        with pytest.raises(RuntimeError):
            async with browser_context():
                raise RuntimeError("boom")

    mock_ctx.close.assert_awaited_once()
    mock_browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_context_installs_chromium_when_missing():
    mock_browser = AsyncMock()
    mock_ctx = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_ctx)

    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    mock_playwright.chromium.launch = AsyncMock(
        side_effect=[
            Error("BrowserType.launch: Executable doesn't exist at /tmp/missing/chrome"),
            mock_browser,
        ]
    )

    with (
        patch("wttj_scraper.browser.async_playwright", return_value=mock_playwright),
        patch("wttj_scraper.browser.subprocess.run") as mock_run,
    ):
        async with browser_context() as ctx:
            assert ctx is mock_ctx

    mock_run.assert_called_once()
    mock_playwright.chromium.launch.assert_awaited()
    assert mock_playwright.chromium.launch.await_count == 2
    mock_ctx.close.assert_awaited_once()
    mock_browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_context_uses_persistent_profile_when_requested():
    mock_ctx = AsyncMock()

    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    mock_playwright.chromium.launch_persistent_context = AsyncMock(return_value=mock_ctx)

    profile_dir = Path("/tmp/wttj-profile")
    with patch("wttj_scraper.browser.async_playwright", return_value=mock_playwright):
        async with browser_context(profile_dir=profile_dir) as ctx:
            assert ctx is mock_ctx

    mock_playwright.chromium.launch_persistent_context.assert_awaited_once()
    args, kwargs = mock_playwright.chromium.launch_persistent_context.await_args
    assert kwargs["user_data_dir"] == str(profile_dir)
    assert kwargs["headless"] is True
    assert kwargs["locale"] == "fr-FR"
    assert kwargs["timezone_id"] == "Europe/Paris"
    mock_ctx.close.assert_awaited_once()
