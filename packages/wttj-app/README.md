---
title: WTTJ Jobs
emoji: 💼
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# WTTJ Jobs Browser

Browse and download job offers scraped daily from Welcome to the Jungle.

Required Space secrets:

- `HF_DATASET_REPO`
- `HF_TOKEN`
- `APP_USERNAME`
- `APP_PASSWORD`

The app reads `jobs.parquet` from the private dataset and only exposes the data after authentication.
