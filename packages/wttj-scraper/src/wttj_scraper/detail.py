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
