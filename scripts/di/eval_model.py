"""DI eval service: run a local HF model (or the Keel HTTP API) on a fixed DI sample and score it.

usage (kit venv python, from anywhere):
  python scripts/di/eval_model.py --model-dir C:/KeelWork/pro/runs/it1/merged --sample dev [--name it1] [--limit N]
  python scripts/di/eval_model.py --engine http --base-url http://127.0.0.1:8080/api --http-model decider-3.0.0 --sample dev --name keel-lite

Writes C:/KeelWork/di-runs/<name>-<sample>-<stamp>/ (results.jsonl, scores, sample-score.json), appends a line to
C:/KeelWork/di-samples/history.jsonl and a row to artifacts/parity/pro/di-results.md. See artifacts/parity/pro/EVAL.md.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORK = Path(os.environ.get("KEELWORK", "C:/KeelWork"))
KIT = WORK / "decision-index"
PY = KIT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
RESULTS_MD = REPO / "artifacts/parity/pro/di-results.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir")
    ap.add_argument("--engine", default="hybrid", choices=["hybrid", "http"])
    ap.add_argument("--base-url")
    ap.add_argument("--http-model")
    ap.add_argument("--sample", choices=["dev", "report"], required=True)
    ap.add_argument("--name")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--resume", help="existing run dir to resume")
    ap.add_argument("--end-token", action="store_true", help="Keel-Pro serving policy: score key + <|im_end|> (see hybrid_engine.py)")
    ap.add_argument("--letters", action="store_true", help="Keel-Pro letters serving policy: single-token option labels (see hybrid_engine.py)")
    ap.add_argument("--load-4bit", action="store_true", help="load --model-dir as a bitsandbytes NF4 base (QLoRA checkpoints)")
    ap.add_argument("--adapter", help="LoRA adapter dir applied on top of --model-dir (kept unmerged with --load-4bit)")
    ap.add_argument("--tta", type=int, default=1, help="letters only: average option probabilities over this many option orders (1 = as given, 2 = + reversed)")
    a = ap.parse_args()

    rows = WORK / "di-samples" / f"{a.sample}.jsonl.gz"
    name = a.name or (Path(a.model_dir).name if a.model_dir else a.http_model)
    out = Path(a.resume) if a.resume else WORK / "di-runs" / f"{name}-{a.sample}-{time.strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(HERE), PYTHONIOENCODING="utf-8", PYTHONUTF8="1", HF_HUB_DISABLE_XET="1")
    cmd = [str(PY), "-m", "decision_index", "run", "--rows", str(rows), "--out", str(out), "--compact"]
    if a.engine == "hybrid":
        cmd += ["--engine", "hybrid_engine:ExactTransformersEngine", "--model", a.model_dir]
        if a.end_token:
            cmd += ["--option", "end_token=1"]
        if a.letters:
            cmd += ["--option", "letters=1"]
        if a.load_4bit:
            cmd += ["--option", "load_4bit=1"]
        if a.adapter:
            cmd += ["--option", f"adapter={a.adapter}"]
        if a.tta > 1:
            cmd += ["--option", f"tta={a.tta}"]
    else:
        cmd += ["--engine", "http", "--option", f"base_url={a.base_url}", "--option", f"model={a.http_model}"]
    if a.limit:
        cmd += ["--limit", str(a.limit)]
    t = time.time()
    with (out / "run.log").open("w", encoding="utf-8") as lf:
        rc = subprocess.call(cmd, cwd=str(KIT), env=env, stdout=lf, stderr=subprocess.STDOUT)
    if rc:
        sys.exit(f"run failed ({rc}); see {out / 'run.log'}")
    minutes = round((time.time() - t) / 60, 1)
    sc = subprocess.run([str(PY), str(HERE / "score_sample.py"), "--results", str(out / "results.jsonl"), "--sample", str(rows), "--boot", str(a.boot)], cwd=str(KIT), env=env, capture_output=True, text=True)
    if sc.returncode:
        sys.exit(sc.stderr[-3000:])
    s = json.loads((out / "sample-score.json").read_text())
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "name": name, "model_dir": a.model_dir or f"{a.base_url}#{a.http_model}", "adapter": a.adapter, "load_4bit": a.load_4bit, "sample": a.sample, "scoring": "http" if a.engine == "http" else ("letters" + (f"-tta{a.tta}" if a.tta > 1 else "") if a.letters else "end-token" if a.end_token else "kit"), "rows": s["rows"], "answered": s["answered"], "limit": a.limit,
           "public_index": s["public_index"], "ci95": s["ci95"], "areas": s["areas"], "per_benchmark": s["per_benchmark"], "latency_ms": s["latency_ms"], "minutes": minutes, "run_dir": str(out)}
    with (WORK / "di-samples" / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    if RESULTS_MD.exists() and not a.limit:
        ci = s["ci95"] or ["", ""]
        areas = " / ".join(f'{x["skill"] * 100:.1f}' for x in s["areas"])
        med = s["latency_ms"].get("median", s["latency_ms"].get("p50", ""))
        line = f'| {rec["time"]} | {name} | {a.sample} | {rec["scoring"]} | {s["rows"]} | **{s["public_index"]:.2f}** | {ci[0]:.2f}–{ci[1]:.2f} | {areas} | {med} | {minutes} |\n'
        txt = RESULTS_MD.read_text(encoding="utf-8")
        RESULTS_MD.write_text(txt.rstrip("\n") + "\n" + line, encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("name", "sample", "rows", "answered", "public_index", "ci95", "minutes")}))


if __name__ == "__main__":
    main()
