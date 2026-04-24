import pytest
from unittest.mock import AsyncMock
from wttj_models.job import JobDetail, JobListing
from wttj_scraper.detail import parse_summary_metadata, scrape_detail


@pytest.fixture
def base_listing():
    return JobListing(
        title="Dev Python",
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev-python",
        snippet="Acme · Paris",
    )


@pytest.fixture
def mock_detail_page():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock(
        return_value={
            "page_title": "Dev Python | Acme | Welcome to the Jungle",
            "text_preview": "Nous recherchons un développeur Python confirmé...",
            "company_name": "Theraclion",
            "contract_type": "Alternance",
            "remote_level": "Télétravail occasionnel",
            "city": "Malakoff",
            "company_sectors": ["MedTech", "AI"],
            "languages_required": ["French", "English"],
            "description_raw": "Description section",
            "missions_raw": "Mission section",
            "profile_raw": "Profile section",
        }
    )
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_context_detail(mock_detail_page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_detail_page)
    return context


@pytest.mark.asyncio
async def test_scrape_detail_returns_job_detail(mock_context_detail, base_listing):
    result = await scrape_detail(mock_context_detail, base_listing)

    assert isinstance(result, JobDetail)
    assert result.url == base_listing.url
    assert result.title == base_listing.title
    assert result.page_title == "Dev Python | Acme | Welcome to the Jungle"
    assert "développeur" in result.text_preview
    assert result.company_name == "Theraclion"
    assert result.contract_type == "Alternance"
    assert result.remote_level == "Télétravail occasionnel"
    assert result.city == "Malakoff"
    assert result.languages_required == ["French", "English"]
    assert result.error is None


@pytest.mark.asyncio
async def test_scrape_detail_stores_error_on_timeout(mock_context_detail, mock_detail_page, base_listing):
    mock_detail_page.goto = AsyncMock(side_effect=TimeoutError("page timeout"))
    result = await scrape_detail(mock_context_detail, base_listing)

    assert isinstance(result, JobDetail)
    assert result.error is not None
    assert "timeout" in result.error.lower()
    assert result.page_title is None


@pytest.mark.asyncio
async def test_scrape_detail_closes_page(mock_context_detail, mock_detail_page, base_listing):
    await scrape_detail(mock_context_detail, base_listing)
    mock_detail_page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_detail_closes_page_on_error(mock_context_detail, mock_detail_page, base_listing):
    mock_detail_page.evaluate = AsyncMock(side_effect=RuntimeError("js error"))
    result = await scrape_detail(mock_context_detail, base_listing)
    mock_detail_page.close.assert_awaited_once()
    assert result.error is not None


def test_parse_summary_metadata_extracts_atomic_fields():
    summary = (
        "Groupe SII Alternance Assistant communication H/F Siege Alternance Paris "
        "Teletravail non autorise Salaire : Non specifie Education : Bac +5 / Master "
        "avant-hier"
    )
    metadata = parse_summary_metadata(summary)
    assert metadata["contract_type"] == "Alternance"
    assert metadata["city"] == "Paris"
    assert metadata["remote_level"] == "Teletravail non autorise"
    assert metadata["date_posted_label"] == "avant-hier"
