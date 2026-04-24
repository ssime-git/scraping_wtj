import json
import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from wttj_models.job import JobDetail, ScrapeResult

_MOCK_RESULT = ScrapeResult(
    source="https://www.welcometothejungle.com/fr/jobs",
    count=1,
    jobs=[
        JobDetail(
            title="Dev Python",
            url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev",
            snippet="Acme · Paris",
            page_title="Dev Python | Acme | WTTJ",
            text_preview="We are looking for...",
        )
    ],
    scraped_at=datetime(2026, 4, 24, 10, 0, 0, tzinfo=timezone.utc),
)


def test_main_outputs_json(capsys):
    with patch("wttj_cli.main.asyncio.run", return_value=_MOCK_RESULT):
        from wttj_cli.main import main
        main(["--url", "https://www.welcometothejungle.com/fr/jobs", "--max-jobs", "5"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["count"] == 1
    assert data["jobs"][0]["title"] == "Dev Python"


def test_main_uses_defaults(capsys):
    with patch("wttj_cli.main.asyncio.run", return_value=_MOCK_RESULT) as mock_run:
        from wttj_cli.main import main
        main([])

    mock_run.assert_called_once()
