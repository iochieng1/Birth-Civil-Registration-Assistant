"""Death registration rules.

Mirrors ``rules`` for births: given the facts of a death, work out the category,
deadline, documents and steps. Families need a burial permit before the burial
and a death certificate later for succession, pensions, insurance and closing
the deceased's records, yet many deaths, especially at home, are never
registered.

Cap. 149 sets the death registration window; it is kept in
``DEATH_REGISTRATION_WINDOW_MONTHS`` so it can be updated if CRS guidance changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from .rules import DEADLINE_WARNING_DAYS, Category, Plan, RequiredDocument, add_months

DEATH_REGISTRATION_WINDOW_MONTHS = 6


class DeathService(StrEnum):
    REGISTER = "death"
    REPLACEMENT = "death_replacement"


class DeathPlace(StrEnum):
    FACILITY = "facility"
    HOME = "home"
    ABROAD = "abroad"


class Circumstance(StrEnum):
    NATURAL = "natural"
    # Accident, violence, suicide or unknown cause: must go through the police.
    UNNATURAL = "unnatural"


@dataclass(frozen=True)
class DeathCase:
    service: DeathService
    date_of_death: date
    place_of_death: DeathPlace = DeathPlace.FACILITY
    circumstance: Circumstance = Circumstance.NATURAL
    deceased_had_id: bool = True
    today: date = field(default_factory=date.today)

    def __post_init__(self):
        if self.date_of_death > self.today:
            raise ValueError("date_of_death cannot be in the future")


def death_registration_deadline(date_of_death: date) -> date:
    return add_months(date_of_death, DEATH_REGISTRATION_WINDOW_MONTHS)


def build_death_plan(case: DeathCase) -> Plan:
    if case.service is DeathService.REPLACEMENT:
        return Plan(
            service=case.service,
            category=Category.DEATH_REPLACEMENT,
            deadline=None,
            days_remaining=None,
            documents=[
                RequiredDocument("police_abstract"),
                RequiredDocument("informant_id"),
                RequiredDocument("death_certificate_copy", mandatory=False),
                RequiredDocument("ecitizen_payment"),
            ],
            steps=["step.report_loss", "step.apply_death_replacement", "step.collect_certificate"],
            warnings=[],
        )

    if case.place_of_death is DeathPlace.ABROAD:
        return Plan(
            service=case.service,
            category=Category.DEATH_ABROAD,
            deadline=None,
            days_remaining=None,
            documents=[],
            steps=["step.death_abroad"],
            warnings=["warn.death_abroad"],
        )

    deadline = death_registration_deadline(case.date_of_death)
    days_remaining = (deadline - case.today).days
    unnatural = case.circumstance is Circumstance.UNNATURAL

    docs = [RequiredDocument("informant_id")]
    if case.deceased_had_id:
        docs.append(RequiredDocument("deceased_id"))
    else:
        docs.append(RequiredDocument("deceased_birth_certificate", mandatory=False))
    if unnatural:
        docs.append(RequiredDocument("police_death_report"))
        docs.append(RequiredDocument("postmortem_report", mandatory=False))
    warnings = ["warn.unnatural_death"] if unnatural else []

    if days_remaining >= 0:
        category = Category.DEATH_TIMELY
        if case.place_of_death is DeathPlace.FACILITY:
            docs.insert(0, RequiredDocument("death_notification"))
            steps = ["step.collect_death_notification"]
        else:
            docs.insert(0, RequiredDocument("death_chief_letter"))
            steps = ["step.report_death_chief"]
        if unnatural:
            steps.append("step.report_death_police")
        steps += ["step.register_death", "step.collect_burial_permit", "step.apply_death_certificate", "step.collect_certificate"]
        warnings.append("warn.burial_permit")
        if days_remaining <= DEADLINE_WARNING_DAYS:
            warnings.insert(0, "warn.deadline_soon")
    else:
        category = Category.DEATH_LATE
        docs.insert(0, RequiredDocument("late_registration_form"))
        # Proof that the death happened: any one of these is acceptable.
        for doc_id in ("death_notification", "burial_permit", "death_chief_letter", "death_affidavit"):
            docs.append(RequiredDocument(doc_id, group="proof_of_death"))
        steps = ["step.get_late_form", "step.gather_death_evidence"]
        if unnatural:
            steps.append("step.report_death_police")
        steps += ["step.submit_late_application", "step.await_verification", "step.apply_death_certificate", "step.collect_certificate"]
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
