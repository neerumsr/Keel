"""Uniform/weighted weight average ("model soup") of checkpoints that share an init.

    python training/keel/t1_soup.py --ckpt training/runs/t1-r7/best training/runs/t1-r8/best [--weights 0.5 0.5] --out training/runs/t1-s78/best
Copies config/tokenizer from the first checkpoint. Select soups by dev loss only (train.py evaluate).
"""
from __future__ import annotations

import argparse
import pathlib
import shutil

from safetensors.torch import load_file, save_file


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--weights", nargs="*", type=float, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    w = args.weights or [1.0 / len(args.ckpt)] * len(args.ckpt)
    assert len(w) == len(args.ckpt), "one weight per checkpoint"
    total = sum(w)
    w = [x / total for x in w]
    states = [load_file(str(pathlib.Path(c) / "model.safetensors")) for c in args.ckpt]
    avg = {}
    for k, v in states[0].items():
        if v.is_floating_point():
            avg[k] = sum(wi * s[k].float() for wi, s in zip(w, states)).to(v.dtype).contiguous()
        else:
            avg[k] = v
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in pathlib.Path(args.ckpt[0]).iterdir():
        if f.name != "model.safetensors":
            shutil.copy(f, out / f.name)
    save_file(avg, str(out / "model.safetensors"), metadata={"format": "pt"})
    print("soup", dict(zip(args.ckpt, w)), "->", out)


if __name__ == "__main__":
    main()
