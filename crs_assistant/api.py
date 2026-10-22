"""HTTP API: citizen self-service, staff/CHP endpoints and the USSD callback."""

from __future__ import annotations

import hmac
import os
import sqlite3
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from typing import Annotated, Literal
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from . import __version__, appointments, checklist, db, notifications, reference, ussd
from .i18n import normalise_lang, t
from .phone import InvalidPhone, normalise
from .rules import Applicant, BirthPlace, Case, Service, build_plan
from .sms import SmsGateway, from_env

Lang = Literal["en", "sw"]


class ChecklistRequest(BaseModel):
    service: Service = Service.REGISTER
    date_of_birth: date
    birth_place: BirthPlace = BirthPlace.FACILITY
    applicant: Applicant = Applicant.PARENT
    parents_married: bool = False
    include_father: bool = True
    lang: Lang = "en"
    have: list[str] | None = Field(default=None, description="Document ids the applicant already has")


class BookingRequest(BaseModel):
    office_id: int
    day: date
    slot: str
    phone: str
    service: Service = Service.REGISTER
    lang: Lang = "en"


class CancelRequest(BaseModel):
    phone: str


class NotificationRequest(BaseModel):
    county_code: str
    date_of_birth: date
    birth_place: BirthPlace
    parent_phone: str
    language: Lang = "en"
    captured_by: str | None = None


class RegisteredRequest(BaseModel):
    registered_on: date | None = None


def get_conn(request: Request) -> sqlite3.Connection:
    return request.app.state.conn


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def _phone(raw: str) -> str:
    try:
        return normalise(raw)
    except InvalidPhone as exc:
        raise HTTPException(422, str(exc)) from exc


def create_app(
    database: str | None = None,
    gateway: SmsGateway | None = None,
    staff_api_key: str | None = None,
    clock: Callable[[], date] = date.today,
) -> FastAPI:
    app = FastAPI(
        title="Birth & Civil Registration Assistant",
        version=__version__,
        description="Helps Kenyan families register births on time: personalised document "
        "checklists, deadline reminders, appointment booking and USSD access.",
    )
    conn = db.connect(database or os.getenv("CRS_DATABASE", "crs.db"))
    sms = gateway or from_env()
    staff_key = staff_api_key if staff_api_key is not None else os.getenv("CRS_STAFF_API_KEY", "")
    app.state.conn, app.state.sms = conn, sms

    def require_staff(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if not staff_key:
            raise HTTPException(503, "staff API is not configured (set CRS_STAFF_API_KEY)")
        if not x_api_key or not hmac.compare_digest(x_api_key, staff_key):
            raise HTTPException(401, "invalid API key")

    staff = [Depends(require_staff)]

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    # Reference data
    @app.get("/counties")
    def list_counties():
        return reference.counties()

    @app.get("/documents")
    def list_documents(lang: Lang = "en"):
        return {doc_id: reference.document_name(doc_id, lang) for doc_id in reference.documents()}

    @app.get("/offices")
    def list_offices(conn: Conn, county: str | None = None):
        if county:
            rows = conn.execute("SELECT * FROM offices WHERE county_code = ? ORDER BY id", (county.zfill(3),))
        else:
            rows = conn.execute("SELECT * FROM offices ORDER BY id")
        return [dict(r) for r in rows.fetchall()]

    # Citizen self-service
    @app.post("/checklist")
    def make_checklist(req: ChecklistRequest):
        try:
            case = Case(
                req.service,
                req.date_of_birth,
                birth_place=req.birth_place,
                applicant=req.applicant,
                parents_married=req.parents_married,
                include_father=req.include_father,
                today=clock(),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        plan = build_plan(case)
        result = {"checklist": asdict(checklist.render(plan, req.lang))}
        if req.have is not None:
            result["readiness"] = asdict(checklist.assess(plan, set(req.have), req.lang))
        return result

    @app.get("/offices/{office_id}/slots")
    def office_slots(office_id: int, day: date, conn: Conn):
        try:
            return {"day": day, "slots": appointments.available_slots(conn, office_id, day, today=clock())}
        except appointments.OfficeNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except appointments.SlotUnavailable as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/appointments", status_code=201)
    def create_appointment(req: BookingRequest, conn: Conn):
        phone = _phone(req.phone)
        try:
            appt = appointments.book(conn, req.office_id, req.day, req.slot, phone, req.service.value, today=clock())
        except appointments.OfficeNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except appointments.SlotUnavailable as exc:
            raise HTTPException(409, str(exc)) from exc
        sms.send(
            phone,
            t("sms.appointment_booked", req.lang, reference=appt.reference, office=appt.office_name, day=appt.day, slot=appt.slot),
        )
        return asdict(appt)

    @app.get("/appointments/{ref}")
    def get_appointment(ref: str, phone: Annotated[str, Query()], conn: Conn):
        appt = appointments.get(conn, ref)
        if appt is None or appt.phone != _phone(phone):
            raise HTTPException(404, "appointment not found")
        return asdict(appt)

    @app.post("/appointments/{ref}/cancel")
    def cancel_appointment(ref: str, req: CancelRequest, conn: Conn):
        if not appointments.cancel(conn, ref, _phone(req.phone)):
            raise HTTPException(404, "no active appointment with that reference and phone")
        return {"reference": ref.upper(), "status": "cancelled"}

    # Community health promoters and registry staff
    @app.post("/notifications", status_code=201, dependencies=staff)
    def create_notification(req: NotificationRequest, conn: Conn):
        try:
            n = notifications.record(
                conn,
                req.county_code,
                req.date_of_birth,
                req.birth_place,
                req.parent_phone,
                req.language,
                req.captured_by,
                gateway=sms,
                today=clock(),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"reference": n.reference, "deadline": n.deadline, "county_code": n.county_code}

    @app.post("/notifications/{ref}/registered", dependencies=staff)
    def notification_registered(ref: str, conn: Conn, req: RegisteredRequest | None = None):
        on = (req.registered_on if req else None) or clock()
        if not notifications.mark_registered(conn, ref, on):
            raise HTTPException(404, "no open notification with that reference")
        return {"reference": ref.upper(), "registered_on": on}

    @app.post("/reminders/run", dependencies=staff)
    def run_reminders(conn: Conn):
        return {"sent": notifications.send_reminders(conn, sms, today=clock())}

    @app.get("/reports/gaps", dependencies=staff)
    def gaps(conn: Conn):
        return [
            {**asdict(g), "registration_rate": g.registration_rate}
            for g in notifications.gap_report(conn, today=clock())
        ]

    # USSD callback (Africa's Talking posts application/x-www-form-urlencoded)
    @app.post("/ussd", response_class=PlainTextResponse)
    async def ussd_callback(request: Request, conn: Conn):
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
        try:
            phone = normalise(form.get("phoneNumber", ""))
        except InvalidPhone:
            return ussd.end(t("ussd.invalid", normalise_lang(None)))
        return ussd.handle(conn, sms, phone, form.get("text", ""), today=clock())

    return app
