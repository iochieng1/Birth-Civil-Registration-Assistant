"""Command-line tasks: ``python -m crs_assistant <command>``.

send-reminders  run daily from cron to send deadline reminders
gap-report      print the per-county registration gap report
load-offices    load real registration offices from a CSV file
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
from datetime import date

from . import db, notifications, reference
from .sms import from_env

PLACEHOLDER_SUFFIX = " County Civil Registration Office"


def load_offices(conn: sqlite3.Connection, path: str) -> int:
    """Load offices from a CSV with columns county_code,name[,slot_capacity].

    Placeholder offices for the counties in the file are removed unless they
    already have appointments. Existing offices with the same name are updated.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for i, row in enumerate(rows, start=2):
        county = reference.county_by_code(row.get("county_code", "").strip())
        if county is None or not row.get("name", "").strip():
            raise ValueError(f"line {i}: needs a valid county_code and a name")
        row["county_code"] = county["code"]

    conn.execute("BEGIN")
    try:
        for code in {r["county_code"] for r in rows}:
            placeholder = reference.county_by_code(code)["name"] + PLACEHOLDER_SUFFIX
            conn.execute(
                "DELETE FROM offices WHERE county_code = ? AND name = ?"
                " AND id NOT IN (SELECT office_id FROM appointments)",
                (code, placeholder),
            )
        for row in rows:
            capacity = int(row.get("slot_capacity") or 4)
            name = row["name"].strip()
            existing = conn.execute("SELECT id FROM offices WHERE name = ?", (name,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE offices SET county_code = ?, slot_capacity = ? WHERE id = ?",
                    (row["county_code"], capacity, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO offices (county_code, name, slot_capacity) VALUES (?, ?, ?)",
                    (row["county_code"], name, capacity),
                )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crs_assistant", description=__doc__.split("\n")[0])
    parser.add_argument("--database", default=os.getenv("CRS_DATABASE", "crs.db"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("send-reminders", help="send due deadline reminders by SMS")
    sub.add_parser("gap-report", help="print notified vs registered births per county")
    load = sub.add_parser("load-offices", help="load offices from CSV (county_code,name,slot_capacity)")
    load.add_argument("csv_path")
    args = parser.parse_args(argv)

    conn = db.connect(args.database)
    if args.command == "send-reminders":
        print(f"sent {notifications.send_reminders(conn, from_env(), today=date.today())} reminder(s)")
    elif args.command == "gap-report":
        print(f"{'County':<18}{'Notified':>9}{'Registered':>11}{'On time':>8}{'Pending':>8}{'Overdue':>8}{'Rate':>7}")
        for g in notifications.gap_report(conn):
            print(
                f"{g.county_name:<18}{g.notified:>9}{g.registered:>11}{g.registered_on_time:>8}"
                f"{g.pending_in_window:>8}{g.overdue:>8}{g.registration_rate:>7.0%}"
            )
    elif args.command == "load-offices":
        try:
            print(f"loaded {load_offices(conn, args.csv_path)} office(s)")
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    return 0
