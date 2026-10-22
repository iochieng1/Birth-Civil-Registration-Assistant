# Birth & Civil Registration Assistant

Helps Kenyan families register births and deaths **on time and in one trip**. Families get a personalised document checklist and a readiness check before they go. Parents and next of kin get SMS reminders before the six-month deadline, and they can book a slot at the registry instead of queueing from dawn. It works on smartphones through a web page and on any phone through USSD and SMS.

## The problem

Citizens struggle with document requirements and queues.

The Births and Deaths Registration Act (Cap. 149) requires every birth in Kenya to be registered within **six months**. Many births are still registered late or never, especially home births, births in arid and semi-arid counties, and births to young or unmarried parents. Without a birth certificate a child later struggles to join school, sit national exams, get a national ID, inherit or access services.

Deaths have the same problem. Many deaths, especially at home, are never registered. Without a death certificate the family cannot settle succession, claim pensions or insurance, or close the deceased's accounts and records.

The common reasons are practical, not legal:

| Barrier | What happens | How this project responds |
|---|---|---|
| Unclear requirements | Parents arrive without a document, are turned away and must travel again | Personalised checklist and readiness check, in English and Kiswahili |
| Home births | No hospital notification (B1), so the birth never enters the system | Community Health Promoters log the birth; the parent gets an SMS with next steps |
| Missed deadline | Late registration needs extra evidence and approval, so families give up | Reminders 60, 14 and 3 days before the deadline, plus guidance on late registration |
| Queues | A whole day lost queueing, often after travelling far | 30-minute appointment slots with SMS confirmation |
| Feature phones and low data | Online guidance cannot reach many rural families | USSD menu and SMS work on any phone |
| Unregistered home deaths | The family buries without a permit and later cannot get a death certificate | CHPs or chiefs log the death; the next of kin gets a condolence SMS with the deadline and reminders |
| No view of where the gaps are | Outreach is not targeted | County gap reports comparing notified births and deaths with registrations |

## Features

- **Rules engine** (`crs_assistant/rules.py`): works out whether a case is timely, late, adult late registration, replacement, correction or a birth abroad. It computes the deadline and lists the documents and steps. Proof of age for late registration is modelled as "any one of" clinic card, school record, baptism card or age assessment.
- **Death rules** (`death_rules.py`): timely and late death registration, facility and home deaths, deaths from accident, violence or an unknown cause (which must go through the police), deaths abroad and replacement death certificates. Late registration accepts any one proof of death: D1, burial permit, chief's letter or affidavit.
- **Checklist and readiness** (`checklist.py`): turns the plan into readable text and reports exactly what is still missing.
- **Appointments** (`appointments.py`): office slots with per-slot capacity, a weekday-only window up to 30 days ahead, one booking per phone per day, and cancellation that needs the booking phone. Bookings take a write lock, so the last place in a slot cannot be double-booked.
- **Community notifications** (`notifications.py`): CHPs record births, and CHPs or chiefs record deaths. SMS reminders are sent once per threshold, failed sends are retried, and an overdue notice points the family to late registration.
- **USSD** (`ussd.py`): an Africa's Talking-compatible menu for checklists (full list sent by SMS), deadline checks, booking and appointment lookup.
- **SMS** (`sms.py`): Africa's Talking gateway, with a local outbox for development.
- **Web page** (`static/index.html`): mobile-first, bilingual, with no build step and no external assets.
- **Kiswahili throughout** (`i18n.py`): every message has a Kiswahili translation, and a test checks that placeholders match between the two languages.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q

export CRS_STAFF_API_KEY=change-me      # enables CHP/staff endpoints
uvicorn crs_assistant.main:app --reload # http://localhost:8000 (API docs at /docs)
```

With Docker:

```bash
docker build -t crs-assistant .
docker run -p 8000:8000 -v crs-data:/data -e CRS_STAFF_API_KEY=change-me crs-assistant
```

See `.env.example` for all settings. Without Africa's Talking credentials, SMS messages are logged rather than sent.

## API

| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/` | Public | Self-service web page |
| POST | `/checklist` | Public | Birth checklist; include `have: [...]` for a readiness check |
| POST | `/checklist/death` | Public | Death checklist (same `have` readiness check) |
| GET | `/counties`, `/offices?county=47`, `/documents?lang=sw` | Public | Reference data |
| GET | `/offices/{id}/slots?day=YYYY-MM-DD` | Public | Free appointment slots |
| POST | `/appointments` | Public | Book a slot (SMS confirmation) |
| GET | `/appointments/{ref}?phone=` | Public | View a booking (phone must match) |
| POST | `/appointments/{ref}/cancel` | Public | Cancel a booking (phone must match) |
| POST | `/ussd` | Africa's Talking | USSD callback |
| POST | `/notifications` | Staff / CHP | Record a birth notification |
| POST | `/notifications/deaths` | Staff / CHP / chief | Record a death notification |
| POST | `/notifications/{ref}/registered` | Staff | Mark a notified birth or death as registered |
| POST | `/reminders/run` | Staff | Send due reminders |
| GET | `/reports/gaps?event=birth\|death` | Staff | County registration gap report |

Staff endpoints need the header `X-API-Key: $CRS_STAFF_API_KEY`. They return `503` until a key is configured.

Example:

```bash
curl -X POST localhost:8000/checklist -H 'Content-Type: application/json' \
  -d '{"date_of_birth":"2026-08-01","birth_place":"home","parents_married":false,"lang":"sw","have":["chief_letter","mother_id"]}'
```

## USSD menu

Point an Africa's Talking USSD channel's callback at `POST /ussd`.

```
1. English / 2. Kiswahili
└─ 1. Birth: documents needed    → service → applicant → place of birth → DOB → father's details → SMS checklist
   2. Death: documents needed    → service → place of death → cause → date of death → deceased had ID? → SMS checklist
   3. Check registration deadline → birth or death → date (DDMMYYYY)
   4. Book office appointment     → county number (1–47) → day → time → SMS confirmation
   5. Check my appointment        → reference
```

## Operations

```bash
python -m crs_assistant send-reminders           # run daily, e.g. cron: 0 8 * * * ...
python -m crs_assistant gap-report               # per-county table for births
python -m crs_assistant gap-report --event death # per-county table for deaths
python -m crs_assistant load-offices offices.csv # columns: county_code,name,slot_capacity
```

The database starts with one **placeholder** office per county. Load the real registry offices with `load-offices` before going live.

## Data and privacy

The system stores only what it needs to send reminders and manage bookings: the event (birth or death), county, date, type of place, the parent's or informant's phone number and preferred language. It does not store names or ID numbers. Phone numbers are masked in logs. Before you deploy, review the setup against the **Data Protection Act, 2019**: register as a data controller or processor with the ODPC, set a retention period, and get consent at the point of notification.

## Accuracy of requirements

Requirements in `crs_assistant/data/documents.json` and the rules in `rules.py` and `death_rules.py` summarise public Civil Registration Services guidance. They are **guidance, not legal advice**. Offices may ask for more evidence, and procedures change. Fees are deliberately not hard-coded: applicants are pointed to eCitizen for the current fee. Review the catalogue with CRS whenever guidance changes and update its `last_reviewed` date.

## Roadmap

- Integration with the KHIS / health-facility notification feed, so facility births are tracked automatically
- Public-holiday calendar and per-office opening hours
- Offline-first CHP app that syncs notifications
- More languages (e.g. Somali, Dholuo, Kikuyu) for targeted counties

## License

MIT, see [LICENSE](LICENSE).
