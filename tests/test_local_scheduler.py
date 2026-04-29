from datetime import date, datetime, time
from pathlib import Path

from wttj_scraper.local_scheduler import (
    SchedulerConfig,
    SchedulerState,
    compute_daily_target,
    load_state,
    should_run_now,
    store_state,
)


def test_load_state_returns_default_when_missing(tmp_path: Path) -> None:
    state = load_state(tmp_path / "state.json")
    assert state.date is None
    assert state.last_status == "never"


def test_store_state_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = SchedulerState(date="2026-04-29", target_time="04:12", last_status="success")
    store_state(path, state)
    reloaded = load_state(path)
    assert reloaded.date == "2026-04-29"
    assert reloaded.target_time == "04:12"
    assert reloaded.last_status == "success"


def test_compute_daily_target_is_stable_for_same_day() -> None:
    config = SchedulerConfig(window_start="03:30", window_end="05:30", seed="wttj-prod")
    first = compute_daily_target(date(2026, 4, 29), config)
    second = compute_daily_target(date(2026, 4, 29), config)
    assert first == second
    assert time(3, 30) <= first <= time(5, 30)


def test_should_run_now_false_before_target() -> None:
    config = SchedulerConfig(window_start="03:30", window_end="05:30", seed="wttj-prod")
    state = SchedulerState(date="2026-04-29", target_time="04:30", last_status="scheduled")
    decision = should_run_now(datetime(2026, 4, 29, 4, 0), state, config, lock_held=False)
    assert decision.run is False
    assert decision.reason == "before_target"


def test_should_run_now_false_after_success_today() -> None:
    config = SchedulerConfig(window_start="03:30", window_end="05:30", seed="wttj-prod")
    state = SchedulerState(
        date="2026-04-29",
        target_time="04:00",
        last_status="success",
        last_succeeded_at="2026-04-29T04:08:00",
    )
    decision = should_run_now(datetime(2026, 4, 29, 4, 30), state, config, lock_held=False)
    assert decision.run is False
    assert decision.reason == "already_succeeded_today"


def test_should_run_now_true_when_due_and_unlocked() -> None:
    config = SchedulerConfig(window_start="03:30", window_end="05:30", seed="wttj-prod")
    state = SchedulerState(date="2026-04-29", target_time="04:00", last_status="scheduled")
    decision = should_run_now(datetime(2026, 4, 29, 4, 30), state, config, lock_held=False)
    assert decision.run is True
    assert decision.reason == "due"


from wttj_scraper.local_scheduler import mark_run_finished, mark_run_started


def test_mark_run_started_sets_started_fields() -> None:
    state = SchedulerState(date="2026-04-29", target_time="04:00", last_status="scheduled")
    updated = mark_run_started(state, "2026-04-29T04:01:00")
    assert updated.last_status == "running"
    assert updated.last_started_at == "2026-04-29T04:01:00"


def test_mark_run_finished_success_sets_success_fields() -> None:
    state = SchedulerState(date="2026-04-29", target_time="04:00", last_status="running")
    updated = mark_run_finished(state, "2026-04-29T04:10:00", success=True)
    assert updated.last_status == "success"
    assert updated.last_succeeded_at == "2026-04-29T04:10:00"


def test_mark_run_finished_failure_sets_failure_fields() -> None:
    state = SchedulerState(date="2026-04-29", target_time="04:00", last_status="running")
    updated = mark_run_finished(state, "2026-04-29T04:10:00", success=False)
    assert updated.last_status == "failed"
    assert updated.last_failed_at == "2026-04-29T04:10:00"
