from datetime import datetime, timezone
from pydantic import BaseModel


class JobListing(BaseModel):
    title: str | None
    url: str
    snippet: str | None


class JobDetail(JobListing):
    page_title: str | None = None
    text_preview: str | None = None
    error: str | None = None


class ScrapeResult(BaseModel):
    source: str
    count: int
    jobs: list[JobDetail]
    scraped_at: datetime = datetime.now(timezone.utc)
