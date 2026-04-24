from datetime import datetime, timezone
from wttj_models.job import JobListing, JobDetail, ScrapeResult


def test_job_listing_requires_url():
    job = JobListing(title="Dev Python", url="https://example.com/jobs/1", snippet="Remote")
    assert job.url == "https://example.com/jobs/1"
    assert job.title == "Dev Python"
    assert job.snippet == "Remote"


def test_job_listing_nullable_fields():
    job = JobListing(title=None, url="https://example.com/jobs/2", snippet=None)
    assert job.title is None
    assert job.snippet is None


def test_job_detail_inherits_listing():
    detail = JobDetail(
        title="Dev Python",
        url="https://example.com/jobs/1",
        snippet="Remote",
        page_title="Dev Python | WTTJ",
        text_preview="We are looking for...",
    )
    assert detail.page_title == "Dev Python | WTTJ"
    assert detail.text_preview == "We are looking for..."
    assert detail.error is None


def test_job_detail_can_hold_error():
    detail = JobDetail(
        title=None,
        url="https://example.com/jobs/3",
        snippet=None,
        error="timeout",
    )
    assert detail.error == "timeout"


def test_scrape_result_counts_jobs():
    jobs = [
        JobDetail(title="A", url="https://example.com/jobs/1", snippet=None),
        JobDetail(title="B", url="https://example.com/jobs/2", snippet=None),
    ]
    result = ScrapeResult(
        source="https://www.welcometothejungle.com/fr/jobs",
        count=len(jobs),
        jobs=jobs,
        scraped_at=datetime.now(timezone.utc),
    )
    assert result.count == 2
    assert len(result.jobs) == 2


def test_scrape_result_json_serialisable():
    result = ScrapeResult(
        source="https://www.welcometothejungle.com/fr/jobs",
        count=0,
        jobs=[],
        scraped_at=datetime.now(timezone.utc),
    )
    json_str = result.model_dump_json()
    assert "scraped_at" in json_str
