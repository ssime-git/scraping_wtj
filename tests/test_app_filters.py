import pandas as pd


def test_experience_display_labels_maps_nan_to_non_precise():
    from wttj_app.app import NON_PRECISE_LABEL, experience_display_labels

    series = pd.Series(["< 6 mois", None, "> 5 ans"])
    result = experience_display_labels(series)
    assert list(result) == ["< 6 mois", NON_PRECISE_LABEL, "> 5 ans"]


def test_junior_default_labels_exclude_more_than_one_year():
    from wttj_app.app import JUNIOR_DEFAULT_LABELS

    assert "> 1 an" not in JUNIOR_DEFAULT_LABELS
    assert JUNIOR_DEFAULT_LABELS == {"Non précisé", "< 6 mois", "> 6 mois"}


def test_recent_offers_mask_uses_estimated_publication_date_within_15_days():
    from wttj_app.app import recent_offers_mask

    now = pd.Timestamp("2026-07-30T10:00:00+00:00")
    df = pd.DataFrame(
        {
            "date_posted_estimated": [
                now - pd.Timedelta(days=10),
                now - pd.Timedelta(days=20),
            ],
            "scraped_at": [now, now],
        }
    )
    mask = recent_offers_mask(df, now)
    assert list(mask) == [True, False]


def test_recent_offers_mask_falls_back_to_scraped_at_within_5_days_when_unknown():
    from wttj_app.app import recent_offers_mask

    now = pd.Timestamp("2026-07-30T10:00:00+00:00")
    df = pd.DataFrame(
        {
            "date_posted_estimated": [None, None],
            "scraped_at": [now - pd.Timedelta(days=3), now - pd.Timedelta(days=8)],
        }
    )
    mask = recent_offers_mask(df, now)
    assert list(mask) == [True, False]


def test_recent_offers_mask_handles_missing_columns():
    from wttj_app.app import recent_offers_mask

    now = pd.Timestamp("2026-07-30T10:00:00+00:00")
    df = pd.DataFrame({"job_title": ["A", "B"]})
    mask = recent_offers_mask(df, now)
    assert list(mask) == [False, False]


def test_recent_offers_mask_empty_dataframe():
    from wttj_app.app import recent_offers_mask

    now = pd.Timestamp("2026-07-30T10:00:00+00:00")
    df = pd.DataFrame({"date_posted_estimated": [], "scraped_at": []})
    mask = recent_offers_mask(df, now)
    assert list(mask) == []
