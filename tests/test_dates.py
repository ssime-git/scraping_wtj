from datetime import datetime, timezone

from wttj_scraper.dates import estimate_date_posted

REFERENCE = datetime(2026, 7, 30, 10, 0, tzinfo=timezone.utc)


def test_returns_none_for_missing_label_or_reference():
    assert estimate_date_posted(None, REFERENCE) is None
    assert estimate_date_posted("il y a 3 jours", None) is None


def test_returns_none_for_nan_label_from_parquet():
    assert estimate_date_posted(float("nan"), REFERENCE) is None


def test_returns_none_for_unrecognized_label():
    assert estimate_date_posted("some unknown label", REFERENCE) is None


def test_parses_hours():
    assert estimate_date_posted("il y a 5 heures", REFERENCE) == datetime(
        2026, 7, 30, 5, 0, tzinfo=timezone.utc
    )


def test_parses_days():
    assert estimate_date_posted("il y a 3 jours", REFERENCE) == datetime(
        2026, 7, 27, 10, 0, tzinfo=timezone.utc
    )


def test_parses_today_variants():
    assert estimate_date_posted("aujourd'hui", REFERENCE) == REFERENCE
    assert estimate_date_posted("Today", REFERENCE) == REFERENCE
    assert estimate_date_posted("today", REFERENCE) == REFERENCE


def test_parses_yesterday():
    assert estimate_date_posted("hier", REFERENCE) == datetime(
        2026, 7, 29, 10, 0, tzinfo=timezone.utc
    )


def test_parses_day_before_yesterday():
    assert estimate_date_posted("avant-hier", REFERENCE) == datetime(
        2026, 7, 28, 10, 0, tzinfo=timezone.utc
    )


def test_parses_last_month_as_30_days():
    assert estimate_date_posted("le mois dernier", REFERENCE) == datetime(
        2026, 6, 30, 10, 0, tzinfo=timezone.utc
    )


def test_accepts_isoformat_string_reference():
    assert estimate_date_posted("hier", REFERENCE.isoformat()) == datetime(
        2026, 7, 29, 10, 0, tzinfo=timezone.utc
    )


def test_naive_reference_is_treated_as_utc():
    naive = datetime(2026, 7, 30, 10, 0)
    assert estimate_date_posted("hier", naive) == datetime(2026, 7, 29, 10, 0, tzinfo=timezone.utc)
