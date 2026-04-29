from __future__ import annotations

from collections.abc import Sequence
import re

from playwright.async_api import Locator
from playwright.async_api import Page

_EXPERIENCE_LABELS = (
    "Débutant/Diplômé (0-1 an)",
    "Junior (1-3 ans)",
    "Intermédiaire (3-5 ans)",
    "Senior (> 5 ans)",
)
_REMOTE_LABELS = (
    "Télétravail fréquent",
    "Télétravail occasionnel",
    "Pas de télétravail",
    "Télétravail total",
)
_CONTRACT_LABELS = (
    "CDI",
    "Freelance",
    "CDD / Temporaire",
    "Stage",
    "Alternance",
)


async def _save_filters(page: Page) -> None:
    await page.locator("form").first.evaluate("(form) => form.requestSubmit()")
    await page.wait_for_load_state("networkidle", timeout=120_000)


async def _open_section(page: Page, title: str) -> None:
    section_button = page.get_by_role("button", name=title, exact=True).first
    expanded = await section_button.get_attribute("aria-expanded")
    if expanded != "true":
        await section_button.click()


async def _click_label(page: Page, label: str) -> None:
    target = page.locator("label").filter(has_text=label).first
    if await target.count() == 0:
        raise RuntimeError(f"Filter label not found: {label}")
    await target.click()


async def _set_text_input(locator: Locator, value: str) -> None:
    await locator.evaluate(
        """(input, nextValue) => {
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
            setter?.call(input, nextValue);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));
        }""",
        value,
    )


async def _expand_contract_options(page: Page) -> None:
    toggle = page.get_by_test_id("contract-type-toggle-button").first
    if await toggle.count():
        toggle_text = (await toggle.text_content() or "").strip().lower()
        if "voir plus" in toggle_text:
            await toggle.click()


def _parse_salary_label(label: str) -> str | None:
    normalized = label.replace("\xa0", " ")
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*([kKmM])", normalized)
    if not match:
        digits = re.sub(r"[^\d]", "", normalized)
        return digits or None
    value = float(match.group(1).replace(",", "."))
    multiplier = 1_000 if match.group(2).lower() == "k" else 1_000_000
    return str(int(value * multiplier))


async def _set_checkbox(page: Page, label: str, expected: bool) -> None:
    checkbox = page.locator("label").filter(has_text=label).locator('input[type="checkbox"]').first
    if await checkbox.count() == 0:
        if expected:
            raise RuntimeError(f"Checkbox not found for label: {label}")
        return
    is_checked = await checkbox.is_checked()
    if is_checked != expected:
        await _click_label(page, label)


async def _set_salary_input(page: Page, salary_labels: Sequence[str]) -> None:
    if not salary_labels:
        return
    parsed_value = _parse_salary_label(salary_labels[0])
    if parsed_value is None:
        raise RuntimeError(f"Could not parse salary label: {salary_labels[0]}")
    salary_input = page.locator('input[name="salary.value"]').first
    if await salary_input.count() == 0:
        raise RuntimeError("Salary input not found")
    await _set_text_input(salary_input, parsed_value)


async def apply_global_filters(
    page: Page,
    *,
    location: Sequence[str],
    experience: Sequence[str],
    remote: Sequence[str],
    contract: Sequence[str],
    salary: Sequence[str],
) -> None:
    await _open_section(page, "Rôle")
    experience_set = set(experience)
    for label in _EXPERIENCE_LABELS:
        await _set_checkbox(page, label, label in experience_set)

    await _open_section(page, "Localisation")
    location_input = page.locator('input[name="locations"]').first
    for label in location:
        await _set_text_input(location_input, label)
    remote_set = set(remote)
    for label in _REMOTE_LABELS:
        await _set_checkbox(page, label, label in remote_set)

    await _open_section(page, "Contrat et salaire")
    await _expand_contract_options(page)
    contract_set = set(contract)
    for label in _CONTRACT_LABELS:
        await _set_checkbox(page, label, label in contract_set)
    await _set_salary_input(page, salary)
    await _save_filters(page)


async def apply_role_variant(page: Page, role: str) -> None:
    await _open_section(page, "Rôle")
    role_input = page.locator('input[name="futureRole"]').first
    await _set_text_input(role_input, role)
    await _save_filters(page)


async def collect_visible_preference_chips(page: Page) -> list[str]:
    return await page.locator("article span").evaluate_all(
        "els => els.map(el => (el.textContent || '').trim()).filter(Boolean)"
    )
