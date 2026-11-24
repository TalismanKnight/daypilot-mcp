"""Propose -> confirm -> undo. Nothing is written to the planner without a confirmed proposal."""
import json
import uuid
from datetime import datetime

from daypilot import notify
from daypilot.timeutil import now, parse_dt, iso, say_time, say_minutes


def create_proposal(conn, ptype: str, summary: str, payload: dict) -> str:
    pid = "p_" + uuid.uuid4().hex[:6]
    conn.execute("INSERT INTO proposals(id, created_at, type, summary, payload, status) VALUES (?,?,?,?,?, 'pending')",
                 (pid, now().isoformat(), ptype, summary, json.dumps(payload)))
    conn.commit()
    return pid


# ------------------------------------------------------------ apply functions: return (inverse, spoken)
def _add_task(conn, p):
    cur = conn.execute("INSERT INTO tasks(title, est_minutes, deadline, priority) VALUES (?,?,?,?)",
                       (p["title"], p["est_minutes"], p["deadline"], p["priority"]))
    return {"delete_tasks": [cur.lastrowid]}, f"Saved the task {p['title']}."


def _add_event(conn, p):
    cur = conn.execute("INSERT INTO events(title, start, end, location, kind, repeat) VALUES (?,?,?,?,?,?)",
                       (p["title"], p["start"], p["end"], p.get("location"), p.get("kind", "fixed"), p.get("repeat")))
    return {"delete_events": [cur.lastrowid]}, f"Saved the event {p['title']}."


def _plan(conn, p):
    ids = []
    for b in p["blocks"]:
        cur = conn.execute("INSERT INTO events(title, start, end, kind, task_id) VALUES (?,?,?, 'task_block', ?)",
                           (f"Work: {b['title']}", b["start"], b["end"], b["task_id"]))
        ids.append(cur.lastrowid)
    for d in p["departures"]:
        cur = conn.execute("INSERT INTO events(title, start, end, location, kind) VALUES (?,?,?,?, 'travel')",
                           (f"Travel to {d['title']}", d["leave_by"], d["arrive_by"], d["destination"]))
        ids.append(cur.lastrowid)
    return {"delete_events": ids}, f"Saved the plan: {len(p['blocks'])} work blocks and {len(p['departures'])} travel blocks."


def _mark_done(conn, p):
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (p["task_id"],)).fetchone()
    if not row:
        raise ValueError("That task no longer exists.")
    inverse = {"restore_tasks": [{"id": row["id"], "done_minutes": row["done_minutes"], "status": row["status"]}]}
    done = row["est_minutes"] if p["minutes"] is None else min(row["done_minutes"] + p["minutes"], row["est_minutes"])
    status = "done" if done >= row["est_minutes"] else "todo"
    conn.execute("UPDATE tasks SET done_minutes=?, status=? WHERE id=?", (done, status, row["id"]))
    return inverse, f"Updated {row['title']}. " + ("It is now marked done." if status == "done" else f"{say_minutes(done)} logged so far.")


def _set_setting(conn, p):
    old = conn.execute("SELECT value FROM settings WHERE key=?", (p["key"],)).fetchone()
    conn.execute("INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (p["key"], p["value"]))
    return {"restore_settings": {p["key"]: old["value"] if old else None}}, p["spoken"]


def _import_events(conn, p):
    ids = []
    for e in p["events"]:
        cur = conn.execute("INSERT INTO events(title, start, end, location, kind) VALUES (?,?,?,?, 'fixed')",
                           (e["title"], e["start"], e["end"], e.get("location")))
        ids.append(cur.lastrowid)
    return {"delete_events": ids}, f"Imported {len(ids)} events."


def _reminder(conn, p):
    notify.send_push(p["title"], p["message"], parse_dt(p["at"]), p.get("click_url"))
    return {"noop": "A phone push that is already scheduled cannot be recalled from here."}, \
        f"Scheduled the phone reminder for {say_time(parse_dt(p['at']))}."


APPLY = {"add_task": _add_task, "add_event": _add_event, "plan": _plan, "mark_done": _mark_done,
         "set_setting": _set_setting, "import_events": _import_events, "reminder": _reminder}


def confirm(conn, proposal_id: str) -> dict:
    row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
    if not row:
        raise ValueError(f"I could not find a proposal called {proposal_id}. Ask me to propose it again.")
    if row["status"] != "pending":
        raise ValueError(f"Proposal {proposal_id} was already {row['status']}, so nothing was changed.")
    try:
        inverse, spoken = APPLY[row["type"]](conn, json.loads(row["payload"]))
        conn.execute("UPDATE proposals SET status='confirmed' WHERE id=?", (proposal_id,))
        conn.execute("INSERT INTO audit_log(ts, action, detail, inverse, undone) VALUES (?,?,?,?,0)",
                     (now().isoformat(), row["type"], row["summary"], json.dumps(inverse)))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"ok": True, "proposal_id": proposal_id, "action": row["type"], "spoken_summary": spoken + " You can say undo to reverse it."}


def _run_inverse(conn, inv: dict):
    for tid in inv.get("delete_tasks", []):
        conn.execute("DELETE FROM events WHERE task_id=?", (tid,))
        conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
    for eid in inv.get("delete_events", []):
        conn.execute("DELETE FROM events WHERE id=?", (eid,))
    for t in inv.get("restore_tasks", []):
        conn.execute("UPDATE tasks SET done_minutes=?, status=? WHERE id=?", (t["done_minutes"], t["status"], t["id"]))
    for key, value in inv.get("restore_settings", {}).items():
        if value is None:
            conn.execute("DELETE FROM settings WHERE key=?", (key,))
        else:
            conn.execute("UPDATE settings SET value=? WHERE key=?", (value, key))


def undo_last(conn) -> dict:
    row = conn.execute("SELECT * FROM audit_log WHERE undone=0 ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        raise ValueError("There is nothing to undo.")
    inv = json.loads(row["inverse"])
    try:
        _run_inverse(conn, inv)
        conn.execute("UPDATE audit_log SET undone=1 WHERE id=?", (row["id"],))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    extra = f" Note: {inv['noop']}" if "noop" in inv else ""
    return {"ok": True, "undone": row["detail"],
            "spoken_summary": f"Undone: {row['detail']}.{extra}"}


def audit_log(conn, limit=10):
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "time": r["ts"][:16].replace("T", " "), "action": r["action"],
             "detail": r["detail"], "undone": bool(r["undone"])} for r in rows]
