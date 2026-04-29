from pathlib import Path

import pytest

from wttj_scraper.config import load_matches_config


def test_load_matches_config_reads_families_and_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "wttj_matches.yaml"
    config_path.write_text(
        """
        auth:
          login_url: https://example.test/login
          matches_url: https://example.test/matches
          email_env: WTTJ_EMAIL
          password_env: WTTJ_PASSWORD
        global_filters:
          location: [France]
          experience: [Junior (1-3 ans)]
          remote: [Télétravail fréquent]
          contract: [CDI]
          salary: [≥ 10K €par an]
        families:
          data_engineer:
            roles: [Data Engineer, Analytics Engineer]
        limits:
          max_jobs_per_family: 25
          max_pages_per_role: 10
        timing:
          action_delay_seconds: [1.0, 2.0]
          family_delay_seconds: [4.0, 7.0]
          detail_delay_seconds: [1.5, 3.0]
        output:
          save_json: true
          save_parquet: false
          include_listing_snapshot: true
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("WTTJ_EMAIL", "user@example.com")
    monkeypatch.setenv("WTTJ_PASSWORD", "secret")

    config = load_matches_config(config_path)

    assert config.auth.email == "user@example.com"
    assert config.limits.max_jobs_per_family == 25
    assert config.families["data_engineer"].roles == ["Data Engineer", "Analytics Engineer"]


def test_load_matches_config_converts_delay_ranges_to_tuples(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "wttj_matches.yaml"
    config_path.write_text(
        """
        auth:
          login_url: https://example.test/login
          matches_url: https://example.test/matches
          email_env: WTTJ_EMAIL
          password_env: WTTJ_PASSWORD
        global_filters:
          location: []
          experience: []
          remote: []
          contract: []
          salary: []
        families:
          cyber:
            roles: [Security Engineer]
        limits:
          max_jobs_per_family: 25
          max_pages_per_role: 5
        timing:
          action_delay_seconds: [1.0, 2.0]
          family_delay_seconds: [4.0, 7.0]
          detail_delay_seconds: [1.5, 3.0]
        output:
          save_json: true
          save_parquet: true
          include_listing_snapshot: false
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("WTTJ_EMAIL", "user@example.com")
    monkeypatch.setenv("WTTJ_PASSWORD", "secret")

    config = load_matches_config(config_path)

    assert config.timing.action_delay_seconds == (1.0, 2.0)


def test_load_matches_config_fails_when_password_env_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "wttj_matches.yaml"
    config_path.write_text(
        """
        auth:
          login_url: https://example.test/login
          matches_url: https://example.test/matches
          email_env: WTTJ_EMAIL
          password_env: WTTJ_PASSWORD
        global_filters:
          location: [France]
          experience: []
          remote: []
          contract: []
          salary: []
        families:
          data_engineer:
            roles: [Data Engineer]
        limits:
          max_jobs_per_family: 25
          max_pages_per_role: 10
        timing:
          action_delay_seconds: [1.0, 2.0]
          family_delay_seconds: [4.0, 7.0]
          detail_delay_seconds: [1.5, 3.0]
        output:
          save_json: true
          save_parquet: true
          include_listing_snapshot: true
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("WTTJ_EMAIL", "user@example.com")
    monkeypatch.delenv("WTTJ_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="WTTJ_PASSWORD"):
        load_matches_config(config_path)
