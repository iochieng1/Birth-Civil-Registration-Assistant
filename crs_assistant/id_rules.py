"""National ID rules.

Kenyans apply for a national ID at 18. Many young people never do, and a common
reason is that they have no birth certificate, which the Registration of Persons
office asks for. This module works out what an applicant needs, tells under-18s
when they become eligible so they can prepare, and sends anyone without a birth
certificate to get one first (through the birth registration checklist).

Requirements summarise public guidance and must be confirmed with the National
Registration Bureau; fees are never hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from .rules import Category, Plan, RequiredDocument, add_months

ID_ELIGIBLE_AGE = 18


class IdService(StrEnum):
    FIRST_TIME = "id_first"
    REPLACEMENT = "id_replacement"
    CHANGE = "id_change"


class ParentStatus(StrEnum):
    HAS_ID = "has_id"
    DECEASED = "deceased"
    UNKNOWN = "unknown"


class ChangeReason(StrEnum):
    MARRIAGE = "marriage"
    NAME_CHANGE = "name_change"
    ERROR = "error"


@dataclass(frozen=True)
class IdCase:
    service: IdService
    date_of_birth: date
    has_birth_certificate: bool = True
    mother: ParentStatus = ParentStatus.HAS_ID
    father: ParentStatus = ParentStatus.HAS_ID
    change_reason: ChangeReason = ChangeReason.ERROR
    today: date = field(default_factory=date.today)

    def __post_init__(self):
        if self.date_of_birth > self.today:
            raise ValueError("date_of_birth cannot be in the future")


def id_eligibility_date(date_of_birth: date) -> date:
    return add_months(date_of_birth, 12 * ID_ELIGIBLE_AGE)


def build_id_plan(case: IdCase) -> Plan:
    if case.service is IdService.REPLACEMENT:
        return _plan(
            case,
            Category.ID_REPLACEMENT,
            [
                RequiredDocument("id_police_abstract"),
                RequiredDocument("lost_id_copy", mandatory=False),
                RequiredDocument("applicant_birth_certificate", mandatory=False),
                RequiredDocument("id_fee_payment"),
            ],
            ["step.report_lost_id", "step.id_visit_office", "step.id_capture", "step.id_collect"],
        )
    if case.service is IdService.CHANGE:
        evidence = {
            ChangeReason.MARRIAGE: [RequiredDocument("own_marriage_certificate")],
            ChangeReason.NAME_CHANGE: [RequiredDocument("deed_poll")],
            ChangeReason.ERROR: [
                RequiredDocument("applicant_birth_certificate"),
                RequiredDocument("correction_evidence"),
            ],
        }[case.change_reason]
        return _plan(
            case,
            Category.ID_CHANGE,
            [RequiredDocument("original_id"), *evidence, RequiredDocument("id_fee_payment")],
            ["step.id_visit_office", "step.id_capture", "step.id_collect"],
        )
    return _first_time_plan(case)


def _first_time_plan(case: IdCase) -> Plan:
    eligible_on = id_eligibility_date(case.date_of_birth)
    days_to_eligible = (eligible_on - case.today).days

    docs = [RequiredDocument("applicant_birth_certificate")]
    warnings: list[str] = []
    for parent, id_doc in ((case.mother, "mother_id"), (case.father, "father_id")):
        if parent is ParentStatus.HAS_ID:
            docs.append(RequiredDocument(id_doc))
    if ParentStatus.DECEASED in (case.mother, case.father):
        docs.append(RequiredDocument("parent_death_certificate"))
    if ParentStatus.HAS_ID not in (case.mother, case.father):
        # Without a parent's ID the office needs another way to confirm citizenship.
        docs.append(RequiredDocument("id_introduction_letter"))
        warnings.append("warn.id_vetting")
    docs.append(RequiredDocument("school_record", mandatory=False))

    steps = ["step.id_gather", "step.id_visit_office", "step.id_capture", "step.id_collect"]
    if days_to_eligible > 0:
        category = Category.ID_NOT_YET
        steps = ["step.id_prepare", *steps]
        warnings.insert(0, "warn.id_not_yet")
    elif not case.has_birth_certificate:
        category = Category.ID_BIRTH_CERT_FIRST
        steps = ["step.id_get_birth_certificate", *steps]
        warnings.insert(0, "warn.id_birth_certificate_first")
    else:
        category = Category.ID_FIRST_TIME

    return Plan(
        service=case.service,
        category=category,
        deadline=eligible_on,
        days_remaining=days_to_eligible,
        documents=docs,
        steps=steps,
        warnings=warnings,
    )


def _plan(case: IdCase, category: Category, docs: list[RequiredDocument], steps: list[str]) -> Plan:
    return Plan(
        service=case.service,
        category=category,
        deadline=None,
        days_remaining=None,
        documents=docs,
        steps=steps,
        warnings=[],
    )
