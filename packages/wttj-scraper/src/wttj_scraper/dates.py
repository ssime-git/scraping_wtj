from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

_HOUR_RE = re.compile(r"^il y a (\d+) heures?$")
_DAY_RE = re.compile(r"^il y a (\d+) jours?$")
_TODAY_LABELS = {"today", "aujourd'hui", "aujourd’hui"}
_YESTERDAY_LABELS = {"hier"}
_BEFORE_YESTERDAY_LABELS = {"avant-hier"}
_LAST_MONTH_LABELS = {"le mois dernier"}
_LAST_MONTH_DAYS = 30


def _as_aware(reference: datetime | str) -> datetime:
    if isinstance(reference, str):
        reference = datetime.fromisoformat(reference)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return reference


def estimate_date_posted(label: str | None, reference: datetime | str | None) -> datetime | None:
    """Estimate the absolute publication date from a WTTJ relative label.

    Must run only once per job at first sighting (see storage.write_jobs_parquet):
    the label's granularity coarsens over time, so re-deriving it from a later
    scrape would silently drift the estimated date.
    """
    if not isinstance(label, str) or not label or not isinstance(reference, (datetime, str)):
        return None
    reference = _as_aware(reference)
    normalized = label.strip().lower()

    if normalized in _TODAY_LABELS:
        return reference
    if normalized in _YESTERDAY_LABELS:
        return reference - timedelta(days=1)
    if normalized in _BEFORE_YESTERDAY_LABELS:
        return reference - timedelta(days=2)
    if normalized in _LAST_MONTH_LABELS:
        return reference - timedelta(days=_LAST_MONTH_DAYS)

    hour_match = _HOUR_RE.match(normalized)
    if hour_match:
        return reference - timedelta(hours=int(hour_match.group(1)))

    day_match = _DAY_RE.match(normalized)
    if day_match:
        return reference - timedelta(days=int(day_match.group(1)))

    return None
