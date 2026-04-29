from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import call

import pytest

from wttj_scraper.matches_filters import apply_global_filters
from wttj_scraper.matches_filters import apply_role_variant
from wttj_scraper.matches_filters import collect_visible_preference_chips


def _make_label_locator(*, checked: bool) -> MagicMock:
    locator = MagicMock()
    locator.first = locator
    locator.count = AsyncMock(return_value=1)
    locator.click = AsyncMock()
    locator.is_checked = AsyncMock(return_value=checked)
    return locator


@pytest.mark.asyncio
async def test_apply_role_variant_updates_input_and_submits_form():
    page = MagicMock()
    page.wait_for_load_state = AsyncMock()
    section_button = MagicMock()
    section_button.first = section_button
    section_button.get_attribute = AsyncMock(return_value="true")
    section_button.click = AsyncMock()

    role_input = MagicMock()
    role_input.first = role_input
    role_input.evaluate = AsyncMock()

    form_locator = MagicMock()
    form_locator.first = form_locator
    form_locator.evaluate = AsyncMock()

    page.get_by_role.return_value = section_button
    page.locator.side_effect = [role_input, form_locator]

    await apply_role_variant(page, "Data Engineer")

    role_input.evaluate.assert_awaited_once()
    assert role_input.evaluate.await_args.args[1] == "Data Engineer"
    form_locator.evaluate.assert_awaited_once_with("(form) => form.requestSubmit()")
    page.wait_for_load_state.assert_awaited_once_with("networkidle", timeout=120_000)


@pytest.mark.asyncio
async def test_apply_global_filters_sets_expected_checkbox_states_and_submits():
    page = MagicMock()
    page.wait_for_load_state = AsyncMock()

    role_button = MagicMock()
    role_button.first = role_button
    role_button.get_attribute = AsyncMock(return_value="true")

    location_button = MagicMock()
    location_button.first = location_button
    location_button.get_attribute = AsyncMock(return_value="true")

    contract_button = MagicMock()
    contract_button.first = contract_button
    contract_button.get_attribute = AsyncMock(return_value="true")

    toggle = MagicMock()
    toggle.first = toggle
    toggle.count = AsyncMock(return_value=1)
    toggle.text_content = AsyncMock(return_value="Voir plus")
    toggle.click = AsyncMock()

    location_input = MagicMock()
    location_input.first = location_input
    location_input.evaluate = AsyncMock()

    salary_input = MagicMock()
    salary_input.first = salary_input
    salary_input.count = AsyncMock(return_value=1)
    salary_input.evaluate = AsyncMock()

    form_locator = MagicMock()
    form_locator.first = form_locator
    form_locator.evaluate = AsyncMock()

    label_states = {
        "Débutant/Diplômé (0-1 an)": _make_label_locator(checked=True),
        "Junior (1-3 ans)": _make_label_locator(checked=False),
        "Intermédiaire (3-5 ans)": _make_label_locator(checked=False),
        "Senior (> 5 ans)": _make_label_locator(checked=True),
        "Télétravail fréquent": _make_label_locator(checked=False),
        "Télétravail occasionnel": _make_label_locator(checked=True),
        "Pas de télétravail": _make_label_locator(checked=True),
        "Télétravail total": _make_label_locator(checked=False),
        "CDI": _make_label_locator(checked=False),
        "Freelance": _make_label_locator(checked=True),
        "CDD / Temporaire": _make_label_locator(checked=True),
        "Stage": _make_label_locator(checked=False),
        "Alternance": _make_label_locator(checked=True),
        "≥ 10K €par an": _make_label_locator(checked=False),
    }

    def locator(selector: str) -> MagicMock:
        if selector == 'input[name="locations"]':
            return location_input
        if selector == 'input[name="salary.value"]':
            return salary_input
        if selector == "form":
            return form_locator
        if selector == "label":
            label_root = MagicMock()

            def filter_side_effect(*, has_text: str) -> MagicMock:
                return MagicMock(locator=MagicMock(return_value=label_states[has_text]), first=label_states[has_text], count=label_states[has_text].count, click=label_states[has_text].click)

            label_root.filter.side_effect = filter_side_effect
            return label_root
        raise AssertionError(f"Unexpected locator selector: {selector}")

    page.get_by_role.side_effect = [role_button, location_button, contract_button]
    page.get_by_test_id.return_value = toggle
    page.locator.side_effect = locator

    await apply_global_filters(
        page,
        location=["France"],
        experience=["Débutant/Diplômé (0-1 an)", "Junior (1-3 ans)", "Intermédiaire (3-5 ans)"],
        remote=["Télétravail fréquent", "Pas de télétravail", "Télétravail total"],
        contract=["CDI", "CDD / Temporaire", "Stage"],
        salary=["≥ 10K €par an"],
    )

    location_input.evaluate.assert_awaited_once()
    assert location_input.evaluate.await_args.args[1] == "France"
    assert label_states["Junior (1-3 ans)"].click.await_count == 1
    assert label_states["Intermédiaire (3-5 ans)"].click.await_count == 1
    assert label_states["Senior (> 5 ans)"].click.await_count == 1
    assert label_states["Télétravail fréquent"].click.await_count == 1
    assert label_states["Télétravail occasionnel"].click.await_count == 1
    assert label_states["CDI"].click.await_count == 1
    assert label_states["Freelance"].click.await_count == 1
    assert label_states["Stage"].click.await_count == 1
    assert label_states["Alternance"].click.await_count == 1
    salary_input.evaluate.assert_awaited_once()
    assert salary_input.evaluate.await_args.args[1] == "10000"
    toggle.click.assert_awaited_once()
    form_locator.evaluate.assert_awaited_once_with("(form) => form.requestSubmit()")
    page.wait_for_load_state.assert_awaited_once_with("networkidle", timeout=120_000)


@pytest.mark.asyncio
async def test_collect_visible_preference_chips_reads_chip_texts():
    page = MagicMock()
    chips_locator = MagicMock()
    chips_locator.evaluate_all = AsyncMock(return_value=["France", "CDI"])
    page.locator.return_value = chips_locator

    chips = await collect_visible_preference_chips(page)

    assert chips == ["France", "CDI"]
