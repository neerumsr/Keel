"""Shared helpers for the Keel-Pro training-corpus builders.

Every emitted row has exactly one question under "q1" (the kit engine renders one question per
prompt and never shows the question key). Framing helpers come from the Decision Index kit itself
where possible (decision_index.suite.build.layout.choice_row etc.).
"""
import json
import os
import random
import sys
from pathlib import Path

KIT = Path(os.environ.get("DI_KIT", r"C:\KeelWork\decision-index"))
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))

RAW = Path(os.environ.get("KEEL_PRO_RAW", r"C:\KeelWork\pro\raw"))
OUT = Path(os.environ.get("KEEL_PRO_DATA", r"C:\KeelWork\pro\data"))

# Paths the generators must never read (contract Phase 3 / task rule 2). Checked by guard().
FORBIDDEN = [
    r"c:\keelwork\di-work\artifacts\benchmark-suite\requests",
    r"c:\keelwork\di-work\artifacts\benchmark-suite\release-",
    r"c:\keelwork\di-work\artifacts\benchmark-suite\normalized",
    r"c:\keelwork\di-work\artifacts\benchmark-suite\selected-rows",
    r"c:\keelwork\di-work\artifacts\benchmark-suite\added-rows",
    r"c:\keelwork\di-work\artifacts\benchmark-suite\gsm8k-rows",
    r"c:\keelwork\di-samples",
    r"c:\keelwork\decision-index\suite-",
]


def guard(path):
    p = str(Path(path).resolve()).lower()
    assert not any(p.startswith(f) for f in FORBIDDEN), f"forbidden path: {path}"
    assert p.startswith(str(RAW.resolve()).lower()), f"builders read only from {RAW}: {path}"
    return Path(path)


def text(x):
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def row(benchmark, source, state, question, gold):
    assert question["type"] in ("choice", "noul")
    if question["type"] == "choice":
        assert gold in question["criteria"], (benchmark, gold, list(question["criteria"])[:5])
        assert 2 <= len(question["criteria"]) <= 255
    else:
        assert isinstance(gold, bool)
    return {"benchmark": benchmark, "source": source, "state": state, "questions": {"q1": question}, "gold": {"q1": gold}}


def from_kit_row(benchmark, source, kit_row):
    """Split a kit-shaped row (state + questions + gold/expected) into one row per question."""
    exp = kit_row.get("gold") or kit_row.get("expected")
    for k, q in kit_row["questions"].items():
        yield row(benchmark, source, kit_row["state"], q, exp[k])


def letters(n):
    return [chr(65 + i) for i in range(n)]


def rng(*parts):
    return random.Random(":".join(str(p) for p in ("keel-pro-2026", *parts)))


def clip(s, n):
    """Training-only truncation of one free-text field: keep head and tail."""
    if not isinstance(s, str) or len(s) <= n:
        return s
    h = int(n * 0.7)
    return s[:h] + " ... " + s[-(n - h):]


def sample(items, k, seed):
    items = list(items)
    if len(items) <= k:
        return items
    return rng("sample", seed).sample(items, k)
