from datetime import date

import pytest

from crs_assistant import checklist, reference
from crs_assistant.i18n import MESSAGES
from crs_assistant.id_rules import (
    ChangeReason,
    IdCase,
    IdService,
    ParentStatus,
    build_id_plan,
    id_eligibility_date,
)
from crs_assistant.rules import Category

TODAY = date(2026, 10, 22)


def doc_ids(plan):
    return [d.id for d in plan.documents]


def test_eligibility_date_handles_leap_day():
    assert id_eligibility_date(date(2008, 2, 29)) == date(2026, 2, 28)
    assert id_eligibility_date(date(2008, 10, 22)) == date(2026, 10, 22)


def test_future_birth_rejected():
    with pytest.raises(ValueError):
        IdCase(IdService.FIRST_TIME, date(2026, 10, 23), today=TODAY)


def test_first_time_with_both_parents():
    plan = build_id_plan(IdCase(IdService.FIRST_TIME, date(2008, 1, 1), today=TODAY))
    assert plan.category is Category.ID_FIRST_TIME
    assert doc_ids(plan) == ["applicant_birth_certificate", "mother_id", "father_id", "school_record"]
    assert plan.warnings == []
    assert "id_fee_payment" not in doc_ids(plan)


def test_eligible_on_18th_birthday():
    plan = build_id_plan(IdCase(IdService.FIRST_TIME, date(2008, 10, 22), today=TODAY))
    assert plan.category is Category.ID_FIRST_TIME
    assert plan.days_remaining == 0


def test_under_18_gets_eligibility_date_and_preparation_steps():
    plan = build_id_plan(IdCase(IdService.FIRST_TIME, date(2008, 12, 1), today=TODAY))
    assert plan.category is Category.ID_NOT_YET
    assert plan.deadline == date(2026, 12, 1)
    assert plan.days_remaining == 40
    assert plan.steps[0] == "step.id_prepare"
    rendered = checklist.render(plan, "en")
    assert rendered.warnings[0] == "You can apply from 2026-12-01, in 40 day(s). Prepare the documents now."


def test_no_birth_certificate_routes_to_birth_registration_first():
    plan = build_id_plan(IdCase(IdService.FIRST_TIME, date(2005, 1, 1), has_birth_certificate=False, today=TODAY))
    assert plan.category is Category.ID_BIRTH_CERT_FIRST
    assert plan.steps[0] == "step.id_get_birth_certificate"
    assert plan.warnings[0] == "warn.id_birth_certificate_first"
    assert not checklist.assess(plan, {"mother_id", "father_id"}).ready


def test_deceased_and_unknown_parents():
    plan = build_id_plan(
        IdCase(IdService.FIRST_TIME, date(2005, 1, 1), mother=ParentStatus.HAS_ID, father=ParentStatus.DECEASED, today=TODAY)
    )
    assert doc_ids(plan) == ["applicant_birth_certificate", "mother_id", "parent_death_certificate", "school_record"]
    assert plan.warnings == []

    orphan = build_id_plan(
        IdCase(IdService.FIRST_TIME, date(2005, 1, 1), mother=ParentStatus.DECEASED, father=ParentStatus.UNKNOWN, today=TODAY)
    )
    assert "id_introduction_letter" in doc_ids(orphan)
    assert orphan.warnings == ["warn.id_vetting"]


def test_replacement():
    plan = build_id_plan(IdCase(IdService.REPLACEMENT, date(1990, 1, 1), today=TODAY))
    assert plan.category is Category.ID_REPLACEMENT
    assert {d.id: d.mandatory for d in plan.documents} == {
        "id_police_abstract": True,
        "lost_id_copy": False,
        "applicant_birth_certificate": False,
        "id_fee_payment": True,
    }


@pytest.mark.parametrize(
    "reason,evidence",
    [
        (ChangeReason.MARRIAGE, {"own_marriage_certificate"}),
        (ChangeReason.NAME_CHANGE, {"deed_poll"}),
        (ChangeReason.ERROR, {"applicant_birth_certificate", "correction_evidence"}),
    ],
)
def test_change_of_particulars(reason, evidence):
    plan = build_id_plan(IdCase(IdService.CHANGE, date(1990, 1, 1), change_reason=reason, today=TODAY))
    assert plan.category is Category.ID_CHANGE
    assert set(doc_ids(plan)) == {"original_id", "id_fee_payment"} | evidence


@pytest.mark.parametrize("service", list(IdService))
@pytest.mark.parametrize("dob", [date(2010, 1, 1), date(2008, 10, 22), date(1990, 1, 1)])
@pytest.mark.parametrize("has_cert", [True, False])
@pytest.mark.parametrize("mother", list(ParentStatus))
@pytest.mark.parametrize("father", list(ParentStatus))
def test_every_id_plan_renders(service, dob, has_cert, mother, father):
    plan = build_id_plan(IdCase(service, dob, has_cert, mother, father, today=TODAY))
    for doc in plan.documents:
        assert doc.id in reference.documents()
    for key in [f"category.{plan.category.value}", *plan.steps, *plan.warnings]:
        assert key in MESSAGES
    assert checklist.render(plan, "sw").category_label
