"""Drop encoder layers from an HF cross-encoder checkpoint (layer-drop init for a faster Pro/student).

    python training/keel/t2_prune.py --ckpt training/runs/t2-dxs-b3/best --out training/runs/t2-dxs6-init --keep 0,2,4,6,8,11
"""
from __future__ import annotations

import argparse

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep", required=True, help="comma-separated layer indices to keep, in order")
    args = ap.parse_args()
    keep = [int(x) for x in args.keep.split(",")]
    model = AutoModelForSequenceClassification.from_pretrained(args.ckpt, dtype=torch.float32)
    enc = getattr(model, model.base_model_prefix).encoder
    enc.layer = torch.nn.ModuleList([enc.layer[i] for i in keep])
    model.config.num_hidden_layers = len(keep)
    model.save_pretrained(args.out)
    AutoTokenizer.from_pretrained(args.ckpt).save_pretrained(args.out)
    print(f"kept layers {keep} -> {args.out}")


if __name__ == "__main__":
    main()
