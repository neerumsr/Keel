"""Validate the corpus framing: print 3 random rendered rows per benchmark and check instructions, criteria key
style and state shape against the kit builder source.

Usage: python -X utf8 validate.py [path\\to\\train.jsonl.gz] [--show N]
"""
import collections
import gzip
import json
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from common import render_prompt  # noqa: E402

KIT_BUILD = Path(r"C:\KeelWork\decision-index\decision_index\suite\build")

# benchmark -> (state shape, criteria key regex, instruction source)
# state shape: "str" | "empty-str" | "{}" | tuple of required dict keys
EXPECT = {
    1: (("conversation", "functions", "task"), r"yes|no", "kit"),
    2: (("query", "task"), r"yes|no", "kit"),
    3: (("dialogue", "available_tools", "task"), r"option_\d+", "kit"),
    4: ("{}", r"option_\d+", "kit"),
    5: ("{}", r"option_\d+", "kit"),
    9: (("now", "devices", "policy", "request"), r"k_[0-9a-f]{8}", "kit"),
    11: ("str", r"Entailment|Contradiction|NotMentioned", "kit"),
    12: ("{}", r"[A-C]", "kit"),
    21: ("empty-str", r"headline_[12]", "kit"),
    25: ("empty-str", r"[A-D]", "data"),
    28: ("{}", r"[AB]", "kit"),
    29: ("{}", r"[A-D]", "kit"),
    30: (("question", "task"), r"option_\d+", "kit"),
    31: (("fen",), r".+", "kit"),
    32: ("{}", r"[A-Z]", "data"),
    37: (("search_query", "product"), r"[ESCI]", "kit"),
    38: (("review", "task"), r"yes|no", "kit"),
    40: ("any", r".+", "kit"),
    41: ("{}", r"[A-C]", "kit"),
    42: (("primary_trial",), r"Entailment|Contradiction", "kit"),
    43: (("code", "input", "task"), r"option_\d+", "kit"),
    44: ("{}", r"[AB]", "data"),
    50: (("policy_question", "participant_opinions"), r"option_\d+", "kit"),
    57: ("str", r"[A-J]", "kit"),
    58: ("str", r".+", "kit"),
    59: (("prompt",), r".+", "kit"),
    61: (("claim", "evidence"), r".+", "kit"),
    62: (("tools", "question"), r"[A-D]", "kit"),
    64: (("scene", "description", "uncanny_description", "entities"), r"[A-E]", "kit"),
}


def kit_text():
    files = sorted(KIT_BUILD.glob("*.py"))
    # 56 PhishNChips: the kit loads its nine questions from jev-phishing-bench/run_jev.py (adapters_added.phishnchips)
    jev = Path(os.environ.get("DI_WORK", r"C:\KeelWork\di-work")) / "artifacts/benchmark-suite/raw/repos/jev-phishing-bench/run_jev.py"
    if jev.exists():
        files.append(jev)
    src = "\n".join(p.read_text(encoding="utf-8") for p in files)
    src = re.sub(r'"\s+"', "", src)  # implicit concatenation of adjacent literals
    return src.replace("\\n", "\n")


def instr_match(instr, kit):
    s = instr["task"] if isinstance(instr, dict) else instr
    lines = [x for x in s.split("\n") if x.strip()]
    for label, piece in (("full", s), ("first-line", lines[0] if lines else ""), ("last-line", lines[-1] if lines else ""), ("prefix40", s[:40])):
        if len(piece) >= 12 and piece in kit:
            return label
    for line in lines[1:-1]:
        if len(line) >= 30 and line in kit:
            return "inner-line"
    # f-string templates: compare with placeholders replaced
    for line in lines[:1] + lines[-1:]:
        words = re.split(r"\s+", line)
        for n in (6, 4, 3):
            head, tail = " ".join(words[:n]), " ".join(words[-n:])
            if len(head) >= 12 and head in kit:
                return f"head{n}"
            if len(tail) >= 12 and tail in kit:
                return f"tail{n}"
    return None


def state_ok(spec, st):
    if spec == "any":
        return True
    if spec == "str":
        return isinstance(st, str) and bool(st)
    if spec == "empty-str":
        return st == ""
    if spec == "{}":
        return st == {}
    return isinstance(st, dict) and all(k in st for k in spec)


def main():
    path = Path(next((a for a in sys.argv[1:] if not a.startswith("--")), r"C:\KeelWork\pro\data\train.jsonl.gz"))
    show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 3
    by = collections.defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            by[r["benchmark"]].append(r)
    kit = kit_text()
    problems = []
    summary = []
    for b in sorted(by):
        rows = by[b]
        state_spec, key_re, isrc = EXPECT.get(b, ("any", r".+", "kit"))
        bad_state = sum(not state_ok(state_spec, r["state"]) for r in rows)
        bad_keys = sum(not all(re.fullmatch(key_re, k) for k in r["questions"]["q1"]["criteria"]) for r in rows)
        bad_gold = sum((type(r["gold"]["q1"]) is not bool) if r["questions"]["q1"]["type"] == "noul" else (r["gold"]["q1"] not in r["questions"]["q1"]["criteria"]) for r in rows)
        matches = collections.Counter(instr_match(r["questions"]["q1"]["instructions"], kit) if isrc == "kit" else "data-derived" for r in rows[:500])
        summary.append((b, len(rows), bad_state, bad_keys, bad_gold, dict(matches)))
        if bad_state or bad_keys or bad_gold or (isrc == "kit" and matches.get(None)):
            problems.append(b)
        for r in random.Random(f"validate:{b}").sample(rows, min(show, len(rows))):
            text = render_prompt(r["state"], r["questions"]["q1"])
            print(f"\n######## benchmark {b} | {r['source'][:100]} | gold={r['gold']['q1']} | {len(text)} chars")
            print(text if len(text) <= 2500 else text[:1700] + "\n[... display cut ...]\n" + text[-700:])
    print("\n\nbenchmark rows bad_state bad_keys bad_gold instruction_match(first 500)")
    for s in summary:
        print(*s)
    print("PROBLEMS:", problems or "none")


if __name__ == "__main__":
    main()
