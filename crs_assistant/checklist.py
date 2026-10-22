"""Turn a rules Plan into a readable checklist and check an applicant's readiness.

The readiness check exists to cut repeat trips: before queueing at the office an
applicant ticks off what they already have and is told exactly what is missing.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import reference
from .i18n import normalise_lang, t
from .rules import Plan


@dataclass
class ChecklistItem:
    id: str
    label: str
    mandatory: bool
    group: str | None
    have: bool | None = None


@dataclass
class Checklist:
    category: str
    category_label: str
    deadline: str | None
    days_remaining: int | None
    items: list[ChecklistItem]
    steps: list[str]
    warnings: list[str]
    disclaimer: str


@dataclass
class Readiness:
    ready: bool
    missing: list[str]
    missing_groups: list[str]
    message: str


def render(plan: Plan, lang: str = "en") -> Checklist:
    lang = normalise_lang(lang)
    deadline = plan.deadline.isoformat() if plan.deadline else None
    params = {"days": plan.days_remaining, "deadline": deadline}
    return Checklist(
        category=plan.category.value,
        category_label=t(f"category.{plan.category.value}", lang),
        deadline=deadline,
        days_remaining=plan.days_remaining,
        items=[
            ChecklistItem(d.id, reference.document_name(d.id, lang), d.mandatory, d.group)
            for d in plan.documents
        ],
        steps=[t(key, lang) for key in plan.steps],
        warnings=[t(key, lang, **params) for key in plan.warnings],
        disclaimer=t("disclaimer", lang),
    )


def assess(plan: Plan, have: set[str], lang: str = "en") -> Readiness:
    lang = normalise_lang(lang)
    missing: list[str] = []
    groups: dict[str, bool] = {}
    for doc in plan.documents:
        if doc.group:
            groups[doc.group] = groups.get(doc.group, False) or doc.id in have
        elif doc.mandatory and doc.id not in have:
            missing.append(doc.id)
    missing_groups = [g for g, satisfied in groups.items() if not satisfied]

    if not missing and not missing_groups:
        return Readiness(True, [], [], t("ready.yes", lang))

    labels = [reference.document_name(d, lang) for d in missing]
    labels += [t(f"group.{g}", lang) for g in missing_groups]
    return Readiness(False, missing, missing_groups, t("ready.no", lang, missing="; ".join(labels)))
