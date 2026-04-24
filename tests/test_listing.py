import pytest
from unittest.mock import AsyncMock, patch
from wttj_models.job import JobListing
from wttj_scraper.listing import scrape_listing


@pytest.fixture
def mock_page_with_jobs():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.mouse = AsyncMock()
    page.mouse.wheel = AsyncMock()
    page.evaluate = AsyncMock(
        return_value=[
            {
                "title": "Développeur Python",
                "url": "https://www.welcometothejungle.com/fr/companies/acme/jobs/dev-python",
                "snippet": "Acme · Paris · CDI",
            },
            {
                "title": "Data Engineer",
                "url": "https://www.welcometothejungle.com/fr/companies/beta/jobs/data-eng",
                "snippet": "Beta · Lyon · CDI",
            },
        ]
    )
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_context_with_jobs(mock_page_with_jobs):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page_with_jobs)
    return context


@pytest.mark.asyncio
async def test_scrape_listing_returns_job_listings(mock_context_with_jobs):
    url = "https://www.welcometothejungle.com/fr/jobs"
    results = await scrape_listing(mock_context_with_jobs, url, max_jobs=30)

    assert len(results) == 2
    assert all(isinstance(j, JobListing) for j in results)
    assert results[0].title == "Développeur Python"
    assert results[1].url == "https://www.welcometothejungle.com/fr/companies/beta/jobs/data-eng"


@pytest.mark.asyncio
async def test_scrape_listing_navigates_and_scrolls(mock_context_with_jobs, mock_page_with_jobs):
    url = "https://www.welcometothejungle.com/fr/jobs"
    await scrape_listing(mock_context_with_jobs, url)

    mock_page_with_jobs.goto.assert_awaited_once_with(
        url, wait_until="domcontentloaded", timeout=60_000
    )
    mock_page_with_jobs.mouse.wheel.assert_awaited_once_with(0, 2500)


@pytest.mark.asyncio
async def test_scrape_listing_closes_page(mock_context_with_jobs, mock_page_with_jobs):
    await scrape_listing(mock_context_with_jobs, "https://www.welcometothejungle.com/fr/jobs")
    mock_page_with_jobs.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_listing_closes_page_on_error(mock_context_with_jobs, mock_page_with_jobs):
    mock_page_with_jobs.goto = AsyncMock(side_effect=TimeoutError("timeout"))
    with pytest.raises(TimeoutError):
        await scrape_listing(mock_context_with_jobs, "https://www.welcometothejungle.com/fr/jobs")
    mock_page_with_jobs.close.assert_awaited_once()
