"""Convert public TRAIN splits into Keel training groups (same schema as training/data/train.jsonl).

Only datasets whose license permits training (registry.Spec.train_ok) are converted.
Every train row whose normalized text also appears in the dataset's evaluation pool
(the full eval split(s) used by build_eval.py) is dropped.

Output: training/data/public/<name>.jsonl  rows
  {"family": "public_<name>", "state": str, "question": {type, instructions, criteria}, "target": [...], "gold": int}
and training/data/public/READY.json.

Usage: python training/public/to_groups.py [--max-per-dataset 5000] [--only a,b]
Trainers: python training/keel/train.py ... --extra-train training/data/public/boolq.jsonl@0.5 ...
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registry import SPECS, BY_NAME, Spec, dump, norm  # noqa: E402
from build_eval import eval_rows, load_rows, stratified  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "training" / "data" / "public"
SEED = 7
MAX_OPTIONS = 12
SMOOTH = 0.05


def state_str(state) -> str:
    return state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)


def to_group(spec: Spec, request: dict, gold, rng: random.Random) -> dict | None:
    q = dict(request["questions"]["answer"])
    kind = q["type"]
    if kind == "choice":
        keys = list(q["criteria"].keys())
        g = int(gold)
        if len(keys) > MAX_OPTIONS:
            negatives = rng.sample([i for i in range(len(keys)) if i != g], MAX_OPTIONS - 1)
            idx = negatives + [g]
            rng.shuffle(idx)
            q["criteria"] = {keys[i]: q["criteria"][keys[i]] for i in idx}
            g = idx.index(g)
        n = len(q["criteria"])
        target = [SMOOTH / (n - 1)] * n
        target[g] = 1 - SMOOTH
        return {"family": f"public_{spec.name}", "state": state_str(request["state"]), "question": q, "target": target, "gold": g}
    if kind == "noul":
        yes = bool(gold)
        return {"family": f"public_{spec.name}", "state": state_str(request["state"]), "question": q,
                "target": [0.95, 0.05] if yes else [0.05, 0.95], "gold": 0 if yes else 1}
    if kind == "score":
        levels = len(q["criteria"])
        t = float(gold["target"])
        w = [math.exp(-((i - t) ** 2) / (2 * 0.35 ** 2)) for i in range(levels)]
        s = sum(w)
        return {"family": f"public_{spec.name}", "state": state_str(request["state"]), "question": q,
                "target": [x / s for x in w], "gold": int(gold["level"])}
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-dataset", type=int, default=5000)
    ap.add_argument("--only", default="")
    ap.add_argument("--max-options", type=int, default=12, help="choice groups with more labels keep gold + random negatives")
    args = ap.parse_args()
    global MAX_OPTIONS
    MAX_OPTIONS = args.max_options
    OUT.mkdir(parents=True, exist_ok=True)
    only = [s for s in args.only.split(",") if s]
    specs = [BY_NAME[n] for n in only] if only else [s for s in SPECS if s.train_ok and s.train_split]
    ready_path = OUT / "READY.json"
    ready = json.loads(ready_path.read_text()) if ready_path.exists() else {"datasets": {}}
    for spec in specs:
        if not spec.train_ok or not spec.train_split:
            print(f"skip {spec.name}: license/train split not OK", flush=True)
            continue
        blocked = {norm(spec.text(r)) for r in eval_rows(spec)}
        take = spec.stream_take * 3 if spec.stream else None
        rows = load_rows(spec, spec.train_split, take=take)
        clean = [r for r in rows if norm(spec.text(r)) not in blocked]
        dropped = len(rows) - len(clean)
        picked = stratified(clean, spec, args.max_per_dataset, SEED)
        rng = random.Random(SEED)
        n = 0
        with (OUT / f"{spec.name}.jsonl").open("w", encoding="utf-8") as f:
            for r in picked:
                request, gold = spec.adapt(r)
                g = to_group(spec, request, gold, rng)
                if g:
                    f.write(dump(g) + "\n")
                    n += 1
        ready["datasets"][spec.name] = {
            "file": f"training/data/public/{spec.name}.jsonl", "groups": n, "family": f"public_{spec.name}",
            "source": f"{spec.hf}{'/' + spec.config if spec.config else ''} split={spec.train_split}",
            "train_pool": len(rows), "dropped_overlap_with_eval": dropped, "license": spec.license,
            "license_url": spec.license_url, "note": spec.train_note,
        }
        print(f"{spec.name}: pool={len(rows)} dropped={dropped} groups={n}", flush=True)
        ready["groups"] = sum(d["groups"] for d in ready["datasets"].values())
        ready["files"] = [d["file"] for d in ready["datasets"].values()]
        ready["createdAt"] = dt.datetime.now(dt.timezone.utc).isoformat()
        ready["schema"] = "same as training/data/train.jsonl (family/state/question/target/gold)"
        ready["evalOnly"] = [s.name for s in SPECS if not s.train_ok]
        # Every file listed is complete; "complete" turns true once this run has finished all datasets.
        ready["complete"] = False
        ready_path.write_text(json.dumps(ready, indent=2))
    ready["complete"] = True
    ready_path.write_text(json.dumps(ready, indent=2))


if __name__ == "__main__":
    main()
