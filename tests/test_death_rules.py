from datetime import date

import pytest

from crs_assistant import checklist, reference
from crs_assistant.death_rules import (
    Circumstance,
    DeathCase,
    DeathPlace,
    DeathService,
    build_death_plan,
    death_registration_deadline,
)
from crs_assistant.i18n import MESSAGES
from crs_assistant.rules import Category

TODAY = date(2026, 10, 22)


def doc_ids(plan):
    return [d.id for d in plan.documents]


def test_deadline_is_six_months():
    assert death_registration_deadline(date(2026, 8, 31)) == date(2027, 2, 28)


def test_future_death_rejected():
    with pytest.raises(ValueError):
        DeathCase(DeathService.REGISTER, date(2026, 10, 23), today=TODAY)


def test_timely_facility_death():
    plan = build_death_plan(DeathCase(DeathService.REGISTER, date(2026, 10, 20), today=TODAY))
    assert plan.category is Category.DEATH_TIMELY
    assert plan.deadline == date(2027, 4, 20)
    assert doc_ids(plan) == ["death_notification", "informant_id", "deceased_id", "ecitizen_payment"]
    assert plan.steps[0] == "step.collect_death_notification"
    assert "step.collect_burial_permit" in plan.steps
    assert plan.warnings == ["warn.burial_permit"]


def test_home_death_needs_chief_letter():
    plan = build_death_plan(DeathCase(DeathService.REGISTER, date(2026, 10, 20), place_of_death=DeathPlace.HOME, today=TODAY))
    assert doc_ids(plan)[0] == "death_chief_letter"
    assert "death_notification" not in doc_ids(plan)
    assert plan.steps[0] == "step.report_death_chief"


def test_unnatural_death_goes_through_police():
    plan = build_death_plan(
        DeathCase(DeathService.REGISTER, date(2026, 10, 20), circumstance=Circumstance.UNNATURAL, today=TODAY)
    )
    mandatory = {d.id: d.mandatory for d in plan.documents}
    assert mandatory["police_death_report"] is True
    assert mandatory["postmortem_report"] is False
    assert "step.report_death_police" in plan.steps
    assert plan.warnings[0] == "warn.unnatural_death"


def test_deceased_without_id():
    plan = build_death_plan(DeathCase(DeathService.REGISTER, date(2026, 10, 20), deceased_had_id=False, today=TODAY))
    assert "deceased_id" not in doc_ids(plan)
    assert {d.id: d.mandatory for d in plan.documents}["deceased_birth_certificate"] is False


def test_deadline_soon_warning():
    plan = build_death_plan(DeathCase(DeathService.REGISTER, date(2026, 5, 1), today=TODAY))
    assert plan.warnings[0] == "warn.deadline_soon"


def test_late_death_registration_requires_proof_of_death():
    plan = build_death_plan(DeathCase(DeathService.REGISTER, date(2024, 1, 1), place_of_death=DeathPlace.HOME, today=TODAY))
    assert plan.category is Category.DEATH_LATE
    assert plan.warnings[0] == "warn.deadline_passed"
    assert [d.id for d in plan.documents if d.group == "proof_of_death"] == [
        "death_notification",
        "burial_permit",
        "death_chief_letter",
        "death_affidavit",
    ]
    base = {"late_registration_form", "informant_id", "deceased_id", "ecitizen_payment"}
    assert not checklist.assess(plan, base).ready
    assert checklist.assess(plan, base | {"death_affidavit"}).ready


def test_abroad_and_replacement():
    abroad = build_death_plan(DeathCase(DeathService.REGISTER, date(2026, 10, 1), place_of_death=DeathPlace.ABROAD, today=TODAY))
    assert abroad.category is Category.DEATH_ABROAD
    assert abroad.documents == []

    replacement = build_death_plan(DeathCase(DeathService.REPLACEMENT, date(2010, 1, 1), today=TODAY))
    assert replacement.category is Category.DEATH_REPLACEMENT
    assert "police_abstract" in doc_ids(replacement)


@pytest.mark.parametrize("service", list(DeathService))
@pytest.mark.parametrize("place", list(DeathPlace))
@pytest.mark.parametrize("circumstance", list(Circumstance))
@pytest.mark.parametrize("dod", [date(2026, 10, 1), date(2026, 5, 1), date(2020, 1, 1)])
def test_every_death_plan_renders(service, place, circumstance, dod):
    plan = build_death_plan(DeathCase(service, dod, place_of_death=place, circumstance=circumstance, today=TODAY))
    for doc in plan.documents:
        assert doc.id in reference.documents()
    for key in [f"category.{plan.category.value}", *plan.steps, *plan.warnings]:
        assert key in MESSAGES
    rendered = checklist.render(plan, "sw")
    assert rendered.category_label
