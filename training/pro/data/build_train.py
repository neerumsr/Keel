"""Build the Keel-Pro training corpus.

Usage (kit venv python):
  C:\\KeelWork\\decision-index\\.venv\\Scripts\\python.exe -X utf8 build_train.py [--include-unlicensed] [--only 4,5] [--scale 1.0]

Writes C:\\KeelWork\\pro\\data\\train.jsonl.gz, train-holdout.jsonl.gz, train-stats.json.
Deterministic: every builder uses rows.rng(...) seeded from fixed strings; the final shuffle uses SEED.
"""
import argparse
import collections
import gzip
import hashlib
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

SEED = "keel-pro-2026:shuffle"
HOLDOUT_PCT = 1

# (job name, module, function, kwargs, license class). License class "unlicensed" = no explicit license found;
# excluded unless --include-unlicensed.
JOBS = [
    ("winogrande", "src_knowledge", "winogrande", {"cap": 15000}, "ok"),
    ("hellaswag", "src_knowledge", "hellaswag", {"cap": 20000}, "ok"),
    ("gsm8k", "src_knowledge", "gsm8k", {"cap": 14000}, "ok"),
    ("mcq", "src_knowledge", "mmlu_pro_and_gpqa", {"cap57": 30000, "cap25": 12000}, "ok"),
    ("chess", "src_knowledge", "chessbench", {"cap": 12000}, "ok"),
    ("bbh", "synth_bbh", "bbh", {"cap": 15000}, "ok"),
    ("crux", "synth_crux", "crux", {"cap": 12000}, "ok"),
    ("cladder", "synth_cladder", "cladder", {"cap": 10000}, "ok"),
    ("anli", "src_language", "anli_proxy", {"cap": 35000}, "ok"),
    ("contractnli", "src_language", "contractnli", {"cap": 20000}, "ok"),
    ("isarcasm", "src_language", "isarcasm", {"cap": 20000}, "ok"),
    ("ragtruth", "src_language", "ragtruth", {"cap": 20000}, "ok"),
    ("nli4ct", "src_language", "nli4ct", {"cap": 20000}, "unlicensed"),
    ("vast", "src_language", "vast", {"cap": 20000}, "unlicensed"),
    ("acos", "src_language", "acos", {"cap": 15000}, "unlicensed"),
    ("banking77", "src_retrieval", "banking77", {"cap": 10000}, "ok"),
    ("clinc", "src_retrieval", "clinc", {"cap": 20000}, "ok"),
    ("esci", "src_retrieval", "esci", {"cap": 20000}, "ok"),
    ("hover", "src_retrieval", "hover", {"cap": 18000}, "ok"),
    ("toolret", "src_retrieval", "toolret", {"cap": 15000}, "ok"),
    ("bfcl", "src_tools", "bfcl", {"cap": 15000}, "ok"),
    ("apibank", "src_tools", "apibank", {"cap": 10000}, "ok"),
    ("when2call", "src_tools", "when2call", {"cap": 15000}, "ok"),
    ("home", "synth_home", "home", {"cap": 12000}, "ok"),
    ("phish", "synth_phish", "phish", {"cap": 9000}, "ok"),
    ("chords", "synth_chords", "chords", {"cap": 6000}, "ok"),
    ("sata", "synth_sata", "sata", {"cap": 8000}, "ok"),
    ("musr", "synth_musr", "musr", {"cap": 9000}, "ok"),
    ("finentity", "synth_finentity", "finentity", {"cap": 6000}, "ok"),
    ("color", "synth_color", "color", {"cap": 5000}, "ok"),
    ("newyorker", "src_arts", "newyorker", {"cap": 15000}, "ok"),
    ("habermas", "src_arts", "habermas", {"cap": 15000}, "ok"),
    ("humicroedit", "src_arts", "humicroedit", {"cap": 12000}, "unlicensed"),
]


def run_job(job, scale):
    name, mod, fn, kw, _ = job
    import importlib

    t = time.time()
    kw = {k: max(1, int(v * scale)) for k, v in kw.items()}
    rows = getattr(importlib.import_module(mod), fn)(**kw)
    if isinstance(rows, tuple):
        rows = [r for part in rows for r in part]
    return name, rows, round(time.time() - t, 1)


def content_key(r):
    return hashlib.sha256(json.dumps([r["benchmark"], r["state"], r["questions"], r["gold"]], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def pctl(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else None


def main():
    if not sys.flags.utf8_mode:
        import subprocess

        sys.exit(subprocess.call([sys.executable, "-X", "utf8", *sys.argv]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-unlicensed", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from rows import OUT
    from common import render_prompt

    out_dir = Path(a.out) if a.out else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    only = set(filter(None, a.only.split(",")))
    jobs = [j for j in JOBS if (not only or j[0] in only) and (a.include_unlicensed or j[4] != "unlicensed")]
    skipped = [j[0] for j in JOBS if j not in jobs]
    os.environ["PYTHONUTF8"] = "1"
    rows, timings = [], {}
    with ProcessPoolExecutor(max_workers=min(a.workers, 8)) as ex:
        for name, rs, secs in ex.map(run_job, jobs, [a.scale] * len(jobs)):
            print(f"{name}: {len(rs)} rows in {secs}s", flush=True)
            timings[name] = secs
            rows.extend(rs)
    seen, uniq, dups = set(), [], collections.Counter()
    for r in rows:
        k = content_key(r)
        if k in seen and r["benchmark"] != 5:  # CLINC oos_train is intentionally repeated
            dups[r["benchmark"]] += 1
            continue
        seen.add(k)
        uniq.append((k, r))
    uniq.sort(key=lambda kr: hashlib.sha256((SEED + kr[0]).encode()).hexdigest())
    random.Random(SEED).shuffle(uniq)
    train = [r for k, r in uniq if int(k[:8], 16) % 100 >= HOLDOUT_PCT]
    hold = [r for k, r in uniq if int(k[:8], 16) % 100 < HOLDOUT_PCT]
    for fname, data in (("train.jsonl.gz", train), ("train-holdout.jsonl.gz", hold)):
        with gzip.open(out_dir / fname, "wt", encoding="utf-8", compresslevel=6) as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    per_b = collections.defaultdict(lambda: {"rows": 0, "holdout": 0, "sources": collections.Counter(), "gold": collections.Counter(), "chars": []})
    for split, data in (("rows", train), ("holdout", hold)):
        for r in data:
            s = per_b[str(r["benchmark"])]
            s[split] += 1
            if split == "rows":
                s["sources"][r["source"].split("#")[0]] += 1
                g = r["gold"]["q1"]
                s["gold"][str(g)] += 1
                s["chars"].append(len(render_prompt(r["state"], r["questions"]["q1"])))
    stats = {
        "train_rows": len(train),
        "holdout_rows": len(hold),
        "duplicates_dropped": dict(dups),
        "jobs_skipped": skipped,
        "include_unlicensed": a.include_unlicensed,
        "scale": a.scale,
        "seed": SEED,
        "holdout_rule": f"sha256(content) first 8 hex mod 100 < {HOLDOUT_PCT}",
        "build_seconds": timings,
        "benchmarks": {
            b: {"rows": s["rows"], "holdout": s["holdout"], "sources": dict(s["sources"]), "gold_top": dict(s["gold"].most_common(6)), "gold_distinct": len(s["gold"]), "rendered_chars": {"p50": pctl(s["chars"], 0.5), "p95": pctl(s["chars"], 0.95), "max": max(s["chars"]) if s["chars"] else None, "over_6000": sum(c > 6000 for c in s["chars"])}}
            for b, s in sorted(per_b.items(), key=lambda kv: int(kv[0]))
        },
        "truncation_rules": {
            "11 ContractNLI": "contract text cut to <=5000 chars: all evidence spans kept, plus random other spans in document order, joined with ' ... '",
            "37 ESCI": "product title <=300, description/bullets <=600, brand/color <=100 chars (rows.clip: head 70% + ' ... ' + tail)",
            "61 HoVer": "each evidence document <=1500 chars (rows.clip)",
            "59 RAGTruth": "rows with prompt+response > 7000 chars dropped (not truncated)",
            "3 API-Bank": "none: state carries the full published catalog like DI (~30k chars); trainers with a short max_len will drop these rows",
        },
    }
    (out_dir / "train-stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "benchmarks"}, indent=1))
    for b, s in stats["benchmarks"].items():
        print(b, s["rows"], s["rendered_chars"])


if __name__ == "__main__":
    main()
