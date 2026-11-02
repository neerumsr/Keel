"""Build Keel-2 training data.

    python training/keel/build_data.py --n 40000 --seed 7 [--nli 8000]

Writes training/data/train.jsonl and dev.jsonl. Held-out and open-domain eval
states are loaded from training/data/evals.json (scripts/export-evals.ts) and any
generated state sharing a 6-gram with them is dropped, then re-checked as a hard
failure so contamination cannot slip in silently.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.families import generate, ordinal  # noqa: E402
from keel.hypothesis import state_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "training" / "data"


def grams(text: str, n: int = 6) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def eval_groups(case: dict, copies: int) -> list[dict]:
    """Turn a labeled eval case into training groups (labeled-50 only)."""
    out = []
    exp = case["expect"]
    for qid, q in case["questions"].items():
        target = None
        if exp.get("choice") and exp["choice"]["id"] == qid:
            keys = list(q["criteria"].keys())
            if exp["choice"].get("maxConfidence") is not None:
                target = [1 / len(keys)] * len(keys)
            else:
                target = [0.96 if k == exp["choice"]["key"] else 0.04 / (len(keys) - 1) for k in keys]
        elif exp.get("score") and exp["score"]["id"] == qid:
            n = len(q["criteria"])
            mid = (exp["score"]["min"] + exp["score"]["max"]) / 2
            target = ordinal(n, mid, 0.4)
        elif exp.get("noul") and exp["noul"]["id"] == qid:
            p = 0.9 if exp["noul"].get("min") is not None else 0.1
            target = [p, 1 - p]
        if target is not None:
            out.extend({"family": "labeled50", "state": case["state"], "question": q, "target": target} for _ in range(copies))
    return out


def nli_replay(n: int, seed: int) -> list[dict]:
    """Optional: MNLI pairs as single-hypothesis groups to keep generic entailment sharp."""
    from datasets import load_dataset

    ds = load_dataset("nyu-mll/glue", "mnli", split="train").shuffle(seed=seed).select(range(n))
    out = []
    for row in ds:
        out.append({"family": "nli", "state": row["premise"], "pair": row["hypothesis"], "label": 1.0 if row["label"] == 0 else 0.0})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nli", type=int, default=0)
    ap.add_argument("--labeled-copies", type=int, default=6)
    args = ap.parse_args()

    evals = json.loads((DATA / "evals.json").read_text(encoding="utf-8"))
    blocked: set = set()
    for suite in ("holdout", "holdoutB", "open"):
        for case in evals[suite]:
            blocked |= grams(state_text(case["state"]))

    seen: set[str] = set()
    rows: list[dict] = []
    dropped = 0
    for g in generate(args.n, args.seed):
        key = json.dumps([g["state"], g["question"]], sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        if grams(state_text(g["state"])) & blocked:
            dropped += 1
            continue
        rows.append(g)

    labeled = [r for case in evals["labeled"] for r in eval_groups(case, args.labeled_copies)]
    rng = random.Random(args.seed)
    rng.shuffle(rows)
    n_dev = max(500, len(rows) // 20)
    dev, train = rows[:n_dev], rows[n_dev:]
    train += labeled
    if args.nli:
        train += nli_replay(args.nli, args.seed)
    rng.shuffle(train)

    for r in train + dev:
        if "question" in r and grams(state_text(r["state"])) & blocked and r["family"] != "labeled50":
            raise SystemExit("contamination: a training state overlaps a held-out/open eval state")

    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "train.jsonl").open("w", encoding="utf-8") as f:
        for r in train:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (DATA / "dev.jsonl").open("w", encoding="utf-8") as f:
        for r in dev:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    fams: dict[str, int] = {}
    for r in train:
        fams[r["family"]] = fams.get(r["family"], 0) + 1
    print(f"train={len(train)} dev={len(dev)} unique_generated={len(rows)} dropped_for_overlap={dropped}")
    print(json.dumps(dict(sorted(fams.items(), key=lambda kv: -kv[1]))))


if __name__ == "__main__":
    main()
