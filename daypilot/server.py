"""DayPilot MCP server. Read tools run freely; write tools only return a proposal.
Nothing changes until confirm(proposal_id) is called. Every tool returns a spoken_summary."""
import functools
import urllib.parse
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from daypilot import changes, engine, ics, voice
from daypilot.db import connect
from daypilot.timeutil import (IST, iso, now, parse_date, parse_dt, say_day, say_hours,
                               say_minutes, say_time)

try:  # optional .env support
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

mcp = FastMCP("DayPilot")


def safe(fn):
    """Bad input returns a clear spoken error instead of a crash or a guess."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            return {"ok": False, "error": str(exc), "spoken_summary": f"That did not work. {exc}"}
    return wrapper


def _proposal(conn, ptype, summary, payload, preview, spoken):
    pid = changes.create_proposal(conn, ptype, summary, payload)
    return {"ok": True, "needs_confirmation": True, "proposal_id": pid, "preview": preview,
            "spoken_summary": f"{spoken} Nothing is saved yet. Say confirm to save it."}


def _clean(task_or_slot: dict) -> dict:
    return {k: v for k, v in task_or_slot.items() if not k.startswith("_")}


def _resolve_occurrence(conn, event_id: int, date=None):
    row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        raise ValueError(f"I could not find an event with id {event_id}.")
    if not row["location"]:
        raise ValueError(f"{row['title']} has no location, so there is no trip to plan.")
    if row["repeat"]:
        d = parse_date(date)
        lo = datetime.combine(d, time(0, 0), tzinfo=IST)
        occ = engine.occurrences(row, lo, lo + timedelta(days=1))
        if not occ:
            raise ValueError(f"{row['title']} does not happen on {d.isoformat()}.")
        start = occ[0][0]
    else:
        start = parse_dt(row["start"])
    return row, start


def _overview(conn, d) -> dict:
    lo = datetime.combine(d, time(0, 0), tzinfo=IST)
    hi = lo + timedelta(days=1)
    events = engine.day_events(conn, d)
    free = engine.free_slots(conn, lo, hi, 30)
    total_free = sum(s["minutes"] for s in free)
    ranked = engine.priority_list(conn, 50)
    due_soon = [t for t in ranked if t["due_in_hours"] is not None and 0 < t["due_in_hours"] <= 48]
    top = ranked[0] if ranked else None
    departures = []
    if engine.get_setting(conn, "home"):
        for ev in events:
            if ev["location"] and ev["end"] > now():
                dep = engine.departure(conn, ev["start"], ev["location"])
                departures.append({"event_id": ev["id"], "title": ev["title"], **engine.public(dep)})
    when = say_day(d)
    parts = []
    if events:
        listing = ", ".join(f"{e['title']} at {say_time(e['start'])}" for e in events)
        parts.append(f"For {when} you have {len(events)} event{'s' if len(events) != 1 else ''}: {listing}.")
    else:
        parts.append(f"For {when} you have no fixed events.")
    for dep in departures:
        parts.append(f"Leave by {say_time(parse_dt(dep['leave_by']))} for {dep['title']}, "
                     f"{say_minutes(dep['travel_minutes'])} of travel plus {say_minutes(dep['buffer_minutes'])} buffer.")
    if due_soon:
        parts.append("Due soon: " + ", ".join(f"{t['title']} in {say_hours(t['due_in_hours'])}" for t in due_soon) + ".")
    parts.append(f"You have {say_minutes(total_free)} of free time.")
    if top:
        parts.append(f"Your top priority is {top['title']}: {top['reason']}.")
    return {"date": d.isoformat(), "events": [{"id": e["id"], "title": e["title"], "start": iso(e["start"]),
                                                "end": iso(e["end"]), "location": e["location"]} for e in events],
            "departures": departures, "tasks_due_soon": due_soon, "total_free_minutes": total_free,
            "free_slots": [{"start": iso(s["start"]), "end": iso(s["end"]), "minutes": s["minutes"]} for s in free],
            "top_priority": top, "spoken_summary": " ".join(parts)}


# ============================================================ READ TOOLS
@mcp.tool()
@safe
def get_day_overview(date: str | None = None) -> dict:
    """Get a day's events, leave-by times, tasks due soon, free time and top priority in one call."""
    conn = connect()
    return _overview(conn, parse_date(date))


@mcp.tool()
@safe
def get_free_slots(start_date: str | None = None, end_date: str | None = None, min_minutes: int = 30) -> dict:
    """List exact free time slots, in minutes, after events, routines, planned work and travel."""
    if not 5 <= min_minutes <= 480:
        raise ValueError("min_minutes must be between 5 and 480.")
    conn = connect()
    d1 = parse_date(start_date)
    d2 = parse_date(end_date) if end_date else d1
    if d2 < d1 or (d2 - d1).days > 14:
        raise ValueError("The date range must run forward and cover at most 14 days.")
    lo = datetime.combine(d1, time(0, 0), tzinfo=IST)
    hi = datetime.combine(d2, time(0, 0), tzinfo=IST) + timedelta(days=1)
    slots = engine.free_slots(conn, lo, hi, min_minutes)
    total = sum(s["minutes"] for s in slots)
    out = [{"start": iso(s["start"]), "end": iso(s["end"]), "minutes": s["minutes"]} for s in slots]
    if slots:
        listing = "; ".join(f"{say_time(s['start'])} to {say_time(s['end'])}" for s in slots[:5])
        spoken = f"You have {say_minutes(total)} free in {len(slots)} gap{'s' if len(slots) != 1 else ''}. " + \
                 (f"The first ones are {listing}." if d1 == d2 else "")
    else:
        spoken = "You have no free gaps of that length in that range."
    return {"slots": out, "total_free_minutes": total, "spoken_summary": spoken}


@mcp.tool()
@safe
def get_priority_list(limit: int = 5) -> dict:
    """Rank unfinished tasks by urgency and importance, with a plain-language reason for each."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")
    conn = connect()
    ranked = engine.priority_list(conn, limit)
    if not ranked:
        return {"tasks": [], "spoken_summary": "You have no unfinished tasks."}
    spoken = " ".join(f"Number {i + 1}: {t['title']}, {t['reason']}." for i, t in enumerate(ranked[:3]))
    return {"tasks": ranked, "spoken_summary": spoken}


@mcp.tool()
@safe
def find_slot_for(task: str) -> dict:
    """Find the best free slot before a task's deadline, split across days if needed, or say honestly it does not fit."""
    conn = connect()
    row = (conn.execute("SELECT * FROM tasks WHERE id=?", (int(task),)).fetchone() if task.strip().isdigit()
           else conn.execute("SELECT * FROM tasks WHERE lower(title) LIKE ? AND status != 'done'",
                             (f"%{task.strip().lower()}%",)).fetchone())
    if not row:
        raise ValueError(f"I could not find a task matching '{task}'.")
    res = engine.find_slot_for(conn, row)
    if res["fits"]:
        listing = " and ".join(f"{say_time(parse_dt(b['start']))} to {say_time(parse_dt(b['end']))} on "
                               f"{say_day(parse_dt(b['start']).date())}" for b in res["blocks"])
        spoken = f"{res['task']} fits: {listing}. Reason: {res['reason']}."
    else:
        spoken = (f"{res['task']} does not fit. It needs {say_minutes(res['needed_minutes'])} but only "
                  f"{say_minutes(res['total_free_minutes_before_deadline'])} is free before the deadline, "
                  f"short by {say_minutes(res['shortfall_minutes'])}.")
    res = _clean(res)
    res["spoken_summary"] = spoken
    return res


@mcp.tool()
@safe
def has_event(title: str, date: str | None = None) -> dict:
    """Answer yes or no, with time and place, to questions like do I have a dentist appointment today."""
    if not title.strip():
        raise ValueError("Tell me which event to look for.")
    conn = connect()
    d = parse_date(date)
    hits = [e for e in engine.day_events(conn, d) if title.strip().lower() in e["title"].lower()]
    if not hits:
        return {"found": False, "spoken_summary": f"No, you have no {title} on {say_day(d)}."}
    e = hits[0]
    where = f" at {e['location']}" if e["location"] else ""
    return {"found": True, "event": {"id": e["id"], "title": e["title"], "start": iso(e["start"]),
                                     "end": iso(e["end"]), "location": e["location"]},
            "spoken_summary": f"Yes, {e['title']} is {say_day(d)} at {say_time(e['start'])}{where}."}


@mcp.tool()
@safe
def get_travel_time(origin: str, destination: str, depart_at: str | None = None,
                    mode: Literal["drive", "transit", "walk", "bicycle"] = "transit") -> dict:
    """Get travel duration and distance between two places by drive, transit, walk or bicycle."""
    when = parse_dt(depart_at) if depart_at else now()
    res = engine.maps.get_travel(origin.strip(), destination.strip(), when, mode)
    return {**res, "mode": mode, "spoken_summary":
            f"By {mode} it takes about {say_minutes(res['duration_min'])}, {res['distance_km']} kilometres. "
            f"I cannot check whether crossings or pavements on the way are safe."}


@mcp.tool()
@safe
def plan_departure(event_id: int, buffer_min: int | None = None,
                   mode: Literal["drive", "transit", "walk", "bicycle"] | None = None,
                   date: str | None = None) -> dict:
    """Work out when to leave for an event: arrival time minus travel time minus a safety buffer."""
    conn = connect()
    row, start = _resolve_occurrence(conn, event_id, date)
    dep = engine.departure(conn, start, row["location"], buffer_min, mode)
    extra = " This profile adds extra time for finding stops and entrances." if dep["profile"] == "voice_first" else ""
    dep = engine.public(dep)
    dep["spoken_summary"] = (f"Leave by {say_time(parse_dt(dep['leave_by']))} for {row['title']} at "
                             f"{say_time(parse_dt(dep['arrive_by']))}. Travel is {say_minutes(dep['travel_minutes'])} "
                             f"by {dep['mode']}, plus {say_minutes(dep['buffer_minutes'])} buffer.{extra}")
    return dep


@mcp.tool()
@safe
def prepare_ride(event_id: int, provider: Literal["uber", "ola", "rapido"] = "uber", date: str | None = None) -> dict:
    """Build a one-tap ride link for an event; DayPilot never books or charges."""
    conn = connect()
    row, start = _resolve_occurrence(conn, event_id, date)
    dep = engine.departure(conn, start, row["location"])
    leave = say_time(dep["_leave_dt"])
    if provider == "uber":
        link = ("https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]="
                + urllib.parse.quote(row["location"], safe=""))
        note = "Tap the link to open Uber with the destination filled in. You confirm and pay inside the app."
    else:
        link = None
        note = (f"Open the {provider.title()} app and enter this destination: {row['location']}. "
                "A prefilled link for this provider is not set up yet.")
    return {"provider": provider, "link": link, "destination": row["location"], "leave_by": iso(dep["_leave_dt"]),
            "note": note, "spoken_summary": f"Your {provider.title()} ride to {row['title']} is ready for "
            f"{leave}. {note}"}


@mcp.tool()
@safe
def speak_morning_briefing(date: str | None = None) -> dict:
    """Turn the day overview into a spoken audio briefing using ElevenLabs."""
    conn = connect()
    overview = _overview(conn, parse_date(date))
    text = "Good morning. " + overview["spoken_summary"]
    audio = voice.synthesize(text)
    return {"briefing_text": text, "audio_path": audio["audio_path"], "voice_note": audio["note"],
            "spoken_summary": text}


@mcp.tool()
@safe
def get_audit_log(limit: int = 10) -> dict:
    """List the most recent confirmed changes, so the user can ask what was changed."""
    conn = connect()
    log = changes.audit_log(conn, max(1, min(limit, 50)))
    if not log:
        return {"entries": [], "spoken_summary": "No changes have been made yet."}
    spoken = "Recent changes: " + "; ".join(
        f"{e['detail']}{' (undone)' if e['undone'] else ''}" for e in log[:5]) + "."
    return {"entries": log, "spoken_summary": spoken}


# ============================================================ PROPOSE TOOLS (write nothing)
@mcp.tool()
@safe
def propose_plan(date: str | None = None) -> dict:
    """Draft a plan for a day with reasons and leave-by times; this writes nothing until confirmed."""
    conn = connect()
    d = parse_date(date)
    plan = engine.build_plan(conn, d)
    parts = [f"Here is a draft plan for {say_day(d)}."]
    for b in plan["blocks"]:
        parts.append(f"{b['title']} from {say_time(parse_dt(b['start']))} to {say_time(parse_dt(b['end']))}.")
    for dep in plan["departures"]:
        parts.append(f"Leave by {say_time(parse_dt(dep['leave_by']))} for {dep['title']}.")
    for c in plan["carry_over"]:
        parts.append(f"{c['title']}: {c['note']}.")
    for n in plan["does_not_fit"]:
        drop = ", ".join(f"{x['title']} ({say_minutes(x['minutes'])})" for x in n["suggest_dropping"])
        parts.append(f"{n['title']} does not fully fit: {n['note']}." +
                     (f" To make room, drop or move {drop}." if drop else " There is nothing lower priority to drop."))
    if not plan["blocks"] and not plan["departures"]:
        parts.append("There is nothing to schedule.")
    return _proposal(conn, "plan", f"Plan for {d.isoformat()}", plan, plan, " ".join(parts))


@mcp.tool()
@safe
def add_task(title: str, est_minutes: int, deadline: str | None = None,
             priority: Literal["low", "normal", "high"] = "normal") -> dict:
    """Propose adding a flexible task with a time estimate and optional deadline."""
    if not title.strip() or len(title) > 120:
        raise ValueError("A task needs a title of up to 120 characters.")
    if not 5 <= est_minutes <= 960:
        raise ValueError("The estimate must be between 5 minutes and 16 hours.")
    dl = parse_dt(deadline) if deadline else None
    if dl and dl <= now():
        raise ValueError("That deadline is already in the past.")
    conn = connect()
    payload = {"title": title.strip(), "est_minutes": est_minutes, "deadline": iso(dl) if dl else None,
               "priority": engine.PRIORITY[priority]}
    when = f", due {say_day(dl.date())} at {say_time(dl)}" if dl else ""
    return _proposal(conn, "add_task", f"Add task {title.strip()}", payload, payload,
                     f"I can add {title.strip()}, {say_minutes(est_minutes)}{when}, {priority} priority.")


@mcp.tool()
@safe
def add_event(title: str, start: str, end: str, location: str | None = None,
              repeat: Literal["daily", "weekdays", "weekly"] | None = None) -> dict:
    """Propose adding a fixed event or repeating routine, with an optional location."""
    if not title.strip():
        raise ValueError("An event needs a title.")
    s, e = parse_dt(start), parse_dt(end)
    if e <= s:
        raise ValueError("The end time must be after the start time.")
    conn = connect()
    payload = {"title": title.strip(), "start": iso(s), "end": iso(e), "location": location, "repeat": repeat,
               "kind": "routine" if repeat else "fixed"}
    return _proposal(conn, "add_event", f"Add event {title.strip()}", payload, payload,
                     f"I can add {title.strip()} on {say_day(s.date())} from {say_time(s)} to {say_time(e)}.")


@mcp.tool()
@safe
def mark_done(task_id: int, minutes: int | None = None) -> dict:
    """Propose logging work on a task, or marking it fully done when minutes is left out."""
    conn = connect()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        raise ValueError(f"I could not find a task with id {task_id}.")
    if minutes is not None and not 1 <= minutes <= 960:
        raise ValueError("Minutes must be between 1 and 960.")
    what = "mark it done" if minutes is None else f"log {say_minutes(minutes)}"
    return _proposal(conn, "mark_done", f"Update task {row['title']}", {"task_id": task_id, "minutes": minutes},
                     {"task": row["title"]}, f"I can {what} on {row['title']}.")


@mcp.tool()
@safe
def set_home_location(address: str) -> dict:
    """Propose saving the default starting point used for travel time."""
    if len(address.strip()) < 5:
        raise ValueError("Please give a fuller address so travel time is accurate.")
    conn = connect()
    return _proposal(conn, "set_setting", "Set home location",
                     {"key": "home", "value": address.strip(), "spoken": f"Home is now {address.strip()}."},
                     {"home": address.strip()}, f"I can set your home to {address.strip()}.")


@mcp.tool()
@safe
def set_profile(profile: Literal["standard", "voice_first"]) -> dict:
    """Propose switching the accessibility profile; voice_first adds wayfinding time to every trip."""
    conn = connect()
    text = ("voice first, which adds extra minutes for finding stops, crossings and entrances"
            if profile == "voice_first" else "standard")
    return _proposal(conn, "set_setting", f"Set profile {profile}",
                     {"key": "profile", "value": profile, "spoken": f"Profile is now {text}."},
                     {"profile": profile}, f"I can switch to the {text} profile.")


@mcp.tool()
@safe
def import_calendar(source: str) -> dict:
    """Propose importing timed events from an .ics calendar file path."""
    if source.strip().lower() in ("google", "google calendar"):
        raise ValueError("Google Calendar sync is not in this prototype yet. Export an .ics file and give me its path.")
    path = Path(source.strip()).expanduser()
    if path.suffix.lower() != ".ics" or not path.is_file():
        raise ValueError("Give me the path to an existing .ics file.")
    events = ics.parse_ics(path.read_text(encoding="utf-8", errors="ignore"))
    if not events:
        raise ValueError("I found no timed events in that file.")
    conn = connect()
    return _proposal(conn, "import_events", f"Import {len(events)} events", {"events": events},
                     {"count": len(events), "first": events[:3]}, f"I found {len(events)} events to import.")


@mcp.tool()
@safe
def set_departure_reminder(event_id: int, date: str | None = None) -> dict:
    """Propose a phone push reminder, with the ride link, shortly before the leave-by time."""
    conn = connect()
    row, start = _resolve_occurrence(conn, event_id, date)
    dep = engine.departure(conn, start, row["location"])
    at = dep["_leave_dt"] - timedelta(minutes=10)
    if at <= now():
        raise ValueError("The leave-by time for that event has already passed.")
    link = "https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]=" + \
           urllib.parse.quote(row["location"], safe="")
    payload = {"title": f"Leave soon for {row['title']}", "at": iso(at), "click_url": link,
               "message": f"Leave by {say_time(dep['_leave_dt'])} for {row['title']}. Tap to open your ride."}
    return _proposal(conn, "reminder", f"Reminder for {row['title']}", payload, payload,
                     f"I can send a phone reminder at {say_time(at)}, ten minutes before you need to leave.")


# ============================================================ COMMIT AND UNDO
@mcp.tool()
@safe
def confirm(proposal_id: str) -> dict:
    """Commit a proposal the user has approved; this is the only tool that changes anything."""
    return changes.confirm(connect(), proposal_id.strip())


@mcp.tool()
@safe
def undo_last_change() -> dict:
    """Reverse the most recent confirmed change."""
    return changes.undo_last(connect())


if __name__ == "__main__":
    mcp.run()
