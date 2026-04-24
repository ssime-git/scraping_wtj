import os


def test_requires_auth_before_data_load(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    os.environ.pop("HF_DATASET_REPO", None)
    from wttj_app.app import check_credentials

    assert check_credentials("admin", "wrong") is False
    assert check_credentials("admin", "secret") is True
