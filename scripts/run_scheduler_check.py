from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

from wttj_scraper.local_scheduler import SchedulerConfig, load_state, should_run_now, store_state

STATE_PATH = Path(os.getenv("WTTJ_STATE_PATH", Path.home() / ".local/state/wttj-scrape/state.json"))
LOCK_PATH = Path(os.getenv("WTTJ_LOCK_PATH", Path.home() / ".local/state/wttj-scrape/run.lock"))


def main() -> int:
    config = SchedulerConfig(
        window_start=os.getenv("WTTJ_WINDOW_START", "03:30"),
        window_end=os.getenv("WTTJ_WINDOW_END", "05:30"),
        seed=os.getenv("WTTJ_SCHEDULER_SEED", "wttj-local"),
    )
    state = load_state(STATE_PATH)
    decision = should_run_now(datetime.now(), state, config, lock_held=LOCK_PATH.exists())
    store_state(STATE_PATH, decision.state)
    print(f"decision={decision.reason} run={decision.run}")
    if not decision.run:
        return 0
    subprocess.run(["systemctl", "--user", "start", "wttj-scrape.service"], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
