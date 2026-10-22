from datetime import date

import pytest

from crs_assistant import appointments, db
from crs_assistant.refs import ALPHABET, new_reference

TODAY = date(2026, 10, 22)  # Thursday
MONDAY = date(2026, 10, 26)
PHONE = "+254712345678"


@pytest.fixture
def conn():
    connection = db.connect()
    connection.execute("UPDATE offices SET slot_capacity = 2 WHERE id = 1")
    return connection


def test_reference_format():
    ref = new_reference("APT")
    assert ref.startswith("APT-")
    assert all(ch in ALPHABET for ch in ref[4:])


def test_day_slots_cover_office_hours():
    slots = appointments.day_slots()
    assert slots[0] == "08:00"
    assert slots[-1] == "15:30"
    assert len(slots) == 16


def test_book_and_fetch(conn):
    appt = appointments.book(conn, 1, MONDAY, "09:00", PHONE, "register", today=TODAY)
    fetched = appointments.get(conn, appt.reference.lower())
    assert fetched.slot == "09:00"
    assert fetched.office_name == "Mombasa County Civil Registration Office"
    assert appointments.available_slots(conn, 1, MONDAY, today=TODAY)["09:00"] == 1


def test_full_slot_rejected_and_hidden(conn):
    appointments.book(conn, 1, MONDAY, "09:00", "+254700000001", "register", today=TODAY)
    appointments.book(conn, 1, MONDAY, "09:00", "+254700000002", "register", today=TODAY)
    with pytest.raises(appointments.SlotUnavailable, match="full"):
        appointments.book(conn, 1, MONDAY, "09:00", "+254700000003", "register", today=TODAY)
    assert "09:00" not in appointments.available_slots(conn, 1, MONDAY, today=TODAY)


def test_one_booking_per_phone_per_day(conn):
    appointments.book(conn, 1, MONDAY, "09:00", PHONE, "register", today=TODAY)
    with pytest.raises(appointments.SlotUnavailable, match="already"):
        appointments.book(conn, 1, MONDAY, "10:00", PHONE, "register", today=TODAY)


@pytest.mark.parametrize(
    "day,slot,match",
    [
        (date(2026, 10, 21), "09:00", "past"),
        (date(2026, 10, 24), "09:00", "weekend"),
        (date(2026, 12, 30), "09:00", "ahead"),
        (MONDAY, "09:15", "invalid"),
        (MONDAY, "16:00", "invalid"),
    ],
)
def test_invalid_bookings(conn, day, slot, match):
    with pytest.raises(appointments.SlotUnavailable, match=match):
        appointments.book(conn, 1, day, slot, PHONE, "register", today=TODAY)


def test_unknown_office(conn):
    with pytest.raises(appointments.OfficeNotFound):
        appointments.available_slots(conn, 999, MONDAY, today=TODAY)


def test_cancel_requires_matching_phone_and_frees_slot(conn):
    appt = appointments.book(conn, 1, MONDAY, "09:00", PHONE, "register", today=TODAY)
    assert not appointments.cancel(conn, appt.reference, "+254799999999")
    assert appointments.cancel(conn, appt.reference, PHONE)
    assert not appointments.cancel(conn, appt.reference, PHONE)
    assert appointments.available_slots(conn, 1, MONDAY, today=TODAY)["09:00"] == 2
    assert appointments.get(conn, appt.reference).status == "cancelled"
