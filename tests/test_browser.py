import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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
