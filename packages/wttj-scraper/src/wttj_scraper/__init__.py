import asyncio
from datetime import datetime, timezone

from wttj_models.job import ScrapeResult
from wttj_scraper.browser import browser_context
from wttj_scraper.detail import scrape_detail
from wttj_scraper.config import load_matches_config
from wttj_scraper.logging_utils import configure_logger
from wttj_scraper.listing import scrape_listing
from wttj_scraper.orchestrator import run_authenticated_matches

_DELAY_BETWEEN_DETAILS = 1.2


async def scrape(
    url: str,
    max_jobs: int = 30,
    enrich_count: int = 15,
    scroll_count: int = 1,
) -> ScrapeResult:
    async with browser_context() as context:
        listings = await scrape_listing(context, url, max_jobs, scroll_count)
        enriched = []
        for job in listings[:enrich_count]:
            detail = await scrape_detail(context, job)
            enriched.append(detail)
            await asyncio.sleep(_DELAY_BETWEEN_DETAILS)

    return ScrapeResult(
        source=url,
        count=len(enriched),
        jobs=enriched,
        scraped_at=datetime.now(timezone.utc),
    )


async def scrape_authenticated_matches(config_path: str) -> ScrapeResult:
    config = load_matches_config(config_path)
    logger = configure_logger()
    async with browser_context() as context:
        return await run_authenticated_matches(context, config, logger)
