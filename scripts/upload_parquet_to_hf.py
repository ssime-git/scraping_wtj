import os
from pathlib import Path

from huggingface_hub import HfApi

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
PARQUET_FILE = DATA_DIR / "jobs.parquet"


def main() -> None:
    if not PARQUET_FILE.exists():
        raise FileNotFoundError(f"Missing parquet file: {PARQUET_FILE}")
    token = os.environ["HF_TOKEN"]
    repo_id = os.environ["HF_DATASET_REPO"]
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=str(PARQUET_FILE),
        path_in_repo="jobs.parquet",
        repo_id=repo_id,
        repo_type="dataset",
    )
    print(f"Pushed parquet to HF Dataset: {repo_id}")


if __name__ == "__main__":
    main()
