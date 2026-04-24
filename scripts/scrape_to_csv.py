import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path

from wttj_scraper.browser import browser_context
from wttj_scraper.detail import scrape_detail
from wttj_scraper.listing import scrape_listing

LISTING_URL = "https://www.welcometothejungle.com/fr/jobs"
SCROLL_COUNT = 3
MAX_JOBS = 60
ENRICH_COUNT = 10

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_FILE = DATA_DIR / "jobs.csv"
SEEN_URLS_FILE = DATA_DIR / "seen_urls.txt"

CSV_FIELDS = ["title", "url", "snippet", "page_title", "text_preview", "error", "source", "scraped_at"]


def load_seen_urls() -> set[str]:
    if not SEEN_URLS_FILE.exists():
        return set()
    return set(SEEN_URLS_FILE.read_text(encoding="utf-8").splitlines())


def append_seen_urls(new_urls: list[str]) -> None:
    with SEEN_URLS_FILE.open("a", encoding="utf-8") as f:
        for url in new_urls:
            f.write(url + "\n")


def append_to_csv(rows: list[dict]) -> None:
    write_header = not CSV_FILE.exists()
    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


async def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    seen_urls = load_seen_urls()
    print(f"Known URLs: {len(seen_urls)}")

    async with browser_context() as context:
        print(f"Scraping listing ({SCROLL_COUNT} scrolls, max {MAX_JOBS} jobs)…")
        listings = await scrape_listing(context, LISTING_URL, MAX_JOBS, SCROLL_COUNT)
        new_listings = [job for job in listings if job.url not in seen_urls]
        print(f"  {len(listings)} found, {len(new_listings)} new")

        if not new_listings:
            print("Nothing new to enrich.")
            return

        enriched = []
        for job in new_listings[:ENRICH_COUNT]:
            detail = await scrape_detail(context, job)
            enriched.append(detail)
            await asyncio.sleep(1.2)

    scraped_at = datetime.now(timezone.utc).isoformat()
    rows = [
        {**job.model_dump(), "source": LISTING_URL, "scraped_at": scraped_at}
        for job in enriched
    ]

    append_to_csv(rows)
    append_seen_urls([job.url for job in enriched])

    print(f"Saved {len(rows)} new jobs → {CSV_FILE}")
    print(f"Total seen URLs: {len(seen_urls) + len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
