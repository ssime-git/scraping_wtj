import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from wttj_scraper.browser import browser_context
from wttj_scraper.detail import scrape_detail
from wttj_scraper.listing import scrape_listing
from wttj_scraper.storage import write_jobs_parquet

LISTING_URL = "https://www.welcometothejungle.com/fr/jobs"
SCROLL_COUNT = 3
MAX_JOBS = 60
ENRICH_COUNT = 10

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
PARQUET_FILE = DATA_DIR / "jobs.parquet"
SEEN_URLS_FILE = DATA_DIR / "seen_urls.txt"


def load_seen_urls() -> set[str]:
    if not SEEN_URLS_FILE.exists():
        return set()
    return set(SEEN_URLS_FILE.read_text(encoding="utf-8").splitlines())


def append_seen_urls(new_urls: list[str]) -> None:
    with SEEN_URLS_FILE.open("a", encoding="utf-8") as f:
        for url in new_urls:
            f.write(url + "\n")

def push_to_hf() -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=os.environ["HF_TOKEN"])
    repo_id = os.environ["HF_DATASET_REPO"]
    api.upload_file(
        path_or_fileobj=str(PARQUET_FILE),
        path_in_repo="jobs.parquet",
        repo_id=repo_id,
        repo_type="dataset",
    )
    if SEEN_URLS_FILE.exists():
        api.upload_file(
            path_or_fileobj=str(SEEN_URLS_FILE),
            path_in_repo="seen_urls.txt",
            repo_id=repo_id,
            repo_type="dataset",
        )
    print(f"Pushed to HF Dataset: {repo_id}")


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
        {
            **job.model_dump(),
            "job_title": job.job_title or job.title,
            "job_url": job.job_url or job.url,
            "source": LISTING_URL,
            "scraped_at": scraped_at,
        }
        for job in enriched
    ]

    write_jobs_parquet(rows, PARQUET_FILE)
    append_seen_urls([job.url for job in enriched])

    print(f"Saved {len(rows)} new jobs → {PARQUET_FILE}")
    print(f"Total seen URLs: {len(seen_urls) + len(rows)}")

    if os.getenv("HF_TOKEN") and os.getenv("HF_DATASET_REPO"):
        push_to_hf()


if __name__ == "__main__":
    asyncio.run(main())
