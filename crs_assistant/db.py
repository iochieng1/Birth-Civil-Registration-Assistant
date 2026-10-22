"""SQLite persistence.

Only the minimum personal data needed to send reminders and manage
appointments is stored, in line with the Data Protection Act, 2019.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import reference

SCHEMA = """
CREATE TABLE IF NOT EXISTS offices (
    id            INTEGER PRIMARY KEY,
    county_code   TEXT NOT NULL,
    name          TEXT NOT NULL,
    slot_capacity INTEGER NOT NULL DEFAULT 4
);

CREATE TABLE IF NOT EXISTS appointments (
    id         INTEGER PRIMARY KEY,
    reference  TEXT NOT NULL UNIQUE,
    office_id  INTEGER NOT NULL REFERENCES offices(id),
    day        TEXT NOT NULL,
    slot       TEXT NOT NULL,
    phone      TEXT NOT NULL,
    service    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'booked',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_appointments_slot ON appointments(office_id, day, slot, status);

CREATE TABLE IF NOT EXISTS notifications (
    id             INTEGER PRIMARY KEY,
    reference      TEXT NOT NULL UNIQUE,
    event          TEXT NOT NULL DEFAULT 'birth',
    county_code    TEXT NOT NULL,
    event_date     TEXT NOT NULL,
    place          TEXT NOT NULL,
    phone          TEXT NOT NULL,
    language       TEXT NOT NULL DEFAULT 'en',
    captured_by    TEXT,
    registered_on  TEXT,
    last_reminder  INTEGER,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notifications_event ON notifications(event, registered_on, county_code);
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    # Autocommit mode: modules open explicit transactions where atomicity matters.
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _migrate(conn)
    conn.executescript(SCHEMA)
    _seed_offices(conn)
    return conn


# Databases created before death registration have a birth-only table.
MIGRATE_BIRTH_NOTIFICATIONS = """
BEGIN;
ALTER TABLE birth_notifications RENAME TO notifications;
ALTER TABLE notifications RENAME COLUMN date_of_birth TO event_date;
ALTER TABLE notifications RENAME COLUMN birth_place TO place;
ALTER TABLE notifications RENAME COLUMN parent_phone TO phone;
ALTER TABLE notifications ADD COLUMN event TEXT NOT NULL DEFAULT 'birth';
DROP INDEX IF EXISTS idx_notifications_open;
COMMIT;
"""


def _migrate(conn: sqlite3.Connection) -> None:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "birth_notifications" in tables and "notifications" not in tables:
        conn.executescript(MIGRATE_BIRTH_NOTIFICATIONS)


def _seed_offices(conn: sqlite3.Connection) -> None:
    """Seed one placeholder office per county until real office data is loaded."""
    if conn.execute("SELECT 1 FROM offices LIMIT 1").fetchone():
        return
    with conn:
        conn.executemany(
            "INSERT INTO offices (county_code, name) VALUES (?, ?)",
            [(c["code"], f"{c['name']} County Civil Registration Office") for c in reference.counties()],
        )
