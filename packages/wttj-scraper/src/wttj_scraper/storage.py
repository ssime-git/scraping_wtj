from pathlib import Path

import pandas as pd


def write_jobs_parquet(rows: list[dict], path: Path, *, dedupe_on: str = "job_url") -> None:
    frame = pd.DataFrame(rows)
    if path.exists():
        existing = pd.read_parquet(path)
        frame = pd.concat([existing, frame], ignore_index=True)
    if dedupe_on in frame.columns:
        frame = frame.drop_duplicates(subset=[dedupe_on], keep="last")
    frame.to_parquet(path, index=False)
