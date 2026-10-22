import sqlite3

import pytest

from crs_assistant import db, phone


@pytest.mark.parametrize(
    "raw",
    ["0712345678", "+254712345678", "254712345678", "712345678", "0712 345 678", "0112345678"],
)
def test_normalise_accepts_common_formats(raw):
    assert phone.normalise(raw).startswith("+254")
    assert len(phone.normalise(raw)) == 13


@pytest.mark.parametrize("raw", ["", "12345", "0812345678", "+255712345678", "07123456789"])
def test_normalise_rejects_invalid(raw):
    with pytest.raises(phone.InvalidPhone):
        phone.normalise(raw)


def test_mask_hides_middle_digits():
    assert phone.mask("+254712345678") == "+254712***678"


def test_connect_seeds_one_office_per_county_once():
    conn = db.connect()
    assert conn.execute("SELECT COUNT(*) FROM offices").fetchone()[0] == 47
    db._seed_offices(conn)
    assert conn.execute("SELECT COUNT(*) FROM offices").fetchone()[0] == 47


def test_migrates_birth_only_notifications_table(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(
        """
        CREATE TABLE birth_notifications (
            id INTEGER PRIMARY KEY, reference TEXT NOT NULL UNIQUE, county_code TEXT NOT NULL,
            date_of_birth TEXT NOT NULL, birth_place TEXT NOT NULL, parent_phone TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'en', captured_by TEXT, registered_on TEXT,
            last_reminder INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_notifications_open ON birth_notifications(registered_on, county_code);
        INSERT INTO birth_notifications (reference, county_code, date_of_birth, birth_place, parent_phone)
        VALUES ('BN-OLD123', '047', '2026-09-01', 'home', '+254712345678');
        """
    )
    old.close()

    conn = db.connect(path)
    row = conn.execute("SELECT * FROM notifications").fetchone()
    assert (row["event"], row["event_date"], row["place"], row["phone"]) == ("birth", "2026-09-01", "home", "+254712345678")
    db.connect(path)  # migrating again is a no-op
