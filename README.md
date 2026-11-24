# DayPilot MCP

**The Latverians | wHACKiest 2026 | Track 1: Make MCP Matter**

### Your day. Your pace. Your decisions.

DayPilot is an accessibility-first MCP assistant designed primarily for blind and low-vision users, while remaining usable by everyone. It combines everyday planning, mobility and payment assistance in a standalone web interface.

Users retain control over schedule changes and payment handoffs.

## The Problem

People with disabilities often face additional challenges when managing appointments, deadlines, transportation and everyday payments across multiple applications.

DayPilot aims to reduce these accessibility barriers by bringing essential everyday services together through the Model Context Protocol (MCP).

## Features

### Intelligent Daily Planning

- Daily schedule overview.
- Automatic free-time detection.
- Deadline-based task prioritization.
- Deterministic scheduling and time calculations in IST.
- Appointment and task management.
- Plan confirmation, undo and audit history.

### Accessibility

- Voice commands and spoken responses.
- ElevenLabs-powered daily briefings.
- High-contrast mode.
- Adjustable text size.
- ADHD focus mode.
- Text-based interaction for hearing-impaired users.
- Personalized travel buffers.
- Keyboard-accessible controls.

### Mobility Assistance

- Travel-time estimation.
- Personalized departure-time calculations.
- Additional wayfinding buffers.
- Uber ride-service handoff.
- Departure reminders.

### Accessible UPI Payment Assistant

- Recipient name, UPI ID and amount entry.
- Payment draft preparation.
- Spoken payment review.
- Explicit confirmation and cancellation.
- UPI ID format and amount validation.
- External UPI application handoff.
- Safe demonstration mode.

DayPilot never collects UPI PINs, directly transfers money or verifies banking transactions.

## Why DayPilot Is Different

| Feature | Description |
|---|---|
| Accessibility-first design | Designed around different accessibility needs. |
| Propose, then confirm | Planning changes and payment handoffs require explicit approval. |
| Undo and audit log | Confirmed planning changes are recorded and reversible. |
| Deterministic scheduling | Time calculations are performed in Python instead of relying on AI-generated estimates. |
| Spoken summaries | MCP tools return human-readable summaries suitable for speech output. |
| Everyday integrations | Combines planning, mobility and payment assistance. |
| Standalone application | No Claude account or general-purpose LLM required. |
| MCP interoperability | Compatible with external MCP clients. |
| Honest failure handling | Reports conflicts and limitations instead of inventing results. |

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend and scheduling engine |
| FastMCP | Model Context Protocol server |
| SQLite | Local database |
| HTML5 | Web interface structure |
| CSS3 | Responsive and accessible styling |
| JavaScript | User interaction |
| ElevenLabs | AI-powered spoken briefings |
| Browser Speech Recognition | Voice input |
| Google Routes API | Travel-time estimation |
| ntfy | Notification integration |
| Uber Deep Links | Ride-service handoff |
| UPI Intent Links | External payment handoff |
| GitHub | Version control |

## System Architecture

```
User
  |
  | Voice / Text / Accessible Controls
  v
DayPilot Web Interface
  |
  v
Python Web Bridge (localhost:8765)
  |
  | MCP over stdio
  v
DayPilot FastMCP Extended Server
  |
  +-- Scheduling Engine
  +-- Task Prioritization
  +-- Accessibility Preferences
  +-- Proposal and Confirmation Engine
  +-- Undo and Audit Log
  +-- UPI Payment Assistant
  |
  +-- SQLite Database
  +-- ElevenLabs Voice API
  +-- Google Routes API
  +-- ntfy Notifications
  +-- Uber Ride Handoff
  +-- External UPI Application
```

External MCP clients can also connect directly to the DayPilot server.

## Installation

### Prerequisites

- Python 3.11
- Git
- A modern web browser
- ElevenLabs API key (optional for text-only usage)
- Node.js (optional, for MCP Inspector)

### Windows Quick Start

Clone the repository:

```cmd
git clone https://github.com/TalismanKnight/daypilot-mcp.git
cd daypilot-mcp
```

Create a virtual environment:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```cmd
pip install -r requirements.txt
```

Load fresh demonstration data:

```cmd
python -m daypilot.seed
```

Launch DayPilot:

```cmd
python web_app.py
```

Open:

http://127.0.0.1:8765

No Claude connection is required.

Use the seed command only for a fresh demonstration database, not an existing personal database.

### macOS / Linux

Activate the virtual environment using:

```bash
source .venv/bin/activate
```

Follow the remaining installation steps above.

## ElevenLabs Configuration

Create a local `.env` file using `.env.example` as a reference.

Configure your ElevenLabs API key:

```env
ELEVENLABS_API_KEY=your_api_key_here
```

Without ElevenLabs configuration, text-based briefings remain available.

Never upload `.env`, API credentials, personal databases or private generated audio to GitHub.

## MCP Inspector

DayPilot can be tested independently using MCP Inspector.

With Node.js installed, run:

```cmd
npx @modelcontextprotocol/inspector python -m daypilot.payment_server
```

Connect the server and explore the available MCP tools.

The original planning server remains available through:

```cmd
python -m daypilot.server
```

## MCP Tools

The original DayPilot server contains 20 MCP tools. The V3 extended server registers three additional payment tools, bringing the total to 23 in the source code.

### Read and Utility Tools

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

### Planning Proposal Tools

- `propose_plan`
- `add_task`
- `add_event`
- `mark_done`
- `set_home_location`
- `set_profile`
- `import_calendar`
- `set_departure_reminder`

### Planning Confirmation and Recovery

- `confirm`
- `undo_last_change`

### Payment Tools

| Tool | Function |
|---|---|
| `prepare_payment` | Creates a validated payment draft and spoken review. |
| `confirm_payment_handoff` | Confirms the payment draft and prepares an external handoff. |
| `cancel_payment` | Cancels a pending payment draft. |

The standalone web interface exposes a selected subset of these tools.

## Example User Journey

### Daily Planning

1. The user requests their daily schedule.
2. DayPilot retrieves appointments and deadlines.
3. The scheduling engine calculates available time.
4. Tasks are ranked according to priority.
5. Travel time and accessibility buffers are considered.
6. A proposed schedule is presented.
7. The user confirms or rejects the proposal.
8. The confirmed plan is saved and logged.
9. The user can receive a spoken briefing or undo the planning change.

### Accessible Payment Assistance

1. The user enters the recipient name, UPI ID and amount.
2. DayPilot validates the payment information.
3. The payment details are presented through text or speech.
4. The user explicitly confirms or cancels the request.
5. In live handoff mode, DayPilot prepares a UPI intent link.
6. A compatible external payment application independently verifies and authorizes the actual payment.

DayPilot does not execute the financial transaction itself.

## Safe UPI Demonstration

To demonstrate the payment assistant without transferring real money:

1. Open the Accessible UPI Payment Assistant.
2. Select **Load safe demo example**.
3. Keep **Demo mode** enabled.
4. Select **Review payment**.
5. Select **Read payment aloud**.
6. Review the recipient, UPI ID and amount.
7. Select **Confirm payment handoff**.
8. Prepare another payment draft and demonstrate cancellation.

Demo mode does not generate a live payment link or transfer money.

## Payment Safety and Privacy

- Explicit confirmation is required before payment handoff.
- Payment drafts expire after ten minutes.
- Already handled payment drafts cannot be confirmed again.
- The prototype validates UPI ID format and payment amounts between ₹0.01 and ₹10,000.
- UPI ID format validation does not verify recipient identity or bank account ownership.
- DayPilot never collects UPI PINs or banking passwords.
- Financial authorization remains within the external payment application.
- DayPilot does not verify transaction completion.
- Planning undo cannot reverse financial transactions.
- Payment draft information is stored in the local SQLite database.
- Demonstrations should use fictional payment details.

## Accessibility Profiles

| Target users | Prototype support |
|---|---|
| Blind and visually impaired users | Spoken summaries, voice input and additional wayfinding time |
| Low-vision users | High contrast and adjustable text sizes |
| Deaf and hard-of-hearing users | Text-based interaction and visual information |
| Mobility-impaired users | Personalized travel buffers |
| ADHD and attention difficulties | Focus mode and task prioritization |
| Motor disabilities | Voice commands and reduced-input interaction |

These are initial accessibility features. Further testing with people with disabilities is required.

## Testing

Run the terminal demonstration:

```cmd
python demo_run.py
```

Run automated tests:

```cmd
pytest -q
```

The original backend includes 12 automated tests covering scheduling, free-time calculations, confirmation, undo, input validation and calendar import.

The team has exercised the V3 payment workflow through the standalone web interface. Automated payment tests and full extended-server MCP discovery testing remain pending.

## Prototype Status

### Implemented and Demonstrated

- Core scheduling engine.
- Task prioritization.
- Free-time calculations.
- Proposal, confirmation and undo.
- Original MCP server connectivity and discovery of 20 tools.
- Standalone V3 web application.
- ElevenLabs spoken briefings.
- Accessibility preferences.
- Safe UPI payment demonstration.

### Requires Further Testing

- Full discovery of all 23 extended-server MCP tools.
- Cross-device voice recognition.
- Screen-reader compatibility.
- Live Google Routes API requests.
- Phone notification delivery.
- Ride-service links on mobile devices.
- Live UPI handoff on compatible mobile devices.
- Accessibility testing with disability communities.

## Current Limitations

- The standalone interface currently uses predefined conversational commands rather than general-purpose LLM tool calling.
- Travel estimates cannot guarantee safe or step-free routes.
- Reminders are not guaranteed phone alarms.
- Ride-service handoff does not automatically book rides or charge users.
- Google Calendar write-back is not currently implemented. Calendar import uses `.ics` files.
- Actual payment authorization requires a compatible external UPI application.
- Accessibility features are not yet clinically validated or accessibility-certified.
- DayPilot is a localhost prototype, not a production payment service.

## Future Roadmap

- Flexible natural-language AI interaction.
- Regional-language voice assistance.
- Google Calendar and email integration.
- Dynamic schedule replanning.
- Improved accessible mobility information.
- Haptic notifications.
- Braille-ready schedule exports.
- Energy-aware scheduling.
- Mobile application.
- AWS cloud deployment.
- Further accessibility and security testing.

## Project Vision

DayPilot aims to make everyday activities more accessible, independent and manageable.

By combining planning, mobility and payment assistance through MCP, DayPilot demonstrates how technology can adapt to individual accessibility needs while keeping users in control.

**One MCP engine. Multiple accessibility needs. Complete user control.**

## Hackathon Details

| Detail | Information |
|---|---|
| Event | wHACKiest 2026 |
| Track | Track 1 — Make MCP Matter |
| Team | The Latverians |
| College | R.R. Institute of Technology, Bengaluru |
| Team ID | 5627b355 |
| Sponsor Technology | ElevenLabs |
| Prototype Version | V3 |

## Team Members

- Adity Garwad — Team Lead
- Pragya D Khanapur
- Mohammed Ehsan

---

**Built by The Latverians — Accessibility First.**

**DayPilot MCP — Your day. Your pace. Your decisions.**
