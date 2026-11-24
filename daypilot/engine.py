"""Scheduling engine: free slots, priorities, slot finding, departures, day plans.
Pure logic over SQLite. Every number the assistant needs is computed here, in IST."""
import json
from datetime import datetime, timedelta, time, date

from daypilot import maps
from daypilot.timeutil import (IST, now, parse_dt, iso, say_time, say_minutes, say_hours)

WAKE_START = time(8, 0)
WAKE_END = time(22, 0)
MIN_CHUNK = 30
MAX_CHUNK = 120
PRIORITY = {"low": 1, "normal": 2, "high": 3}
PRIORITY_NAME = {1: "low", 2: "normal", 3: "high"}
DEFAULT_BUFFER = {"drive": 10, "transit": 15, "walk": 10, "bicycle": 10}
WAYFINDING_EXTRA = 10  # extra minutes in the voice_first profile for finding stops, crossings and entrances


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


# ---------------------------------------------------------------- events
def occurrences(row, range_start: datetime, range_end: datetime):
    """(start, end) pairs of an event that overlap the range, expanding repeats."""
    start, end = parse_dt(row["start"]), parse_dt(row["end"])
    duration = end - start
    repeat = row["repeat"]
    if not repeat:
        return [(start, end)] if start < range_end and end > range_start else []
    out = []
    d = range_start.date() - timedelta(days=1)
    while d <= range_end.date():
        if d >= start.date():
            ok = (repeat == "daily"
                  or (repeat == "weekdays" and d.weekday() < 5)
                  or (repeat == "weekly" and d.weekday() == start.weekday()))
            if ok:
                s = datetime.combine(d, start.timetz())
                e = s + duration
                if s < range_end and e > range_start:
                    out.append((s, e))
        d += timedelta(days=1)
    return out


def departure(conn, event_start: datetime, location: str, buffer_min=None, mode=None) -> dict:
    """Two-pass leave-by: arrival minus travel minus buffer, re-checking traffic at the leave time."""
    home = get_setting(conn, "home")
    if not home:
        raise ValueError("Set your home location first so I can work out travel time.")
    mode = mode or get_setting(conn, "travel_mode", "transit")
    profile = get_setting(conn, "profile", "standard")
    if buffer_min is None:
        buffer_min = DEFAULT_BUFFER.get(mode, 10) + (WAYFINDING_EXTRA if profile == "voice_first" else 0)
    if not 0 <= buffer_min <= 120:
        raise ValueError("Buffer must be between 0 and 120 minutes.")
    first = maps.get_travel(home, location, event_start, mode)
    guess = event_start - timedelta(minutes=first["duration_min"] + buffer_min)
    second = maps.get_travel(home, location, guess, mode)
    leave_by = event_start - timedelta(minutes=second["duration_min"] + buffer_min)
    return {
        "origin": home, "destination": location, "mode": mode, "profile": profile,
        "arrive_by": iso(event_start), "leave_by": iso(leave_by),
        "travel_minutes": second["duration_min"], "distance_km": second["distance_km"],
        "buffer_minutes": buffer_min, "total_minutes_before_event": second["duration_min"] + buffer_min,
        "source": second["source"],
        "_leave_dt": leave_by, "_start_dt": event_start,
    }


def public(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def busy_blocks(conn, range_start, range_end, include_travel=True):
    """Everything that occupies time in the range, including travel before located events."""
    out = []
    home = get_setting(conn, "home")
    for row in conn.execute("SELECT * FROM events"):
        for s, e in occurrences(row, range_start, range_end + timedelta(hours=6)):
            if s < range_end and e > range_start:
                out.append({"start": s, "end": e, "title": row["title"], "kind": row["kind"],
                            "event_id": row["id"], "location": row["location"]})
            if include_travel and home and row["location"] and row["kind"] == "fixed":
                dep = departure(conn, s, row["location"])
                ts, te = dep["_leave_dt"], s
                if ts < range_end and te > range_start:
                    out.append({"start": ts, "end": te, "title": f"Travel to {row['title']}",
                                "kind": "travel", "event_id": row["id"], "location": None})
    return out


def merge(intervals):
    merged = []
    for s, e in sorted(intervals):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def free_slots(conn, range_start: datetime, range_end: datetime, min_minutes=30, include_travel=True):
    """Exact free time inside waking hours, after events, routines, tasks blocks and travel."""
    t = now()
    rounded = t + timedelta(minutes=(-t.minute) % 5)
    rounded = rounded.replace(second=0)
    busy = merge([(b["start"], b["end"]) for b in busy_blocks(conn, range_start, range_end, include_travel)])
    slots = []
    d = range_start.date()
    while d <= range_end.date():
        lo = max(datetime.combine(d, WAKE_START, tzinfo=IST), range_start)
        hi = min(datetime.combine(d, WAKE_END, tzinfo=IST), range_end)
        if d == t.date():
            lo = max(lo, rounded)
        cursor = lo
        for s, e in busy:
            if e <= cursor or s >= hi:
                continue
            if s > cursor:
                slots.append({"start": cursor, "end": min(s, hi)})
            cursor = max(cursor, e)
        if cursor < hi:
            slots.append({"start": cursor, "end": hi})
        d += timedelta(days=1)
    out = []
    for s in slots:
        mins = int((s["end"] - s["start"]).total_seconds() // 60)
        if mins >= min_minutes:
            out.append({"start": s["start"], "end": s["end"], "minutes": mins})
    return out


# ---------------------------------------------------------------- tasks
def scheduled_minutes(conn, task_id, after):
    total = 0
    for r in conn.execute("SELECT start, end FROM events WHERE kind='task_block' AND task_id=?", (task_id,)):
        s, e = parse_dt(r["start"]), parse_dt(r["end"])
        if e > after:
            total += int((e - max(s, after)).total_seconds() // 60)
    return total


def score_task(conn, task, t=None) -> dict:
    t = t or now()
    needs = max(task["est_minutes"] - task["done_minutes"], 0)
    sched = scheduled_minutes(conn, task["id"], t)
    unscheduled = max(needs - sched, 0)
    dl = parse_dt(task["deadline"]) if task["deadline"] else None
    hours_left = (dl - t).total_seconds() / 3600 if dl else None
    horizon = hours_left if hours_left is not None else 24 * 14
    urgency = (needs / 60) / max(horizon, 0.5)
    score = task["priority"] * 10 + min(urgency, 2.0) * 40
    if hours_left is not None and hours_left <= 0:
        score += 50
    elif hours_left is not None and hours_left <= 24:
        score += 15
    reasons = []
    if dl is None:
        reasons.append("no deadline")
    elif hours_left <= 0:
        reasons.append("overdue")
    else:
        reasons.append(f"due in {say_hours(hours_left)}")
    reasons.append(f"needs {say_minutes(needs)}")
    reasons.append(f"{PRIORITY_NAME[task['priority']]} priority")
    reasons.append("not started" if task["done_minutes"] == 0 else f"{say_minutes(task['done_minutes'])} done")
    return {
        "id": task["id"], "title": task["title"], "est_minutes": task["est_minutes"],
        "done_minutes": task["done_minutes"], "needs_minutes": needs,
        "scheduled_minutes": sched, "unscheduled_minutes": unscheduled,
        "deadline": task["deadline"], "due_in_hours": round(hours_left, 1) if hours_left is not None else None,
        "priority": PRIORITY_NAME[task["priority"]], "score": round(score, 1), "reason": ", ".join(reasons),
    }


def priority_list(conn, limit=10):
    t = now()
    rows = conn.execute("SELECT * FROM tasks WHERE status != 'done'").fetchall()
    ranked = sorted((score_task(conn, r, t) for r in rows), key=lambda x: -x["score"])
    return ranked[:limit]


def place_task(slots, minutes, deadline=None, per_slot_cap=MAX_CHUNK, min_chunk=MIN_CHUNK, total_cap=None):
    """Place minutes of work into slots (mutated). Prefers one slot; otherwise splits chronologically."""
    need = minutes if total_cap is None else min(minutes, total_cap)
    blocks = []

    def room(s):
        end = min(s["end"], deadline) if deadline else s["end"]
        return int((end - s["start"]).total_seconds() // 60)

    def take(s, chunk):
        b = {"start": s["start"], "end": s["start"] + timedelta(minutes=chunk), "minutes": chunk}
        s["start"] = b["end"]
        blocks.append(b)

    if need <= 3 * 60:
        for s in slots:
            if room(s) >= need >= 1:
                take(s, need)
                return blocks, need
    left = need
    for s in slots:
        while left > 0 and room(s) >= min(min_chunk, left):
            take(s, min(room(s), left, per_slot_cap))
            left -= blocks[-1]["minutes"]
        if left <= 0:
            break
    return blocks, need - left


def find_slot_for(conn, task_row) -> dict:
    t = now()
    info = score_task(conn, task_row, t)
    need = info["unscheduled_minutes"]
    deadline = parse_dt(task_row["deadline"]) if task_row["deadline"] else None
    window_end = deadline or (t + timedelta(days=14))
    if window_end <= t:
        raise ValueError(f"{task_row['title']} is already past its deadline, so there is no slot before it.")
    slots = free_slots(conn, t, window_end, MIN_CHUNK)
    total_free = sum(s["minutes"] for s in slots)
    blocks, placed = place_task(slots, need, deadline)
    fits = placed >= need
    return {
        "task": info["title"], "task_id": info["id"], "fits": fits,
        "needed_minutes": need, "total_free_minutes_before_deadline": total_free,
        "shortfall_minutes": max(need - placed, 0),
        "blocks": [{"start": iso(b["start"]), "end": iso(b["end"]), "minutes": b["minutes"]} for b in blocks],
        "reason": ("earliest free gap that is long enough" if len(blocks) == 1
                   else f"split across {len(blocks)} sessions because no single gap is long enough" if blocks
                   else "no free gap before the deadline"),
        "_blocks": blocks,
    }


# ---------------------------------------------------------------- day plan
def day_events(conn, d: date):
    lo = datetime.combine(d, time(0, 0), tzinfo=IST)
    hi = lo + timedelta(days=1)
    out = []
    for row in conn.execute("SELECT * FROM events WHERE kind='fixed'"):
        for s, e in occurrences(row, lo, hi):
            out.append({"id": row["id"], "title": row["title"], "start": s, "end": e, "location": row["location"]})
    return sorted(out, key=lambda x: x["start"])


def build_plan(conn, d: date) -> dict:
    lo = datetime.combine(d, time(0, 0), tzinfo=IST)
    hi = lo + timedelta(days=1)
    slots = free_slots(conn, lo, hi, MIN_CHUNK)
    events = day_events(conn, d)
    departures = []
    if get_setting(conn, "home"):
        for ev in events:
            if ev["location"] and ev["end"] > now():
                dep = departure(conn, ev["start"], ev["location"])
                departures.append({"event_id": ev["id"], "title": ev["title"], **public(dep)})
    blocks, placed_ids, carry, no_fit = [], [], [], []
    ranked = priority_list(conn, 50)
    for task in ranked:
        need = task["unscheduled_minutes"]
        if need <= 0:
            continue
        dl = parse_dt(task["deadline"]) if task["deadline"] else None
        urgent = dl is not None and dl <= lo + timedelta(hours=48)
        got, placed = place_task(slots, need, dl, total_cap=None if urgent else MAX_CHUNK)
        for b in got:
            blocks.append({"task_id": task["id"], "title": task["title"], "start": iso(b["start"]),
                           "end": iso(b["end"]), "minutes": b["minutes"],
                           "reason": task["reason"]})
        if placed:
            placed_ids.append(task["id"])
        leftover = need - placed
        if leftover > 0 and urgent:
            later = free_slots(conn, hi, dl, MIN_CHUNK) if dl > hi else []
            later_free = sum(s["minutes"] for s in later)
            if later_free >= leftover:
                carry.append({"title": task["title"], "minutes": leftover,
                              "note": f"{say_minutes(leftover)} continues on a later day before the deadline"})
            else:
                short = leftover - later_free
                lower = [b for b in ranked if b["id"] in placed_ids and b["score"] < task["score"] and b["id"] != task["id"]]
                lower.sort(key=lambda x: x["score"])
                drop, freed = [], 0
                for cand in lower:
                    got_min = sum(b["minutes"] for b in blocks if b["task_id"] == cand["id"])
                    drop.append({"title": cand["title"], "minutes": got_min})
                    freed += got_min
                    if freed >= short:
                        break
                no_fit.append({"title": task["title"], "needed_minutes": need, "short_by_minutes": short,
                               "suggest_dropping": drop if freed >= short else drop,
                               "covers_gap": freed >= short,
                               "note": f"needs {say_minutes(need)}, but only {say_minutes(need - short)} is free before the deadline"})
    blocks.sort(key=lambda b: b["start"])
    return {"date": d.isoformat(), "blocks": blocks, "departures": departures,
            "carry_over": carry, "does_not_fit": no_fit}
