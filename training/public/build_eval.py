"""Build stratified eval samples (<= --cap items per dataset) from public TEST splits.

Writes training/public/eval/<name>.jsonl rows:
  {"id", "dataset", "kind", "request": <Keel wire request>, "gold": ..., "src_index"}
and training/public/eval/MANIFEST.json (sizes, splits, seeds).

Usage: python training/public/build_eval.py [--cap 1000] [--only a,b]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registry import SPECS, BY_NAME, Spec, init_labels, dump  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "training" / "public" / "eval"
SEED = 20261028


def load_rows(spec: Spec, split: str, take: int | None = None) -> list[dict]:
    from datasets import load_dataset

    if spec.stream:
        ds = load_dataset(spec.hf, spec.config, split=split, streaming=True)
        init_labels(spec, ds.features)
        rows = []
        limit = take or spec.stream_take
        for i, r in enumerate(ds):
            if i >= limit:
                break
            r = dict(r)
            r["__idx"] = i
            if spec.keep(r):
                rows.append(r)
        return rows
    ds = load_dataset(spec.hf, spec.config, split=split)
    init_labels(spec, ds.features)
    rows = []
    for i, r in enumerate(ds):
        r = dict(r)
        r["__idx"] = i
        if spec.keep(r):
            rows.append(r)
    return rows


def eval_rows(spec: Spec) -> list[dict]:
    rows = []
    for split in [spec.eval_split, *spec.extra_eval_splits]:
        for r in load_rows(spec, split):
            r["__split"] = split
            rows.append(r)
    return rows


def stratified(rows: list[dict], spec: Spec, cap: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    groups: dict = defaultdict(list)
    for r in rows:
        groups[spec.label(r)].append(r)
    for g in groups.values():
        rng.shuffle(g)
    if len(rows) <= cap:
        picked = [r for g in groups.values() for r in g]
    elif spec.balanced:
        per = cap // len(groups)
        picked = [r for g in groups.values() for r in g[:per]]
    else:
        # Largest-remainder proportional allocation.
        total = len(rows)
        quotas = {k: cap * len(g) / total for k, g in groups.items()}
        alloc = {k: int(q) for k, q in quotas.items()}
        rest = cap - sum(alloc.values())
        for k in sorted(quotas, key=lambda k: quotas[k] - alloc[k], reverse=True)[:rest]:
            alloc[k] += 1
        picked = [r for k, g in groups.items() for r in g[: alloc[k]]]
    rng.shuffle(picked)
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=1000)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    only = [s for s in args.only.split(",") if s]
    specs = [BY_NAME[n] for n in only] if only else SPECS
    manifest_path = OUT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for spec in specs:
        rows = eval_rows(spec)
        picked = stratified(rows, spec, args.cap, SEED)
        with (OUT / f"{spec.name}.jsonl").open("w", encoding="utf-8") as f:
            for j, r in enumerate(picked):
                request, gold = spec.adapt(r)
                f.write(dump({"id": f"{spec.name}-{r['__split']}-{r['__idx']}", "dataset": spec.name, "kind": spec.kind,
                              "request": request, "gold": gold}) + "\n")
        manifest[spec.name] = {
            "hf": spec.hf, "config": spec.config, "splits": [spec.eval_split, *spec.extra_eval_splits],
            "pool": len(rows), "n": len(picked), "seed": SEED, "kind": spec.kind,
            "balanced": spec.balanced, "license": spec.license, "notes": spec.notes,
        }
        print(f"{spec.name}: pool={len(rows)} n={len(picked)}", flush=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
