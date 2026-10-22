from datetime import date, timedelta

import pytest

from crs_assistant import db, notifications
from crs_assistant.rules import BirthPlace
from crs_assistant.sms import ConsoleGateway

TODAY = date(2026, 10, 22)


@pytest.fixture
def conn():
    return db.connect()


def record(conn, dob, county="047", phone="0712345678", lang="en", gateway=None):
    return notifications.record(conn, county, dob, BirthPlace.HOME, phone, lang, "CHP-1", gateway=gateway, today=TODAY)


def test_record_normalises_and_confirms_by_sms(conn):
    gateway = ConsoleGateway()
    n = record(conn, date(2026, 10, 1), lang="sw", gateway=gateway)
    assert n.reference.startswith("BN-")
    assert n.parent_phone == "+254712345678"
    assert n.deadline == date(2027, 4, 1)
    to, message = gateway.outbox[0]
    assert to == "+254712345678"
    assert n.reference in message and "Sajili" in message


@pytest.mark.parametrize(
    "county,dob,phone",
    [("999", date(2026, 10, 1), "0712345678"), ("047", date(2026, 10, 23), "0712345678"), ("047", date(2026, 10, 1), "123")],
)
def test_record_validation(conn, county, dob, phone):
    with pytest.raises(ValueError):
        record(conn, dob, county=county, phone=phone)


def test_mark_registered_only_once(conn):
    n = record(conn, date(2026, 10, 1))
    assert notifications.mark_registered(conn, n.reference.lower(), TODAY)
    assert not notifications.mark_registered(conn, n.reference, TODAY)
    assert notifications.get(conn, n.reference).registered_on == TODAY


def test_reminders_follow_thresholds_and_do_not_repeat(conn):
    gateway = ConsoleGateway()
    n = record(conn, date(2026, 6, 1))  # deadline 2026-12-01
    deadline = n.deadline

    def run(day):
        return notifications.send_reminders(conn, gateway, today=day)

    assert run(deadline - timedelta(days=61)) == 0
    assert run(deadline - timedelta(days=60)) == 1
    assert run(deadline - timedelta(days=59)) == 0
    assert run(deadline - timedelta(days=10)) == 1
    assert run(deadline - timedelta(days=2)) == 1
    assert run(deadline) == 0
    assert run(deadline + timedelta(days=1)) == 1
    assert run(deadline + timedelta(days=30)) == 0
    assert "passed" in gateway.outbox[-1][1]
    assert "2 day(s)" in gateway.outbox[-2][1]


def test_late_join_sends_only_most_urgent_reminder(conn):
    gateway = ConsoleGateway()
    n = record(conn, date(2026, 5, 1))
    assert notifications.send_reminders(conn, gateway, today=n.deadline - timedelta(days=5)) == 1
    assert notifications.send_reminders(conn, gateway, today=n.deadline - timedelta(days=3)) == 1
    assert notifications.send_reminders(conn, gateway, today=n.deadline - timedelta(days=1)) == 0


def test_no_reminders_after_registration(conn):
    gateway = ConsoleGateway()
    n = record(conn, date(2026, 6, 1))
    notifications.mark_registered(conn, n.reference, TODAY)
    assert notifications.send_reminders(conn, gateway, today=n.deadline - timedelta(days=3)) == 0


def test_failed_send_is_retried(conn):
    class Failing:
        def send(self, to, message):
            return False

    n = record(conn, date(2026, 6, 1))
    day = n.deadline - timedelta(days=10)
    assert notifications.send_reminders(conn, Failing(), today=day) == 0
    assert notifications.send_reminders(conn, ConsoleGateway(), today=day) == 1


def test_gap_report_orders_worst_county_first(conn):
    a = record(conn, date(2026, 1, 1), county="047")
    record(conn, date(2026, 10, 1), county="047")
    notifications.mark_registered(conn, a.reference, date(2026, 3, 1))
    record(conn, date(2025, 1, 1), county="023")
    record(conn, date(2026, 9, 1), county="023")

    report = notifications.gap_report(conn, today=TODAY)
    assert [g.county_name for g in report] == ["Turkana", "Nairobi"]
    turkana, nairobi = report
    assert (turkana.notified, turkana.registered, turkana.overdue, turkana.pending_in_window) == (2, 0, 1, 1)
    assert nairobi.registration_rate == 0.5
    assert nairobi.registered_on_time == 1
