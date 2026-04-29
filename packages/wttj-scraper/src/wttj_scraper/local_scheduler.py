from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time
import fcntl
import hashlib
import json
import random
from pathlib import Path


def is_lock_held(path: Path) -> bool:
    """Return True only if the lock file is actively held by another process."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)
        return False
    except OSError:
        return True


@dataclass(slots=True)
class SchedulerConfig:
    window_start: str
    window_end: str
    seed: str = "wttj-local"


@dataclass(slots=True)
class SchedulerState:
    date: str | None = None
    target_time: str | None = None
    last_started_at: str | None = None
    last_succeeded_at: str | None = None
    last_failed_at: str | None = None
    last_status: str = "never"


@dataclass(slots=True)
class SchedulerDecision:
    run: bool
    reason: str
    state: SchedulerState


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _format_hhmm(value: time) -> str:
    return value.strftime("%H:%M")


def load_state(path: Path) -> SchedulerState:
    if not path.exists():
        return SchedulerState()
    return SchedulerState(**json.loads(path.read_text(encoding="utf-8")))


def store_state(path: Path, state: SchedulerState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")


def compute_daily_target(day: date, config: SchedulerConfig) -> time:
    start = _parse_hhmm(config.window_start)
    end = _parse_hhmm(config.window_end)
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    digest = hashlib.sha256(f"{config.seed}:{day.isoformat()}".encode()).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    chosen = rng.randint(start_minutes, end_minutes)
    return time(chosen // 60, chosen % 60)


def should_run_now(
    now: datetime,
    state: SchedulerState,
    config: SchedulerConfig,
    *,
    lock_held: bool,
) -> SchedulerDecision:
    today = now.date().isoformat()
    if state.date != today:
        target = compute_daily_target(now.date(), config)
        state = SchedulerState(date=today, target_time=_format_hhmm(target), last_status="scheduled")
    if lock_held:
        return SchedulerDecision(run=False, reason="lock_held", state=state)
    if state.last_succeeded_at and state.last_succeeded_at.startswith(today):
        return SchedulerDecision(run=False, reason="already_succeeded_today", state=state)
    target = _parse_hhmm(state.target_time or config.window_start)
    if now.time() < target:
        return SchedulerDecision(run=False, reason="before_target", state=state)
    if state.last_failed_at and state.last_failed_at.startswith(today):
        return SchedulerDecision(run=False, reason="already_failed_today", state=state)
    return SchedulerDecision(run=True, reason="due", state=state)


def mark_run_started(state: SchedulerState, started_at: str) -> SchedulerState:
    state.last_status = "running"
    state.last_started_at = started_at
    return state


def mark_run_finished(state: SchedulerState, finished_at: str, *, success: bool) -> SchedulerState:
    state.last_status = "success" if success else "failed"
    if success:
        state.last_succeeded_at = finished_at
    else:
        state.last_failed_at = finished_at
    return state
