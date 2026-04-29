# wttj-cli

Command-line interface for running WTTJ scrapes interactively.

## Where it runs

Locally, on demand. Not used in the automated daily pipeline (which calls scripts directly via systemd).

## Install

```bash
uv sync --package wttj-cli
```

## Usage

### Public listing scrape

Scrapes the public WTTJ job listing at a given URL.

```bash
uv run wttj --url "https://www.welcometothejungle.com/fr/jobs" --max-jobs 60 --enrich-count 10
```

| Flag | Default | Description |
|---|---|---|
| `--url` | required | Listing page URL |
| `--max-jobs` | `60` | Maximum jobs to collect from listing |
| `--enrich-count` | `10` | Number of jobs to enrich with detail page data |

### Authenticated matches scrape

Uses a YAML config to scrape the authenticated matches area.

```bash
uv run wttj --config config/wttj_matches.yaml
```

Reads `WTTJ_EMAIL` and `WTTJ_PASSWORD` from environment.

## Output

JSON-formatted `ScrapeResult` printed to stdout:

```json
{
  "source": "https://...",
  "job_count": 42,
  "jobs": [...],
  "scraped_at": "2026-04-29T10:00:00+00:00"
}
```
