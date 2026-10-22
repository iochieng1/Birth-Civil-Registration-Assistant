"""USSD menu (Africa's Talking callback format).

Africa's Talking posts the whole session's input as ``text`` joined by ``*``
(e.g. ``"2*1*3"``), so the menu is stateless: every request replays the path
from the start. Responses start with ``CON`` (expect more input) or ``END``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date, datetime, timedelta

from . import appointments, checklist, reference
from .i18n import t
from .rules import Applicant, BirthPlace, Case, Service, build_plan, registration_deadline
from .sms import SmsGateway

LANGUAGE_MENU = "1. English\n2. Kiswahili"
LANGUAGES = {"1": "en", "2": "sw"}
SERVICES = {"1": Service.REGISTER, "2": Service.REPLACEMENT, "3": Service.CORRECTION}
APPLICANTS = {"1": Applicant.PARENT, "2": Applicant.GUARDIAN, "3": Applicant.SELF}
BIRTH_PLACES = {"1": BirthPlace.FACILITY, "2": BirthPlace.HOME, "3": BirthPlace.ABROAD}
FATHER_OPTIONS = {"1": (True, True), "2": (False, True), "3": (False, False)}  # (married, include_father)
DAYS_OFFERED = 5
SLOTS_OFFERED = 6


class _Invalid(Exception):
    pass


def con(text: str) -> str:
    return f"CON {text}"


def end(text: str) -> str:
    return f"END {text}"


def parse_dob(raw: str, today: date) -> date:
    try:
        dob = datetime.strptime(raw, "%d%m%Y").date()
    except ValueError as exc:
        raise _Invalid from exc
    if dob > today:
        raise _Invalid
    return dob


def _choice(options: dict, key: str):
    if key not in options:
        raise _Invalid
    return options[key]


def checklist_sms(plan, lang: str) -> str:
    rendered = checklist.render(plan, lang)
    lines = [t("sms.checklist_header", lang, category=rendered.category_label)]
    seen_groups = set()
    for item in rendered.items:
        if item.group:
            if item.group in seen_groups:
                continue
            seen_groups.add(item.group)
            lines.append(f"- {t('group.' + item.group, lang)}")
        else:
            suffix = "" if item.mandatory else f" {t('sms.optional', lang)}"
            lines.append(f"- {item.label}{suffix}")
    lines.extend(rendered.warnings)
    return "\n".join(lines)


class UssdSession:
    def __init__(self, conn: sqlite3.Connection, gateway: SmsGateway, phone: str, today: date):
        self.conn = conn
        self.gateway = gateway
        self.phone = phone
        self.today = today

    def handle(self, text: str) -> str:
        inputs = [part.strip() for part in text.split("*")] if text else []
        if not inputs:
            return con(LANGUAGE_MENU)
        lang = LANGUAGES.get(inputs[0])
        if lang is None:
            return end(t("ussd.invalid"))
        rest = inputs[1:]
        if not rest:
            return con(t("ussd.main", lang))
        flows: dict[str, Callable[[list[str], str], str]] = {
            "1": self._checklist_flow,
            "2": self._deadline_flow,
            "3": self._booking_flow,
            "4": self._lookup_flow,
        }
        try:
            return _choice(flows, rest[0])(rest[1:], lang)
        except _Invalid:
            return end(t("ussd.invalid", lang))

    # 1. Documents checklist
    def _checklist_flow(self, inputs: list[str], lang: str) -> str:
        if not inputs:
            return con(t("ussd.service", lang))
        service = _choice(SERVICES, inputs[0])
        if len(inputs) < 2:
            return con(t("ussd.applicant", lang))
        applicant = _choice(APPLICANTS, inputs[1])

        if service is not Service.REGISTER:
            return self._send_checklist(Case(service, self.today, applicant=applicant, today=self.today), lang)

        if len(inputs) < 3:
            return con(t("ussd.birth_place", lang))
        place = _choice(BIRTH_PLACES, inputs[2])
        if len(inputs) < 4:
            return con(t("ussd.dob", lang))
        dob = parse_dob(inputs[3], self.today)
        if applicant is Applicant.SELF:
            case = Case(service, dob, birth_place=place, applicant=applicant, today=self.today)
            return self._send_checklist(case, lang)
        if len(inputs) < 5:
            return con(t("ussd.father", lang))
        married, include_father = _choice(FATHER_OPTIONS, inputs[4])
        case = Case(
            service,
            dob,
            birth_place=place,
            applicant=applicant,
            parents_married=married,
            include_father=include_father,
            today=self.today,
        )
        return self._send_checklist(case, lang)

    def _send_checklist(self, case: Case, lang: str) -> str:
        plan = build_plan(case)
        self.gateway.send(self.phone, checklist_sms(plan, lang))
        category = t(f"category.{plan.category.value}", lang)
        count = sum(1 for d in plan.documents if d.mandatory and not d.group) + (
            1 if any(d.group for d in plan.documents) else 0
        )
        return end(t("ussd.checklist_sent", lang, category=category, count=count))

    # 2. Deadline check
    def _deadline_flow(self, inputs: list[str], lang: str) -> str:
        if not inputs:
            return con(t("ussd.dob", lang))
        deadline = registration_deadline(parse_dob(inputs[0], self.today))
        days = (deadline - self.today).days
        if days >= 0:
            return end(t("ussd.deadline_open", lang, deadline=deadline.isoformat(), days=days))
        return end(t("ussd.deadline_passed", lang, deadline=deadline.isoformat()))

    # 3. Appointment booking
    def _bookable_days(self) -> list[date]:
        days, current = [], self.today + timedelta(days=1)
        while len(days) < DAYS_OFFERED:
            if current.weekday() < 5:
                days.append(current)
            current += timedelta(days=1)
        return days

    def _booking_flow(self, inputs: list[str], lang: str) -> str:
        if not inputs:
            return con(t("ussd.county", lang))
        county = reference.county_by_code(inputs[0]) if inputs[0].isdigit() else None
        if county is None:
            raise _Invalid
        office = self.conn.execute(
            "SELECT id FROM offices WHERE county_code = ? ORDER BY id LIMIT 1", (county["code"],)
        ).fetchone()
        if office is None:
            raise _Invalid

        days = self._bookable_days()
        if len(inputs) < 2:
            menu = "\n".join(f"{i}. {d.strftime('%a %d %b')}" for i, d in enumerate(days, 1))
            return con(f"{t('ussd.pick_day', lang)}\n{menu}")
        day = _choice({str(i): d for i, d in enumerate(days, 1)}, inputs[1])

        slots = list(appointments.available_slots(self.conn, office["id"], day, today=self.today))[:SLOTS_OFFERED]
        if not slots:
            return end(t("ussd.no_slots", lang))
        if len(inputs) < 3:
            menu = "\n".join(f"{i}. {s}" for i, s in enumerate(slots, 1))
            return con(f"{t('ussd.pick_slot', lang)}\n{menu}")
        slot = _choice({str(i): s for i, s in enumerate(slots, 1)}, inputs[2])

        try:
            appt = appointments.book(self.conn, office["id"], day, slot, self.phone, Service.REGISTER.value, today=self.today)
        except appointments.BookingError:
            return end(t("ussd.no_slots", lang))
        self.gateway.send(
            self.phone,
            t("sms.appointment_booked", lang, reference=appt.reference, office=appt.office_name, day=appt.day, slot=appt.slot),
        )
        return end(t("ussd.booked", lang, reference=appt.reference, day=appt.day, slot=appt.slot))

    # 4. Appointment lookup
    def _lookup_flow(self, inputs: list[str], lang: str) -> str:
        if not inputs:
            return con(t("ussd.reference", lang))
        appt = appointments.get(self.conn, inputs[0])
        if appt is None or appt.phone != self.phone:
            return end(t("ussd.not_found", lang))
        return end(
            t("ussd.appointment", lang, reference=appt.reference, office=appt.office_name, day=appt.day, slot=appt.slot, status=appt.status)
        )


def handle(conn: sqlite3.Connection, gateway: SmsGateway, phone: str, text: str, today: date | None = None) -> str:
    return UssdSession(conn, gateway, phone, today or date.today()).handle(text)
