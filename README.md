# AEGIS MCP

**Accessible Everyday Guidance & Intelligent Support** — Intelligence without barriers.

**The Latverians | wHACKiest 2026 | Track 1: Make MCP Matter**

**Your day. Your pace. Your decisions.**

AEGIS is an accessibility-first MCP assistant designed primarily for blind and low-vision users, while remaining usable by everyone. It combines planning, mobility and payment review in a standalone local web interface. Users retain control over schedule changes and payment handoffs.

## Features

- Daily overview, free-slot detection, task ranking and deterministic IST scheduling.
- Proposed planning changes, explicit confirmation, undo and audit history.
- Travel estimates, personalized buffers and ride-app handoff.
- ElevenLabs spoken daily briefing, with text fallback.
- Browser voice input and spoken summaries, subject to browser support.
- High contrast, larger text, focus mode and accessibility preferences.
- UPI payment draft preparation, spoken review, confirmation and cancellation.
- Local web application that calls MCP tools without requiring Claude or a general-purpose LLM.

## Quick start (Windows)

The repository and Python package retain the original `daypilot` name for compatibility.

```cmd
git clone https://github.com/TalismanKnight/daypilot-mcp.git
cd daypilot-mcp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m daypilot.seed
python web_app.py
```

Use `daypilot.seed` for a fresh demonstration database, not an existing personal database. Open http://127.0.0.1:8765 if the browser does not open automatically.

For macOS/Linux, activate the virtual environment with `source .venv/bin/activate` instead.

### API configuration

Create a local `.env` using `.env.example` as a reference. Set `ELEVENLABS_API_KEY` for briefing audio. Use mock travel mode for reproducible demonstrations. Do not commit `.env`, private databases, generated personal audio, or API keys.

## Safe UPI demonstration

1. Open Accessible UPI payment assistant in the web interface.
2. Select **Load safe demo example**. Keep **Demo mode** enabled.
3. Select **Review payment**. Review the recipient, UPI ID and amount; select **Read payment aloud** for spoken review.
4. Select **Confirm payment handoff**. Demo mode produces no live link and moves no money.
5. Prepare another draft and select **Cancel payment**.

The payment extension validates the UPI ID format and amount (prototype range ₹0.01–₹10,000). Drafts expire after ten minutes; an already handled draft cannot be confirmed again. Validation does not verify a bank account or recipient identity. In non-demo mode, the server prepares a UPI intent link after confirmation; a compatible external payment application must independently verify and authorize any actual payment. Live handoff has not been verified. AEGIS never collects UPI PINs, transfers funds, or verifies transaction status. Planning undo cannot reverse a payment. Payment draft information is stored in the local SQLite database; demo users should use fictional details.

## MCP tools

The base server has 20 tools. The V3 extended server registers those tools plus three payment tools (23 in code). The web client exposes a selected subset.

**Read / utility:** `get_day_overview`, `get_free_slots`, `get_priority_list`, `find_slot_for`, `has_event`, `get_travel_time`, `plan_departure`, `prepare_ride`, `speak_morning_briefing`, `get_audit_log`.

**Planning proposals:** `propose_plan`, `add_task`, `add_event`, `mark_done`, `set_home_location`, `set_profile`, `import_calendar`, `set_departure_reminder`.

**Planning commit / recovery:** `confirm`, `undo_last_change`.

**Payment extension:**

| Tool | Function |
|---|---|
| `prepare_payment` | Create a validated payment draft and return a spoken review. |
| `confirm_payment_handoff` | Confirm the draft and prepare a handoff; no link in demo mode. |
| `cancel_payment` | Cancel a pending draft. |

### MCP Inspector

With Node.js installed, run:

```cmd
npx @modelcontextprotocol/inspector python -m daypilot.payment_server
```

The original planning server is still available as `python -m daypilot.server`. Other compatible MCP clients can use the extended module over stdio.

### Terminal demo and tests

```cmd
python demo_run.py
pytest -q
```

The original project includes planning tests. The added payment workflow has been exercised by the team through the web UI; automated payment tests and a fresh full 23-tool Inspector check are still pending.

## Architecture

```text
User (text / voice / accessible controls)
    |
Local HTML / CSS / JavaScript interface
    |
Python web bridge (localhost:8765)
    | MCP over stdio
FastMCP extended server (daypilot.payment_server)
    |-- Core planning tools (daypilot.server)
    |-- Payment review / confirmation / cancellation
    |-- SQLite: tasks, settings, proposals, audit, payment drafts
    |-- ElevenLabs: daily briefing audio
    |-- Google Routes: travel estimates / mock fallback
    |-- ICS import / ntfy reminders / Uber links
    +-- UPI intent link: external authorization only
```

## Accessibility and innovation

The goal is to reduce fragmented interactions across everyday services, not to replace assistive technology. AEGIS combines speech-friendly output, text alternatives, accessible controls and personalized scheduling buffers with reliable code-based calculations and user-controlled actions. These are prototype accessibility features, not a claim of certified accessibility or validated outcomes.

## Prototype status and limitations

- Demonstrated by the team: core MCP connectivity (20 original tools), planning, confirmation and undo, standalone web interface, ElevenLabs briefing and safe UPI demo.
- Further testing: full V3 tool discovery, cross-device speech recognition, screen readers, accessibility with disability communities, live Maps, push notifications, ride links and real-device UPI handoff.
- Voice/text commands are predefined; no general-purpose LLM tool calling in the standalone interface yet.
- Travel estimates cannot guarantee safe or step-free routes. Reminders are not guaranteed alarms. Ride links do not book or charge.
- Calendar import is via `.ics`; Google Calendar write-back is not implemented.
- This is a localhost prototype, not a production payment service.

## Roadmap

Accessible interaction testing, flexible natural-language MCP calls, regional-language speech, improved mobility information, calendar integration, dynamic replanning, haptic notifications, braille-ready exports and cloud deployment.

## Team

**The Latverians — R.R. Institute of Technology, Bengaluru**

- Adity Garwad (team lead)
- Pragya D Khanapur
- Mohammed Ehsan

wHACKiest 2026 | Track 1 — Make MCP Matter | Sponsor technology: ElevenLabs
