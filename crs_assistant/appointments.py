"""Appointment slots at registration offices.

Booking a time slot ahead, after the readiness check, replaces the
"arrive at dawn and queue" model that costs families a day's income.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .refs import new_reference

OPENING = time(8, 0)
CLOSING = time(16, 0)
SLOT_MINUTES = 30
MAX_DAYS_AHEAD = 30


class BookingError(Exception):
    pass


class OfficeNotFound(BookingError):
    pass


class SlotUnavailable(BookingError):
    pass


@dataclass
class Appointment:
    reference: str
    office_id: int
    office_name: str
    day: str
    slot: str
    phone: str
    service: str
    status: str


def day_slots() -> list[str]:
    slots = []
    current = datetime.combine(date.min, OPENING)
    end = datetime.combine(date.min, CLOSING)
    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=SLOT_MINUTES)
    return slots


def _office(conn: sqlite3.Connection, office_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM offices WHERE id = ?", (office_id,)).fetchone()
    if row is None:
        raise OfficeNotFound(f"office {office_id} not found")
    return row


def _check_day(day: date, today: date) -> None:
    if day < today:
        raise SlotUnavailable("cannot book a day in the past")
    if day > today + timedelta(days=MAX_DAYS_AHEAD):
        raise SlotUnavailable(f"bookings open {MAX_DAYS_AHEAD} days ahead")
    if day.weekday() >= 5:
        raise SlotUnavailable("offices are closed on weekends")


def available_slots(conn: sqlite3.Connection, office_id: int, day: date, today: date | None = None) -> dict[str, int]:
    """Return remaining capacity per slot (only slots with space left)."""
    office = _office(conn, office_id)
    _check_day(day, today or date.today())
    taken = dict(
        conn.execute(
            "SELECT slot, COUNT(*) FROM appointments WHERE office_id = ? AND day = ? AND status = 'booked' GROUP BY slot",
            (office_id, day.isoformat()),
        ).fetchall()
    )
    remaining = {s: office["slot_capacity"] - taken.get(s, 0) for s in day_slots()}
    return {s: n for s, n in remaining.items() if n > 0}


def book(
    conn: sqlite3.Connection,
    office_id: int,
    day: date,
    slot: str,
    phone: str,
    service: str,
    today: date | None = None,
) -> Appointment:
    office = _office(conn, office_id)
    if slot not in day_slots():
        raise SlotUnavailable(f"invalid slot {slot}")
    _check_day(day, today or date.today())

    # BEGIN IMMEDIATE takes the write lock up front so two concurrent bookings
    # cannot both see the last free place in a slot.
    conn.execute("BEGIN IMMEDIATE")
    try:
        duplicate = conn.execute(
            "SELECT 1 FROM appointments WHERE phone = ? AND day = ? AND status = 'booked'",
            (phone, day.isoformat()),
        ).fetchone()
        if duplicate:
            raise SlotUnavailable("this phone already has a booking on that day")
        taken = conn.execute(
            "SELECT COUNT(*) FROM appointments WHERE office_id = ? AND day = ? AND slot = ? AND status = 'booked'",
            (office_id, day.isoformat(), slot),
        ).fetchone()[0]
        if taken >= office["slot_capacity"]:
            raise SlotUnavailable(f"slot {slot} is full")
        reference = new_reference("APT")
        conn.execute(
            "INSERT INTO appointments (reference, office_id, day, slot, phone, service) VALUES (?, ?, ?, ?, ?, ?)",
            (reference, office_id, day.isoformat(), slot, phone, service),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return Appointment(reference, office_id, office["name"], day.isoformat(), slot, phone, service, "booked")


def get(conn: sqlite3.Connection, reference: str) -> Appointment | None:
    row = conn.execute(
        "SELECT a.*, o.name AS office_name FROM appointments a JOIN offices o ON o.id = a.office_id WHERE a.reference = ?",
        (reference.upper(),),
    ).fetchone()
    if row is None:
        return None
    return Appointment(
        row["reference"], row["office_id"], row["office_name"], row["day"], row["slot"], row["phone"], row["service"], row["status"]
    )


def cancel(conn: sqlite3.Connection, reference: str, phone: str) -> bool:
    """Cancel a booking; the phone must match so references cannot be cancelled by strangers."""
    cur = conn.execute(
        "UPDATE appointments SET status = 'cancelled' WHERE reference = ? AND phone = ? AND status = 'booked'",
        (reference.upper(), phone),
    )
    return cur.rowcount == 1
