---
title: WTTJ Jobs
emoji: 💼
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# wttj-app

Streamlit app for browsing WTTJ job offers scraped daily. Deployed on Hugging Face Spaces.

## Where it runs

**Hugging Face Spaces** — deployed automatically by GitHub Actions when `packages/wttj-app/**` changes on `main`.

Can also run locally for development.

## Data source

Reads `jobs.parquet` from the private HF dataset (`HF_DATASET_REPO`) via `hf_hub_download`. Cache TTL: 5 minutes — the app refreshes automatically without redeployment when the scraper uploads new data.

## Features

- Login wall (username + password)
- Full-text search across title, company, city
- Multi-select filters: role family, contract type, remote level, city
- Metrics: total offers, last scrape date, unique companies
- Configurable column visibility
- CSV export

## HF Space secrets

Configure these in the Space settings:

| Secret | Description |
|---|---|
| `HF_DATASET_REPO` | Dataset repo id (e.g. `username/wttj-jobs`) |
| `HF_TOKEN` | Hugging Face token with dataset read access |
| `APP_USERNAME` | Login username for the app |
| `APP_PASSWORD` | Login password for the app |

## Run locally

```bash
uv sync --package wttj-app
HF_DATASET_REPO=username/wttj-jobs \
HF_TOKEN=hf_... \
APP_USERNAME=admin \
APP_PASSWORD=secret \
uv run streamlit run packages/wttj-app/src/wttj_app/app.py
```

Or with a local parquet file (no HF required):

```bash
DATA_PATH=data/jobs.parquet \
APP_USERNAME=admin \
APP_PASSWORD=secret \
uv run streamlit run packages/wttj-app/src/wttj_app/app.py
```

## Deploy

Deployment is handled by `.github/workflows/deploy-spaces.yml`. To trigger manually:

```bash
gh workflow run deploy-spaces.yml
```
