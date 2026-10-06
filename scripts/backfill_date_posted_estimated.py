import os
from pathlib import Path

import pandas as pd
from wttj_scraper.dates import estimate_date_posted

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
PARQUET_FILE = DATA_DIR / "jobs.parquet"


def main() -> None:
    if not PARQUET_FILE.exists():
        raise FileNotFoundError(f"Missing parquet file: {PARQUET_FILE}")
    frame = pd.read_parquet(PARQUET_FILE)

    if "date_posted_estimated" not in frame.columns:
        frame["date_posted_estimated"] = None

    missing = frame["date_posted_estimated"].isna()
    frame.loc[missing, "date_posted_estimated"] = [
        estimate_date_posted(label, scraped_at)
        for label, scraped_at in zip(
            frame.loc[missing, "date_posted_label"], frame.loc[missing, "scraped_at"]
        )
    ]

    frame.to_parquet(PARQUET_FILE, index=False)
    filled = int(missing.sum()) - int(frame.loc[missing, "date_posted_estimated"].isna().sum())
    print(
        {
            "total_rows": len(frame),
            "backfilled": filled,
            "still_unknown": int(frame["date_posted_estimated"].isna().sum()),
        }
    )


if __name__ == "__main__":
    main()
