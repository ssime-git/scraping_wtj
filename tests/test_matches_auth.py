import logging
from unittest.mock import call
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from wttj_scraper.matches_auth import login_to_matches


@pytest.mark.asyncio
async def test_login_to_matches_fills_credentials_and_waits_for_matches_url():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_url = AsyncMock()
    page.close = AsyncMock()
    page.url = "https://example.test/login"
    email_locator = AsyncMock()
    email_locator.first.wait_for = AsyncMock()
    email_locator.first.fill = AsyncMock()
    password_locator = AsyncMock()
    password_locator.first.wait_for = AsyncMock()
    password_locator.first.fill = AsyncMock()
    login_button = AsyncMock()
    login_button.first.click = AsyncMock()
    cookie_dismiss = AsyncMock()
    cookie_dismiss.first.count = AsyncMock(return_value=1)
    cookie_dismiss.first.click = AsyncMock()
    cookie_accept = AsyncMock()
    cookie_accept.first.count = AsyncMock(return_value=0)
    cookie_accept.first.click = AsyncMock()
    cookie_main = AsyncMock()
    cookie_main.first.count = AsyncMock(return_value=0)
    cookie_main.first.click = AsyncMock()
    preferences_heading = AsyncMock()
    preferences_heading.first.wait_for = AsyncMock()
    preferences_button = AsyncMock()
    preferences_button.first.wait_for = AsyncMock()
    cookie_dismiss_after = AsyncMock()
    cookie_dismiss_after.first.count = AsyncMock(return_value=1)
    cookie_dismiss_after.first.click = AsyncMock()
    page.get_by_role = MagicMock(return_value=login_button)
    page.get_by_text = MagicMock(return_value=preferences_heading)
    page.get_by_role = MagicMock(side_effect=[login_button, preferences_button])
    page.locator = MagicMock(
        side_effect=[
            cookie_dismiss,
            email_locator,
            password_locator,
            cookie_dismiss_after,
        ]
    )
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
    assert page.goto.await_args_list == [
        call("https://example.test/login", wait_until="domcontentloaded", timeout=120_000),
        call("https://example.test/matches", wait_until="domcontentloaded", timeout=120_000),
    ]
    assert page.wait_for_url.await_args_list == [
        call("**/matches", timeout=30_000),
        call("**/matches", timeout=120_000),
    ]
    email_locator.first.wait_for.assert_awaited_once_with(state="visible", timeout=120_000)
    password_locator.first.wait_for.assert_awaited_once_with(state="visible", timeout=120_000)
    email_locator.first.fill.assert_awaited_once_with("user@example.com")
    password_locator.first.fill.assert_awaited_once_with("secret")
    login_button.first.click.assert_awaited_once()
    preferences_heading.first.wait_for.assert_awaited_once_with(state="visible", timeout=120_000)
    preferences_button.first.wait_for.assert_awaited_once_with(state="visible", timeout=120_000)
    cookie_dismiss.first.click.assert_awaited_once_with(timeout=5_000)
    cookie_dismiss_after.first.click.assert_awaited_once_with(timeout=5_000)


@pytest.mark.asyncio
async def test_login_to_matches_raises_when_redirect_never_happens():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_url = AsyncMock(side_effect=[PlaywrightTimeoutError("no redirect"), PlaywrightTimeoutError("still no matches page")])
    page.close = AsyncMock()
    page.url = "https://example.test/login"
    email_locator = AsyncMock()
    email_locator.first.wait_for = AsyncMock()
    email_locator.first.fill = AsyncMock()
    password_locator = AsyncMock()
    password_locator.first.wait_for = AsyncMock()
    password_locator.first.fill = AsyncMock()
    login_button = AsyncMock()
    login_button.first.click = AsyncMock()
    cookie_dismiss = AsyncMock()
    cookie_dismiss.first.count = AsyncMock(return_value=0)
    cookie_accept = AsyncMock()
    cookie_accept.first.count = AsyncMock(return_value=0)
    cookie_main = AsyncMock()
    cookie_main.first.count = AsyncMock(return_value=0)
    preferences_heading = AsyncMock()
    preferences_heading.first.wait_for = AsyncMock(side_effect=PlaywrightTimeoutError("no matches page"))
    debug_screenshot = AsyncMock()
    debug_content = AsyncMock(return_value="<html></html>")
    body_locator = AsyncMock()
    body_locator.inner_text = AsyncMock(return_value="body")
    page.screenshot = debug_screenshot
    page.content = debug_content
    page.title = AsyncMock(return_value="title")
    page.get_by_text = MagicMock(return_value=preferences_heading)
    page.locator = MagicMock(
        side_effect=[cookie_dismiss, cookie_accept, cookie_main, email_locator, password_locator, body_locator]
    )
    page.get_by_role = MagicMock(side_effect=[login_button, AsyncMock()])
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


@pytest.mark.asyncio
async def test_login_to_matches_tolerates_aborted_navigation_when_redirect_continues():
    page = AsyncMock()
    page.goto = AsyncMock(side_effect=[None, PlaywrightError("Page.goto: net::ERR_ABORTED")])
    page.wait_for_url = AsyncMock(side_effect=[PlaywrightTimeoutError("no redirect"), None])
    page.close = AsyncMock()
    page.url = "https://example.test/login"
    email_locator = AsyncMock()
    email_locator.first.wait_for = AsyncMock()
    email_locator.first.fill = AsyncMock()
    password_locator = AsyncMock()
    password_locator.first.wait_for = AsyncMock()
    password_locator.first.fill = AsyncMock()
    login_button = AsyncMock()
    login_button.first.click = AsyncMock()
    cookie_dismiss = AsyncMock()
    cookie_dismiss.first.count = AsyncMock(return_value=0)
    cookie_accept = AsyncMock()
    cookie_accept.first.count = AsyncMock(return_value=0)
    cookie_main = AsyncMock()
    cookie_main.first.count = AsyncMock(return_value=0)
    preferences_heading = AsyncMock()
    preferences_heading.first.wait_for = AsyncMock()
    preferences_button = AsyncMock()
    preferences_button.first.wait_for = AsyncMock()
    cookie_dismiss_after = AsyncMock()
    cookie_dismiss_after.first.count = AsyncMock(return_value=0)
    page.get_by_text = MagicMock(return_value=preferences_heading)
    page.get_by_role = MagicMock(side_effect=[login_button, preferences_button])
    page.locator = MagicMock(
        side_effect=[
            cookie_dismiss,
            cookie_accept,
            cookie_main,
            email_locator,
            password_locator,
            cookie_dismiss_after,
            cookie_accept,
            cookie_main,
        ]
    )
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
    page.goto.assert_has_awaits(
        [
            call("https://example.test/login", wait_until="domcontentloaded", timeout=120_000),
            call("https://example.test/matches", wait_until="domcontentloaded", timeout=120_000),
        ]
    )
