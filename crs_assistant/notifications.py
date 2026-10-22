"""Community birth notifications, deadline reminders and the registration gap report.

Many births, especially home births, never reach a registrar. Community Health
Promoters (CHPs) already visit new mothers, so they log the birth here; the
parent then gets SMS reminders as the six-month deadline approaches, and county
officers can see where notified births are not turning into registrations.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from . import reference as ref_data
from .i18n import normalise_lang, t
from .phone import normalise
from .refs import new_reference
from .rules import BirthPlace, registration_deadline
from .sms import SmsGateway

# Days-before-deadline at which a reminder is sent; -1 marks the one-off overdue notice.
REMINDER_THRESHOLDS = (60, 14, 3)
OVERDUE = -1


class NotificationError(ValueError):
    pass


@dataclass
class BirthNotification:
    reference: str
    county_code: str
    date_of_birth: date
    birth_place: str
    parent_phone: str
    language: str
    registered_on: date | None
    deadline: date


def _from_row(row: sqlite3.Row) -> BirthNotification:
    dob = date.fromisoformat(row["date_of_birth"])
    return BirthNotification(
        reference=row["reference"],
        county_code=row["county_code"],
        date_of_birth=dob,
        birth_place=row["birth_place"],
        parent_phone=row["parent_phone"],
        language=row["language"],
        registered_on=date.fromisoformat(row["registered_on"]) if row["registered_on"] else None,
        deadline=registration_deadline(dob),
    )


def record(
    conn: sqlite3.Connection,
    county_code: str,
    date_of_birth: date,
    birth_place: BirthPlace,
    parent_phone: str,
    language: str = "en",
    captured_by: str | None = None,
    gateway: SmsGateway | None = None,
    today: date | None = None,
) -> BirthNotification:
    today = today or date.today()
    county = ref_data.county_by_code(county_code)
    if county is None:
        raise NotificationError(f"unknown county code {county_code!r}")
    if date_of_birth > today:
        raise NotificationError("date_of_birth cannot be in the future")
    phone = normalise(parent_phone)
    lang = normalise_lang(language)
    reference = new_reference("BN")
    conn.execute(
        "INSERT INTO birth_notifications (reference, county_code, date_of_birth, birth_place, parent_phone, language, captured_by)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (reference, county["code"], date_of_birth.isoformat(), BirthPlace(birth_place).value, phone, lang, captured_by),
    )
    notification = get(conn, reference)
    if gateway is not None:
        gateway.send(
            phone,
            t("sms.notification_received", lang, reference=reference, deadline=notification.deadline.isoformat()),
        )
    return notification


def get(conn: sqlite3.Connection, reference: str) -> BirthNotification | None:
    row = conn.execute("SELECT * FROM birth_notifications WHERE reference = ?", (reference.upper(),)).fetchone()
    return _from_row(row) if row else None


def mark_registered(conn: sqlite3.Connection, reference: str, on: date | None = None) -> bool:
    cur = conn.execute(
        "UPDATE birth_notifications SET registered_on = ? WHERE reference = ? AND registered_on IS NULL",
        ((on or date.today()).isoformat(), reference.upper()),
    )
    return cur.rowcount == 1


def _due_threshold(days_remaining: int) -> int | None:
    if days_remaining < 0:
        return OVERDUE
    crossed = [th for th in REMINDER_THRESHOLDS if days_remaining <= th]
    return min(crossed) if crossed else None


def send_reminders(conn: sqlite3.Connection, gateway: SmsGateway, today: date | None = None) -> int:
    """Send at most one reminder per notification per threshold. Returns the number sent."""
    today = today or date.today()
    sent = 0
    rows = conn.execute("SELECT * FROM birth_notifications WHERE registered_on IS NULL").fetchall()
    for row in rows:
        notification = _from_row(row)
        days_remaining = (notification.deadline - today).days
        threshold = _due_threshold(days_remaining)
        last = row["last_reminder"]
        if threshold is None or (last is not None and threshold >= last):
            continue
        params = {"reference": notification.reference, "deadline": notification.deadline.isoformat()}
        if threshold == OVERDUE:
            message = t("sms.overdue", notification.language, **params)
        else:
            message = t("sms.reminder", notification.language, days=days_remaining, **params)
        if gateway.send(notification.parent_phone, message):
            conn.execute("UPDATE birth_notifications SET last_reminder = ? WHERE id = ?", (threshold, row["id"]))
            sent += 1
    return sent


@dataclass
class CountyGap:
    county_code: str
    county_name: str
    notified: int
    registered: int
    registered_on_time: int
    pending_in_window: int
    overdue: int

    @property
    def registration_rate(self) -> float:
        return round(self.registered / self.notified, 3) if self.notified else 0.0


def gap_report(conn: sqlite3.Connection, today: date | None = None) -> list[CountyGap]:
    """Per-county view of notified births vs registrations, worst counties first."""
    today = today or date.today()
    stats: dict[str, CountyGap] = {}
    for row in conn.execute("SELECT * FROM birth_notifications").fetchall():
        n = _from_row(row)
        gap = stats.get(n.county_code)
        if gap is None:
            name = ref_data.county_by_code(n.county_code)["name"]
            gap = stats[n.county_code] = CountyGap(n.county_code, name, 0, 0, 0, 0, 0)
        gap.notified += 1
        if n.registered_on:
            gap.registered += 1
            gap.registered_on_time += n.registered_on <= n.deadline
        elif today <= n.deadline:
            gap.pending_in_window += 1
        else:
            gap.overdue += 1
    return sorted(stats.values(), key=lambda g: (g.registration_rate, -g.overdue))
