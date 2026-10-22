from datetime import date

import pytest

from crs_assistant import db, ussd
from crs_assistant.sms import ConsoleGateway

TODAY = date(2026, 10, 22)  # Thursday
PHONE = "+254712345678"


@pytest.fixture
def env():
    return db.connect(), ConsoleGateway()


def dial(env, text, phone=PHONE):
    conn, gateway = env
    return ussd.handle(conn, gateway, phone, text, today=TODAY)


def test_first_screen_is_language_menu(env):
    assert dial(env, "") == "CON " + ussd.LANGUAGE_MENU


def test_main_menu_in_swahili(env):
    assert dial(env, "2").startswith("CON Msaidizi")


@pytest.mark.parametrize("text", ["9", "1*9", "1*1*9", "1*1*1*1*32132026", "1*2*31022026", "1*3*99"])
def test_invalid_input_ends_session(env, text):
    assert dial(env, text).startswith("END Invalid") or dial(env, text).startswith("END Ingizo")


def test_full_checklist_flow_sends_sms(env):
    assert dial(env, "1*1").startswith("CON Which service")
    assert dial(env, "1*1*1").startswith("CON Who is applying")
    assert dial(env, "1*1*1*1").startswith("CON Where was")
    assert dial(env, "1*1*1*1*2").startswith("CON Enter date")
    assert dial(env, "1*1*1*1*2*01092026").startswith("CON Father")
    reply = dial(env, "1*1*1*1*2*01092026*2")
    assert reply.startswith("END Within the 6-month")
    _, gateway = env
    to, message = gateway.outbox[-1]
    assert to == PHONE
    assert "Assistant Chief" in message
    assert "joint request" in message


def test_late_registration_sms_groups_proof_of_age(env):
    dial(env, "1*1*1*1*1*01012020*3")
    message = env[1].outbox[-1][1]
    assert "one proof of date of birth" in message
    assert message.count("clinic") == 0


def test_adult_self_skips_father_question(env):
    reply = dial(env, "2*1*1*3*1*01011990")
    assert reply.startswith("END Usajili wa kuchelewa wa mtu mzima")


def test_replacement_skips_birth_questions(env):
    assert dial(env, "1*1*2*1").startswith("END Replacement")
    assert "police abstract" in env[1].outbox[-1][1].lower()


def test_ussd_screens_fit_length_limit(env):
    for text in ["1", "2", "1*1", "2*1", "1*1*1", "2*1*1", "1*1*1*1", "2*1*1*1", "1*1*1*1*1", "1*1*1*1*1*01092026", "1*3", "1*3*47"]:
        assert len(dial(env, text)) <= 182, text


def test_deadline_check(env):
    assert dial(env, "1*2*01092026") == "END Register by 2027-03-01: 130 day(s) left."
    assert "late registration" in dial(env, "1*2*01012020")


def test_booking_flow_and_lookup(env):
    days_menu = dial(env, "1*3*47")
    assert days_menu.startswith("CON Choose a day")
    assert "1. Fri 23 Oct" in days_menu
    assert "Sat" not in days_menu
    slots_menu = dial(env, "1*3*47*2")  # Monday 26 Oct
    assert "1. 08:00" in slots_menu
    reply = dial(env, "1*3*47*2*1")
    assert reply.startswith("END Booked APT-")
    assert "2026-10-26 08:00" in reply
    reference = reply.split()[2].rstrip(":")
    assert "Nairobi County" in env[1].outbox[-1][1]

    assert dial(env, f"1*4*{reference}").startswith(f"END {reference}: Nairobi")
    assert dial(env, f"1*4*{reference}", phone="+254799999999").startswith("END No appointment")


def test_booking_unknown_county(env):
    assert dial(env, "1*3*48").startswith("END Invalid")
    assert dial(env, "1*3*abc").startswith("END Invalid")


def test_second_booking_same_day_reports_no_slots(env):
    dial(env, "1*3*47*2*1")
    assert dial(env, "1*3*47*2*2").startswith("END No free slots")
