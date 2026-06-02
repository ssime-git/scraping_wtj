# Project: scraping_wtj

## What this project does
Scrapes job listings from Welcome to the Jungle (WTTJ) using headless Playwright auth, saves to parquet, pushes to Hugging Face dataset `huggingsime/wttj-jobs`. A Streamlit app reads that dataset.

## Stack
- UV workspace — 4 packages: `wttj-scraper`, `wttj-models`, `wttj-app`, `wttj-cli`
- Playwright (headless Chromium) for authenticated scraping
- Systemd user services for scheduling (WSL2)
- Docker Compose for healthchecks.io and the Streamlit app

## Runtime environment
- **Env file**: `~/.config/wttj-scrape.env` — credentials, HF token, HC ping URL
- **Auth state**: `~/.local/state/wttj-scrape/auth-state.json` — Playwright session cookies
- **Scraper state**: `~/.local/state/wttj-scrape/state.json` — last run date/status
- **Data**: `data/jobs.parquet` (pushed to HF), `data/seen_urls.txt`

## Systemd services (user scope)
- `wttj-scheduler.timer` — fires every 30 min, calls `wttj-scheduler.service`
- `wttj-scheduler.service` — checks `state.json`, runs scrape once per day in the 03:30–05:30 window
- `wttj-scrape.service` — runs `scripts/scrape_matches_to_parquet.py`

Always use `systemctl --user` (not `sudo systemctl`).

## Monitoring
- **healthchecks.io** self-hosted in Docker, `http://localhost:8000` (admin / admin)
- Ping URL in `~/.config/wttj-scrape.env` as `HC_PING_URL`
- Scrape script pings `/fail` on exception OR `saved_jobs=0`, success ping with job count
- Docker must be running for pings to land — Docker Desktop "Start on login" should be enabled
- `make wttj-check` — quick health summary: last run state + saved_jobs history + errors

## Key Makefile targets
```
make wttj-check          # health check — run this first when diagnosing issues
make wttj-last-logs      # full output of last scrape run
make wttj-status         # systemd service status
make wttj-logs           # follow live logs
make wttj-state          # print state.json
make wttj-refresh-auth   # re-authenticate (if session expired)
make hc-start            # start healthchecks container
```

## Silent failure pattern — CRITICAL
`saved_jobs=0` with `last_status=success` is a silent failure. It means the scraper ran but got no jobs. Causes seen:
- WTTJ changed DOM structure (CSS class names, card layout) — `extract_listing_cards` returns 0
- Session cookie expired server-side — auth "succeeds" but matches page returns empty
- Filter section not expanding before checkboxes are clicked (`_open_section` timing)

**Always check `make wttj-check` first** — it surfaces `saved_jobs=0` lines explicitly.

## WTTJ scraper internals
- `packages/wttj-scraper/src/wttj_scraper/matches_listing.py` — card extraction via `[data-testid^="job-card-"]` (WTTJ redesigned DOM in May 2026; title is now the `<a>` text, not a `<p>` child)
- `packages/wttj-scraper/src/wttj_scraper/matches_filters.py` — filter panel interactions; `_open_section` polls `aria-expanded` after click
- `packages/wttj-scraper/src/wttj_scraper/matches_auth.py` — session reuse via `auth-state.json`; falls back to full login if session stale
- `scripts/scrape_matches_to_parquet.py` — entry point; handles HC pings

## Docker Compose
- `healthchecks` service — always on, no profile
- `scraper` service — profile `scrape`, one-shot
- `app` service — Streamlit on port 8501
- Start healthchecks: `docker compose up -d healthchecks`

## Debugging scraper issues
1. `make wttj-check` — check state and saved_jobs history
2. `make wttj-last-logs` — look for errors and tracebacks
3. Run inline with env: `set -a && source ~/.config/wttj-scrape.env && set +a && uv run python scripts/scrape_matches_to_parquet.py`
4. For DOM issues: capture page HTML after filter application and inspect `a[href*="/jobs/"]` structure
