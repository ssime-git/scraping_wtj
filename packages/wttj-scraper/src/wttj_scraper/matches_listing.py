from __future__ import annotations

from collections.abc import Iterable

from playwright.async_api import Page


async def extract_listing_cards(page: Page) -> list[dict[str, str | None]]:
    return await page.locator('a[href*="/jobs/"]').evaluate_all(
        """
        els => {
            const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
            const uniqueTexts = (nodes) => {
                const out = [];
                for (const node of nodes) {
                    const text = normalize(node.textContent);
                    if (text && !out.includes(text)) out.push(text);
                }
                return out;
            };
            return els.map(el => {
                const url = el.href;
                const title =
                    uniqueTexts(el.querySelectorAll("p[class*='heading-md'], p[class*='heading-sm'], h1, h2, h3, h4"))[0] ||
                    null;
                const company =
                    uniqueTexts(el.querySelectorAll("p[class*='body-lg-strong'], p[class*='body-md-strong']"))[0] ||
                    null;
                const description =
                    uniqueTexts(el.querySelectorAll("p[class*='body-lg']:not([class*='strong'])"))[0] ||
                    null;
                const chips = uniqueTexts(el.querySelectorAll("div[class*='_variant-warm'] span"));
                const dates = uniqueTexts(el.querySelectorAll("div[class*='text-neutral-70']"));
                const snippetParts = [company, description, ...chips, ...dates].filter(Boolean);
                return {
                    url,
                    title,
                    snippet: snippetParts.join(' ') || null,
                };
            }).filter(row => row.url && row.title);
        }
        """
    )


def dedupe_listing_urls(rows: Iterable[dict[str, str | None]]) -> list[dict[str, str | None]]:
    out: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for row in rows:
        url = row.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(row)
    return out


def accumulate_family_candidates(
    existing: list[dict[str, str | None]],
    fresh: list[dict[str, str | None]],
    limit: int,
) -> list[dict[str, str | None]]:
    merged = dedupe_listing_urls([*existing, *fresh])
    return merged[:limit]
