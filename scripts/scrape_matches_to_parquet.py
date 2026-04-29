import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from wttj_scraper import scrape_authenticated_matches
from wttj_scraper.storage import write_jobs_parquet

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
PARQUET_FILE = DATA_DIR / "jobs.parquet"
CONFIG_PATH = os.getenv("WTTJ_MATCHES_CONFIG", "config/wttj_matches.yaml")


async def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    result = await scrape_authenticated_matches(CONFIG_PATH)
    scraped_at = result.scraped_at.astimezone(timezone.utc).isoformat()
    rows = [
        {
            **job.model_dump(),
            "job_title": job.job_title or job.title,
            "job_url": job.job_url or job.url,
            "source": result.source,
            "scraped_at": scraped_at,
        }
        for job in result.jobs
    ]
    write_jobs_parquet(rows, PARQUET_FILE)
    print(
        {
            "saved_jobs": len(rows),
            "parquet": str(PARQUET_FILE),
            "scraped_at": scraped_at,
            "run_started_at": datetime.now(timezone.utc).isoformat(),
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
