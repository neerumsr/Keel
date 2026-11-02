"""jev-3: quantization-loss study for Keel-2. Compares quantization recipes against the fp32 graph
on the same (state, hypothesis) groups as parity.py: max/mean margin diff, argmax flips, size, latency.

    python artifacts/parity/jev/quant.py

Needs artifacts/parity/jev/scratch-fp32.onnx (written by parity.py). Writes quant.json; scratch
models go to artifacts/parity/jev/scratch-*.onnx (delete after; not for commit).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import onnxruntime as ort
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoTokenizer

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/parity/jev"
sys.path.insert(0, str(OUT))
from parity import groups  # noqa: E402

fp32 = OUT / "scratch-fp32.onnx"
recipes = {
    "shipped (dynamic QInt8, all ops)": (ROOT / "models/keel-2/onnx/model_quantized.onnx", None),
    "dynamic QInt8 per-channel": (OUT / "scratch-q8-pc.onnx", dict(weight_type=QuantType.QInt8, per_channel=True)),
    "dynamic QInt8 MatMul-only (no Gather/embeddings)": (OUT / "scratch-q8-mm.onnx", dict(weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul"])),
    "dynamic QInt8 MatMul-only per-channel": (OUT / "scratch-q8-mmpc.onnx", dict(weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul"], per_channel=True)),
    "dynamic QUInt8 reduce_range": (OUT / "scratch-qu8.onnx", dict(weight_type=QuantType.QUInt8, reduce_range=True)),
}
for name, (path, kw) in recipes.items():
    if kw is not None and not path.exists():
        quantize_dynamic(str(fp32), str(path), **kw)

tok = AutoTokenizer.from_pretrained(ROOT / "models/keel-2")
names = ["input_ids", "attention_mask", "token_type_ids"]
so = ort.SessionOptions()
so.intra_op_num_threads = 4
so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL


def run(sess, prem, hyps):
    e = tok(prem, hyps, padding=True, truncation=True, max_length=256, return_tensors="np")
    lg = sess.run(["logits"], {n: e[n].astype(np.int64) for n in names})[0]
    return lg[:, 0] - lg[:, 1]


gs = groups()
ref_sess = ort.InferenceSession(str(fp32), so, providers=["CPUExecutionProvider"])
ref = [[run(ref_sess, [g["state"]] * len(hs), hs) for _, hs, _ in g["qs"]] for g in gs]
res = {}
for name, (path, _) in [("fp32", (fp32, None))] + list(recipes.items()):
    sess = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
    diffs, flips, n, lat = [], 0, 0, []
    for g, rg in zip(gs, ref):
        for (qid, hs, qt), r in zip(g["qs"], rg):
            t0 = time.perf_counter()
            m = run(sess, [g["state"]] * len(hs), hs)
            lat.append((time.perf_counter() - t0) * 1000)
            diffs.append(float(np.abs(m - r).max()))
            flips += int(m.argmax() != r.argmax())
            n += 1
    lat.sort()
    res[name] = {"size_mb": round(path.stat().st_size / 1e6, 1), "max_diff": round(max(diffs), 3), "mean_maxdiff": round(float(np.mean(diffs)), 3),
                 "argmax_flips": f"{flips}/{n}", "p50_ms_per_question": round(lat[len(lat) // 2], 2), "p95_ms_per_question": round(lat[int(0.95 * len(lat))], 2)}
    print(name, res[name], flush=True)
(OUT / "quant.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
