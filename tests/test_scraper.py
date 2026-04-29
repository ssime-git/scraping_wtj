import pytest
from unittest.mock import AsyncMock, patch
from wttj_models.job import JobDetail, JobListing, ScrapeResult
from wttj_scraper import scrape

_LISTING_URL = "https://www.welcometothejungle.com/fr/jobs"

_MOCK_LISTINGS = [
    JobListing(
        title="Dev Python",
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev",
        snippet="Acme · Paris",
    ),
    JobListing(
        title="Data Engineer",
        url="https://www.welcometothejungle.com/fr/companies/beta/jobs/data",
        snippet="Beta · Lyon",
    ),
]

_MOCK_DETAILS = [
    JobDetail(
        title="Dev Python",
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev",
        snippet="Acme · Paris",
        page_title="Dev Python | Acme | WTTJ",
        text_preview="We are looking for...",
    ),
    JobDetail(
        title="Data Engineer",
        url="https://www.welcometothejungle.com/fr/companies/beta/jobs/data",
        snippet="Beta · Lyon",
        page_title="Data Engineer | Beta | WTTJ",
        text_preview="We need a data engineer...",
    ),
]


@pytest.mark.asyncio
async def test_scrape_returns_scrape_result():
    with (
        patch("wttj_scraper.browser_context") as mock_bctx,
        patch("wttj_scraper.scrape_listing", AsyncMock(return_value=_MOCK_LISTINGS)),
        patch("wttj_scraper.scrape_detail", side_effect=_MOCK_DETAILS),
        patch("wttj_scraper.asyncio.sleep", AsyncMock()),
    ):
        mock_bctx.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_bctx.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await scrape(_LISTING_URL, max_jobs=30, enrich_count=2)

    assert isinstance(result, ScrapeResult)
    assert result.source == _LISTING_URL
    assert result.count == 2
    assert len(result.jobs) == 2


@pytest.mark.asyncio
async def test_scrape_limits_enrich_count():
    with (
        patch("wttj_scraper.browser_context") as mock_bctx,
        patch("wttj_scraper.scrape_listing", AsyncMock(return_value=_MOCK_LISTINGS)),
        patch("wttj_scraper.scrape_detail", AsyncMock(return_value=_MOCK_DETAILS[0])),
        patch("wttj_scraper.asyncio.sleep", AsyncMock()),
    ):
        mock_bctx.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_bctx.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await scrape(_LISTING_URL, max_jobs=30, enrich_count=1)

    assert result.count == 1


@pytest.mark.asyncio
async def test_scrape_authenticated_matches_uses_browser_context_and_orchestrator():
    loaded_config = object()
    entered_context = object()
    logger = object()
    expected_result = ScrapeResult(
        source="https://example.test/matches",
        count=1,
        jobs=[
            JobDetail(
                title="A",
                url="https://example.com/1",
                snippet="a",
            )
        ],
    )
    mock_run_authenticated_matches = AsyncMock(return_value=expected_result)
    with (
        patch("wttj_scraper.browser_context") as mock_bctx,
        patch("wttj_scraper.load_matches_config") as mock_load,
        patch("wttj_scraper.configure_logger", return_value=logger),
        patch("wttj_scraper.run_authenticated_matches", mock_run_authenticated_matches),
    ):
        mock_load.return_value = loaded_config
        mock_bctx.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_bctx.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_bctx.return_value.__aenter__.return_value = entered_context
        from wttj_scraper import scrape_authenticated_matches

        result = await scrape_authenticated_matches("config/wttj_matches.yaml")

    mock_load.assert_called_once_with("config/wttj_matches.yaml")
    mock_bctx.assert_called_once_with()
    mock_bctx.return_value.__aenter__.assert_awaited_once()
    mock_run_authenticated_matches.assert_awaited_once_with(entered_context, loaded_config, logger)
    assert result == expected_result
