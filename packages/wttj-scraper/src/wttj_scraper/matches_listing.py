from __future__ import annotations

from collections.abc import Iterable
import re
import unicodedata

from playwright.async_api import Page


async def extract_listing_cards(page: Page) -> list[dict[str, str | None]]:
    # Cards are now div[data-testid^="job-card-"]; the <a href*="/jobs/"> is the
    # title element itself (text content), not a wrapper with <p> children.
    return await page.locator('[data-testid^="job-card-"]').evaluate_all(
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
                const anchor = el.querySelector('a[href*="/jobs/"]');
                if (!anchor) return null;
                const url = anchor.href;
                const title = normalize(anchor.textContent) || null;
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
            }).filter(row => row && row.url && row.title);
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


def _fold(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def _role_tokens(role: str) -> list[str]:
    tokens = [
        token
        for token in re.findall(r"[\w]+", _fold(role))
        if len(token) > 2 or token in {"ai", "bi", "ml"}
    ]
    aliases = {
        "ai": ["ia"],
        "cybersecurity": ["cyber", "securite"],
        "engineer": ["ingenieur"],
        "ml": ["ia"],
    }
    expanded = tokens + [alias for token in tokens for alias in aliases.get(token, [])]
    generic = {"analyst", "engineer", "ingenieur", "scientist"}
    specific = [token for token in expanded if token not in generic]
    return specific or expanded


def keep_role_matches(
    rows: Iterable[dict[str, str | None]], role: str
) -> list[dict[str, str | None]]:
    tokens = _role_tokens(role)
    if not tokens:
        return list(rows)
    return [
        row
        for row in rows
        if any(
            token in _fold(f"{row.get('title') or ''} {row.get('snippet') or ''}")
            for token in tokens
        )
    ]


def tag_listing_cards(
    rows: Iterable[dict[str, str | None]], role: str
) -> list[dict[str, str | None]]:
    return [{**row, "matched_role_query": role} for row in rows]


def accumulate_family_candidates(
    existing: list[dict[str, str | None]],
    fresh: list[dict[str, str | None]],
    limit: int,
) -> list[dict[str, str | None]]:
    merged = dedupe_listing_urls([*existing, *fresh])
    return merged[:limit]
