from datetime import date

import pytest

from crs_assistant import appointments, cli, db, notifications
from crs_assistant.death_rules import DeathPlace
from crs_assistant.rules import BirthPlace


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "crs.db")


def write_csv(tmp_path, text):
    path = tmp_path / "offices.csv"
    path.write_text(text)
    return str(path)


def test_load_offices_replaces_placeholder(tmp_path, db_path):
    csv_path = write_csv(tmp_path, "county_code,name,slot_capacity\n47,Nyayo House Registry,10\n47,Kibra Sub-County Office,\n")
    assert cli.main(["--database", db_path, "load-offices", csv_path]) == 0
    conn = db.connect(db_path)
    names = [r["name"] for r in conn.execute("SELECT name FROM offices WHERE county_code = '047' ORDER BY id")]
    assert names == ["Nyayo House Registry", "Kibra Sub-County Office"]
    capacities = [r[0] for r in conn.execute("SELECT slot_capacity FROM offices WHERE county_code = '047' ORDER BY id")]
    assert capacities == [10, 4]
    assert conn.execute("SELECT COUNT(*) FROM offices").fetchone()[0] == 48


def test_load_offices_is_idempotent_and_keeps_booked_placeholder(tmp_path, db_path):
    conn = db.connect(db_path)
    appointments.book(conn, 47, date(2026, 10, 26), "08:00", "+254712345678", "register", today=date(2026, 10, 22))
    csv_path = write_csv(tmp_path, "county_code,name,slot_capacity\n047,Nyayo House Registry,6\n")
    cli.load_offices(conn, csv_path)
    cli.load_offices(conn, csv_path)
    names = [r["name"] for r in conn.execute("SELECT name FROM offices WHERE county_code = '047'")]
    assert names == ["Nairobi County Civil Registration Office", "Nyayo House Registry"]


def test_load_offices_rejects_bad_rows(tmp_path, db_path, capsys):
    csv_path = write_csv(tmp_path, "county_code,name\n99,Nowhere\n")
    assert cli.main(["--database", db_path, "load-offices", csv_path]) == 1
    assert "line 2" in capsys.readouterr().err
    assert db.connect(db_path).execute("SELECT COUNT(*) FROM offices").fetchone()[0] == 47


def test_send_reminders_and_gap_report(db_path, capsys, monkeypatch):
    monkeypatch.delenv("AT_USERNAME", raising=False)
    conn = db.connect(db_path)
    dob = date.today().replace(day=1)
    notifications.record(conn, "023", dob, BirthPlace.HOME, "0712345678", today=date.today())
    assert cli.main(["--database", db_path, "send-reminders"]) == 0
    assert cli.main(["--database", db_path, "gap-report"]) == 0
    out = capsys.readouterr().out
    assert "reminder(s)" in out
    assert "Turkana" in out


def test_gap_report_for_deaths(db_path, capsys):
    conn = db.connect(db_path)
    notifications.record_death(conn, "009", date(2025, 1, 1), DeathPlace.HOME, "0712345678", today=date.today())
    assert cli.main(["--database", db_path, "gap-report", "--event", "death"]) == 0
    assert "Mandera" in capsys.readouterr().out
    assert cli.main(["--database", db_path, "gap-report"]) == 0
    assert "Mandera" not in capsys.readouterr().out
