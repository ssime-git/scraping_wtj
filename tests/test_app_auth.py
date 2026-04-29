import os


def test_requires_auth_before_data_load(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    os.environ.pop("HF_DATASET_REPO", None)
    from wttj_app.app import check_credentials

    assert check_credentials("admin", "wrong") is False
    assert check_credentials("admin", "secret") is True


def test_all_columns_are_visible_by_default():
    from wttj_app.app import get_default_visible_columns

    columns = ["description_raw", "job_title", "company_name", "city", "role_family"]
    assert get_default_visible_columns(columns) == [
        "role_family",
        "job_title",
        "company_name",
        "city",
        "description_raw",
    ]
