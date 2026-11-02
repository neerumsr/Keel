"""Dev metrics (train.py evaluate) for one or more checkpoints; used to select soups on DEV only.

    python training/keel/t1_deveval.py --ckpt a/best b/best --dev training/data/v3/v9/dev.jsonl [--dev-max 0] [--threads 8]
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.train import evaluate, load_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--dev", nargs="+", required=True)
    ap.add_argument("--dev-max", type=int, default=0)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    rows = [r for d in args.dev for r in load_jsonl(pathlib.Path(d))]
    if args.dev_max and len(rows) > args.dev_max:
        rows = rows[:: math.ceil(len(rows) / args.dev_max)]
    for c in args.ckpt:
        tok = AutoTokenizer.from_pretrained(c)
        model = AutoModelForSequenceClassification.from_pretrained(c, dtype=torch.float32).eval()
        m = evaluate(model, tok, rows, args.max_len, "cpu", 64)
        print(json.dumps({"ckpt": c, "groups": len(rows), **m}), flush=True)


if __name__ == "__main__":
    main()
