"""jev-3: PyTorch vs ONNX fp32 vs ONNX int8 parity, quantization loss, batch-composition
sensitivity, and Python-vs-JS tokenizer parity for Keel-2.

    python artifacts/parity/jev/parity.py

Inputs: training/runs/xd6-v2/best (PyTorch), models/keel-2 (served int8), training/data/evals.json
(non-blind suites only), training/data/dev.jsonl. Writes artifacts/parity/jev/parity.json and
artifacts/parity/jev/tok-pairs.json (consumed by tok-js.ts for tokenizer parity).
"""
from __future__ import annotations

import json
import pathlib
import random
import sys

import numpy as np
import onnxruntime as ort
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "training"))
from keel.export import TraceableBert  # noqa: E402
from keel.hypothesis import hypotheses, state_text  # noqa: E402

OUT = ROOT / "artifacts/parity/jev"
CKPT = ROOT / "training/runs/xd6-v2/best"
SERVED = ROOT / "models/keel-2"
torch.set_num_threads(6)


def groups():
    ev = json.loads((ROOT / "training/data/evals.json").read_text(encoding="utf-8"))
    out = []
    for suite in ("labeled", "holdout", "holdoutB", "open"):
        for case in ev[suite]:
            qs = [(qid, hypotheses(q), q["type"]) for qid, q in case["questions"].items()]
            out.append({"suite": suite, "id": case["id"], "state": state_text(case["state"]), "qs": qs})
    dev = [json.loads(l) for l in (ROOT / "training/data/dev.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rng = random.Random(3)
    for i, r in enumerate(rng.sample(dev, 200)):
        out.append({"suite": "dev", "id": i, "state": state_text(r["state"]), "qs": [("q", hypotheses(r["question"]), r["question"]["type"])]})
    return out


def main():
    tok = AutoTokenizer.from_pretrained(SERVED)
    tok_ck = AutoTokenizer.from_pretrained(CKPT)
    model = AutoModelForSequenceClassification.from_pretrained(CKPT, dtype=torch.float32, attn_implementation="eager").eval()
    fp32_path = OUT / "scratch-fp32.onnx"
    names = ["input_ids", "attention_mask", "token_type_ids"]
    if not fp32_path.exists():
        sample = tok(["a state that is long enough", "short"], ["a hypothesis", "another longer hypothesis here"], padding=True, return_tensors="pt")
        torch.onnx.export(TraceableBert(model).eval(), tuple(sample[n] for n in names), str(fp32_path), input_names=names, output_names=["logits"],
                          dynamic_axes={**{n: {0: "batch", 1: "seq"} for n in names}, "logits": {0: "batch"}}, opset_version=17, do_constant_folding=True, dynamo=False)
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    s32 = ort.InferenceSession(str(fp32_path), so, providers=["CPUExecutionProvider"])
    s8 = ort.InferenceSession(str(SERVED / "onnx/model_quantized.onnx"), so, providers=["CPUExecutionProvider"])

    def enc(prem, hyps, t=tok):
        return t(prem, hyps, padding=True, truncation=True, max_length=256, return_tensors="np")

    def ort_m(sess, prem, hyps):
        e = enc(prem, hyps)
        lg = sess.run(["logits"], {n: e[n].astype(np.int64) for n in names})[0]
        return lg[:, 0] - lg[:, 1]

    @torch.no_grad()
    def torch_m(prem, hyps):
        e = tok(prem, hyps, padding=True, truncation=True, max_length=256, return_tensors="pt")
        lg = model(**e).logits.numpy()
        return lg[:, 0] - lg[:, 1]

    gs = groups()
    tok_mismatch = 0
    d_torch_fp32, d_fp32_int8, d_batch = [], [], []
    flips_q, flips_batch, n_groups = 0, 0, 0
    trunc160, trunc256, ntrain_pairs = 0, 0, 0
    pairs_for_js = []
    per_suite = {}
    for g in gs:
        all_h = [h for _, hs, _ in g["qs"] for h in hs]
        prem = [g["state"]] * len(all_h)
        # tokenizer parity: served tokenizer vs checkpoint tokenizer
        a, b = enc(prem, all_h), enc(prem, all_h, tok_ck)
        if a["input_ids"].shape != b["input_ids"].shape or (a["input_ids"] != b["input_ids"]).any():
            tok_mismatch += 1
        for h in all_h:
            n = len(tok(g["state"], h)["input_ids"])
            trunc160 += int(n > 160)
            trunc256 += int(n > 256)
            ntrain_pairs += 1
        if len(pairs_for_js) < 400:
            pairs_for_js += [{"premise": g["state"], "hyp": h, "ids": tok(g["state"], h, truncation=True, max_length=256)["input_ids"]} for h in all_h[:3]]
        # per-question (how rawMargins / export calibration see it) vs whole-request batch (how neuralWeights serves it)
        batched = ort_m(s8, prem, all_h)
        off = 0
        for qid, hs, qt in g["qs"]:
            p = [g["state"]] * len(hs)
            mt, m32, m8 = torch_m(p, hs), ort_m(s32, p, hs), ort_m(s8, p, hs)
            mb = batched[off : off + len(hs)]
            off += len(hs)
            d_torch_fp32.append(float(np.abs(mt - m32).max()))
            d_fp32_int8.append(float(np.abs(m32 - m8).max()))
            d_batch.append(float(np.abs(m8 - mb).max()))
            n_groups += 1
            if qt != "noul":
                f = int(mt.argmax() != m8.argmax())
                fb = int(m8.argmax() != mb.argmax())
            else:
                f = int((mt[0] > mt[1]) != (m8[0] > m8[1]))
                fb = int((m8[0] > m8[1]) != (mb[0] > mb[1]))
            flips_q += f
            flips_batch += fb
            ps = per_suite.setdefault(g["suite"], {"groups": 0, "quant_flips": 0, "batch_flips": 0, "max_quant_diff": 0.0, "max_batch_diff": 0.0})
            ps["groups"] += 1
            ps["quant_flips"] += f
            ps["batch_flips"] += fb
            ps["max_quant_diff"] = max(ps["max_quant_diff"], float(np.abs(mt - m8).max()))
            ps["max_batch_diff"] = max(ps["max_batch_diff"], float(np.abs(m8 - mb).max()))

    def q(v):
        v = np.array(v)
        return {"max": float(v.max()), "p95": float(np.quantile(v, 0.95)), "mean": float(v.mean())}

    res = {
        "groups": n_groups,
        "tokenizer_served_vs_ckpt_mismatching_requests": tok_mismatch,
        "margin_absdiff_torch_vs_onnx_fp32": q(d_torch_fp32),
        "margin_absdiff_onnx_fp32_vs_int8": q(d_fp32_int8),
        "margin_absdiff_int8_question_alone_vs_full_request_batch": q(d_batch),
        "argmax_flips_torch_vs_int8": flips_q,
        "argmax_flips_int8_alone_vs_batched": flips_batch,
        "per_suite": per_suite,
        "pairs_over_160_tokens": trunc160,
        "pairs_over_256_tokens": trunc256,
        "pairs_total": ntrain_pairs,
    }
    (OUT / "parity.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "tok-pairs.json").write_text(json.dumps(pairs_for_js), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
