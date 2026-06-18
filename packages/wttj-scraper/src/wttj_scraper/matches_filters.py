from __future__ import annotations

import asyncio
from collections.abc import Sequence
from contextlib import suppress
import re
from typing import Any

Locator = Any
Page = Any

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


async def _dismiss_axeptio_if_present(page: Page) -> bool:
    """Try to dismiss known Axeptio cookie buttons or labeled cookie buttons.
    Return True if a dismissal click was performed."""
    for button_id in (
        "axeptio_btn_configure",
        "axeptio_btn_dismiss",
        "axeptio_btn_acceptAll",
        "axeptio_btn_acceptAllAndNext",
        "axeptio_main_button",
    ):
        btn = page.locator(f"#{button_id}").first
        if await btn.count():
            try:
                await btn.click(timeout=5_000)
                return True
            except Exception:
                continue
    for label in ("OK pour moi", "Non merci", "Je choisis", "J'accepte tout"):
        btn = page.get_by_role("button", name=label).first
        if await btn.count():
            try:
                await btn.click(timeout=5_000)
                return True
            except Exception:
                continue
    return False


async def _safe_click(
    page: Page, locator_obj, *, attempts: int = 4, retry_delay: float = 0.5
) -> None:
    """Attempt to click a locator, handling overlay interception by dismissing Axeptio and retrying."""
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            await locator_obj.click(timeout=5_000)
            return
        except Exception as exc:
            last_exc = exc
            with suppress(Exception):
                await locator_obj.scroll_into_view_if_needed()
            with suppress(Exception):
                await _dismiss_axeptio_if_present(page)
            await asyncio.sleep(retry_delay)
    if last_exc is not None:
        raise last_exc


async def _open_section(page: Page, title: str) -> None:
    section_button = page.get_by_role("button", name=title, exact=True).first
    expanded = await section_button.get_attribute("aria-expanded")
    if expanded != "true":
        await _safe_click(page, section_button)
        for _ in range(25):
            await asyncio.sleep(0.2)
            if await section_button.get_attribute("aria-expanded") == "true":
                return
        raise RuntimeError(f"Section '{title}' did not expand after click")


async def _click_label(page: Page, label: str) -> None:
    target = page.locator("label").filter(has_text=label).first
    if await target.count() == 0:
        raise RuntimeError(f"Filter label not found: {label}")
    await _safe_click(page, target)


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
            await _safe_click(page, toggle)


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
    checkbox = (
        page.locator("label")
        .filter(has_text=label)
        .locator('input[type="checkbox"]')
        .first
    )
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
