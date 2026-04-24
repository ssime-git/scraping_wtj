import re

from playwright.async_api import BrowserContext
from wttj_models.job import JobDetail, JobListing

_EXTRACT_JS = """
() => {
    const normalize = (v) => (v || '').replace(/\\s+/g, ' ').trim();
    const collectTexts = (selectors) => Array.from(document.querySelectorAll(selectors))
        .map((node) => normalize(node.textContent))
        .filter(Boolean);
    const sectionText = (patterns) => {
        const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, strong, summary'));
        for (const heading of headings) {
            const headingText = normalize(heading.textContent).toLowerCase();
            if (patterns.some((pattern) => headingText.includes(pattern))) {
                const container = heading.closest('section, article, div') || heading.parentElement;
                const text = normalize(container?.innerText || '');
                if (text) return text;
            }
        }
        return null;
    };
    const factTexts = collectTexts('aside *, section *, article *');
    const companyName =
        normalize(document.querySelector("a[href*='/companies/']")?.textContent) ||
        normalize(document.querySelector("[data-testid='company-name']")?.textContent) ||
        null;
    const findFact = (patterns) =>
        factTexts.find((text) => patterns.some((pattern) => text.toLowerCase().includes(pattern))) || null;
    return {
        page_title: normalize(document.querySelector('h1')?.textContent) || null,
        text_preview: normalize(document.body.innerText).slice(0, 3000),
        company_name: companyName,
        contract_type: findFact(['cdi', 'cdd', 'alternance', 'stage', 'freelance', 'internship']),
        remote_level: findFact(['télétravail', 'remote', 'hybride']),
        location_label: findFact(['france', 'paris', 'lyon', 'malakoff']),
        city: findFact(['malakoff', 'paris', 'lyon', 'marseille', 'bordeaux']),
        date_posted_label: findFact(['month', 'mois', 'semaine', 'jour', 'today', 'aujourd']),
        company_sectors: collectTexts("a[href*='/jobs?aroundQuery='], a[href*='/companies/'] + *").slice(0, 5),
        description_raw: sectionText(['description', 'descriptif', 'about the job']),
        missions_raw: sectionText(['mission', 'responsabilit', 'what you will do']),
        profile_raw: sectionText(['profil', 'requirements', 'about you']),
        benefits_raw: sectionText(['benefit', 'avantage']),
        facts_raw: factTexts.slice(0, 100),
    };
}
"""


def _compact(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_languages(*texts: str | None) -> list[str]:
    haystack = " ".join(_compact(text).lower() for text in texts if text)
    found = []
    for label, patterns in {
        "French": ["français", "french"],
        "English": ["anglais", "english"],
        "German": ["allemand", "german"],
        "Spanish": ["espagnol", "spanish"],
        "Portuguese": ["portugais", "portuguese"],
    }.items():
        if any(pattern in haystack for pattern in patterns):
            found.append(label)
    return found


def _extract_tools(*texts: str | None) -> list[str]:
    haystack = " ".join(_compact(text).lower() for text in texts if text)
    tools = []
    for tool, patterns in {
        "CRM": ["crm"],
        "SEO": ["seo"],
        "LinkedIn": ["linkedin"],
        "WhatsApp": ["whatsapp"],
        "Emailing": ["emailing"],
        "Webinars": ["webinar", "webinaire"],
    }.items():
        if any(pattern in haystack for pattern in patterns):
            tools.append(tool)
    return tools


def _extract_job_functions(*texts: str | None) -> list[str]:
    haystack = " ".join(_compact(text).lower() for text in texts if text)
    functions = []
    for function, patterns in {
        "Marketing Strategy": ["marketing", "brand"],
        "B2B": ["b2b"],
        "B2B2C": ["b2b2c"],
        "Product Marketing": ["product marketing", "marketing produit"],
        "Corporate Communication": ["communication corporate", "communication"],
        "Lead Generation": ["lead generation", "génération de leads"],
        "Events": ["congrès", "event", "webinar", "webinaire"],
        "Social Media": ["linkedin", "social media", "réseaux sociaux"],
    }.items():
        if any(pattern in haystack for pattern in patterns):
            functions.append(function)
    return functions


def _extract_education_level(*texts: str | None) -> str | None:
    haystack = " ".join(_compact(text) for text in texts if text)
    match = re.search(r"(Bac\s*\+\s*\d)", haystack, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_experience_months(*texts: str | None) -> tuple[int | None, int | None]:
    haystack = " ".join(_compact(text) for text in texts if text)
    if re.search(r"(<|moins de)\s*6\s*mois", haystack, re.IGNORECASE):
        return 0, 6
    matches = [int(value) for value in re.findall(r"(\d+)\s*mois", haystack, re.IGNORECASE)]
    if not matches:
        return None, None
    return min(matches), max(matches)


async def scrape_detail(context: BrowserContext, job: JobListing) -> JobDetail:
    page = await context.new_page()
    try:
        await page.goto(job.url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(1_200)
        details: dict = await page.evaluate(_EXTRACT_JS)
        details["job_title"] = details.get("page_title") or job.title
        details["job_url"] = job.url
        details["job_id"] = job.url.rstrip("/").rsplit("/", 1)[-1]
        details["company_sectors"] = details.get("company_sectors") or []
        details["languages_required"] = details.get("languages_required") or _extract_languages(
            details.get("profile_raw"),
            details.get("missions_raw"),
            details.get("text_preview"),
        )
        details["tools"] = details.get("tools") or _extract_tools(
            details.get("profile_raw"),
            details.get("missions_raw"),
            details.get("text_preview"),
        )
        details["job_functions"] = details.get("job_functions") or _extract_job_functions(
            details.get("missions_raw"),
            details.get("description_raw"),
            details.get("text_preview"),
        )
        details["education_level"] = details.get("education_level") or _extract_education_level(
            details.get("profile_raw"),
            details.get("text_preview"),
        )
        if details.get("experience_min_months") is None and details.get("experience_max_months") is None:
            details["experience_min_months"], details["experience_max_months"] = _extract_experience_months(
                details.get("profile_raw"),
                details.get("text_preview"),
            )
        payload = job.model_dump()
        payload.update(details)
        return JobDetail(**payload)
    except Exception as exc:
        return JobDetail(**job.model_dump(), error=str(exc))
    finally:
        await page.close()
