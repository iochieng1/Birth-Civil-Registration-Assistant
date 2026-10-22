from datetime import date

import pytest
from fastapi.testclient import TestClient

from crs_assistant.api import create_app
from crs_assistant.sms import ConsoleGateway

TODAY = date(2026, 10, 22)
STAFF = {"X-API-Key": "secret"}


@pytest.fixture
def gateway():
    return ConsoleGateway()


@pytest.fixture
def client(gateway):
    app = create_app(":memory:", gateway=gateway, staff_api_key="secret", clock=lambda: TODAY)
    return TestClient(app)


def test_index_page_served(client):
    resp = client.get("/")
    assert resp.headers["content-type"].startswith("text/html")
    assert "Birth &amp; Death Registration Assistant" in resp.text


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_reference_endpoints(client):
    assert len(client.get("/counties").json()) == 47
    assert client.get("/documents", params={"lang": "sw"}).json()["mother_id"].startswith("Kitambulisho")
    offices = client.get("/offices", params={"county": "47"}).json()
    assert offices[0]["name"] == "Nairobi County Civil Registration Office"


def test_checklist_with_readiness(client):
    body = {
        "date_of_birth": "2026-09-01",
        "birth_place": "home",
        "parents_married": True,
        "have": ["chief_letter", "mother_id"],
    }
    data = client.post("/checklist", json=body).json()
    assert data["checklist"]["category"] == "timely"
    assert data["checklist"]["deadline"] == "2027-03-01"
    assert data["readiness"]["ready"] is False
    assert data["readiness"]["missing"] == ["father_id", "ecitizen_payment"]


def test_checklist_without_have_omits_readiness(client):
    data = client.post("/checklist", json={"date_of_birth": "2015-01-01", "lang": "sw"}).json()
    assert "readiness" not in data
    assert data["checklist"]["category"] == "late"


def test_checklist_rejects_future_birth(client):
    assert client.post("/checklist", json={"date_of_birth": "2027-01-01"}).status_code == 422


def test_booking_lifecycle(client, gateway):
    slots = client.get("/offices/47/slots", params={"day": "2026-10-26"}).json()["slots"]
    assert slots["08:00"] == 4

    resp = client.post(
        "/appointments",
        json={"office_id": 47, "day": "2026-10-26", "slot": "08:00", "phone": "0712345678", "lang": "sw"},
    )
    assert resp.status_code == 201
    ref = resp.json()["reference"]
    assert "Miadi" in gateway.outbox[-1][1]

    assert client.get(f"/appointments/{ref}", params={"phone": "0712345678"}).json()["slot"] == "08:00"
    assert client.get(f"/appointments/{ref}", params={"phone": "0799999999"}).status_code == 404
    assert client.post(f"/appointments/{ref}/cancel", json={"phone": "0799999999"}).status_code == 404
    assert client.post(f"/appointments/{ref}/cancel", json={"phone": "+254712345678"}).json()["status"] == "cancelled"


@pytest.mark.parametrize(
    "body,status",
    [
        ({"office_id": 999, "day": "2026-10-26", "slot": "08:00", "phone": "0712345678"}, 404),
        ({"office_id": 47, "day": "2026-10-24", "slot": "08:00", "phone": "0712345678"}, 409),
        ({"office_id": 47, "day": "2026-10-26", "slot": "08:00", "phone": "12345"}, 422),
    ],
)
def test_booking_errors(client, body, status):
    assert client.post("/appointments", json=body).status_code == status


def test_slots_errors(client):
    assert client.get("/offices/999/slots", params={"day": "2026-10-26"}).status_code == 404
    assert client.get("/offices/1/slots", params={"day": "2026-10-25"}).status_code == 409


def test_staff_endpoints_require_key(client):
    assert client.get("/reports/gaps").status_code == 401
    assert client.get("/reports/gaps", headers={"X-API-Key": "wrong"}).status_code == 401


def test_staff_endpoints_disabled_without_configured_key():
    app = create_app(":memory:", gateway=ConsoleGateway(), staff_api_key="", clock=lambda: TODAY)
    assert TestClient(app).get("/reports/gaps", headers=STAFF).status_code == 503


def test_notification_flow(client, gateway):
    body = {"county_code": "23", "date_of_birth": "2026-06-01", "birth_place": "home", "parent_phone": "0712345678"}
    resp = client.post("/notifications", json=body, headers=STAFF)
    assert resp.status_code == 201
    ref = resp.json()["reference"]
    assert resp.json()["deadline"] == "2026-12-01"
    assert gateway.outbox[-1][0] == "+254712345678"

    assert client.post("/reminders/run", headers=STAFF).json() == {"sent": 1}
    assert client.post("/reminders/run", headers=STAFF).json() == {"sent": 0}

    report = client.get("/reports/gaps", headers=STAFF).json()
    assert report[0]["county_name"] == "Turkana"
    assert report[0]["pending_in_window"] == 1

    assert client.post(f"/notifications/{ref}/registered", headers=STAFF).json()["registered_on"] == "2026-10-22"
    assert client.post(f"/notifications/{ref}/registered", headers=STAFF).status_code == 404
    assert client.get("/reports/gaps", headers=STAFF).json()[0]["registration_rate"] == 1.0


def test_notification_validation(client):
    body = {"county_code": "99", "date_of_birth": "2026-06-01", "birth_place": "home", "parent_phone": "0712345678"}
    assert client.post("/notifications", json=body, headers=STAFF).status_code == 422


def test_ussd_callback(client):
    form = {"sessionId": "s1", "serviceCode": "*384#", "phoneNumber": "+254712345678", "text": ""}
    resp = client.post("/ussd", data=form)
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text.startswith("CON 1. English")

    form["text"] = "1*3*1*01092026"
    assert client.post("/ussd", data=form).text.startswith("END Register by 2027-03-01")

    form["phoneNumber"] = "bad"
    assert client.post("/ussd", data=form).text.startswith("END Invalid")


def test_death_checklist(client):
    body = {"date_of_death": "2026-10-20", "place_of_death": "home", "circumstance": "unnatural", "have": ["death_chief_letter"]}
    data = client.post("/checklist/death", json=body).json()
    assert data["checklist"]["category"] == "death_timely"
    assert data["checklist"]["deadline"] == "2027-04-20"
    assert "police_death_report" in data["readiness"]["missing"]

    replacement = client.post("/checklist/death", json={"service": "death_replacement", "date_of_death": "2010-01-01", "lang": "sw"})
    assert replacement.json()["checklist"]["category"] == "death_replacement"
    assert client.post("/checklist/death", json={"date_of_death": "2027-01-01"}).status_code == 422


def test_death_notification_and_report(client, gateway):
    body = {"county_code": "23", "date_of_death": "2026-10-01", "place_of_death": "home", "informant_phone": "0712345678"}
    resp = client.post("/notifications/deaths", json=body, headers=STAFF)
    assert resp.status_code == 201
    assert resp.json()["reference"].startswith("DN-")
    assert resp.json()["event"] == "death"
    assert "condolences" in gateway.outbox[-1][1]

    assert client.get("/reports/gaps", headers=STAFF).json() == []
    deaths = client.get("/reports/gaps", params={"event": "death"}, headers=STAFF).json()
    assert deaths[0]["county_name"] == "Turkana"
    assert client.get("/reports/gaps", params={"event": "marriage"}, headers=STAFF).status_code == 422
    assert client.post("/notifications/deaths", json=body).status_code == 401


def test_booking_accepts_death_service(client):
    body = {"office_id": 47, "day": "2026-10-26", "slot": "09:00", "phone": "0712345678", "service": "death"}
    assert client.post("/appointments", json=body).json()["service"] == "death"


def test_id_checklist(client):
    data = client.post("/checklist/id", json={"date_of_birth": "2008-01-01", "father": "deceased", "have": ["applicant_birth_certificate"]}).json()
    assert data["checklist"]["category"] == "id_first_time"
    assert data["readiness"]["missing"] == ["mother_id", "parent_death_certificate"]
    assert "next" not in data

    blocked = client.post("/checklist/id", json={"date_of_birth": "2005-01-01", "has_birth_certificate": False, "lang": "sw"}).json()
    assert blocked["checklist"]["category"] == "id_birth_cert_first"
    assert blocked["next"] == {"path": "/checklist", "body": {"date_of_birth": "2005-01-01", "applicant": "self"}}
    follow = client.post(blocked["next"]["path"], json=blocked["next"]["body"]).json()
    assert follow["checklist"]["category"] == "late_adult"

    young = client.post("/checklist/id", json={"date_of_birth": "2010-05-05"}).json()
    assert young["checklist"]["category"] == "id_not_yet"
    assert young["checklist"]["deadline"] == "2028-05-05"

    change = client.post("/checklist/id", json={"service": "id_change", "change_reason": "marriage", "date_of_birth": "1990-01-01"})
    assert change.json()["checklist"]["category"] == "id_change"
    assert client.post("/checklist/id", json={"date_of_birth": "2030-01-01"}).status_code == 422


def test_id_reminders_and_gap_report(client, gateway):
    body = {"county_code": "9", "date_of_birth": "2004-06-01", "phone": "0712345678", "captured_by": "SCHOOL-7"}
    resp = client.post("/notifications/ids", json=body, headers=STAFF)
    assert resp.status_code == 201
    assert resp.json()["event"] == "id" and resp.json()["reference"].startswith("ID-")
    assert gateway.outbox[-1][1].startswith("You turned 18")
    report = client.get("/reports/gaps", params={"event": "id"}, headers=STAFF).json()
    assert (report[0]["county_name"], report[0]["overdue"]) == ("Mandera", 1)
    assert client.post("/notifications/ids", json=body).status_code == 401
