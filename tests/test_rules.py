from datetime import date

import pytest

from crs_assistant import reference
from crs_assistant.rules import (
    Applicant,
    BirthPlace,
    Case,
    Category,
    Service,
    add_months,
    age_in_years,
    build_plan,
    registration_deadline,
)

TODAY = date(2026, 10, 22)


def doc_ids(plan):
    return [d.id for d in plan.documents]


def test_add_months_clamps_to_month_end():
    assert add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert add_months(date(2027, 8, 31), 6) == date(2028, 2, 29)


def test_registration_deadline_is_six_months():
    assert registration_deadline(date(2026, 5, 1)) == date(2026, 11, 1)


def test_age_in_years_respects_birthday():
    assert age_in_years(date(2008, 10, 23), TODAY) == 17
    assert age_in_years(date(2008, 10, 22), TODAY) == 18


def test_future_birth_date_rejected():
    with pytest.raises(ValueError):
        Case(Service.REGISTER, date(2026, 10, 23), today=TODAY)


def test_timely_facility_birth():
    plan = build_plan(Case(Service.REGISTER, date(2026, 9, 1), parents_married=True, today=TODAY))
    assert plan.category is Category.TIMELY
    assert plan.deadline == date(2027, 3, 1)
    assert plan.days_remaining == 130
    assert doc_ids(plan)[0] == "birth_notification"
    assert "marriage_certificate" in doc_ids(plan)
    assert "joint_parent_consent" not in doc_ids(plan)
    assert plan.steps[0] == "step.collect_notification"
    assert plan.warnings == []


def test_timely_home_birth_needs_chief_letter():
    plan = build_plan(Case(Service.REGISTER, date(2026, 9, 1), birth_place=BirthPlace.HOME, today=TODAY))
    assert "chief_letter" in doc_ids(plan)
    assert "birth_notification" not in doc_ids(plan)
    assert plan.steps[0] == "step.report_home_birth"


def test_unmarried_parents_need_joint_consent_for_father():
    plan = build_plan(Case(Service.REGISTER, date(2026, 9, 1), parents_married=False, today=TODAY))
    assert "joint_parent_consent" in doc_ids(plan)
    assert "warn.father_joint_consent" in plan.warnings


def test_father_omitted_when_not_included():
    plan = build_plan(Case(Service.REGISTER, date(2026, 9, 1), include_father=False, today=TODAY))
    assert "father_id" not in doc_ids(plan)
    assert "joint_parent_consent" not in doc_ids(plan)


def test_deadline_soon_warning():
    plan = build_plan(Case(Service.REGISTER, date(2026, 5, 10), today=TODAY))
    assert plan.category is Category.TIMELY
    assert plan.warnings[0] == "warn.deadline_soon"


def test_last_day_is_still_timely():
    plan = build_plan(Case(Service.REGISTER, date(2026, 4, 22), today=TODAY))
    assert plan.category is Category.TIMELY
    assert plan.days_remaining == 0


def test_late_registration_requires_proof_of_age_group():
    plan = build_plan(Case(Service.REGISTER, date(2022, 1, 15), today=TODAY))
    assert plan.category is Category.LATE
    assert plan.warnings[0] == "warn.deadline_passed"
    grouped = [d.id for d in plan.documents if d.group == "proof_of_age"]
    assert grouped == ["clinic_card", "school_record", "baptism_card", "age_assessment"]
    assert doc_ids(plan)[0] == "late_registration_form"


def test_late_adult_self_application():
    plan = build_plan(
        Case(Service.REGISTER, date(1990, 3, 3), applicant=Applicant.SELF, today=TODAY)
    )
    assert plan.category is Category.LATE_ADULT
    assert "applicant_id" in doc_ids(plan)
    assert "father_id" not in doc_ids(plan)


def test_guardian_needs_proof_of_guardianship():
    plan = build_plan(
        Case(Service.REGISTER, date(2026, 9, 1), applicant=Applicant.GUARDIAN, include_father=False, today=TODAY)
    )
    mandatory = {d.id: d.mandatory for d in plan.documents}
    assert mandatory["guardian_proof"] is True
    assert mandatory["mother_id"] is False


def test_abroad_points_to_mission():
    plan = build_plan(Case(Service.REGISTER, date(2026, 9, 1), birth_place=BirthPlace.ABROAD, today=TODAY))
    assert plan.category is Category.ABROAD
    assert plan.steps == ["step.contact_mission"]


def test_replacement_and_correction_plans():
    replacement = build_plan(Case(Service.REPLACEMENT, date(2010, 1, 1), today=TODAY))
    assert replacement.category is Category.REPLACEMENT
    assert "police_abstract" in doc_ids(replacement)

    correction = build_plan(Case(Service.CORRECTION, date(2010, 1, 1), applicant=Applicant.SELF, today=TODAY))
    assert correction.category is Category.CORRECTION
    assert {"original_certificate", "applicant_id", "correction_evidence"} <= set(doc_ids(correction))


@pytest.mark.parametrize("service", list(Service))
@pytest.mark.parametrize("place", list(BirthPlace))
@pytest.mark.parametrize("applicant", list(Applicant))
@pytest.mark.parametrize("dob", [date(2026, 9, 1), date(2015, 1, 1), date(1980, 1, 1)])
def test_every_plan_references_known_documents(service, place, applicant, dob):
    plan = build_plan(Case(service, dob, birth_place=place, applicant=applicant, today=TODAY))
    known = reference.documents()
    for doc in plan.documents:
        assert doc.id in known
