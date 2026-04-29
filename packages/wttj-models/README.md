# wttj-models

Pydantic data models shared across all WTTJ packages.

## Where it runs

Imported by `wttj-scraper`, `wttj-cli`, and `wttj-app`. No runtime process of its own.

## Models

### `JobListing`

Base model populated from listing pages.

| Field | Type | Description |
|---|---|---|
| `job_url` | `str` | Canonical job URL |
| `job_title` | `str \| None` | Job title |
| `company_name` | `str \| None` | Company name |
| `location_label` | `str \| None` | Raw location text |
| `role_family` | `str \| None` | Role family (from config) |
| `matched_role_query` | `str \| None` | Query that matched this job |

### `JobDetail`

Extends `JobListing` with all fields extracted from detail pages.

Key fields: `city`, `contract_type`, `remote_level`, `salary_label`, `experience_label`, `date_posted_label`, `skills`, `benefits`, `sector`, `company_size`, `scraped_at`.

### `ScrapeResult`

Container returned by the scraper.

| Field | Description |
|---|---|
| `source` | Source URL or identifier |
| `job_count` | Number of jobs collected |
| `jobs` | List of `JobDetail` |
| `scraped_at` | ISO 8601 timestamp |

## Install

```bash
uv add wttj-models
# or within the workspace
uv sync
```
