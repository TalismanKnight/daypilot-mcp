"""Tiny .ics reader: timed events only (all-day events are skipped)."""
import re
from datetime import datetime, timezone

from daypilot.timeutil import IST, iso
from zoneinfo import ZoneInfo


def _parse_stamp(params: str, value: str):
    value = value.strip()
    if "VALUE=DATE" in params and "T" not in value:
        return None  # all-day
    m = re.match(r"(\d{8})T(\d{6})(Z?)$", value)
    if not m:
        return None
    dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    if m.group(3) == "Z":
        return dt.replace(tzinfo=timezone.utc).astimezone(IST)
    tz = re.search(r"TZID=([^;:]+)", params)
    if tz:
        try:
            return dt.replace(tzinfo=ZoneInfo(tz.group(1))).astimezone(IST)
        except Exception:
            pass
    return dt.replace(tzinfo=IST)


def parse_ics(text: str):
    text = re.sub(r"\r?\n[ \t]", "", text)  # unfold long lines
    events, cur = [], None
    for line in text.splitlines():
        if line.startswith("BEGIN:VEVENT"):
            cur = {}
        elif line.startswith("END:VEVENT") and cur is not None:
            if cur.get("start") and cur.get("end") and cur["end"] > cur["start"]:
                events.append({"title": cur.get("title", "Untitled"), "start": iso(cur["start"]),
                               "end": iso(cur["end"]), "location": cur.get("location")})
            cur = None
        elif cur is not None and ":" in line:
            head, _, value = line.partition(":")
            name, _, params = head.partition(";")
            if name == "SUMMARY":
                cur["title"] = value.strip()
            elif name == "LOCATION":
                cur["location"] = value.replace("\\,", ",").strip() or None
            elif name == "DTSTART":
                cur["start"] = _parse_stamp(params, value)
            elif name == "DTEND":
                cur["end"] = _parse_stamp(params, value)
    return events
