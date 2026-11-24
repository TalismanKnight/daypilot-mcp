"""Rehearsal script: runs the 90-second demo flow through the real MCP tool layer.
Usage: python demo_run.py            (pins the clock to 09:00 on the seed date so output is repeatable)"""
import asyncio
import json
import os
import tempfile

os.environ.setdefault("DAYPILOT_NOW", "2026-11-24 09:00")
os.environ.setdefault("DAYPILOT_DB", os.path.join(tempfile.mkdtemp(), "demo.db"))
os.environ.setdefault("MAPS_MODE", "mock")

from daypilot import seed  # noqa: E402
from daypilot.server import mcp  # noqa: E402


async def call(name, **args):
    result = await mcp.call_tool(name, args)
    content = result[0] if isinstance(result, tuple) else result
    data = json.loads(content[0].text)
    print(f"\n>>> {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})")
    print("   ", data.get("spoken_summary", data))
    return data


async def main():
    seed.seed()
    await call("get_day_overview")
    await call("get_free_slots")
    await call("get_priority_list")
    plan = await call("propose_plan")
    await call("plan_departure", event_id=5)
    await call("confirm", proposal_id=plan["proposal_id"])
    await call("get_audit_log")
    await call("speak_morning_briefing")
    await call("undo_last_change")
    await call("get_day_overview")


if __name__ == "__main__":
    asyncio.run(main())
