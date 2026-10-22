"""Community notifications, reminders and the registration gap report (births, deaths, IDs).

Many births, especially home births, never reach a registrar. Community Health
Promoters (CHPs) already visit new mothers, so they log the birth here; the
parent then gets SMS reminders as the six-month deadline approaches, and county
officers can see where notified births are not turning into registrations.

Deaths follow the same pattern: a CHP or chief records the death and the
informant (next of kin) is reminded to register it, since the death certificate
is needed for succession, pensions and insurance.

National IDs reuse it with the 18th birthday as the date that matters: schools,
chiefs or CHPs register a young person, who is reminded as they approach 18 and
told when they can apply. Marking the record "registered" means the ID was
issued, so the gap report shows people who turned 18 without one.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from . import reference as ref_data
from .death_rules import DeathPlace, death_registration_deadline
from .i18n import normalise_lang, t
from .id_rules import id_eligibility_date
from .phone import normalise
from .refs import new_reference
from .rules import BirthPlace, registration_deadline
from .sms import SmsGateway

# Days-before-deadline at which a reminder is sent; -1 marks the one-off overdue notice.
REMINDER_THRESHOLDS = (60, 14, 3)
OVERDUE = -1


class NotificationError(ValueError):
    pass


BIRTH = "birth"
DEATH = "death"
NATIONAL_ID = "id"
# event -> (reference prefix, deadline rule)
EVENTS = {
    BIRTH: ("BN", registration_deadline),
    DEATH: ("DN", death_registration_deadline),
    NATIONAL_ID: ("ID", id_eligibility_date),
}
# event -> SMS message keys: (confirmation, reminder, overdue)
SMS_KEYS = {
    BIRTH: ("sms.notification_received", "sms.reminder", "sms.overdue"),
    DEATH: ("sms.death_notification_received", "sms.death_reminder", "sms.death_overdue"),
    NATIONAL_ID: ("sms.id_reminder_registered", "sms.id_reminder", "sms.id_eligible"),
}


@dataclass
class Notification:
    reference: str
    event: str
    county_code: str
    event_date: date
    place: str
    phone: str
    language: str
    registered_on: date | None
    deadline: date


def _from_row(row: sqlite3.Row) -> Notification:
    event_date = date.fromisoformat(row["event_date"])
    _, deadline_rule = EVENTS[row["event"]]
    return Notification(
        reference=row["reference"],
        event=row["event"],
        county_code=row["county_code"],
        event_date=event_date,
        place=row["place"],
        phone=row["phone"],
        language=row["language"],
        registered_on=date.fromisoformat(row["registered_on"]) if row["registered_on"] else None,
        deadline=deadline_rule(event_date),
    )


def _insert(
    conn: sqlite3.Connection,
    event: str,
    county_code: str,
    event_date: date,
    place: str,
    phone: str,
    language: str,
    captured_by: str | None,
    today: date,
) -> Notification:
    county = ref_data.county_by_code(county_code)
    if county is None:
        raise NotificationError(f"unknown county code {county_code!r}")
    if event_date > today:
        raise NotificationError(f"{event} date cannot be in the future")
    prefix, _ = EVENTS[event]
    reference = new_reference(prefix)
    conn.execute(
        "INSERT INTO notifications (reference, event, county_code, event_date, place, phone, language, captured_by)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (reference, event, county["code"], event_date.isoformat(), place, normalise(phone), normalise_lang(language), captured_by),
    )
    return get(conn, reference)


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
) -> Notification:
    notification = _insert(
        conn,
        BIRTH,
        county_code,
        date_of_birth,
        BirthPlace(birth_place).value,
        parent_phone,
        language,
        captured_by,
        today or date.today(),
    )
    _confirm(notification, gateway)
    return notification


def record_death(
    conn: sqlite3.Connection,
    county_code: str,
    date_of_death: date,
    place_of_death: DeathPlace,
    informant_phone: str,
    language: str = "en",
    captured_by: str | None = None,
    gateway: SmsGateway | None = None,
    today: date | None = None,
) -> Notification:
    """Record a death reported by a CHP or chief; the informant is the next of kin to remind."""
    notification = _insert(
        conn,
        DEATH,
        county_code,
        date_of_death,
        DeathPlace(place_of_death).value,
        informant_phone,
        language,
        captured_by,
        today or date.today(),
    )
    _confirm(notification, gateway)
    return notification


def record_id_reminder(
    conn: sqlite3.Connection,
    county_code: str,
    date_of_birth: date,
    phone: str,
    language: str = "en",
    captured_by: str | None = None,
    gateway: SmsGateway | None = None,
    today: date | None = None,
) -> Notification:
    """Register a young person for turning-18 reminders to apply for a national ID."""
    today = today or date.today()
    notification = _insert(
        conn, NATIONAL_ID, county_code, date_of_birth, "", phone, language, captured_by, today
    )
    if notification.deadline <= today:
        # Already eligible: tell them now and skip the countdown reminders.
        conn.execute("UPDATE notifications SET last_reminder = ? WHERE reference = ?", (OVERDUE, notification.reference))
        if gateway is not None:
            _, _, eligible_key = SMS_KEYS[NATIONAL_ID]
            gateway.send(
                notification.phone,
                t(eligible_key, notification.language, reference=notification.reference,
                  deadline=notification.deadline.isoformat()),
            )
    else:
        _confirm(notification, gateway)
    return notification


def _confirm(notification: Notification, gateway: SmsGateway | None) -> None:
    if gateway is None:
        return
    key, _, _ = SMS_KEYS[notification.event]
    gateway.send(
        notification.phone,
        t(key, notification.language, reference=notification.reference, deadline=notification.deadline.isoformat()),
    )


def get(conn: sqlite3.Connection, reference: str) -> Notification | None:
    row = conn.execute("SELECT * FROM notifications WHERE reference = ?", (reference.upper(),)).fetchone()
    return _from_row(row) if row else None


def mark_registered(conn: sqlite3.Connection, reference: str, on: date | None = None) -> bool:
    cur = conn.execute(
        "UPDATE notifications SET registered_on = ? WHERE reference = ? AND registered_on IS NULL",
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
    rows = conn.execute("SELECT * FROM notifications WHERE registered_on IS NULL").fetchall()
    for row in rows:
        notification = _from_row(row)
        days_remaining = (notification.deadline - today).days
        threshold = _due_threshold(days_remaining)
        last = row["last_reminder"]
        if threshold is None or (last is not None and threshold >= last):
            continue
        params = {"reference": notification.reference, "deadline": notification.deadline.isoformat()}
        _, reminder_key, overdue_key = SMS_KEYS[notification.event]
        if threshold == OVERDUE:
            message = t(overdue_key, notification.language, **params)
        else:
            message = t(reminder_key, notification.language, days=days_remaining, **params)
        if gateway.send(notification.phone, message):
            conn.execute("UPDATE notifications SET last_reminder = ? WHERE id = ?", (threshold, row["id"]))
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


def gap_report(conn: sqlite3.Connection, today: date | None = None, event: str = BIRTH) -> list[CountyGap]:
    """Per-county view of notified events vs registrations, worst counties first."""
    today = today or date.today()
    stats: dict[str, CountyGap] = {}
    for row in conn.execute("SELECT * FROM notifications WHERE event = ?", (event,)).fetchall():
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
