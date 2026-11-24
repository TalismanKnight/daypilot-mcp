"""Seed one realistic day in IST so the demo works every time. Run: python -m daypilot.seed [YYYY-MM-DD]"""
import sys
from datetime import date, datetime, timedelta

from daypilot.db import connect, db_path
from daypilot.timeutil import IST, iso, now


def seed(start: date | None = None, reset=True):
    start = start or now().date()
    conn = connect()
    if reset:
        for table in ("events", "tasks", "proposals", "audit_log", "settings"):
            conn.execute(f"DELETE FROM {table}")

    def at(d, hh, mm=0):
        return iso(datetime(d.year, d.month, d.day, hh, mm, tzinfo=IST))

    tomorrow = start + timedelta(days=1)
    events = [
        ("Breakfast", at(start, 8), at(start, 8, 30), None, "routine", "daily"),
        ("Lunch", at(start, 13), at(start, 13, 45), None, "routine", "daily"),
        ("Dinner", at(start, 20), at(start, 20, 45), None, "routine", "daily"),
        ("Team meeting", at(start, 11), at(start, 12), None, "fixed", None),
        ("Dentist appointment", at(start, 16), at(start, 17), "Jayanagar 4th Block, Bengaluru", "fixed", None),
        ("Call with mentor", at(tomorrow, 15), at(tomorrow, 15, 30), None, "fixed", None),
    ]
    for title, s, e, loc, kind, rep in events:
        conn.execute("INSERT INTO events(title, start, end, location, kind, repeat) VALUES (?,?,?,?,?,?)",
                     (title, s, e, loc, kind, rep))
    tasks = [
        ("Project report", 180, at(tomorrow, 12), 3),
        ("Read chapter 5", 60, at(start + timedelta(days=3), 18), 2),
        ("Gym session", 60, None, 1),
    ]
    for title, est, dl, pr in tasks:
        conn.execute("INSERT INTO tasks(title, est_minutes, deadline, priority) VALUES (?,?,?,?)", (title, est, dl, pr))
    conn.execute("INSERT INTO settings(key, value) VALUES ('home', 'MSR Nagar, Bengaluru')")
    conn.commit()
    return db_path()


if __name__ == "__main__":
    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    print("Seeded:", seed(d))
