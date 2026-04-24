from playwright.async_api import BrowserContext
from wttj_models.job import JobListing

_EXTRACT_JS = """
(limit) => {
    const normalize = (v) => (v || '').replace(/\\s+/g, ' ').trim();
    const absolute = (href) => {
        if (!href) return '';
        if (href.startsWith('http')) return href;
        return 'https://www.welcometothejungle.com' + href;
    };
    const anchors = Array.from(document.querySelectorAll("a[href*='/jobs/']"));
    const seen = new Set();
    const out = [];
    for (const a of anchors) {
        const href = absolute(a.getAttribute('href'));
        if (!href || seen.has(href)) continue;
        seen.add(href);
        const card = a.closest('article, li, div');
        const title = normalize(
            a.textContent || card?.querySelector('h2,h3,h4')?.textContent
        );
        const snippet = normalize(card?.textContent || '');
        if (!title && !snippet) continue;
        out.push({ title: title || null, url: href, snippet: snippet || null });
        if (out.length >= limit) break;
    }
    return out;
}
"""


async def scrape_listing(
    context: BrowserContext, url: str, max_jobs: int = 30, scroll_count: int = 1
) -> list[JobListing]:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(2_500)
        for _ in range(scroll_count):
            await page.mouse.wheel(0, 3_000)
            await page.wait_for_timeout(1_500)
        raw: list[dict] = await page.evaluate(_EXTRACT_JS, max_jobs)
        return [JobListing(**item) for item in raw]
    finally:
        await page.close()
