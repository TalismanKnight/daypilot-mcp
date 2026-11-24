"""All date and time handling. Everything is IST and computed in code, never by the assistant."""
import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now() -> datetime:
    """Current IST time. DAYPILOT_NOW pins the clock for rehearsals and tests."""
    override = os.environ.get("DAYPILOT_NOW")
    if override:
        return parse_dt(override)
    return datetime.now(IST).replace(microsecond=0)


def parse_dt(value) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Please give a date and time like 2026-11-24 16:00.")
    text = value.strip().replace("T", " ")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"I could not read '{value}' as a date and time. Use the form 2026-11-24 16:00.")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def parse_date(value=None) -> date:
    if value is None or str(value).strip().lower() in ("", "today"):
        return now().date()
    text = str(value).strip().lower()
    if text == "tomorrow":
        return now().date() + timedelta(days=1)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"I could not read '{value}' as a date. Use the form 2026-11-24, or say today or tomorrow.")


def say_time(dt: datetime) -> str:
    h = dt.hour % 12 or 12
    suffix = "AM" if dt.hour < 12 else "PM"
    return f"{h} {suffix}" if dt.minute == 0 else f"{h}:{dt.minute:02d} {suffix}"


def say_minutes(minutes) -> str:
    m = int(round(minutes))
    h, r = divmod(m, 60)
    parts = []
    if h:
        parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if r or not h:
        parts.append(f"{r} minute{'s' if r != 1 else ''}")
    return " ".join(parts)


def say_hours(hours: float) -> str:
    if hours < 1:
        return say_minutes(max(hours, 0) * 60)
    if hours < 48:
        return f"{round(hours)} hours"
    return f"{round(hours / 24)} days"


def say_day(d: date) -> str:
    today = now().date()
    if d == today:
        return "today"
    if d == today + timedelta(days=1):
        return "tomorrow"
    return d.strftime("%A %d %B")


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")
