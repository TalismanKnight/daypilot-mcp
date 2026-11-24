# DayPilot MCP

**Team The Latverians | wHACKiest 2026 | Track 1: Make MCP Matter**

### Your day. Your pace. Your decisions.

DayPilot is an accessibility-first, MCP-powered intelligent daily planning assistant designed primarily for people with disabilities, especially blind and low-vision users, while remaining usable by everyone.

It connects everyday scheduling, task management, travel planning and voice assistance into a single, user-controlled experience.

**Nothing is committed without explicit user confirmation, and confirmed planning changes can be undone.**

## The Problem

Managing everyday activities often requires switching between multiple applications, including calendars, task managers, navigation services and transportation platforms.

For people with disabilities, fragmented and visually dependent interfaces can introduce additional accessibility barriers.

DayPilot aims to simplify this experience through accessible interaction, personalized planning and controlled MCP integrations.

## Key Features

- Intelligent daily scheduling.
- Automatic free-time detection.
- Deadline-based task prioritization.
- Voice commands and spoken responses.
- ElevenLabs-powered daily briefings.
- Personalized departure-time calculations.
- Travel assistance and Uber ride handoff.
- Appointment management.
- Explicit confirmation before committing planning changes.
- Undo functionality and audit logs.
- Standalone accessible web dashboard.
- 20 MCP tools.

## Accessibility First

| Accessibility need | Prototype support |
|---|---|
| Blind and low-vision | Voice interaction, spoken summaries and additional wayfinding time |
| Hearing impairment | Text-based interaction and visual information |
| Mobility impairment | Personalized travel buffers |
| ADHD and attention difficulties | Focus mode and task prioritization |
| Low vision | High-contrast interface and adjustable text size |
| Motor difficulties | Voice commands and reduced-input interactions |

These are initial accessibility features. Further testing with people with disabilities is planned.

## Why DayPilot Is Different

| Feature | Description |
|---|---|
| Propose, then confirm | Planning changes require explicit approval before being committed. |
| Undo and audit log | Confirmed changes are recorded and reversible. |
| Deterministic time calculations | Scheduling, countdowns and durations are calculated in Python rather than guessed by an AI model. |
| Spoken summaries | MCP tools return human-readable responses suitable for speech output. |
| Honest failure | Reports scheduling conflicts instead of inventing available time. |
| Accessibility profiles | Allows interaction and planning preferences to be adapted to individual needs. |
| Standalone interface | Operates without requiring Claude or another external AI assistant. |
| MCP interoperability | Compatible with external MCP clients. |

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend and scheduling logic |
| FastMCP | Model Context Protocol server |
| SQLite | Local storage |
| HTML, CSS, JavaScript | Accessible web interface |
| ElevenLabs | AI-powered briefing audio |
| Browser Speech Recognition | Voice input where supported |
| Google Routes API | Travel-time estimation |
| ntfy | Notification integration |
| Uber Deep Links | Ride-service handoff |
| GitHub | Version control |

## Quick Start

### Windows

Clone the repository:

`git clone https://github.com/TalismanKnight/daypilot-mcp.git`

`cd daypilot-mcp`

Install dependencies:

`pip install -r requirements.txt`

Load demonstration data:

`python -m daypilot.seed`

Launch the standalone application:

`python web_app.py`

Open the following address in your browser:

http://127.0.0.1:8765

No Claude connection is required.

### ElevenLabs Configuration

Create a local `.env` file using `.env.example` as a reference.

Set `ELEVENLABS_API_KEY` to your own API key.

Never commit your `.env` file or private API credentials to GitHub.

Without ElevenLabs configuration, text-based briefings remain available.

## MCP Inspector

DayPilot can also be tested independently using MCP Inspector.

Run:

`npx @modelcontextprotocol/inspector python -m daypilot.server`

Connect the server and select any available MCP tool.

Node.js is required for MCP Inspector.

## Terminal Demonstration

Run:

`python demo_run.py`

Run automated tests:

`pytest -q`

For repeatable demonstrations, the clock can be pinned using the `DAYPILOT_NOW` environment variable.

## Example User Journey

1. The user asks DayPilot to plan their day.
2. DayPilot retrieves appointments and deadlines.
3. The scheduling engine calculates available time.
4. Tasks are prioritized and fitted into available slots.
5. Travel time and accessibility buffers are considered.
6. DayPilot presents a proposed schedule.
7. The user confirms or rejects the proposal.
8. The confirmed plan is saved and recorded.
9. The user can receive a spoken briefing or undo the change.

## MCP Tools (20)

### Read Tools

- `get_day_overview`
- `get_free_slots`
- `get_priority_list`
- `find_slot_for`
- `has_event`
- `get_travel_time`
- `plan_departure`
- `prepare_ride`
- `speak_morning_briefing`
- `get_audit_log`

### Proposal Tools

- `propose_plan`
- `add_task`
- `add_event`
- `mark_done`
- `set_home_location`
- `set_profile`
- `import_calendar`
- `set_departure_reminder`

### Commit and Recovery

- `confirm`
- `undo_last_change`

## System Architecture

```
User
  |
  | Voice / Text / Accessible Controls
  v
DayPilot Web Interface
  |
  v
Local MCP Client
  |
  | MCP over stdio
  v
DayPilot FastMCP Server
  |
  +-- Scheduling Engine
  +-- Accessibility Preferences
  +-- Proposal and Confirmation Engine
  +-- Undo and Audit Log
  |
  +-- SQLite Database
  +-- ElevenLabs Voice API
  +-- Google Routes API
  +-- ntfy Notifications
  +-- Uber Ride Handoff
```

External MCP clients can also connect directly to the DayPilot server.

## Prototype Status

### Implemented and demonstrated

- Core scheduling engine.
- Task prioritization.
- Free-time calculations.
- Proposal, confirmation and undo.
- MCP server connectivity.
- Discovery of all 20 MCP tools.
- Standalone web application.
- ElevenLabs briefing integration.
- Accessibility controls and preferences.

### Requires Further Testing

- Browser voice recognition across different devices.
- Live Google Routes API requests.
- Phone notification delivery.
- Ride deep links on mobile devices.
- Screen-reader compatibility and accessibility testing with actual users.

### Current Limitations

- The web prototype uses predefined conversational commands rather than a general-purpose LLM.
- Travel estimates cannot guarantee safe or step-free routes.
- DayPilot hands users off to ride applications and never books rides or charges users.
- Notifications are reminders, not guaranteed phone alarms.
- Google Calendar write-back is not currently implemented. Calendar import uses `.ics` files.
- Accessibility preferences are early prototype features, not fully validated assistive technology.

## Future Roadmap

- Natural-language AI assistant with MCP tool calling.
- Google Calendar and email integration.
- Dynamic schedule replanning.
- Regional-language voice assistance.
- Verified accessible transit and step-free navigation information.
- Haptic notifications.
- Braille-ready schedule exports.
- Energy-aware scheduling.
- Mobile application.
- AWS cloud deployment.
- User testing with disability communities.

## Vision

DayPilot aims to make everyday planning more independent, accessible and manageable.

One MCP engine. Multiple accessibility needs. The user remains in control.

## Hackathon

**Event:** wHACKiest 2026

**Track:** Track 1 — Make MCP Matter

**Team:** The Latverians

**College:** R.R. Institute of Technology, Bengaluru

**Sponsor Technology:** ElevenLabs

## Team Members

- Adity Garwad — Team Lead
- Pragya D Khanapur
- Mohammed Ehsan

**Built by The Latverians — Accessibility First.**
