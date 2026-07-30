import pandas as pd

from wttj_scraper.storage import write_jobs_parquet


def test_write_jobs_parquet(tmp_path):
    rows = [{"job_title": "Dev Python", "job_url": "https://example.com/jobs/1"}]
    path = tmp_path / "jobs.parquet"
    write_jobs_parquet(rows, path)
    frame = pd.read_parquet(path)
    assert list(frame["job_title"]) == ["Dev Python"]


def test_write_jobs_parquet_appends_existing_rows(tmp_path):
    path = tmp_path / "jobs.parquet"
    write_jobs_parquet([{"job_title": "A", "job_url": "https://example.com/jobs/1"}], path)
    write_jobs_parquet([{"job_title": "B", "job_url": "https://example.com/jobs/2"}], path)
    frame = pd.read_parquet(path)
    assert list(frame["job_title"]) == ["A", "B"]


def test_write_jobs_parquet_dedupes_by_job_url_keeping_latest(tmp_path):
    path = tmp_path / "jobs.parquet"
    write_jobs_parquet([{"job_title": "A", "job_url": "https://example.com/jobs/1"}], path)
    write_jobs_parquet([{"job_title": "A updated", "job_url": "https://example.com/jobs/1"}], path)
    frame = pd.read_parquet(path)
    assert len(frame) == 1
    assert list(frame["job_title"]) == ["A updated"]


def test_write_jobs_parquet_computes_date_posted_estimated(tmp_path):
    path = tmp_path / "jobs.parquet"
    write_jobs_parquet(
        [
            {
                "job_url": "https://example.com/jobs/1",
                "date_posted_label": "il y a 3 jours",
                "scraped_at": "2026-07-10T10:00:00+00:00",
            }
        ],
        path,
    )
    frame = pd.read_parquet(path)
    assert pd.Timestamp(frame.loc[0, "date_posted_estimated"]) == pd.Timestamp(
        "2026-07-07T10:00:00+00:00"
    )


def test_write_jobs_parquet_preserves_date_posted_estimated_on_rescrape(tmp_path):
    path = tmp_path / "jobs.parquet"
    write_jobs_parquet(
        [
            {
                "job_url": "https://example.com/jobs/1",
                "date_posted_label": "il y a 3 jours",
                "scraped_at": "2026-07-01T10:00:00+00:00",
            }
        ],
        path,
    )
    first = pd.read_parquet(path).loc[0, "date_posted_estimated"]

    write_jobs_parquet(
        [
            {
                "job_url": "https://example.com/jobs/1",
                "date_posted_label": "il y a 10 jours",
                "scraped_at": "2026-07-08T10:00:00+00:00",
            }
        ],
        path,
    )
    frame = pd.read_parquet(path)
    assert len(frame) == 1
    assert frame.loc[0, "date_posted_estimated"] == first


def test_write_jobs_parquet_backfills_missing_date_posted_estimated_on_rescrape(tmp_path):
    path = tmp_path / "jobs.parquet"
    write_jobs_parquet(
        [{"job_url": "https://example.com/jobs/1", "date_posted_label": None, "scraped_at": "2026-07-01T10:00:00+00:00"}],
        path,
    )
    write_jobs_parquet(
        [
            {
                "job_url": "https://example.com/jobs/1",
                "date_posted_label": "il y a 2 jours",
                "scraped_at": "2026-07-08T10:00:00+00:00",
            }
        ],
        path,
    )
    frame = pd.read_parquet(path)
    assert pd.Timestamp(frame.loc[0, "date_posted_estimated"]) == pd.Timestamp(
        "2026-07-06T10:00:00+00:00"
    )
