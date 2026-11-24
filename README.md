# DayPilot MCP

**Team The Latverians** · wHACKiest 2026 · Track 1: Make MCP Matter

A voice-first MCP server that plans your day. It finds real free time, fits tasks into it, works out
when to leave using travel time, and hands you a ride link at the right moment. **It never changes
anything until you confirm**, and every change can be undone. Designed first for people who can't rely
on a screen (blind and low-vision users), usable by anyone.

Any MCP client (Claude Desktop, Claude Code, Cursor, VS Code, MCP Inspector) can plug in.

## Why it is different

| | |
|---|---|
| **Propose, then confirm** | Every write tool returns a proposal. Only `confirm(proposal_id)` changes anything. |
| **Undo + audit log** | Each confirmed change is logged with its inverse. `undo_last_change()` reverses it. |
| **Server-side time math** | Durations, countdowns and free minutes are computed in code (IST) and returned as numbers. |
| **Spoken output** | Every tool returns a `spoken_summary` in plain sentences, ready for text-to-speech. |
| **Honest failure** | If a task does not fit, it says by how much and what lower-priority work could be dropped. |
| **Validated inputs** | Bad dates, durations and addresses return a clear message, not a guess. |
| **Accessibility profile** | `voice_first` adds wayfinding time (+10 min) for finding stops, crossings and entrances. |

## Quick start

```bash
git clone <this repo> && cd daypilot-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m daypilot.seed          # loads one realistic day in IST
python demo_run.py               # runs the whole demo flow in the terminal
pytest -q                        # 12 tests
```

Try it visually: `mcp dev daypilot/server.py` opens MCP Inspector.

### Connect Claude Desktop

Add to `claude_desktop_config.json` (use your absolute paths):

```json
{
  "mcpServers": {
    "daypilot": {
      "command": "/ABS/PATH/daypilot-mcp/.venv/bin/python",
      "args": ["-m", "daypilot.server"],
      "env": {
        "PYTHONPATH": "/ABS/PATH/daypilot-mcp",
        "MAPS_MODE": "mock",
        "ELEVENLABS_API_KEY": "",
        "NTFY_TOPIC": ""
      }
    }
  }
}
```

### Demo prompt

> I have a dentist appointment at 4, a report due tomorrow noon, and I want to hit the gym. Plan my day,
> and tell me what to drop if it does not fit.

The assistant chains `get_day_overview` → `get_free_slots` → `get_priority_list` → `propose_plan`,
reads the draft aloud, and waits. Then: *"When do I need to leave for the dentist?"* → `plan_departure`.
*"Confirm."* → `confirm`. *"Undo that."* → `undo_last_change`.

For repeatable rehearsals pin the clock: `DAYPILOT_NOW="2026-11-24 09:00"`.

## Tools (20)

**Read (run freely):** `get_day_overview`, `get_free_slots`, `get_priority_list`, `find_slot_for`,
`has_event`, `get_travel_time`, `plan_departure`, `prepare_ride`, `speak_morning_briefing`, `get_audit_log`

**Propose (write nothing):** `propose_plan`, `add_task`, `add_event`, `mark_done`, `set_home_location`,
`set_profile`, `import_calendar` (.ics), `set_departure_reminder`

**Commit:** `confirm`, `undo_last_change`

## Architecture

```
MCP client (Claude Desktop / Inspector / Cursor)
        │  MCP over stdio
        ▼
DayPilot server (FastMCP) ── engine: free slots · priorities · slot finder · two-pass leave-by
        │                       changes: propose → confirm → undo · audit log
        ├── SQLite (events, tasks, proposals, audit log, settings)
        ├── Google Routes API  (live travel time; mock fallback)
        ├── ElevenLabs         (spoken briefing audio)
        ├── ntfy               (phone reminder with ride link)
        └── Uber deep link     (user taps; DayPilot never books or charges)
```

## Status: what is tested and what is not

- **Tested (12 automated tests + stdio check):** free-slot maths, leave-by, priorities, propose/confirm/undo,
  double-confirm rejection, honest does-not-fit, input validation, `.ics` import, voice_first profile.
- **Written but not yet tested live:** Google Routes API calls, ElevenLabs audio, ntfy push, and the Uber
  link format. Each has a built-in fallback (mock travel times, text-only briefing, error message) so
  the demo still works if one fails. Test the ride link on a real phone before presenting.
- **Not in this prototype:** Google Calendar write-back (use `.ics` import), `replan_day`,
  Ola/Rapido prefilled links (the tool says so instead of guessing a format).

## Honest limits

- DayPilot sends reminders, not literal phone alarms.
- It hands off to ride apps; it never books or charges.
- Travel estimates do not know whether crossings or pavements are safe, and the tool says so.

## Roadmap

One engine, multiple accessibility profiles: deaf and hard-of-hearing (visual and haptic alerts, text
confirmations), wheelchair users (step-free routing), ADHD and cognitive support (one step at a time),
braille-ready daily plan export, Google Calendar write-back, `replan_day`, AWS hosting.

## Team

The Latverians: Aditya Garwad (lead), Pragya D Khanapur, Mohammed Ehsan, RIT Bengaluru.
