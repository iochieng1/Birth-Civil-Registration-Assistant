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


@pytest.mark.parametrize("text", ["9", "1*9", "1*1*9", "1*1*1*1*32132026", "1*4*1*31022026", "1*4*4", "1*5*99", "1*3*9", "1*3*3*7", "1*3*1*01012005*3", "1*3*1*01012005*1*5", "1*2*3", "1*2*1*1*1*01011990*7"])
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
    screens = ["1", "2", "1*1", "2*1", "1*1*1", "2*1*1", "1*1*1*1", "2*1*1*1", "1*1*1*1*1", "1*1*1*1*1*01092026"]
    screens += ["1*2", "2*2", "1*2*1", "2*2*1", "1*2*1*1", "2*2*1*1", "1*2*1*1*1", "2*2*1*1*1*01102026"]
    screens += ["1*4", "2*4", "1*5", "1*5*47", "1*3", "2*3", "1*3*1", "1*3*1*01012005", "2*3*1*01012005", "1*3*1*01012005*1", "2*3*1*01012005*1", "1*3*3", "2*3*3"]
    for text in screens:
        assert len(dial(env, text)) <= 182, text


def test_deadline_check(env):
    assert dial(env, "1*4").startswith("CON Deadline for")
    assert dial(env, "1*4*1").startswith("CON Enter date of birth")
    assert dial(env, "1*4*1*01092026") == "END Register by 2027-03-01: 130 day(s) left."
    assert "late registration" in dial(env, "1*4*1*01012020")
    assert dial(env, "1*4*2").startswith("CON Enter date of death")
    assert dial(env, "1*4*2*20102026") == "END Register by 2027-04-20: 180 day(s) left."


def test_booking_flow_and_lookup(env):
    days_menu = dial(env, "1*5*47")
    assert days_menu.startswith("CON Choose a day")
    assert "1. Fri 23 Oct" in days_menu
    assert "Sat" not in days_menu
    slots_menu = dial(env, "1*5*47*2")  # Monday 26 Oct
    assert "1. 08:00" in slots_menu
    reply = dial(env, "1*5*47*2*1")
    assert reply.startswith("END Booked APT-")
    assert "2026-10-26 08:00" in reply
    reference = reply.split()[2].rstrip(":")
    assert "Nairobi County" in env[1].outbox[-1][1]

    assert dial(env, f"1*6*{reference}").startswith(f"END {reference}: Nairobi")
    assert dial(env, f"1*6*{reference}", phone="+254799999999").startswith("END No appointment")


def test_booking_unknown_county(env):
    assert dial(env, "1*5*48").startswith("END Invalid")
    assert dial(env, "1*5*abc").startswith("END Invalid")


def test_second_booking_same_day_reports_no_slots(env):
    dial(env, "1*5*47*2*1")
    assert dial(env, "1*5*47*2*2").startswith("END No free slots")


def test_death_checklist_flow_sends_sms(env):
    assert dial(env, "1*2").startswith("CON Our condolences")
    assert dial(env, "1*2*1").startswith("CON Where did the death")
    assert dial(env, "1*2*1*2").startswith("CON Cause of death")
    assert dial(env, "1*2*1*2*2").startswith("CON Enter date of death")
    assert dial(env, "1*2*1*2*2*20102026").startswith("CON Did the deceased")
    reply = dial(env, "1*2*1*2*2*20102026*2")
    assert reply.startswith("END Death registration within the 6-month window")
    message = env[1].outbox[-1][1]
    assert "Assistant Chief" in message
    assert "Police abstract" in message
    assert "national ID card or passport" not in message  # deceased had no ID
    assert "burial permit" in message


def test_late_death_sms_groups_proof_of_death(env):
    reply = dial(env, "2*2*1*1*1*01012020*1")
    assert reply.startswith("END Usajili wa kifo uliochelewa")
    assert "uthibitisho mmoja wa kifo" in env[1].outbox[-1][1]


def test_death_replacement_and_abroad_end_early(env):
    assert dial(env, "1*2*2").startswith("END Replacement of a lost death certificate")
    assert dial(env, "1*2*1*3").startswith("END Death outside Kenya")


def test_first_id_flow_sends_checklist(env):
    assert dial(env, "1*3").startswith("CON National ID")
    assert dial(env, "1*3*1").startswith("CON Enter date of birth")
    assert dial(env, "1*3*1*01012005").startswith("CON Do you have your own birth certificate")
    assert dial(env, "1*3*1*01012005*1").startswith("CON Which parents")
    reply = dial(env, "1*3*1*01012005*1*2")
    assert reply.startswith("END First-time national ID application")
    message = env[1].outbox[-1][1]
    assert "Mother's national ID" in message
    assert "Father's" not in message


def test_no_birth_certificate_points_to_birth_registration(env):
    reply = dial(env, "2*3*1*01012005*2")
    assert reply.startswith("END Unahitaji cheti cha kuzaliwa kwanza")
    assert "sajili kuzaliwa kwako kwanza" in env[1].outbox[-1][1]
    # The suggested path really is the adult's own late birth registration.
    assert dial(env, "2*1*1*3*1*01012005").startswith("END Usajili wa kuchelewa wa mtu mzima")


def test_under_18_learns_eligibility_date(env):
    reply = dial(env, "1*3*1*01122008")
    assert reply.startswith("END Not yet eligible")
    assert "You can apply from 2026-12-01" in env[1].outbox[-1][1]


def test_id_replacement_and_change(env):
    assert dial(env, "1*3*2").startswith("END Replacement of a lost or damaged national ID")
    assert "police abstract" in env[1].outbox[-1][1].lower()
    assert dial(env, "1*3*3").startswith("CON What is changing")
    assert dial(env, "1*3*3*2").startswith("END Change of details")
    assert "deed poll" in env[1].outbox[-1][1]


def test_turning_18_deadline_check(env):
    assert dial(env, "1*4*3").startswith("CON Enter date of birth")
    assert dial(env, "1*4*3*01122008") == "END You can apply for a national ID from 2026-12-01: 40 day(s) to go."
    assert dial(env, "1*4*3*01012005").startswith("END You have been eligible since 2023-01-01")
