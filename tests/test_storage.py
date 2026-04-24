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
