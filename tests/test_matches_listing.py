from typing import Any

import pytest

from wttj_scraper.matches_listing import (
    accumulate_family_candidates,
    dedupe_listing_urls,
    extract_listing_cards,
    keep_role_matches,
    tag_listing_cards,
)


def test_dedupe_listing_urls_keeps_first_seen_order():
    rows: list[dict[str, str | None]] = [
        {"url": "https://example.com/1", "title": "A"},
        {"url": "https://example.com/2", "title": "B"},
        {"url": "https://example.com/1", "title": "A again"},
    ]

    deduped = dedupe_listing_urls(rows)

    assert [row["url"] for row in deduped] == [
        "https://example.com/1",
        "https://example.com/2",
    ]


@pytest.mark.asyncio
async def test_extract_listing_cards_reads_link_text_and_href():
    page: Any = type("Page", (), {})()
    locator_calls: list[str] = []
    evaluate_all_scripts: list[str] = []

    class Locator:
        async def evaluate_all(self, _script: str):
            evaluate_all_scripts.append(_script)
            return [
                {
                    "url": "https://example.com/1",
                    "title": "Data Engineer",
                    "snippet": "Paris CDI",
                },
                {
                    "url": "https://example.com/2",
                    "title": "MLOps Engineer",
                    "snippet": "Lyon CDI",
                },
            ]

    def locator(selector: str):
        locator_calls.append(selector)
        return Locator()

    page.locator = locator

    cards = await extract_listing_cards(page)

    assert cards[0]["title"] == "Data Engineer"
    assert cards[1]["url"] == "https://example.com/2"
    assert locator_calls == ['[data-testid^="job-card-"]']
    assert 'a[href*="/jobs/"]' in evaluate_all_scripts[0]
    assert "body-lg-strong" in evaluate_all_scripts[0]
    assert "replace(/\\s+/g, ' ')" in evaluate_all_scripts[0]


def test_accumulate_family_candidates_accumulates_until_cap():
    existing: list[dict[str, str | None]] = [
        {"url": "https://example.com/1", "title": "A", "snippet": "a"}
    ]
    fresh: list[dict[str, str | None]] = [
        {"url": "https://example.com/1", "title": "A", "snippet": "a"},
        {"url": "https://example.com/2", "title": "B", "snippet": "b"},
    ]

    merged = accumulate_family_candidates(existing, fresh, limit=2)

    assert [row["url"] for row in merged] == [
        "https://example.com/1",
        "https://example.com/2",
    ]


def test_tag_listing_cards_keeps_the_role_variant_that_found_the_card():
    rows = [{"url": "https://example.com/1", "title": "Analytics Engineer", "snippet": "Paris"}]

    tagged = tag_listing_cards(rows, "Analytics Engineer")

    assert tagged == [
        {
            "url": "https://example.com/1",
            "title": "Analytics Engineer",
            "snippet": "Paris",
            "matched_role_query": "Analytics Engineer",
        }
    ]


def test_keep_role_matches_drops_cards_unrelated_to_active_role():
    rows = [
        {"url": "https://example.com/1", "title": "Data Engineer", "snippet": "Spark"},
        {"url": "https://example.com/2", "title": "Product Owner", "snippet": "Delivery"},
    ]

    kept = keep_role_matches(rows, "Data Engineer")

    assert [row["url"] for row in kept] == ["https://example.com/1"]


def test_keep_role_matches_handles_french_role_variants():
    rows = [
        {"url": "https://example.com/1", "title": "Ingénieur cybersécurité", "snippet": ""},
        {"url": "https://example.com/2", "title": "Ingénieur IA", "snippet": ""},
    ]

    assert [row["url"] for row in keep_role_matches(rows, "Cybersecurity")] == [
        "https://example.com/1"
    ]
    assert [row["url"] for row in keep_role_matches(rows, "ML Engineer")] == [
        "https://example.com/2"
    ]
