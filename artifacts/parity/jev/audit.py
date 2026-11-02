"""jev-3 calibration / blend audit for Keel-2.

    python artifacts/parity/jev/audit.py [--margins artifacts/parity/jev/margins.json] [--model models/keel-2]

Reproduces neural.server.ts groupProbabilities + wire.ts projection from dumped raw
margins, then:
  1. reproduces the bench grading per suite (sanity check vs keel-bench),
  2. calibration metrics (ECE/Brier/NLL for choice, MAE for score, Brier/ECE for noul)
     on dev and on each held-out suite,
  3. sweeps lexicalBlend / temperature / abstain threshold selecting ONLY on dev,
     and reports the held-out effect separately as diagnosis,
  4. writes a per-failure table for the error taxonomy.
Outputs artifacts/parity/jev/audit.json and prints markdown tables.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
HELD = ["holdout-20", "holdout-b-20", "open-60"]


def softmax(x):
    x = np.asarray(x, dtype=float)
    e = np.exp(x - x.max())
    return e / e.sum()


def sig(x):
    return 1 / (1 + math.exp(-x))


def group_probs(cfg, qtype, raw, lex):
    t = cfg["temperature"][qtype]
    b = cfg["lexicalBlend"][qtype]
    lexlog = np.log(np.maximum(np.asarray(lex, dtype=float), 1e-4))
    p = softmax(np.asarray(raw) / t + b * lexlog)
    top = max(sig(m) for m in raw)
    th = cfg["abstain"]["threshold"]
    if th > 0 and top < th:
        keep = cfg["abstain"].get("floor", 0) + (1 - cfg["abstain"].get("floor", 0)) * (top / th)
        p = keep * p + (1 - keep) / len(p)
    return p


def noul_prob(cfg, raw, lex):
    lx = min(max(lex[0], 1e-3), 1 - 1e-3) if lex[0] not in (0, 1) else lex[0]
    lexlogit = math.log(max(lex[0], 1e-3) / max(1 - lex[0], 1e-3))
    z = (raw[0] - raw[1]) / cfg["temperature"]["noul"] + cfg.get("noulBias", 0) + cfg["lexicalBlend"]["noul"] * lexlogit
    return sig(z)


def answer(cfg, q):
    if q["type"] == "noul":
        return {"noul": noul_prob(cfg, q["margins"], q["lex"])}
    p = group_probs(cfg, q["type"], q["margins"], q["lex"])
    out = {"p": p, "conf": float(p.max()), "arg": int(p.argmax())}
    if q["type"] == "score":
        out["score"] = float(np.dot(np.arange(len(p)), p))
    return out


def ece(conf, correct, bins=10):
    conf, correct = np.asarray(conf), np.asarray(correct, dtype=float)
    if len(conf) == 0:
        return float("nan")
    e = 0.0
    for lo in np.linspace(0, 1, bins, endpoint=False):
        m = (conf > lo) & (conf <= lo + 1 / bins) if lo > 0 else (conf <= 1 / bins)
        if m.any():
            e += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(e)


def grade_case(cfg, row):
    exp = row["expect"]
    qs = {q["qid"]: q for q in row["questions"]}
    res = {"choiceOk": None, "scoreOk": None, "noulOk": None, "safetyMiss": False, "detail": {}}
    if exp.get("choice"):
        q = qs[exp["choice"]["id"]]
        a = answer(cfg, q)
        key = q["keys"][a["arg"]]
        res["detail"]["choice"] = (key, round(a["conf"], 3))
        if exp["choice"].get("maxConfidence") is not None:
            res["choiceOk"] = a["conf"] <= exp["choice"]["maxConfidence"]
        else:
            res["choiceOk"] = key == exp["choice"]["key"]
        if exp.get("safetyMiss") and key in exp["safetyMiss"]["keys"]:
            res["safetyMiss"] = True
    if exp.get("score"):
        q = qs[exp["score"]["id"]]
        a = answer(cfg, q)
        s = round(a["score"], 2)
        res["detail"]["score"] = s
        res["scoreOk"] = exp["score"]["min"] <= s <= exp["score"]["max"]
    if exp.get("noul"):
        q = qs[exp["noul"]["id"]]
        n = round(answer(cfg, q)["noul"], 4)
        res["detail"]["noul"] = n
        lo = exp["noul"].get("min") if exp["noul"].get("min") is not None else 0
        hi = exp["noul"].get("max") if exp["noul"].get("max") is not None else 1
        res["noulOk"] = lo <= n <= hi
    res["fully"] = all(v is not False for v in (res["choiceOk"], res["scoreOk"], res["noulOk"])) and not res["safetyMiss"]
    return res


def suite_summary(cfg, rows):
    agg = {"choice": [0, 0], "score": [0, 0], "noul": [0, 0], "safety": 0, "fully": 0, "cases": len(rows)}
    for r in rows:
        g = grade_case(cfg, r)
        for k in ("choice", "score", "noul"):
            v = g[k + "Ok"]
            if v is not None:
                agg[k][0] += int(v)
                agg[k][1] += 1
        agg["safety"] += int(g["safetyMiss"])
        agg["fully"] += int(g["fully"])
    return agg


def calib_heldout(cfg, rows):
    """Choice: one-hot gold (excluding maxConfidence/ambiguous cases). Score: |E - band mid|. Noul: binary label."""
    conf, corr, nll, brier = [], [], [], []
    amb_conf = []
    smae, sin_band_sharp = [], []
    nprob, nlab = [], []
    for r in rows:
        exp = r["expect"]
        qs = {q["qid"]: q for q in r["questions"]}
        if exp.get("choice"):
            q = qs[exp["choice"]["id"]]
            a = answer(cfg, q)
            if exp["choice"].get("maxConfidence") is not None:
                amb_conf.append(a["conf"])
            else:
                gi = q["keys"].index(exp["choice"]["key"])
                conf.append(a["conf"])
                corr.append(int(a["arg"] == gi))
                nll.append(-math.log(max(a["p"][gi], 1e-6)))
                oh = np.zeros(len(a["p"]))
                oh[gi] = 1
                brier.append(float(((a["p"] - oh) ** 2).sum()))
        if exp.get("score"):
            q = qs[exp["score"]["id"]]
            a = answer(cfg, q)
            mid = (exp["score"]["min"] + exp["score"]["max"]) / 2
            smae.append(abs(a["score"] - mid))
            sin_band_sharp.append(a["conf"])
        if exp.get("noul"):
            q = qs[exp["noul"]["id"]]
            p = answer(cfg, q)["noul"]
            y = 1 if exp["noul"].get("min") is not None else 0
            nprob.append(p)
            nlab.append(y)
    out = {
        "choice_n": len(conf),
        "choice_acc": float(np.mean(corr)) if corr else None,
        "choice_mean_conf": float(np.mean(conf)) if conf else None,
        "choice_ece": ece(conf, corr),
        "choice_nll": float(np.mean(nll)) if nll else None,
        "choice_brier": float(np.mean(brier)) if brier else None,
        "ambiguous_mean_conf": float(np.mean(amb_conf)) if amb_conf else None,
        "score_n": len(smae),
        "score_mae_mid": float(np.mean(smae)) if smae else None,
        "noul_n": len(nprob),
        "noul_brier": float(np.mean((np.array(nprob) - np.array(nlab)) ** 2)) if nprob else None,
        "noul_acc@0.5": float(np.mean((np.array(nprob) >= 0.5) == np.array(nlab))) if nprob else None,
        "noul_mean_p_yes_cases": float(np.mean([p for p, y in zip(nprob, nlab) if y == 1])) if any(nlab) else None,
        "noul_mean_p_no_cases": float(np.mean([p for p, y in zip(nprob, nlab) if y == 0])) if nlab and not all(nlab) else None,
    }
    return out


def calib_dev(cfg, rows):
    by = {"choice": {"conf": [], "corr": [], "nll": [], "brier": []}, "score": {"mae": [], "nll": [], "pred": [], "true": []}, "noul": {"p": [], "y": [], "nll": []}}
    amb = []
    for r in rows:
        q = r["questions"][0]
        t = np.asarray(r["target"], dtype=float)
        if q["type"] == "noul":
            p = answer(cfg, q)["noul"]
            y = t[0]
            by["noul"]["p"].append(p)
            by["noul"]["y"].append(y)
            by["noul"]["nll"].append(-(y * math.log(max(p, 1e-6)) + (1 - y) * math.log(max(1 - p, 1e-6))))
            continue
        a = answer(cfg, q)
        if t.max() < 0.5:
            amb.append(a["conf"])
            continue
        if q["type"] == "choice":
            gi = int(t.argmax())
            by["choice"]["conf"].append(a["conf"])
            by["choice"]["corr"].append(int(a["arg"] == gi))
            by["choice"]["nll"].append(float(-(t * np.log(np.maximum(a["p"], 1e-6))).sum()))
            by["choice"]["brier"].append(float(((a["p"] - t) ** 2).sum()))
        else:
            tv = float(np.dot(np.arange(len(t)), t))
            by["score"]["mae"].append(abs(a["score"] - tv))
            by["score"]["nll"].append(float(-(t * np.log(np.maximum(a["p"], 1e-6))).sum()))
            by["score"]["pred"].append(a["score"] / (len(t) - 1))
            by["score"]["true"].append(tv / (len(t) - 1))
    c, s, n = by["choice"], by["score"], by["noul"]
    pred, true = np.array(s["pred"]), np.array(s["true"])
    slope = float(np.polyfit(true, pred, 1)[0]) if len(true) > 2 else None
    yb = (np.array(n["y"]) >= 0.5).astype(int)
    return {
        "choice_n": len(c["corr"]),
        "choice_acc": float(np.mean(c["corr"])),
        "choice_ece": ece(c["conf"], c["corr"]),
        "choice_nll": float(np.mean(c["nll"])),
        "choice_brier": float(np.mean(c["brier"])),
        "ambiguous_n": len(amb),
        "ambiguous_mean_conf": float(np.mean(amb)) if amb else None,
        "score_n": len(s["mae"]),
        "score_mae": float(np.mean(s["mae"])),
        "score_nll": float(np.mean(s["nll"])),
        "score_slope_pred_vs_true(normalized)": slope,
        "noul_n": len(n["p"]),
        "noul_nll": float(np.mean(n["nll"])),
        "noul_brier": float(np.mean((np.array(n["p"]) - np.array(n["y"])) ** 2)),
        "noul_acc@0.5": float(np.mean((np.array(n["p"]) >= 0.5) == yb)),
        "noul_ece": ece(np.maximum(n["p"], 1 - np.array(n["p"])), (np.array(n["p"]) >= 0.5) == yb),
    }


def with_(cfg, **kw):
    c = json.loads(json.dumps(cfg))
    for k, v in kw.items():
        a, b = k.split("__")
        c[a][b] = v
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margins", default=str(ROOT / "artifacts/parity/jev/margins.json"))
    ap.add_argument("--model", default=str(ROOT / "models/keel-2"))
    ap.add_argument("--tag", default="audit")
    args = ap.parse_args()
    data = json.loads(pathlib.Path(args.margins).read_text(encoding="utf-8"))
    cfg = json.loads((pathlib.Path(args.model) / "keel.json").read_text(encoding="utf-8"))
    cfg.setdefault("noulBias", 0)
    rows = data["rows"]
    suites = {s: [r for r in rows if r["suite"] == s] for s in ["labeled-50"] + HELD}
    dev = [r for r in rows if r["suite"] == "dev"]
    report = {}

    print("## 1. Reproduction of bench grading (shipped keel.json)\n")
    print("| suite | choice | score | noul | safety | fully right |\n|---|---|---|---|---|---|")
    rep = {}
    for s, rs in suites.items():
        a = suite_summary(cfg, rs)
        rep[s] = a
        print(f"| {s} | {a['choice'][0]}/{a['choice'][1]} | {a['score'][0]}/{a['score'][1]} | {a['noul'][0]}/{a['noul'][1]} | {a['safety']} | {a['fully']}/{a['cases']} |")
    report["reproduction"] = rep

    variants = {
        "shipped": cfg,
        "neural-only (blend 0)": with_(cfg, lexicalBlend__choice=0, lexicalBlend__score=0, lexicalBlend__noul=0),
        "lexical-only": None,
    }
    print("\n## 2. Calibration — dev (in-distribution synthetic)\n")
    report["dev"] = {}
    for name, c in variants.items():
        if c is None:
            continue
        report["dev"][name] = calib_dev(c, dev)
        print(name, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in report["dev"][name].items()}))
    print("\n## 3. Calibration — held-out (diagnosis only)\n")
    report["heldout"] = {}
    for name, c in variants.items():
        if c is None:
            continue
        report["heldout"][name] = {}
        for s in HELD + ["ALL"]:
            rs = [r for r in rows if r["suite"] in HELD] if s == "ALL" else suites[s]
            report["heldout"][name][s] = calib_heldout(c, rs)
            print(name, s, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in report["heldout"][name][s].items()}))

    # 4. Sweep on DEV only
    print("\n## 4. Dev-only sweeps\n")
    sweep = []
    for b in [0, 0.1, 0.25, 0.5, 0.75, 1.0]:
        for t in [0.7, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0]:
            c = with_(cfg, lexicalBlend__choice=b, temperature__choice=t)
            d = calib_dev(c, dev)
            h = calib_heldout(c, [r for r in rows if r["suite"] in HELD])
            lab = suite_summary(c, suites["labeled-50"])
            hs = {s: suite_summary(c, suites[s]) for s in HELD}
            sweep.append({
                "blend": b, "T": t, "dev_nll": d["choice_nll"], "dev_acc": d["choice_acc"], "dev_ece": d["choice_ece"],
                "dev_amb_conf": d["ambiguous_mean_conf"],
                "labeled_safety": lab["safety"],
                "held_choice": sum(x["choice"][0] for x in hs.values()), "held_choice_n": sum(x["choice"][1] for x in hs.values()),
                "held_safety": sum(x["safety"] for x in hs.values()), "held_fully": sum(x["fully"] for x in hs.values()),
                "held_nll": h["choice_nll"], "held_ece": h["choice_ece"],
            })
    report["choice_sweep"] = sweep
    best = min(sweep, key=lambda r: r["dev_nll"])
    print("choice sweep best by dev NLL:", best)
    print("| blend | T | dev NLL | dev acc | dev ECE | dev amb conf | lab-50 safety | HELD choice | HELD safety | HELD fully | HELD NLL | HELD ECE |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sweep:
        if r["T"] in (1.0, 1.6, 2.5) or r is best:
            print(f"| {r['blend']} | {r['T']} | {r['dev_nll']:.3f} | {r['dev_acc']:.3f} | {r['dev_ece']:.3f} | {r['dev_amb_conf']:.3f} | {r['labeled_safety']} | {r['held_choice']}/{r['held_choice_n']} | {r['held_safety']} | {r['held_fully']}/100 | {r['held_nll']:.3f} | {r['held_ece']:.3f} |")

    ssweep = []
    for b in [0, 0.15, 0.3, 0.5]:
        for t in [0.5, 0.7, 1.0, 1.5]:
            c = with_(cfg, lexicalBlend__score=b, temperature__score=t)
            d = calib_dev(c, dev)
            hs = {s: suite_summary(c, suites[s]) for s in HELD}
            h = calib_heldout(c, [r for r in rows if r["suite"] in HELD])
            ssweep.append({"blend": b, "T": t, "dev_nll": d["score_nll"], "dev_mae": d["score_mae"], "dev_slope": d["score_slope_pred_vs_true(normalized)"],
                           "held_score": sum(x["score"][0] for x in hs.values()), "held_score_n": sum(x["score"][1] for x in hs.values()), "held_mae_mid": h["score_mae_mid"]})
    report["score_sweep"] = ssweep
    print("\n| score blend | T | dev NLL | dev MAE | dev slope | HELD score band | HELD MAE(mid) |\n|---|---|---|---|---|---|---|")
    for r in ssweep:
        print(f"| {r['blend']} | {r['T']} | {r['dev_nll']:.3f} | {r['dev_mae']:.3f} | {r['dev_slope']:.3f} | {r['held_score']}/{r['held_score_n']} | {r['held_mae_mid']:.3f} |")

    nsweep = []
    for b in [0, 0.3, 0.6]:
        for t in [1.0, 1.5, 2.0]:
            for bias in [0, 0.5, 1.0]:
                c = with_(cfg, lexicalBlend__noul=b, temperature__noul=t)
                c["noulBias"] = bias
                d = calib_dev(c, dev)
                hs = {s: suite_summary(c, suites[s]) for s in HELD}
                h = calib_heldout(c, [r for r in rows if r["suite"] in HELD])
                nsweep.append({"blend": b, "T": t, "bias": bias, "dev_nll": d["noul_nll"], "dev_acc": d["noul_acc@0.5"],
                               "held_noul": sum(x["noul"][0] for x in hs.values()), "held_noul_n": sum(x["noul"][1] for x in hs.values()), "held_brier": h["noul_brier"]})
    report["noul_sweep"] = nsweep
    nb = min(nsweep, key=lambda r: r["dev_nll"])
    print("\nnoul best by dev NLL:", nb)
    print("| noul blend | T | bias | dev NLL | dev acc | HELD noul band | HELD Brier |\n|---|---|---|---|---|---|---|")
    for r in nsweep:
        print(f"| {r['blend']} | {r['T']} | {r['bias']} | {r['dev_nll']:.3f} | {r['dev_acc']:.3f} | {r['held_noul']}/{r['held_noul_n']} | {r['held_brier']:.3f} |")

    asweep = []
    for th in [0, 0.06, 0.15, 0.25, 0.35, 0.5]:
        c = with_(cfg, abstain__threshold=th)
        d = calib_dev(c, dev)
        hs = {s: suite_summary(c, suites[s]) for s in HELD}
        h = calib_heldout(c, [r for r in rows if r["suite"] in HELD])
        lab = suite_summary(c, suites["labeled-50"])
        asweep.append({"th": th, "dev_nll": d["choice_nll"], "dev_acc": d["choice_acc"], "dev_amb_conf": d["ambiguous_mean_conf"], "lab_fully": lab["fully"],
                       "held_fully": sum(x["fully"] for x in hs.values()), "held_choice": sum(x["choice"][0] for x in hs.values()), "held_nll": h["choice_nll"], "held_ece": h["choice_ece"]})
    report["abstain_sweep"] = asweep
    print("\n| abstain th | dev NLL | dev acc | dev amb conf | lab-50 fully | HELD fully | HELD choice | HELD NLL | HELD ECE |\n|---|---|---|---|---|---|---|---|---|")
    for r in asweep:
        print(f"| {r['th']} | {r['dev_nll']:.3f} | {r['dev_acc']:.3f} | {r['dev_amb_conf']:.3f} | {r['lab_fully']}/50 | {r['held_fully']}/100 | {r['held_choice']}/66 | {r['held_nll']:.3f} | {r['held_ece']:.3f} |")

    # 5. top-sigmoid distribution: how often abstain fires
    tops = {s: [max(sig(m) for m in q["margins"]) for r in (suites.get(s) or dev) for q in r["questions"] if q["type"] != "noul"] for s in ["dev"] + HELD}
    report["top_sigmoid_quantiles"] = {s: [float(np.quantile(v, x)) for x in (0.05, 0.25, 0.5)] for s, v in tops.items()}
    print("\ntop sigmoid quantiles (5/25/50%):", report["top_sigmoid_quantiles"])

    # 6. failures with neural-only vs lexical contribution
    fails = []
    neural = variants["neural-only (blend 0)"]
    for s in HELD:
        for r in suites[s]:
            g = grade_case(cfg, r)
            gn = grade_case(neural, r)
            if not g["fully"] or not gn["fully"]:
                fails.append({"suite": s, "id": r["id"], "name": r["name"], "tags": r["tags"], "state": r["state"][:160],
                              "expect": r["expect"], "shipped": g["detail"], "shipped_ok": g["fully"], "neural": gn["detail"], "neural_ok": gn["fully"]})
    report["failures"] = fails
    print(f"\n{len(fails)} held-out cases fail under shipped or neural-only")
    for f in fails:
        print(f"{f['suite']} {f['id']} {f['name']} | shipped_ok={f['shipped_ok']} {f['shipped']} | neural_ok={f['neural_ok']} {f['neural']}")
    (ROOT / f"artifacts/parity/jev/{args.tag}.json").write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()


