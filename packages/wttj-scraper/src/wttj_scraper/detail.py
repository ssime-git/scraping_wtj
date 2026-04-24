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


def _summary_lines(summary: str | None) -> list[str]:
    return [_compact(line) for line in (summary or "").splitlines() if _compact(line)]


def _value_after_label(lines: list[str], labels: tuple[str, ...]) -> str | None:
    label_set = {label.lower().rstrip(":") for label in labels}
    for index, line in enumerate(lines):
        normalized = line.lower().rstrip(":").strip()
        if normalized in label_set and index + 1 < len(lines):
            return lines[index + 1]
        for label in label_set:
            prefix = f"{label} :"
            if line.lower().startswith(prefix):
                value = _compact(line[len(prefix) :])
                return value or (lines[index + 1] if index + 1 < len(lines) else None)
    return None


def _values_after_label_until_next_section(
    lines: list[str], label: str, stop_labels: tuple[str, ...]
) -> list[str]:
    label_normalized = label.lower().rstrip(":")
    stop_set = {stop.lower().rstrip(":") for stop in stop_labels}
    values: list[str] = []
    collecting = False
    for line in lines:
        normalized = line.lower().rstrip(":").strip()
        if normalized == label_normalized:
            collecting = True
            continue
        if collecting and normalized in stop_set:
            break
        if collecting:
            values.append(line)
    return values


def parse_summary_metadata(summary: str | None) -> dict[str, object | None]:
    text = _compact(summary)
    lines = _summary_lines(summary)
    if not text:
        return {
            "city": None,
            "contract_type": None,
            "remote_level": None,
            "date_posted_label": None,
            "salary_label": None,
            "salary_visible": False,
            "start_date": None,
            "experience_label": None,
            "education_level": None,
            "skills_hard": [],
        }

    contract_type = None
    for candidate in ("Alternance", "Stage", "CDI", "CDD", "Freelance", "Internship"):
        if re.search(rf"\b{re.escape(candidate)}\b", text, re.IGNORECASE):
            contract_type = candidate
            break

    remote_level = next(
        (
            line
            for line in lines
            if re.match(r"^(Télétravail|Teletravail|Remote|Hybride)\b", line, re.IGNORECASE)
        ),
        None,
    )
    if remote_level is None:
        remote_match = re.search(
            r"(Télétravail(?:\s+[A-Za-zÀ-ÿ-]+){0,2}|Teletravail(?:\s+[A-Za-zÀ-ÿ-]+){0,2}|Remote(?:\s+[A-Za-zÀ-ÿ-]+){0,2})",
            text,
            re.IGNORECASE,
        )
        if remote_match:
            remote_level = _compact(remote_match.group(1))

    city = None
    city_match = re.search(
        r"\b(Paris|Lille|Lyon|Marseille|Bordeaux|Malakoff|Neuilly-sur-Seine|Boulogne-Billancourt|Wasquehal|Montreuil|Bois-Colombes)\b",
        text,
        re.IGNORECASE,
    )
    if city_match:
        city = city_match.group(1)

    date_posted_label = None
    date_match = re.search(
        r"\b(avant-hier|hier|aujourd'hui|today|last month|le mois dernier|il y a \d+ heures?|il y a \d+ jours?)\b",
        text,
        re.IGNORECASE,
    )
    if date_match:
        date_posted_label = _compact(date_match.group(1))

    salary_label = _value_after_label(lines, ("Salaire", "Salary"))
    salary_visible = bool(salary_label and not re.search(r"non spécifié|non specifie", salary_label, re.IGNORECASE))
    start_date = _value_after_label(lines, ("Début", "Debut", "Start date"))
    experience_label = _value_after_label(lines, ("Expérience", "Experience"))
    education_label = _value_after_label(lines, ("Éducation", "Education"))
    education_level = None
    if education_label:
        education_match = re.search(r"(Bac\s*\+\s*\d)", education_label, re.IGNORECASE)
        education_level = education_match.group(1) if education_match else education_label

    skills_hard = _values_after_label_until_next_section(
        lines,
        "Compétences & expertises",
        (
            "Questions et réponses sur l'offre",
            "Le poste",
            "Descriptif du poste",
            "Profil recherché",
            "L'entreprise",
            "Les avantages salariés",
            "Le lieu de travail",
        ),
    )

    return {
        "city": city,
        "contract_type": contract_type,
        "remote_level": remote_level,
        "date_posted_label": date_posted_label,
        "salary_label": salary_label,
        "salary_visible": salary_visible,
        "start_date": start_date,
        "experience_label": experience_label,
        "education_level": education_level,
        "skills_hard": skills_hard,
    }


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


def _is_noisy_metadata_value(key: str, value: object) -> bool:
    if not isinstance(value, str):
        return False
    if key not in {
        "contract_type",
        "city",
        "remote_level",
        "date_posted_label",
        "salary_label",
        "start_date",
        "experience_label",
        "education_level",
    }:
        return False
    noisy_markers = ("Postuler", "Sauvegarder", "Partager", "Copier le lien")
    return len(value) > 80 or any(marker.lower() in value.lower() for marker in noisy_markers)


def _apply_summary_metadata(details: dict, summary: str | None) -> None:
    metadata = parse_summary_metadata(summary)
    has_salary_label = bool(metadata.get("salary_label"))
    for key, value in metadata.items():
        if key == "salary_visible":
            if has_salary_label and details.get(key) is None:
                details[key] = value
            continue
        if value in (None, "", []):
            continue
        current_value = details.get(key)
        if current_value in (None, "", []) or _is_noisy_metadata_value(key, current_value):
            details[key] = value


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
        facts_raw = details.get("facts_raw") or []
        if isinstance(facts_raw, list):
            _apply_summary_metadata(details, "\n".join(str(fact) for fact in facts_raw))
        _apply_summary_metadata(details, job.snippet)
        _apply_summary_metadata(details, details.get("text_preview"))
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
