"""Merge a di-bench status update into artifacts/parity/pro/status.json (other agents' keys are preserved).

Usage: python di_status.py <step> <state> [note]
"""
import datetime
import json
import os
import sys
from pathlib import Path

STATUS = Path(__file__).resolve().parents[2] / "artifacts" / "parity" / "pro" / "status.json"


def update(step, state, note=None, **extra):
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    mine = data.setdefault("di-bench", {"steps": {}})
    mine.setdefault("steps", {})
    entry = {"state": state, "updated": now}
    if note:
        entry["note"] = note
    entry.update(extra)
    mine["steps"][step] = entry
    mine["updated"] = now
    tmp = STATUS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATUS)


if __name__ == "__main__":
    update(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
