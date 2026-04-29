# wttj-scraper

Core scraping library for Welcome to the Jungle. Handles browser automation, authenticated matches scraping, parquet storage, and local scheduling logic.

## Where it runs

- **Locally on WSL2** via `systemd --user` (daily authenticated scrape)
- Imported by `wttj-cli` for ad-hoc scraping

## Modules

| Module | Purpose |
|---|---|
| `browser.py` | Playwright Chromium context factory |
| `listing.py` | Extracts job cards from public listing pages (scroll + paginate) |
| `detail.py` | Extracts 60+ fields from individual job pages via JS evaluation |
| `config.py` | Loads `wttj_matches.yaml` into typed dataclasses |
| `matches_auth.py` | Logs into the authenticated matches area, handles cookie overlays |
| `matches_filters.py` | Applies role/location/experience/remote/contract filters on matches page |
| `matches_listing.py` | Extracts and deduplicates job cards from authenticated pages |
| `orchestrator.py` | Orchestrates full authenticated scrape across all configured role families |
| `storage.py` | Writes `JobDetail` list to Parquet with URL-based deduplication |
| `local_scheduler.py` | Deterministic daily scheduling: state, decision logic, run tracking |
| `logging_utils.py` | Logging configuration |

## Authenticated scrape flow

```
config/wttj_matches.yaml
  └─ auth: login URL, credentials env vars
  └─ global_filters: location, experience, remote, contract
  └─ families: [data_engineer, data_scientist, data_analyst, ml_engineer, mlops, cyber]
  └─ limits: 25 jobs/family, 10 pages/role

orchestrator.py
  └─ login (matches_auth.py)
  └─ for each family:
       └─ apply filters (matches_filters.py)
       └─ collect job cards (matches_listing.py)
       └─ enrich details (detail.py)
  └─ write parquet (storage.py)
```

## Scheduler logic (`local_scheduler.py`)

The scheduler computes a **deterministic daily target time** using SHA-256:

```python
digest = sha256(f"{seed}:{date}".encode())
target = window_start + (digest % window_duration)
```

This ensures the target is stable for a given day but varies across days.

State machine per day:

```
scheduled → running → success
                    → failed
```

`should_run_now()` returns `False` if: lock held, already succeeded today, already failed today, or before today's target time.

## Install

```bash
# With HF upload support
uv add "wttj-scraper[hf]"

# Within the workspace
uv sync --package wttj-scraper --extra hf
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `WTTJ_EMAIL` | Yes | — | WTTJ account email |
| `WTTJ_PASSWORD` | Yes | — | WTTJ account password |
| `WTTJ_MATCHES_CONFIG` | Yes | `config/wttj_matches.yaml` | Path to matches YAML config |
| `DATA_DIR` | Yes | `../data` | Output directory for parquet |
| `WTTJ_DEBUG_DIR` | No | — | Directory for debug screenshots/HTML |
| `HF_TOKEN` | For upload | — | Hugging Face token |
| `HF_DATASET_REPO` | For upload | — | HF dataset repo id |
