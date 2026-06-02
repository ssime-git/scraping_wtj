import asyncio
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from wttj_scraper import scrape_authenticated_matches
from wttj_scraper.storage import write_jobs_parquet

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
PARQUET_FILE = DATA_DIR / "jobs.parquet"
CONFIG_PATH = os.getenv("WTTJ_MATCHES_CONFIG", "config/wttj_matches.yaml")
HC_PING_URL = os.getenv("HC_PING_URL", "").rstrip("/")


def _hc_ping(suffix: str = "", body: str = "") -> None:
    if not HC_PING_URL:
        return
    url = f"{HC_PING_URL}/{suffix}" if suffix else HC_PING_URL
    try:
        data = body.encode() if body else None
        urllib.request.urlopen(url, data=data, timeout=5)
    except Exception:
        pass


async def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    try:
        result = await scrape_authenticated_matches(CONFIG_PATH)
    except Exception as exc:
        _hc_ping("fail", body=str(exc))
        raise

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

    saved = len(rows)
    summary = f"saved_jobs={saved} scraped_at={scraped_at}"
    print(
        {
            "saved_jobs": saved,
            "parquet": str(PARQUET_FILE),
            "scraped_at": scraped_at,
            "run_started_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    if saved == 0:
        _hc_ping("fail", body=f"saved_jobs=0 (scraper returned empty) scraped_at={scraped_at}")
    else:
        _hc_ping(body=summary)


if __name__ == "__main__":
    asyncio.run(main())
