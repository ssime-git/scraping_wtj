from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

from wttj_scraper.local_scheduler import load_state, mark_run_finished, mark_run_started, store_state

STATE_PATH = Path(os.getenv("WTTJ_STATE_PATH", Path.home() / ".local/state/wttj-scrape/state.json"))
LOCK_PATH = Path(os.getenv("WTTJ_LOCK_PATH", Path.home() / ".local/state/wttj-scrape/run.lock"))
UV = os.getenv("UV_BIN", "/home/seb/.local/bin/uv")


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    state = load_state(STATE_PATH)
    started_at = datetime.now().isoformat(timespec="seconds")
    store_state(STATE_PATH, mark_run_started(state, started_at))
    try:
        _run([UV, "run", "python", "scripts/scrape_matches_to_parquet.py"])
        _run([UV, "run", "--package", "wttj-scraper", "--extra", "hf", "python", "scripts/upload_parquet_to_hf.py"])
    except subprocess.CalledProcessError:
        finished = datetime.now().isoformat(timespec="seconds")
        store_state(STATE_PATH, mark_run_finished(load_state(STATE_PATH), finished, success=False))
        return 1
    finished = datetime.now().isoformat(timespec="seconds")
    store_state(STATE_PATH, mark_run_finished(load_state(STATE_PATH), finished, success=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
