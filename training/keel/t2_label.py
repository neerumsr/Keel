"""Write teacher soft labels (raw entailment margins) for a training jsonl, for cheap offline KD.

    python training/keel/t2_label.py --teacher training/runs/t2-dxs-b2/best --data training/data/v3/train.jsonl \
        --out training/data/v3/teacher_t2dxs.jsonl --max-groups 20000 --minutes 80

Output line: {"key": group_key(row), "margins": [...], "family": ...}. Margins are logit(entail) - logit(not_entail)
per hypothesis, in hypotheses(question) order (NLI rows: one margin). Apply your own KD temperature.
Sampling is random (seeded), optionally family-balanced. Appends (resumable): keys already in --out are skipped.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import sys
import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.t2_train import group_key  # noqa: E402
from keel.train import to_pairs  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-groups", type=int, default=0)
    ap.add_argument("--per-family", type=int, default=0, help="cap groups per family (balanced sample)")
    ap.add_argument("--minutes", type=float, default=80)
    ap.add_argument("--max-len", type=int, default=160)
    ap.add_argument("--pairs-per-batch", type=int, default=128)
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)

    rows = [json.loads(l) for l in pathlib.Path(args.data).read_text(encoding="utf-8").split("\n") if l.strip()]
    random.Random(args.seed).shuffle(rows)
    if args.per_family:
        seen = collections.Counter()
        keep = []
        for r in rows:
            f = r.get("family", "?")
            if seen[f] < args.per_family:
                seen[f] += 1
                keep.append(r)
        rows = keep
    if args.max_groups:
        rows = rows[: args.max_groups]
    out = pathlib.Path(args.out)
    done = set()
    if out.exists():
        done = {json.loads(l)["key"] for l in out.read_text(encoding="utf-8").split("\n") if l.strip()}
    rows = [r for r in rows if group_key(r) not in done]
    print(f"to label: {len(rows)} groups (already {len(done)})", flush=True)

    tok = AutoTokenizer.from_pretrained(args.teacher)
    model = AutoModelForSequenceClassification.from_pretrained(args.teacher, dtype=torch.float32).eval()
    started = time.time()
    # length-sort chunks of 2000 groups to reduce padding
    n_done = 0
    with out.open("a", encoding="utf-8") as fh, torch.inference_mode():
        for c0 in range(0, len(rows), 2000):
            chunk = sorted(rows[c0 : c0 + 2000], key=lambda r: len(to_pairs(r)[0]))
            batch, count = [], 0
            for i, r in enumerate(chunk):
                batch.append(r)
                count += len(to_pairs(r)[1])
                if count >= args.pairs_per_batch or i == len(chunk) - 1:
                    prem, hyps, sizes = [], [], []
                    for b in batch:
                        st, hs, _, _ = to_pairs(b)
                        prem += [st] * len(hs)
                        hyps += hs
                        sizes.append(len(hs))
                    enc = tok(prem, hyps, padding=True, truncation=True, max_length=args.max_len, return_tensors="pt")
                    lg = model(**enc).logits
                    m = (lg[:, 0] - lg[:, 1]).tolist()
                    off = 0
                    for b, n in zip(batch, sizes):
                        fh.write(json.dumps({"key": group_key(b), "margins": [round(x, 4) for x in m[off : off + n]], "family": b.get("family")}) + "\n")
                        off += n
                    n_done += len(batch)
                    batch, count = [], 0
            fh.flush()
            el = time.time() - started
            print(f"labeled {n_done}/{len(rows)} groups, {el / 60:.1f} min, {n_done / el:.1f} groups/s", flush=True)
            if el > args.minutes * 60:
                print("time budget reached", flush=True)
                break


if __name__ == "__main__":
    main()
