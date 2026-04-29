import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from wttj_scraper.matches_auth import login_to_matches


@pytest.mark.asyncio
async def test_login_to_matches_fills_credentials_and_waits_for_matches_url():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_url = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    email_locator = AsyncMock()
    email_locator.first.fill = AsyncMock()
    password_locator = AsyncMock()
    password_locator.first.fill = AsyncMock()
    login_button = AsyncMock()
    login_button.first.click = AsyncMock()
    cookie_button = AsyncMock()
    cookie_button.first.count = AsyncMock(return_value=1)
    cookie_button.first.click = AsyncMock()
    page.locator = MagicMock(side_effect=[email_locator, password_locator])
    page.get_by_role = MagicMock(return_value=login_button)
    page.locator = MagicMock(side_effect=[email_locator, password_locator, cookie_button])
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)

    result = await login_to_matches(
        context=context,
        login_url="https://example.test/login",
        matches_url="https://example.test/matches",
        email="user@example.com",
        password="secret",
        logger=logging.getLogger("test"),
    )

    assert result is page
    page.goto.assert_awaited_once()
    email_locator.first.fill.assert_awaited_once_with("user@example.com")
    password_locator.first.fill.assert_awaited_once_with("secret")
    login_button.first.click.assert_awaited_once()
    page.wait_for_url.assert_awaited_once_with("**/matches", timeout=120_000)
    cookie_button.first.click.assert_awaited_once_with(timeout=5_000)


@pytest.mark.asyncio
async def test_login_to_matches_raises_when_redirect_never_happens():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_url = AsyncMock(side_effect=PlaywrightTimeoutError("no redirect"))
    page.wait_for_load_state = AsyncMock()
    page.close = AsyncMock()
    email_locator = AsyncMock()
    email_locator.first.fill = AsyncMock()
    password_locator = AsyncMock()
    password_locator.first.fill = AsyncMock()
    login_button = AsyncMock()
    login_button.first.click = AsyncMock()
    page.locator = MagicMock(side_effect=[email_locator, password_locator])
    page.get_by_role = MagicMock(return_value=login_button)
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)

    with pytest.raises(RuntimeError, match="jobs-matches"):
        await login_to_matches(
            context=context,
            login_url="https://example.test/login",
            matches_url="https://example.test/matches",
            email="user@example.com",
            password="secret",
            logger=logging.getLogger("test"),
        )
    page.close.assert_awaited_once()
