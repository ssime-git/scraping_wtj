import pytest

from wttj_scraper.matches_listing import (
    accumulate_family_candidates,
    dedupe_listing_urls,
    extract_listing_cards,
)


def test_dedupe_listing_urls_keeps_first_seen_order():
    rows = [
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
    page = type("Page", (), {})()
    locator_calls = []
    evaluate_all_scripts = []

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
    assert locator_calls == ['a[href*="/jobs/"]']
    assert "heading-md" in evaluate_all_scripts[0]
    assert "body-lg-strong" in evaluate_all_scripts[0]
    assert "replace(/\\s+/g, ' ')" in evaluate_all_scripts[0]


def test_accumulate_family_candidates_accumulates_until_cap():
    existing = [{"url": "https://example.com/1", "title": "A", "snippet": "a"}]
    fresh = [
        {"url": "https://example.com/1", "title": "A", "snippet": "a"},
        {"url": "https://example.com/2", "title": "B", "snippet": "b"},
    ]

    merged = accumulate_family_candidates(existing, fresh, limit=2)

    assert [row["url"] for row in merged] == [
        "https://example.com/1",
        "https://example.com/2",
    ]
