"""Registration rules engine.

Given the facts of a case (who is applying, when and where the child was born,
which service is needed) this module works out the registration category, the
deadline that applies and the documents and steps the applicant needs. It
returns message *keys* rather than text so every channel (web, SMS, USSD) can
render them in the user's language.

The Births and Deaths Registration Act (Cap. 149) requires a birth to be
registered within six months. Anything after that is a late registration that
needs extra evidence and the Registrar's approval, which is where most families
get stuck and end up making repeat trips.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

REGISTRATION_WINDOW_MONTHS = 6
DEADLINE_WARNING_DAYS = 30
ADULT_AGE = 18


class Service(StrEnum):
    """Birth services. Death services live in ``death_rules.DeathService``."""

    REGISTER = "register"
    REPLACEMENT = "replacement"
    CORRECTION = "correction"


class BirthPlace(StrEnum):
    FACILITY = "facility"
    HOME = "home"
    ABROAD = "abroad"


class Applicant(StrEnum):
    PARENT = "parent"
    GUARDIAN = "guardian"
    SELF = "self"


class Category(StrEnum):
    TIMELY = "timely"
    LATE = "late"
    LATE_ADULT = "late_adult"
    REPLACEMENT = "replacement"
    CORRECTION = "correction"
    ABROAD = "abroad"
    DEATH_TIMELY = "death_timely"
    DEATH_LATE = "death_late"
    DEATH_REPLACEMENT = "death_replacement"
    DEATH_ABROAD = "death_abroad"


@dataclass(frozen=True)
class Case:
    service: Service
    date_of_birth: date
    birth_place: BirthPlace = BirthPlace.FACILITY
    applicant: Applicant = Applicant.PARENT
    parents_married: bool = False
    include_father: bool = True
    today: date = field(default_factory=date.today)

    def __post_init__(self):
        if self.date_of_birth > self.today:
            raise ValueError("date_of_birth cannot be in the future")


@dataclass(frozen=True)
class RequiredDocument:
    id: str
    mandatory: bool = True
    # Documents sharing a group are alternatives: any one of them satisfies it.
    group: str | None = None


@dataclass
class Plan:
    service: StrEnum
    category: Category
    deadline: date | None
    days_remaining: int | None
    documents: list[RequiredDocument]
    steps: list[str]
    warnings: list[str]


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def age_in_years(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def registration_deadline(dob: date) -> date:
    return add_months(dob, REGISTRATION_WINDOW_MONTHS)


def build_plan(case: Case) -> Plan:
    if case.service is Service.REPLACEMENT:
        return _replacement_plan(case)
    if case.service is Service.CORRECTION:
        return _correction_plan(case)
    return _registration_plan(case)


def _parent_documents(case: Case) -> tuple[list[RequiredDocument], list[str]]:
    docs: list[RequiredDocument] = []
    warnings: list[str] = []
    if case.applicant is Applicant.SELF:
        docs.append(RequiredDocument("applicant_id"))
        docs.append(RequiredDocument("mother_id", mandatory=False))
        return docs, warnings

    if case.applicant is Applicant.GUARDIAN:
        docs.append(RequiredDocument("guardian_proof"))
        docs.append(RequiredDocument("mother_id", mandatory=False))
    else:
        docs.append(RequiredDocument("mother_id"))

    if case.include_father:
        docs.append(RequiredDocument("father_id"))
        if case.parents_married:
            docs.append(RequiredDocument("marriage_certificate", mandatory=False))
        else:
            docs.append(RequiredDocument("joint_parent_consent"))
            warnings.append("warn.father_joint_consent")
    return docs, warnings


def _registration_plan(case: Case) -> Plan:
    if case.birth_place is BirthPlace.ABROAD:
        return Plan(
            service=case.service,
            category=Category.ABROAD,
            deadline=None,
            days_remaining=None,
            documents=[],
            steps=["step.contact_mission"],
            warnings=["warn.abroad"],
        )

    deadline = registration_deadline(case.date_of_birth)
    days_remaining = (deadline - case.today).days
    docs, warnings = _parent_documents(case)

    if days_remaining >= 0:
        category = Category.TIMELY
        if case.birth_place is BirthPlace.FACILITY:
            docs.insert(0, RequiredDocument("birth_notification"))
            steps = ["step.collect_notification"]
        else:
            docs.insert(0, RequiredDocument("chief_letter"))
            docs.append(RequiredDocument("clinic_card", mandatory=False))
            steps = ["step.report_home_birth"]
        steps += ["step.register_at_office", "step.apply_certificate", "step.collect_certificate"]
        if days_remaining <= DEADLINE_WARNING_DAYS:
            warnings.insert(0, "warn.deadline_soon")
    else:
        adult = age_in_years(case.date_of_birth, case.today) >= ADULT_AGE
        category = Category.LATE_ADULT if adult else Category.LATE
        docs.insert(0, RequiredDocument("late_registration_form"))
        if case.birth_place is BirthPlace.FACILITY:
            docs.append(RequiredDocument("birth_notification", mandatory=False))
        else:
            docs.append(RequiredDocument("chief_letter"))
        # Proof of when the person was born: any one of these is acceptable.
        for doc_id in ("clinic_card", "school_record", "baptism_card", "age_assessment"):
            docs.append(RequiredDocument(doc_id, group="proof_of_age"))
        steps = [
            "step.get_late_form",
            "step.gather_evidence",
            "step.submit_late_application",
            "step.await_verification",
            "step.apply_certificate",
            "step.collect_certificate",
        ]
        warnings.insert(0, "warn.deadline_passed")

    docs.append(RequiredDocument("ecitizen_payment"))
    return Plan(
        service=case.service,
        category=category,
        deadline=deadline,
        days_remaining=days_remaining,
        documents=docs,
        steps=steps,
        warnings=warnings,
    )


def _replacement_plan(case: Case) -> Plan:
    applicant_doc = "applicant_id" if case.applicant is Applicant.SELF else "mother_id"
    return Plan(
        service=case.service,
        category=Category.REPLACEMENT,
        deadline=None,
        days_remaining=None,
        documents=[
            RequiredDocument("police_abstract"),
            RequiredDocument(applicant_doc),
            RequiredDocument("certificate_copy", mandatory=False),
            RequiredDocument("ecitizen_payment"),
        ],
        steps=["step.report_loss", "step.apply_replacement", "step.collect_certificate"],
        warnings=[],
    )


def _correction_plan(case: Case) -> Plan:
    applicant_doc = "applicant_id" if case.applicant is Applicant.SELF else "mother_id"
    return Plan(
        service=case.service,
        category=Category.CORRECTION,
        deadline=None,
        days_remaining=None,
        documents=[
            RequiredDocument("original_certificate"),
            RequiredDocument(applicant_doc),
            RequiredDocument("correction_evidence"),
            RequiredDocument("ecitizen_payment"),
        ],
        steps=["step.submit_correction", "step.await_verification", "step.collect_certificate"],
        warnings=[],
    )
