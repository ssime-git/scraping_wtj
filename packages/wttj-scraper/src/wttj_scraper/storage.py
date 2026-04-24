from pathlib import Path

import pandas as pd


def write_jobs_parquet(rows: list[dict], path: Path) -> None:
    frame = pd.DataFrame(rows)
    if path.exists():
        existing = pd.read_parquet(path)
        frame = pd.concat([existing, frame], ignore_index=True)
    frame.to_parquet(path, index=False)
