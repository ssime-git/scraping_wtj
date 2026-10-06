from pathlib import Path

import pandas as pd

from wttj_scraper.dates import estimate_date_posted


def _with_date_posted_estimated(frame: pd.DataFrame) -> pd.DataFrame:
    if "date_posted_label" in frame.columns and "scraped_at" in frame.columns:
        frame["date_posted_estimated"] = [
            estimate_date_posted(label, scraped_at)
            for label, scraped_at in zip(frame["date_posted_label"], frame["scraped_at"])
        ]
    return frame


def _preserve_existing_estimates(
    frame: pd.DataFrame, existing: pd.DataFrame, dedupe_on: str
) -> pd.DataFrame:
    if (
        dedupe_on not in existing.columns
        or "date_posted_estimated" not in existing.columns
        or "date_posted_estimated" not in frame.columns
    ):
        return frame
    existing_estimates = existing.set_index(dedupe_on)["date_posted_estimated"]
    frame["date_posted_estimated"] = [
        existing_estimates[key]
        if key in existing_estimates.index and pd.notna(existing_estimates[key])
        else new_value
        for key, new_value in zip(frame[dedupe_on], frame["date_posted_estimated"])
    ]
    return frame


def write_jobs_parquet(rows: list[dict], path: Path, *, dedupe_on: str = "job_url") -> None:
    frame = _with_date_posted_estimated(pd.DataFrame(rows))
    if path.exists():
        existing = pd.read_parquet(path)
        frame = _preserve_existing_estimates(frame, existing, dedupe_on)
        frame = pd.concat([existing, frame], ignore_index=True)
    if dedupe_on in frame.columns:
        frame = frame.drop_duplicates(subset=[dedupe_on], keep="last")
    frame.to_parquet(path, index=False)
