from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_unit(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_scheduler_timer_runs_scrape_service_directly() -> None:
    timer = _read_unit("deploy/systemd/wttj-scheduler.timer")

    assert "Unit=wttj-scrape.service" in timer
    assert "Unit=wttj-scheduler.service" not in timer
    assert "Persistent=true" in timer
    assert "RandomizedDelaySec=2h" in timer


def test_scrape_service_keeps_lock_and_timeout() -> None:
    service = _read_unit("deploy/systemd/wttj-scrape.service")

    assert "Type=oneshot" in service
    assert "/usr/bin/flock -n %h/.local/state/wttj-scrape/run.lock" in service
    assert "TimeoutStartSec=3h" in service
