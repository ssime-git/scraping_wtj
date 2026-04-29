from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import random

from playwright.async_api import BrowserContext, Page
from tqdm import tqdm
from wttj_models.job import JobDetail, JobListing, ScrapeResult
from wttj_scraper.config import FamilyConfig, LimitsConfig, MatchesConfig, TimingConfig
from wttj_scraper.detail import scrape_detail
from wttj_scraper.matches_auth import login_to_matches
from wttj_scraper.matches_filters import apply_global_filters, apply_role_variant
from wttj_scraper.matches_listing import accumulate_family_candidates, extract_listing_cards


async def _sleep_range(delay_range: tuple[float, float]) -> None:
    await asyncio.sleep(random.uniform(*delay_range))


async def collect_family_jobs(
    page: Page,
    context: BrowserContext,
    family: FamilyConfig,
    limits: LimitsConfig,
    timing: TimingConfig,
    family_name: str,
) -> list[JobDetail]:
    candidates: list[dict[str, str | None]] = []
    matched_role_query: str | None = None
    for role in family.roles:
        await apply_role_variant(page, role)
        await _sleep_range(timing.action_delay_seconds)
        cards = await extract_listing_cards(page)
        candidates = accumulate_family_candidates(candidates, cards, limits.max_jobs_per_family)
        if cards and matched_role_query is None:
            matched_role_query = role
        if len(candidates) >= limits.max_jobs_per_family:
            break

    results: list[JobDetail] = []
    for row in tqdm(candidates, desc=family_name, leave=False):
        listing = JobListing(
            title=row.get("title"),
            url=row["url"],
            snippet=row.get("snippet"),
            role_family=family_name,
            matched_role_query=matched_role_query,
        )
        detail = await scrape_detail(context, listing)
        results.append(detail)
        await _sleep_range(timing.detail_delay_seconds)
    return results


async def run_authenticated_matches(
    context: BrowserContext,
    config: MatchesConfig,
    logger: logging.Logger,
) -> ScrapeResult:
    page = await login_to_matches(
        context=context,
        login_url=config.auth.login_url,
        matches_url=config.auth.matches_url,
        email=config.auth.email,
        password=config.auth.password,
        logger=logger,
    )
    try:
        await apply_global_filters(
            page,
            location=config.global_filters.location,
            experience=config.global_filters.experience,
            remote=config.global_filters.remote,
            contract=config.global_filters.contract,
            salary=config.global_filters.salary,
        )
        jobs: list[JobDetail] = []
        for family_name, family in tqdm(config.families.items(), desc="families"):
            jobs.extend(await collect_family_jobs(page, context, family, config.limits, config.timing, family_name))
            await _sleep_range(config.timing.family_delay_seconds)
        return ScrapeResult(
            source=config.auth.matches_url,
            count=len(jobs),
            jobs=jobs,
            scraped_at=datetime.now(timezone.utc),
        )
    finally:
        await page.close()
