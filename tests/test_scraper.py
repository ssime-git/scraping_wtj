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
