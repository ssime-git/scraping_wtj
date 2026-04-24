# WTTJ Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python UV workspace that scrapes public job listings from welcometothejungle.com, returning structured JSON, organized for future FastAPI microservice integration.

**Architecture:** Three UV packages in a workspace — `wttj-models` (Pydantic types), `wttj-scraper` (Playwright browser logic), `wttj-cli` (CLI entry point). Scraper separates listing-page extraction from detail-page enrichment so the core logic can later be wrapped by a FastAPI router with zero changes.

**Tech Stack:** Python 3.12+, UV workspace, Playwright (async), Pydantic v2, pytest + pytest-asyncio + pytest-playwright

---

## File Map

```
scraping_wtj/
├── pyproject.toml                             # UV workspace root + dev deps
├── packages/
│   ├── wttj-models/
│   │   ├── pyproject.toml
│   │   └── src/wttj_models/
│   │       ├── __init__.py
│   │       └── job.py                         # JobListing, JobDetail, ScrapeResult
│   ├── wttj-scraper/
│   │   ├── pyproject.toml
│   │   └── src/wttj_scraper/
│   │       ├── __init__.py                    # scrape() public API
│   │       ├── browser.py                     # browser_context() async context manager
│   │       ├── listing.py                     # scrape_listing()
│   │       └── detail.py                      # scrape_detail()
│   └── wttj-cli/
│       ├── pyproject.toml
│       └── src/wttj_cli/
│           ├── __init__.py
│           └── main.py                        # argparse CLI → scrape() → JSON stdout
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_listing.py
    ├── test_detail.py
    └── test_scraper.py
```

---

## Task 1: UV Workspace Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `packages/wttj-models/pyproject.toml`
- Create: `packages/wttj-scraper/pyproject.toml`
- Create: `packages/wttj-cli/pyproject.toml`
- Create: `packages/wttj-models/src/wttj_models/__init__.py`
- Create: `packages/wttj-scraper/src/wttj_scraper/__init__.py`
- Create: `packages/wttj-cli/src/wttj_cli/__init__.py`

- [ ] **Step 1: Write workspace root `pyproject.toml`**

```toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-playwright>=0.5",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Write `packages/wttj-models/pyproject.toml`**

```toml
[project]
name = "wttj-models"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pydantic>=2.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wttj_models"]
```

- [ ] **Step 3: Write `packages/wttj-scraper/pyproject.toml`**

```toml
[project]
name = "wttj-scraper"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.40",
    "wttj-models",
]

[tool.uv.sources]
wttj-models = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wttj_scraper"]
```

- [ ] **Step 4: Write `packages/wttj-cli/pyproject.toml`**

```toml
[project]
name = "wttj-cli"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["wttj-scraper"]

[project.scripts]
wttj = "wttj_cli.main:main"

[tool.uv.sources]
wttj-scraper = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wttj_cli"]
```

- [ ] **Step 5: Create empty `__init__.py` files**

```bash
touch packages/wttj-models/src/wttj_models/__init__.py
touch packages/wttj-scraper/src/wttj_scraper/__init__.py
touch packages/wttj-cli/src/wttj_cli/__init__.py
```

- [ ] **Step 6: Sync workspace and install Playwright browsers**

```bash
uv sync
uv run playwright install chromium
```

Expected: no errors, `.venv` created at root, all three packages installed.

- [ ] **Step 7: Commit**

```bash
git init
git add .
git commit -m "chore: UV workspace scaffold with three packages"
```

---

## Task 2: Pydantic Models

**Files:**
- Create: `packages/wttj-models/src/wttj_models/job.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_models.py`:

```python
from datetime import datetime, timezone
from wttj_models.job import JobListing, JobDetail, ScrapeResult


def test_job_listing_requires_url():
    job = JobListing(title="Dev Python", url="https://example.com/jobs/1", snippet="Remote")
    assert job.url == "https://example.com/jobs/1"
    assert job.title == "Dev Python"
    assert job.snippet == "Remote"


def test_job_listing_nullable_fields():
    job = JobListing(title=None, url="https://example.com/jobs/2", snippet=None)
    assert job.title is None
    assert job.snippet is None


def test_job_detail_inherits_listing():
    detail = JobDetail(
        title="Dev Python",
        url="https://example.com/jobs/1",
        snippet="Remote",
        page_title="Dev Python | WTTJ",
        text_preview="We are looking for...",
    )
    assert detail.page_title == "Dev Python | WTTJ"
    assert detail.text_preview == "We are looking for..."
    assert detail.error is None


def test_job_detail_can_hold_error():
    detail = JobDetail(
        title=None,
        url="https://example.com/jobs/3",
        snippet=None,
        error="timeout",
    )
    assert detail.error == "timeout"


def test_scrape_result_counts_jobs():
    jobs = [
        JobDetail(title="A", url="https://example.com/jobs/1", snippet=None),
        JobDetail(title="B", url="https://example.com/jobs/2", snippet=None),
    ]
    result = ScrapeResult(
        source="https://www.welcometothejungle.com/fr/jobs",
        count=len(jobs),
        jobs=jobs,
        scraped_at=datetime.now(timezone.utc),
    )
    assert result.count == 2
    assert len(result.jobs) == 2


def test_scrape_result_json_serialisable():
    result = ScrapeResult(
        source="https://www.welcometothejungle.com/fr/jobs",
        count=0,
        jobs=[],
        scraped_at=datetime.now(timezone.utc),
    )
    json_str = result.model_dump_json()
    assert "scraped_at" in json_str
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'wttj_models.job'`

- [ ] **Step 3: Implement `packages/wttj-models/src/wttj_models/job.py`**

```python
from datetime import datetime, timezone
from pydantic import BaseModel


class JobListing(BaseModel):
    title: str | None
    url: str
    snippet: str | None


class JobDetail(JobListing):
    page_title: str | None = None
    text_preview: str | None = None
    error: str | None = None


class ScrapeResult(BaseModel):
    source: str
    count: int
    jobs: list[JobDetail]
    scraped_at: datetime = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_models.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add packages/wttj-models/src/wttj_models/job.py tests/test_models.py
git commit -m "feat: Pydantic models JobListing, JobDetail, ScrapeResult"
```

---

## Task 3: Browser Context Manager

**Files:**
- Create: `packages/wttj-scraper/src/wttj_scraper/browser.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing test**

Create `tests/conftest.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.mouse = AsyncMock()
    page.mouse.wheel = AsyncMock()
    page.evaluate = AsyncMock()
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_context(mock_page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page)
    context.close = AsyncMock()
    return context
```

Create `tests/test_browser.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from wttj_scraper.browser import browser_context


@pytest.mark.asyncio
async def test_browser_context_yields_context():
    mock_browser = AsyncMock()
    mock_ctx = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_ctx)

    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch("wttj_scraper.browser.async_playwright", return_value=mock_playwright):
        async with browser_context() as ctx:
            assert ctx is mock_ctx

    mock_ctx.close.assert_awaited_once()
    mock_browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_context_closes_on_exception():
    mock_browser = AsyncMock()
    mock_ctx = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_ctx)

    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch("wttj_scraper.browser.async_playwright", return_value=mock_playwright):
        with pytest.raises(RuntimeError):
            async with browser_context():
                raise RuntimeError("boom")

    mock_ctx.close.assert_awaited_once()
    mock_browser.close.assert_awaited_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_browser.py -v
```

Expected: `ModuleNotFoundError: No module named 'wttj_scraper.browser'`

- [ ] **Step 3: Implement `packages/wttj-scraper/src/wttj_scraper/browser.py`**

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import BrowserContext, async_playwright

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@asynccontextmanager
async def browser_context(headless: bool = True) -> AsyncGenerator[BrowserContext, None]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=_USER_AGENT)
        try:
            yield context
        finally:
            await context.close()
            await browser.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_browser.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add packages/wttj-scraper/src/wttj_scraper/browser.py tests/test_browser.py tests/conftest.py
git commit -m "feat: Playwright browser_context async context manager"
```

---

## Task 4: Listing Page Scraper

**Files:**
- Create: `packages/wttj-scraper/src/wttj_scraper/listing.py`
- Create: `tests/test_listing.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_listing.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from wttj_models.job import JobListing
from wttj_scraper.listing import scrape_listing


@pytest.fixture
def mock_page_with_jobs():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.mouse = AsyncMock()
    page.mouse.wheel = AsyncMock()
    page.evaluate = AsyncMock(
        return_value=[
            {
                "title": "Développeur Python",
                "url": "https://www.welcometothejungle.com/fr/companies/acme/jobs/dev-python",
                "snippet": "Acme · Paris · CDI",
            },
            {
                "title": "Data Engineer",
                "url": "https://www.welcometothejungle.com/fr/companies/beta/jobs/data-eng",
                "snippet": "Beta · Lyon · CDI",
            },
        ]
    )
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_context_with_jobs(mock_page_with_jobs):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page_with_jobs)
    return context


@pytest.mark.asyncio
async def test_scrape_listing_returns_job_listings(mock_context_with_jobs):
    url = "https://www.welcometothejungle.com/fr/jobs"
    results = await scrape_listing(mock_context_with_jobs, url, max_jobs=30)

    assert len(results) == 2
    assert all(isinstance(j, JobListing) for j in results)
    assert results[0].title == "Développeur Python"
    assert results[1].url == "https://www.welcometothejungle.com/fr/companies/beta/jobs/data-eng"


@pytest.mark.asyncio
async def test_scrape_listing_navigates_and_scrolls(mock_context_with_jobs, mock_page_with_jobs):
    url = "https://www.welcometothejungle.com/fr/jobs"
    await scrape_listing(mock_context_with_jobs, url)

    mock_page_with_jobs.goto.assert_awaited_once_with(
        url, wait_until="domcontentloaded", timeout=60_000
    )
    mock_page_with_jobs.mouse.wheel.assert_awaited_once_with(0, 2500)


@pytest.mark.asyncio
async def test_scrape_listing_closes_page(mock_context_with_jobs, mock_page_with_jobs):
    await scrape_listing(mock_context_with_jobs, "https://www.welcometothejungle.com/fr/jobs")
    mock_page_with_jobs.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_listing_closes_page_on_error(mock_context_with_jobs, mock_page_with_jobs):
    mock_page_with_jobs.goto = AsyncMock(side_effect=TimeoutError("timeout"))
    with pytest.raises(TimeoutError):
        await scrape_listing(mock_context_with_jobs, "https://www.welcometothejungle.com/fr/jobs")
    mock_page_with_jobs.close.assert_awaited_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_listing.py -v
```

Expected: `ModuleNotFoundError: No module named 'wttj_scraper.listing'`

- [ ] **Step 3: Implement `packages/wttj-scraper/src/wttj_scraper/listing.py`**

```python
from playwright.async_api import BrowserContext
from wttj_models.job import JobListing

_EXTRACT_JS = """
(limit) => {
    const normalize = (v) => (v || '').replace(/\\s+/g, ' ').trim();
    const absolute = (href) => {
        if (!href) return '';
        if (href.startsWith('http')) return href;
        return 'https://www.welcometothejungle.com' + href;
    };
    const anchors = Array.from(document.querySelectorAll("a[href*='/jobs/']"));
    const seen = new Set();
    const out = [];
    for (const a of anchors) {
        const href = absolute(a.getAttribute('href'));
        if (!href || seen.has(href)) continue;
        seen.add(href);
        const card = a.closest('article, li, div');
        const title = normalize(
            a.textContent || card?.querySelector('h2,h3,h4')?.textContent
        );
        const snippet = normalize(card?.textContent || '');
        if (!title && !snippet) continue;
        out.push({ title: title || null, url: href, snippet: snippet || null });
        if (out.length >= limit) break;
    }
    return out;
}
"""


async def scrape_listing(
    context: BrowserContext, url: str, max_jobs: int = 30
) -> list[JobListing]:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(2_500)
        await page.mouse.wheel(0, 2_500)
        await page.wait_for_timeout(1_500)
        raw: list[dict] = await page.evaluate(_EXTRACT_JS, max_jobs)
        return [JobListing(**item) for item in raw]
    finally:
        await page.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_listing.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add packages/wttj-scraper/src/wttj_scraper/listing.py tests/test_listing.py
git commit -m "feat: scrape_listing() extracts job cards from WTTJ listing page"
```

---

## Task 5: Detail Page Scraper

**Files:**
- Create: `packages/wttj-scraper/src/wttj_scraper/detail.py`
- Create: `tests/test_detail.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_detail.py`:

```python
import pytest
from unittest.mock import AsyncMock
from wttj_models.job import JobDetail, JobListing
from wttj_scraper.detail import scrape_detail


@pytest.fixture
def base_listing():
    return JobListing(
        title="Dev Python",
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev-python",
        snippet="Acme · Paris",
    )


@pytest.fixture
def mock_detail_page():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock(
        return_value={
            "page_title": "Dev Python | Acme | Welcome to the Jungle",
            "text_preview": "Nous recherchons un développeur Python confirmé...",
        }
    )
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_context_detail(mock_detail_page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_detail_page)
    return context


@pytest.mark.asyncio
async def test_scrape_detail_returns_job_detail(mock_context_detail, base_listing):
    result = await scrape_detail(mock_context_detail, base_listing)

    assert isinstance(result, JobDetail)
    assert result.url == base_listing.url
    assert result.title == base_listing.title
    assert result.page_title == "Dev Python | Acme | Welcome to the Jungle"
    assert "développeur" in result.text_preview
    assert result.error is None


@pytest.mark.asyncio
async def test_scrape_detail_stores_error_on_timeout(mock_context_detail, mock_detail_page, base_listing):
    mock_detail_page.goto = AsyncMock(side_effect=TimeoutError("page timeout"))
    result = await scrape_detail(mock_context_detail, base_listing)

    assert isinstance(result, JobDetail)
    assert result.error is not None
    assert "timeout" in result.error.lower()
    assert result.page_title is None


@pytest.mark.asyncio
async def test_scrape_detail_closes_page(mock_context_detail, mock_detail_page, base_listing):
    await scrape_detail(mock_context_detail, base_listing)
    mock_detail_page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_detail_closes_page_on_error(mock_context_detail, mock_detail_page, base_listing):
    mock_detail_page.evaluate = AsyncMock(side_effect=RuntimeError("js error"))
    result = await scrape_detail(mock_context_detail, base_listing)
    mock_detail_page.close.assert_awaited_once()
    assert result.error is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_detail.py -v
```

Expected: `ModuleNotFoundError: No module named 'wttj_scraper.detail'`

- [ ] **Step 3: Implement `packages/wttj-scraper/src/wttj_scraper/detail.py`**

```python
from playwright.async_api import BrowserContext
from wttj_models.job import JobDetail, JobListing

_EXTRACT_JS = """
() => {
    const normalize = (v) => (v || '').replace(/\\s+/g, ' ').trim();
    return {
        page_title: normalize(document.querySelector('h1')?.textContent) || null,
        text_preview: normalize(document.body.innerText).slice(0, 1500),
    };
}
"""


async def scrape_detail(context: BrowserContext, job: JobListing) -> JobDetail:
    page = await context.new_page()
    try:
        await page.goto(job.url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(1_200)
        details: dict = await page.evaluate(_EXTRACT_JS)
        return JobDetail(**job.model_dump(), **details)
    except Exception as exc:
        return JobDetail(**job.model_dump(), error=str(exc))
    finally:
        await page.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_detail.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add packages/wttj-scraper/src/wttj_scraper/detail.py tests/test_detail.py
git commit -m "feat: scrape_detail() enriches job listings with page content"
```

---

## Task 6: Scraper Orchestrator

**Files:**
- Modify: `packages/wttj-scraper/src/wttj_scraper/__init__.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scraper.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from wttj_models.job import JobDetail, JobListing, ScrapeResult
from wttj_scraper import scrape

_LISTING_URL = "https://www.welcometothejungle.com/fr/jobs"

_MOCK_LISTINGS = [
    JobListing(
        title="Dev Python",
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev",
        snippet="Acme · Paris",
    ),
    JobListing(
        title="Data Engineer",
        url="https://www.welcometothejungle.com/fr/companies/beta/jobs/data",
        snippet="Beta · Lyon",
    ),
]

_MOCK_DETAILS = [
    JobDetail(
        title="Dev Python",
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev",
        snippet="Acme · Paris",
        page_title="Dev Python | Acme | WTTJ",
        text_preview="We are looking for...",
    ),
    JobDetail(
        title="Data Engineer",
        url="https://www.welcometothejungle.com/fr/companies/beta/jobs/data",
        snippet="Beta · Lyon",
        page_title="Data Engineer | Beta | WTTJ",
        text_preview="We need a data engineer...",
    ),
]


@pytest.mark.asyncio
async def test_scrape_returns_scrape_result():
    with (
        patch("wttj_scraper.browser_context") as mock_bctx,
        patch("wttj_scraper.scrape_listing", AsyncMock(return_value=_MOCK_LISTINGS)),
        patch("wttj_scraper.scrape_detail", side_effect=_MOCK_DETAILS),
        patch("wttj_scraper.asyncio.sleep", AsyncMock()),
    ):
        mock_bctx.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_bctx.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await scrape(_LISTING_URL, max_jobs=30, enrich_count=2)

    assert isinstance(result, ScrapeResult)
    assert result.source == _LISTING_URL
    assert result.count == 2
    assert len(result.jobs) == 2


@pytest.mark.asyncio
async def test_scrape_limits_enrich_count():
    with (
        patch("wttj_scraper.browser_context") as mock_bctx,
        patch("wttj_scraper.scrape_listing", AsyncMock(return_value=_MOCK_LISTINGS)),
        patch("wttj_scraper.scrape_detail", AsyncMock(return_value=_MOCK_DETAILS[0])),
        patch("wttj_scraper.asyncio.sleep", AsyncMock()),
    ):
        mock_bctx.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_bctx.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await scrape(_LISTING_URL, max_jobs=30, enrich_count=1)

    assert result.count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_scraper.py -v
```

Expected: `ImportError: cannot import name 'scrape' from 'wttj_scraper'`

- [ ] **Step 3: Implement `packages/wttj-scraper/src/wttj_scraper/__init__.py`**

```python
import asyncio
from datetime import datetime, timezone

from wttj_models.job import ScrapeResult
from wttj_scraper.browser import browser_context
from wttj_scraper.detail import scrape_detail
from wttj_scraper.listing import scrape_listing

_DELAY_BETWEEN_DETAILS = 1.2


async def scrape(
    url: str,
    max_jobs: int = 30,
    enrich_count: int = 15,
) -> ScrapeResult:
    async with browser_context() as context:
        listings = await scrape_listing(context, url, max_jobs)
        enriched = []
        for job in listings[:enrich_count]:
            detail = await scrape_detail(context, job)
            enriched.append(detail)
            await asyncio.sleep(_DELAY_BETWEEN_DETAILS)

    return ScrapeResult(
        source=url,
        count=len(enriched),
        jobs=enriched,
        scraped_at=datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_scraper.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASSED (no failures)

- [ ] **Step 6: Commit**

```bash
git add packages/wttj-scraper/src/wttj_scraper/__init__.py tests/test_scraper.py
git commit -m "feat: scrape() orchestrator combining listing + detail enrichment"
```

---

## Task 7: CLI Entry Point

**Files:**
- Create: `packages/wttj-cli/src/wttj_cli/main.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, patch
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
    with (
        patch("wttj_cli.main.asyncio.run", return_value=_MOCK_RESULT),
    ):
        from wttj_cli.main import main
        main(["--url", "https://www.welcometothejungle.com/fr/jobs", "--max-jobs", "5"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["count"] == 1
    assert data["jobs"][0]["title"] == "Dev Python"


def test_main_uses_defaults(capsys):
    with (
        patch("wttj_cli.main.asyncio.run", return_value=_MOCK_RESULT),
    ) as mock_run:
        from wttj_cli.main import main
        main([])

    mock_run.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError: No module named 'wttj_cli.main'`

- [ ] **Step 3: Implement `packages/wttj-cli/src/wttj_cli/main.py`**

```python
import argparse
import asyncio
import sys

from wttj_scraper import scrape

_DEFAULT_URL = "https://www.welcometothejungle.com/fr/jobs"
_DEFAULT_MAX_JOBS = 30
_DEFAULT_ENRICH_COUNT = 15


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape public job offers from Welcome to the Jungle")
    parser.add_argument("--url", default=_DEFAULT_URL, help="Jobs listing URL")
    parser.add_argument("--max-jobs", type=int, default=_DEFAULT_MAX_JOBS, help="Max jobs to extract from listing")
    parser.add_argument("--enrich-count", type=int, default=_DEFAULT_ENRICH_COUNT, help="Max jobs to enrich with detail page")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    result = asyncio.run(scrape(args.url, args.max_jobs, args.enrich_count))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Run full test suite one final time**

```bash
uv run pytest tests/ -v --tb=short
```

Expected: all tests PASSED

- [ ] **Step 6: Verify CLI runs end-to-end (smoke test — no real network)**

```bash
uv run wttj --help
```

Expected: usage message with `--url`, `--max-jobs`, `--enrich-count` options

- [ ] **Step 7: Commit**

```bash
git add packages/wttj-cli/src/wttj_cli/main.py tests/test_cli.py
git commit -m "feat: wttj CLI entry point outputting structured JSON"
```

---

## Self-Review

**Spec coverage:**
- [x] Python with Playwright — Task 3/4/5
- [x] UV workspace with packages — Task 1
- [x] Pydantic type safety — Task 2
- [x] KISS + exception handling — detail.py catches per-job errors without aborting run
- [x] title, url, snippet from listing — Task 4
- [x] page_title, text_preview from detail — Task 5
- [x] Structured JSON output — Task 6/7
- [x] CLI runnable with `uv run wttj` — Task 7
- [x] Structure ready for FastAPI microservice — `scrape()` in `__init__.py` is a clean async function, trivially wrapped in a FastAPI route

**Placeholder scan:** No TBD, TODO, or "similar to" patterns. All code blocks are complete.

**Type consistency:**
- `JobListing` used in listing.py → detail.py → __init__.py ✓
- `JobDetail` returned by scrape_detail, stored in ScrapeResult.jobs ✓
- `ScrapeResult` returned by scrape() and used in CLI ✓
- `browser_context` imported in __init__.py from browser.py ✓
- `scrape_listing` / `scrape_detail` imported in __init__.py ✓

---

## Run Commands Summary

```bash
# Install all deps + Playwright browsers
uv sync && uv run playwright install chromium

# Run all tests
uv run pytest tests/ -v

# Run the scraper (LIVE — will open a real browser)
uv run wttj --url "https://www.welcometothejungle.com/fr/jobs" --max-jobs 10 --enrich-count 5
```
