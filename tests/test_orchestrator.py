from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from wttj_models.job import JobDetail
from wttj_scraper.config import AuthConfig, FamilyConfig, FiltersConfig, LimitsConfig, MatchesConfig, OutputConfig, TimingConfig
from wttj_scraper.orchestrator import collect_family_jobs


@pytest.mark.asyncio
async def test_collect_family_jobs_stops_after_limit():
    page = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    family = FamilyConfig(roles=["Data Engineer", "Analytics Engineer"])
    limits = LimitsConfig(max_jobs_per_family=2, max_pages_per_role=5)
    timing = TimingConfig(
        action_delay_seconds=(0.0, 0.0),
        family_delay_seconds=(0.0, 0.0),
        detail_delay_seconds=(0.0, 0.0),
    )

    scrape_detail_mock = AsyncMock(
        side_effect=[
            JobDetail(title="A", url="https://example.com/1", snippet="a"),
            JobDetail(title="B", url="https://example.com/2", snippet="b"),
        ]
    )

    with (
        patch("wttj_scraper.orchestrator.apply_role_variant", AsyncMock()),
        patch(
            "wttj_scraper.orchestrator.extract_listing_cards",
            AsyncMock(
                return_value=[
                    {"url": "https://example.com/1", "title": "A", "snippet": "a"},
                    {"url": "https://example.com/2", "title": "B", "snippet": "b"},
                ]
            ),
        ),
        patch("wttj_scraper.orchestrator.scrape_detail", scrape_detail_mock),
    ):
        jobs = await collect_family_jobs(page, AsyncMock(), family, limits, timing, "data_engineer")

    assert len(jobs) == 2
    assert jobs[0].url == "https://example.com/1"
    first_listing = scrape_detail_mock.await_args_list[0].args[1]
    assert first_listing.role_family == "data_engineer"
    assert first_listing.matched_role_query == "Data Engineer"


@pytest.mark.asyncio
async def test_run_authenticated_matches_returns_scrape_result():
    config = MatchesConfig(
        auth=AuthConfig(
            login_url="https://example.test/login",
            matches_url="https://example.test/matches",
            email_env="WTTJ_EMAIL",
            password_env="WTTJ_PASSWORD",
            email="user@example.test",
            password="secret",
        ),
        global_filters=FiltersConfig(
            location=["Paris"],
            experience=["3 years"],
            remote=["Hybrid"],
            contract=["CDI"],
            salary=["50k"],
        ),
        families={"data_engineer": FamilyConfig(roles=["Data Engineer"])},
        limits=LimitsConfig(max_jobs_per_family=1, max_pages_per_role=1),
        timing=TimingConfig(
            action_delay_seconds=(0.0, 0.0),
            family_delay_seconds=(0.0, 0.0),
            detail_delay_seconds=(0.0, 0.0),
        ),
        output=OutputConfig(),
    )
    page = AsyncMock()
    apply_global_filters_mock = AsyncMock()

    with (
        patch("wttj_scraper.orchestrator.login_to_matches", AsyncMock(return_value=page)),
        patch("wttj_scraper.orchestrator.apply_global_filters", apply_global_filters_mock),
        patch(
            "wttj_scraper.orchestrator.collect_family_jobs",
            AsyncMock(return_value=[JobDetail(title="A", url="https://example.com/1", snippet="a")]),
        ),
    ):
        from wttj_scraper.orchestrator import run_authenticated_matches

        result = await run_authenticated_matches(AsyncMock(), config, logging.getLogger("test"))

    assert result.count == 1
    assert result.source == "https://example.test/matches"
    assert result.jobs[0].url == "https://example.com/1"
    page.close.assert_awaited_once()
    apply_global_filters_mock.assert_awaited_once_with(
        page,
        location=["Paris"],
        experience=["3 years"],
        remote=["Hybrid"],
        contract=["CDI"],
        salary=["50k"],
    )


@pytest.mark.asyncio
async def test_run_authenticated_matches_closes_page_when_collection_fails():
    config = SimpleNamespace(
        auth=SimpleNamespace(
            login_url="https://example.test/login",
            matches_url="https://example.test/matches",
            email="user@example.test",
            password="secret",
        ),
        global_filters=SimpleNamespace(
            location=[],
            experience=[],
            remote=[],
            contract=[],
            salary=[],
        ),
        families={"data_engineer": FamilyConfig(roles=["Data Engineer"])},
        limits=LimitsConfig(max_jobs_per_family=1, max_pages_per_role=1),
        timing=TimingConfig(
            action_delay_seconds=(0.0, 0.0),
            family_delay_seconds=(0.0, 0.0),
            detail_delay_seconds=(0.0, 0.0),
        ),
    )
    page = AsyncMock()

    with (
        patch("wttj_scraper.orchestrator.login_to_matches", AsyncMock(return_value=page)),
        patch("wttj_scraper.orchestrator.apply_global_filters", AsyncMock()),
        patch("wttj_scraper.orchestrator.collect_family_jobs", AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        from wttj_scraper.orchestrator import run_authenticated_matches

        with pytest.raises(RuntimeError, match="boom"):
            await run_authenticated_matches(AsyncMock(), config, logging.getLogger("test"))

    page.close.assert_awaited_once()
