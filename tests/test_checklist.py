import re
from datetime import date

import pytest

from crs_assistant import checklist
from crs_assistant.i18n import MESSAGES, SUPPORTED_LANGUAGES, normalise_lang, t
from crs_assistant.rules import Case, Service, build_plan

TODAY = date(2026, 10, 22)


def test_every_message_has_all_languages_with_matching_placeholders():
    for key, entry in MESSAGES.items():
        for lang in SUPPORTED_LANGUAGES:
            assert entry.get(lang), f"{key} missing {lang}"
        placeholders = {lang: set(re.findall(r"{(\w+)}", entry[lang])) for lang in SUPPORTED_LANGUAGES}
        assert placeholders["en"] == placeholders["sw"], key


def test_normalise_lang():
    assert normalise_lang("SW-KE") == "sw"
    assert normalise_lang("fr") == "en"
    assert normalise_lang(None) == "en"


def test_render_in_swahili_fills_warning_params():
    plan = build_plan(Case(Service.REGISTER, date(2026, 5, 10), today=TODAY))
    rendered = checklist.render(plan, "sw")
    assert rendered.category == "timely"
    assert rendered.category_label == t("category.timely", "sw")
    assert "19" in rendered.warnings[0]
    assert "2026-11-10" in rendered.warnings[0]
    assert rendered.items[0].label.startswith("Taarifa ya kuzaliwa")


def test_assess_ready_when_all_mandatory_present():
    plan = build_plan(Case(Service.REGISTER, date(2026, 9, 1), parents_married=True, today=TODAY))
    have = {d.id for d in plan.documents if d.mandatory}
    result = checklist.assess(plan, have)
    assert result.ready
    assert result.missing == []


def test_assess_lists_missing_mandatory_only():
    plan = build_plan(Case(Service.REGISTER, date(2026, 9, 1), parents_married=True, today=TODAY))
    result = checklist.assess(plan, {"birth_notification", "mother_id"})
    assert not result.ready
    assert result.missing == ["father_id", "ecitizen_payment"]
    assert "marriage_certificate" not in result.missing


@pytest.mark.parametrize("proof", ["clinic_card", "school_record", "baptism_card", "age_assessment"])
def test_any_single_proof_of_age_satisfies_group(proof):
    plan = build_plan(Case(Service.REGISTER, date(2018, 1, 1), include_father=False, today=TODAY))
    base = {"late_registration_form", "mother_id", "ecitizen_payment"}
    assert checklist.assess(plan, base | {proof}).ready


def test_missing_proof_of_age_reported_as_group():
    plan = build_plan(Case(Service.REGISTER, date(2018, 1, 1), include_father=False, today=TODAY))
    result = checklist.assess(plan, {"late_registration_form", "mother_id", "ecitizen_payment"}, "sw")
    assert result.missing_groups == ["proof_of_age"]
    assert t("group.proof_of_age", "sw") in result.message
