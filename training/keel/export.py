"""Export a trained Keel-2 checkpoint to a servable model directory.

    python training/keel/export.py --ckpt training/runs/xd6/best --out models/keel-2

Steps: ONNX export (fp32) -> dynamic int8 quantization -> tokenizer/config copy
-> per-type temperature calibration on dev using the *quantized* ONNX graph
(exactly what Node serves) -> keel.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pathlib
import shutil
import sys

import numpy as np
import onnxruntime as ort
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.hypothesis import hypotheses, state_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOKENIZER_FILES = ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "spm.model", "config.json"]


class TraceableBert(torch.nn.Module):
    """BERT forward with a plain additive mask. transformers 5 mask helpers do not trace."""

    def __init__(self, model):
        super().__init__()
        self.m = model

    def forward(self, input_ids, attention_mask, token_type_ids):
        bert = self.m.bert
        h = bert.embeddings(input_ids=input_ids, token_type_ids=token_type_ids)
        ext = (1.0 - attention_mask[:, None, None, :].to(h.dtype)) * torch.finfo(h.dtype).min
        for layer in bert.encoder.layer:
            out = layer(h, attention_mask=ext)
            h = out[0] if isinstance(out, tuple) else out
        pooled = bert.pooler(h)
        return self.m.classifier(self.m.dropout(pooled))


def quantize(fp32: pathlib.Path, q: pathlib.Path, mode: str) -> None:
    """dynamic: every weight int8 (Keel-2). mixed: per-channel int8, but the FFN output
    projections (GELU outliers) and the pooler/classifier head stay fp32. On xd6 dev the
    plain int8 graph flips ~12% of choice argmaxes vs fp32; mixed flips none (+~5 MB)."""
    if mode == "dynamic":
        quantize_dynamic(str(fp32), str(q), weight_type=QuantType.QInt8)
        return
    import onnx

    graph = onnx.load(str(fp32)).graph
    keep = [
        n.name
        for n in graph.node
        if n.op_type in ("MatMul", "Gemm")
        and (("output/dense" in n.name and "attention" not in n.name) or "pooler" in n.name or "classifier" in n.name)
    ]
    quantize_dynamic(
        str(fp32), str(q), weight_type=QuantType.QInt8, per_channel=True,
        nodes_to_exclude=keep, extra_options={"MatMulConstBOnly": True},
    )


def export_onnx(ckpt: pathlib.Path, out: pathlib.Path, quant: str = "mixed") -> tuple[pathlib.Path, list[str]]:
    model = AutoModelForSequenceClassification.from_pretrained(ckpt, dtype=torch.float32, attn_implementation="eager").eval()
    tok = AutoTokenizer.from_pretrained(ckpt)
    sample = tok(["a state that is long enough", "short"], ["a hypothesis", "another longer hypothesis here"], padding=True, return_tensors="pt")
    names = ["input_ids", "attention_mask", "token_type_ids"]
    wrapper = TraceableBert(model).eval()
    with torch.no_grad():
        ref = model(**sample).logits
        got = wrapper(*(sample[n] for n in names))
    drift = float((ref - got).abs().max())
    assert drift < 1e-3, f"wrapper drift {drift}"
    onnx_dir = out / "onnx"
    onnx_dir.mkdir(parents=True, exist_ok=True)
    fp32 = onnx_dir / "model.onnx"
    axes = {n: {0: "batch", 1: "seq"} for n in names}
    axes["logits"] = {0: "batch"}
    torch.onnx.export(
        wrapper,
        tuple(sample[n] for n in names),
        str(fp32),
        input_names=names,
        output_names=["logits"],
        dynamic_axes=axes,
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    q = onnx_dir / "model_quantized.onnx"
    quantize(fp32, q, quant)
    tok.save_pretrained(out)
    for name in TOKENIZER_FILES:
        src = ckpt / name
        if src.exists() and not (out / name).exists():
            shutil.copy(src, out / name)
    return q, names


class OrtMargins:
    def __init__(self, model_path: pathlib.Path, tok_dir: pathlib.Path, max_len: int):
        self.sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.names = [i.name for i in self.sess.get_inputs()]
        self.tok = AutoTokenizer.from_pretrained(tok_dir)
        self.max_len = max_len

    def __call__(self, premises: list[str], hyps: list[str]) -> np.ndarray:
        enc = self.tok(premises, hyps, padding=True, truncation=True, max_length=self.max_len, return_tensors="np")
        feeds = {n: enc[n].astype(np.int64) for n in self.names}
        logits = self.sess.run(["logits"], feeds)[0]
        return logits[:, 0] - logits[:, 1]


def collect(margin_fn: OrtMargins, rows: list[dict]) -> dict[str, list[tuple[np.ndarray, list[float]]]]:
    groups: dict[str, list] = {"choice": [], "score": [], "noul": []}
    for row in rows:
        if row.get("family") == "nli":
            continue
        q = row["question"]
        hs = hypotheses(q)
        m = margin_fn([state_text(row["state"])] * len(hs), hs)
        groups[q["type"]].append((m, row["target"]))
    return groups


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def fit_temperature(items, kind: str) -> tuple[float, float]:
    best = (1.0, math.inf)
    for t in np.round(np.arange(0.4, 6.01, 0.1), 2):
        nll = 0.0
        for m, target in items:
            if kind == "noul":
                p = 1 / (1 + math.exp(-(m[0] - m[1]) / t))
                y = target[0]
                nll -= y * math.log(max(p, 1e-6)) + (1 - y) * math.log(max(1 - p, 1e-6))
            else:
                p = softmax(m / t)
                nll -= float(np.sum(np.array(target) * np.log(np.maximum(p, 1e-6))))
        nll /= max(1, len(items))
        if nll < best[1]:
            best = (float(t), nll)
    return best


def fit_abstain(items) -> float:
    """Highest threshold that barely touches confident groups; ambiguous groups sit below it."""
    confident = sorted(float(1 / (1 + np.exp(-m.max()))) for m, t in items if max(t) >= 0.5)
    ambiguous = [float(1 / (1 + np.exp(-m.max()))) for m, t in items if max(t) < 0.5]
    if not confident:
        return 0.35
    p05 = confident[int(0.05 * len(confident))]
    if ambiguous:
        amb90 = sorted(ambiguous)[int(0.9 * (len(ambiguous) - 1))]
        return round(float(min(p05, max(0.2, amb90))), 3)
    return round(float(min(p05, 0.35)), 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", default=str(ROOT / "models/keel-2"))
    ap.add_argument("--dev", nargs="+", default=[str(ROOT / "training/data/dev.jsonl")], help="one or more DEV jsonl files for calibration")
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--base-id", default="MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33")
    ap.add_argument("--id", default="decider-2.0.0", help="model id written to keel.json")
    ap.add_argument("--trained-on", default=None, help="trainedOn text for keel.json")
    ap.add_argument("--quant", choices=["mixed", "dynamic"], default="mixed", help="mixed (default) keeps FFN-out + head fp32; dynamic = Keel-2 all-int8")
    args = ap.parse_args()
    ckpt, out = pathlib.Path(args.ckpt), pathlib.Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    q, names = export_onnx(ckpt, out, args.quant)
    print("exported", q, names, flush=True)

    rows = [json.loads(line) for dev in args.dev for line in pathlib.Path(dev).read_text(encoding="utf-8").split("\n") if line.strip()]
    groups = collect(OrtMargins(q, out, args.max_len), rows)
    temps = {k: fit_temperature(v, k) for k, v in groups.items()}
    abstain = fit_abstain(groups["choice"] + groups["score"])
    print("temperatures", temps, "abstain", abstain, flush=True)

    done = ckpt.parent / "done.json"
    run = json.loads(done.read_text()) if done.exists() else {}
    config = {
        "id": args.id,
        "base": args.base_id,
        "hypothesisVersion": 1,
        "maxLength": args.max_len,
        "threads": 4,
        "onnx": "onnx/model_quantized.onnx",
        "temperature": {k: v[0] for k, v in temps.items()},
        "abstain": {"threshold": abstain, "floor": 0},
        "lexicalBlend": {"choice": 0, "score": 0, "noul": 0},
        "scoreSmoothing": 0,
        "noulBias": 0,
        "trainedOn": args.trained_on or f"keel synthetic v1 ({len(rows)} dev groups); exported {dt.date.today().isoformat()}",
        "quantization": args.quant,
        "calibrationSet": [os.path.relpath(d, ROOT).replace(os.sep, "/") for d in args.dev],
        "calibration": {k: {"temperature": v[0], "devNll": round(v[1], 4), "groups": len(groups[k])} for k, v in temps.items()},
        "training": {"bestDevLoss": run.get("best_dev_loss"), "steps": run.get("steps"), "minutes": run.get("minutes")},
    }
    (out / "keel.json").write_text(json.dumps(config, indent=2))
    (out / "onnx" / "model.onnx").unlink()
    print("wrote", out / "keel.json", flush=True)


if __name__ == "__main__":
    main()
