from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_compose_keeps_only_local_healthchecks() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "healthchecks:" in compose
    assert "scraper:" not in compose
    assert "app:" not in compose
    assert "Dockerfile.scraper" not in compose
    assert "Dockerfile.app" not in compose
