import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("DAYPILOT_NOW", "2026-11-24 09:00")
    monkeypatch.setenv("DAYPILOT_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("MAPS_MODE", "mock")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    from daypilot import seed
    seed.seed()


def call(name, **args):
    from daypilot.server import mcp
    res = asyncio.run(mcp.call_tool(name, args))
    content = res[0] if isinstance(res, tuple) else res
    return json.loads(content[0].text)


def test_free_slots_match_hand_calculation():
    # 09:00-11:00, 12:00-13:00, 13:45-15:05 (travel starts 15:05), 17:00-20:00, 20:45-22:00
    r = call("get_free_slots")
    assert [s["minutes"] for s in r["slots"]] == [120, 60, 80, 180, 75]
    assert r["total_free_minutes"] == 515


def test_leave_by_is_arrival_minus_travel_minus_buffer():
    r = call("plan_departure", event_id=5)
    assert r["leave_by"] == "2026-11-24 15:05"          # 16:00 - 40 travel - 15 buffer
    assert r["total_minutes_before_event"] == 55


def test_voice_first_profile_adds_wayfinding_time():
    p = call("set_profile", profile="voice_first")
    call("confirm", proposal_id=p["proposal_id"])
    r = call("plan_departure", event_id=5)
    assert r["buffer_minutes"] == 25 and r["leave_by"] == "2026-11-24 14:55"


def test_nothing_is_written_until_confirm():
    before = call("get_free_slots")["total_free_minutes"]
    call("propose_plan")
    assert call("get_free_slots")["total_free_minutes"] == before


def test_confirm_then_undo_restores_everything():
    before = call("get_free_slots")["total_free_minutes"]
    p = call("propose_plan")
    call("confirm", proposal_id=p["proposal_id"])
    assert call("get_free_slots")["total_free_minutes"] < before
    call("undo_last_change")
    assert call("get_free_slots")["total_free_minutes"] == before


def test_proposal_cannot_be_confirmed_twice():
    p = call("propose_plan")
    call("confirm", proposal_id=p["proposal_id"])
    again = call("confirm", proposal_id=p["proposal_id"])
    assert again["ok"] is False and "already" in again["error"]


def test_honest_does_not_fit_with_what_to_drop():
    # 20h of work due at 12:00 tomorrow cannot fit; the tool must say so, not guess
    p = call("add_task", title="Thesis draft", est_minutes=960, deadline="2026-11-25 12:00", priority="high")
    call("confirm", proposal_id=p["proposal_id"])
    plan = call("propose_plan")
    assert plan["preview"]["does_not_fit"], plan["spoken_summary"]
    assert "does not fully fit" in plan["spoken_summary"]


def test_bad_input_returns_clear_errors():
    assert call("add_task", title="x", est_minutes=1)["ok"] is False
    assert call("add_task", title="x", est_minutes=60, deadline="2020-01-01 10:00")["ok"] is False
    assert call("add_event", title="x", start="2026-11-24 10:00", end="2026-11-24 09:00")["ok"] is False
    assert call("get_free_slots", min_minutes=1)["ok"] is False
    assert call("get_day_overview", date="not-a-date")["ok"] is False


def test_has_event():
    assert call("has_event", title="dentist")["found"] is True
    assert call("has_event", title="gym class")["found"] is False


def test_every_tool_result_has_spoken_summary():
    for name, args in [("get_day_overview", {}), ("get_free_slots", {}), ("get_priority_list", {}),
                       ("find_slot_for", {"task": "Project report"}), ("get_audit_log", {}),
                       ("get_travel_time", {"origin": "MSR Nagar", "destination": "Jayanagar", "mode": "walk"})]:
        assert call(name, **args)["spoken_summary"], name


def test_ics_import(tmp_path):
    f = tmp_path / "c.ics"
    f.write_text("BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Lab viva\nDTSTART:20261125T043000Z\n"
                 "DTEND:20261125T053000Z\nLOCATION:RIT\\, Bengaluru\nEND:VEVENT\nEND:VCALENDAR\n")
    p = call("import_calendar", source=str(f))
    call("confirm", proposal_id=p["proposal_id"])
    r = call("has_event", title="viva", date="2026-11-25")
    assert r["found"] and r["event"]["start"] == "2026-11-25 10:00"   # 04:30Z = 10:00 IST


def test_voice_without_key_is_honest():
    r = call("speak_morning_briefing")
    assert r["audio_path"] is None and "not configured" in r["voice_note"]
