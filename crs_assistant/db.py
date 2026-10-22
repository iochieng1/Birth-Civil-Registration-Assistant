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

CREATE TABLE IF NOT EXISTS birth_notifications (
    id             INTEGER PRIMARY KEY,
    reference      TEXT NOT NULL UNIQUE,
    county_code    TEXT NOT NULL,
    date_of_birth  TEXT NOT NULL,
    birth_place    TEXT NOT NULL,
    parent_phone   TEXT NOT NULL,
    language       TEXT NOT NULL DEFAULT 'en',
    captured_by    TEXT,
    registered_on  TEXT,
    last_reminder  INTEGER,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notifications_open ON birth_notifications(registered_on, county_code);
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    # Autocommit mode: modules open explicit transactions where atomicity matters.
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _seed_offices(conn)
    return conn


def _seed_offices(conn: sqlite3.Connection) -> None:
    """Seed one placeholder office per county until real office data is loaded."""
    if conn.execute("SELECT 1 FROM offices LIMIT 1").fetchone():
        return
    with conn:
        conn.executemany(
            "INSERT INTO offices (county_code, name) VALUES (?, ?)",
            [(c["code"], f"{c['name']} County Civil Registration Office") for c in reference.counties()],
        )
