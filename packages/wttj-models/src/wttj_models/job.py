from datetime import datetime, timezone
from pydantic import BaseModel, Field


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
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
