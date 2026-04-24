import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.mouse = AsyncMock()
    page.mouse.wheel = AsyncMock()
    page.evaluate = AsyncMock()
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_context(mock_page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page)
    context.close = AsyncMock()
    return context
