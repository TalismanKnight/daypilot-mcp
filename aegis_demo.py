"""Isolated, repeatable Asha demo. No real payments or live travel queries."""
import os
import runpy
import tempfile
from pathlib import Path
from datetime import datetime
from daypilot.timeutil import IST

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    os.chdir(root)
    os.environ["DAYPILOT_NOW"] = datetime.now(IST).strftime("%Y-%m-%d 09:00")
    os.environ["MAPS_MODE"] = "mock"
    os.environ["AEGIS_SAFE_DEMO"] = "1"
    from daypilot.seed import seed
    from daypilot.db import connect
    with tempfile.TemporaryDirectory(prefix="aegis-demo-", ignore_cleanup_errors=True) as folder:
        os.environ["DAYPILOT_DB"] = str(Path(folder) / "demo.db")
        seed()
        with connect() as db:
            db.execute("UPDATE events SET title=? WHERE title=?", ("Hospital appointment", "Dentist appointment"))
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", ("profile", "voice_first"))
        runpy.run_path(str(root / "web_app.py"), run_name="__main__")
