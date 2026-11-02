"""Export any HF sequence-classification checkpoint (DeBERTa-v3, BERT, ModernBERT) to a Keel model dir.

    python training/keel/t2_export.py --ckpt training/runs/t2-dxs-a/best --out models/candidates/t2-dxs-a

Same layout and calibration as export.py (int8 ONNX + keel.json, temperatures and abstain fitted on
DEV only), but the ONNX graph is traced from a generic logits wrapper so DeBERTa-v3 (no
token_type_ids) works. The Node loader feeds inputs by session input name, so no loader change.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
import time

import numpy as np
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.export import TOKENIZER_FILES, TraceableBert, OrtMargins, collect, fit_abstain, fit_temperature, quantize  # noqa: E402
from keel.hypothesis import hypotheses, state_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


class Logits(torch.nn.Module):
    def __init__(self, model, names):
        super().__init__()
        self.m = model
        self.names = names

    def forward(self, *inputs):
        return self.m(**dict(zip(self.names, inputs))).logits


def quantize_t2(fp32: pathlib.Path, q: pathlib.Path, mode: str) -> None:
    """mixed/dynamic: export.py's modes. pt-mixed: per-TENSOR int8 (MatMulConstBOnly), with FFN-out, head and
    DeBERTa relative-position projections kept fp32 (per-channel int8 is broken for DeBERTa-v3 in ORT 1.20).
    fp32: no quantization (file copied)."""
    if mode in ("mixed", "dynamic"):
        quantize(fp32, q, mode)
        return
    if mode == "fp32":
        shutil.copy(fp32, q)
        return
    import onnx

    graph = onnx.load(str(fp32)).graph
    keep = [
        n.name
        for n in graph.node
        if n.op_type in ("MatMul", "Gemm")
        and (("output/dense" in n.name and "attention" not in n.name) or "pooler" in n.name or "classifier" in n.name or "_proj_1" in n.name)
    ]
    quantize_dynamic(str(fp32), str(q), weight_type=QuantType.QInt8, per_channel=False, nodes_to_exclude=keep,
                     extra_options={"MatMulConstBOnly": True})


def export_onnx(ckpt: pathlib.Path, out: pathlib.Path, quant: str) -> pathlib.Path:
    model = AutoModelForSequenceClassification.from_pretrained(ckpt, dtype=torch.float32, attn_implementation="eager").eval()
    tok = AutoTokenizer.from_pretrained(ckpt)
    sample = tok(["a state that is long enough to matter", "short"], ["a hypothesis", "another longer hypothesis here"], padding=True, return_tensors="pt")
    if model.config.model_type == "bert":
        names = ["input_ids", "attention_mask", "token_type_ids"]
        wrapper = TraceableBert(model).eval()
    else:
        names = [n for n in ["input_ids", "attention_mask", "token_type_ids"] if n in sample and (n != "token_type_ids" or getattr(model.config, "type_vocab_size", 0) > 0)]
        wrapper = Logits(model, names).eval()
    onnx_dir = out / "onnx"
    onnx_dir.mkdir(parents=True, exist_ok=True)
    fp32 = onnx_dir / "model.onnx"
    axes = {n: {0: "batch", 1: "seq"} for n in names}
    axes["logits"] = {0: "batch"}
    with torch.no_grad():
        torch.onnx.export(wrapper, tuple(sample[n] for n in names), str(fp32), input_names=names, output_names=["logits"],
                          dynamic_axes=axes, opset_version=17, do_constant_folding=True, dynamo=False)
    q = onnx_dir / "model_quantized.onnx"
    quantize_t2(fp32, q, quant)
    tok.save_pretrained(out)
    for name in TOKENIZER_FILES:
        src = ckpt / name
        if src.exists() and not (out / name).exists():
            shutil.copy(src, out / name)

    # parity check: torch vs fp32 ONNX vs int8 ONNX on a longer, different-length batch
    import onnxruntime as ort
    probe = tok(["Deploy the hotfix tonight? Error rate is 4% and climbing after the 2.3 release.", "Refund request"],
                ["Should we act now? Answer: yes.", "Which team? Answer: billing. Money, invoices, refunds"],
                padding=True, return_tensors="pt")
    with torch.no_grad():
        ref = model(**{n: probe[n] for n in names}).logits.numpy()
    for path in [fp32, q]:
        s = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        got = s.run(["logits"], {n: probe[n].numpy().astype(np.int64) for n in names})[0]
        print(f"parity {path.name}: max|dlogit|={float(np.abs(got - ref).max()):.4f}", flush=True)
    return q


def latency(q: pathlib.Path, tok_dir: pathlib.Path, max_len: int, threads: int) -> dict:
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    s = ort.InferenceSession(str(q), opts, providers=["CPUExecutionProvider"])
    names = [i.name for i in s.get_inputs()]
    tok = AutoTokenizer.from_pretrained(tok_dir)
    rows = [json.loads(l) for l in (ROOT / "training/data/dev.jsonl").read_text(encoding="utf-8").split("\n") if l.strip()]
    rows = [r for r in rows if r.get("family") != "nli"][:200]
    times = []
    for r in rows:
        hs = hypotheses(r["question"])
        t = time.perf_counter()
        enc = tok([state_text(r["state"])] * len(hs), hs, padding=True, truncation=True, max_length=max_len, return_tensors="np")
        s.run(["logits"], {n: enc[n].astype(np.int64) for n in names})
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return {"p50": round(times[len(times) // 2], 1), "p95": round(times[int(0.95 * len(times))], 1), "n": len(times), "threads": threads}


def argmax_flips(out: pathlib.Path, rows: list[dict], max_len: int, n: int = 300) -> dict:
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = 6
    tok = AutoTokenizer.from_pretrained(out)
    sess = [ort.InferenceSession(str(out / "onnx" / f), so, providers=["CPUExecutionProvider"]) for f in ["model.onnx", "model_quantized.onnx"]]
    names = [i.name for i in sess[0].get_inputs()]
    choice = [r for r in rows if r.get("family") != "nli" and r["question"]["type"] == "choice"][:n]
    flips = 0
    for r in choice:
        hs = hypotheses(r["question"])
        enc = tok([state_text(r["state"])] * len(hs), hs, padding=True, truncation=True, max_length=max_len, return_tensors="np")
        feeds = {k: enc[k].astype(np.int64) for k in names}
        a, b = (s.run(["logits"], feeds)[0] for s in sess)
        flips += int(np.argmax(a[:, 0] - a[:, 1]) != np.argmax(b[:, 0] - b[:, 1]))
    return {"flips": flips, "n": len(choice)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev", default=str(ROOT / "training/data/dev.jsonl"))
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--id", default="decider-3.0.0-pro")
    ap.add_argument("--base-id", default="MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33")
    ap.add_argument("--quant", choices=["mixed", "dynamic", "pt-mixed", "fp32"], default="pt-mixed")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--trained-on", default="keel synthetic v2")
    args = ap.parse_args()
    ckpt, out = pathlib.Path(args.ckpt), pathlib.Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    q = export_onnx(ckpt, out, args.quant)
    rows = [json.loads(line) for line in pathlib.Path(args.dev).read_text(encoding="utf-8").split("\n") if line.strip()]
    import onnxruntime as ort
    margin_fn = OrtMargins.__new__(OrtMargins)
    so = ort.SessionOptions()
    so.intra_op_num_threads = 6
    margin_fn.sess = ort.InferenceSession(str(q), so, providers=["CPUExecutionProvider"])
    margin_fn.names = [i.name for i in margin_fn.sess.get_inputs()]
    margin_fn.tok = AutoTokenizer.from_pretrained(out)
    margin_fn.max_len = args.max_len
    groups = collect(margin_fn, rows)
    temps = {k: fit_temperature(v, k) for k, v in groups.items()}
    abstain = fit_abstain(groups["choice"] + groups["score"])
    lat = latency(q, out, args.max_len, args.threads)
    print("temperatures", temps, "abstain", abstain, "latency", lat, flush=True)

    done = ckpt.parent / "done.json"
    run = json.loads(done.read_text()) if done.exists() else {}
    config = {
        "id": args.id,
        "base": args.base_id,
        "hypothesisVersion": 1,
        "maxLength": args.max_len,
        "threads": args.threads,
        "onnx": "onnx/model_quantized.onnx",
        "temperature": {k: v[0] for k, v in temps.items()},
        "abstain": {"threshold": abstain, "floor": 0},
        "lexicalBlend": {"choice": 0, "score": 0, "noul": 0},
        "scoreSmoothing": 0,
        "noulBias": 0,
        "trainedOn": f"{args.trained_on} ({len(rows)} dev groups); exported {dt.date.today().isoformat()}",
        "calibration": {k: {"temperature": v[0], "devNll": round(v[1], 4), "groups": len(groups[k])} for k, v in temps.items()},
        "training": {"bestDevLoss": run.get("best_dev_loss"), "steps": run.get("steps"), "minutes": run.get("minutes")},
        "pythonLatencyMs": lat,
        "quantization": args.quant,
    }
    config["int8ArgmaxFlips"] = argmax_flips(out, rows, args.max_len)
    print("int8 vs fp32 argmax flips", config["int8ArgmaxFlips"], flush=True)
    (out / "keel.json").write_text(json.dumps(config, indent=2))
    (out / "onnx" / "model.onnx").unlink()
    print("wrote", out / "keel.json", flush=True)


if __name__ == "__main__":
    main()
