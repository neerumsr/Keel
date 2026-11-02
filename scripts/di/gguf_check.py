"""Check that a Keel-Pro GGUF served by llama-server picks the same option as the transformers model did in a DI run.

Builds the letters prompt (training/pro/common.py) for the first --n single-choice dev questions, sends the token ids
to llama-server's /completion with n_predict=1, takes the most probable label token among the top --top tokens and
compares it with the choice recorded in the run's results.jsonl. Also reports llama-server's prompt-eval time.

usage: python scripts/di/gguf_check.py --tokenizer <hf model dir> --run-dir <di run dir> --url http://127.0.0.1:8091 [--n 40]
"""
import argparse
import gzip
import json
import statistics
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "training" / "pro"))
from common import prompt_ids_letters  # noqa: E402


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--dev", default=r"C:\KeelWork\di-samples\dev.jsonl.gz")
    ap.add_argument("--url", default="http://127.0.0.1:8091")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--max-tokens", type=int, default=4000)
    a = ap.parse_args()
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.tokenizer)
    hf = {}
    for line in open(Path(a.run_dir) / "results.jsonl", encoding="utf-8"):
        r = json.loads(line)
        hf[r["group_id"]] = (r.get("response") or {}).get("answers") or {}
    agree = n = 0
    ms = []
    for line in gzip.open(a.dev, "rt", encoding="utf-8"):
        row = json.loads(line)
        gid = row.get("_evaluation", {}).get("group_id", row["id"])
        if gid not in hf:
            continue
        for qid, q in row["questions"].items():
            if q.get("type") != "choice" or qid not in hf[gid] or "choice" not in hf[gid][qid]:
                continue
            ids, order, lids = prompt_ids_letters(tok, row.get("state"), q)
            if len(ids) > a.max_tokens:
                continue
            out = post(a.url + "/completion", {"prompt": ids, "n_predict": 1, "n_probs": a.top, "temperature": 0, "cache_prompt": False})
            top = out["completion_probabilities"][0]["top_logprobs"] if "top_logprobs" in out["completion_probabilities"][0] else out["completion_probabilities"][0]["top_probs"]
            pick = None
            for t in top:
                if t["id"] in lids:
                    pick = order[lids.index(t["id"])]
                    break
            n += 1
            agree += pick == hf[gid][qid]["choice"]
            ms.append(out.get("timings", {}).get("prompt_ms", 0) + out.get("timings", {}).get("predicted_ms", 0))
            break
        if n >= a.n:
            break
    print(json.dumps({"questions": n, "agree": agree, "agreement": round(agree / max(n, 1), 3), "median_ms": round(statistics.median(ms), 1) if ms else None}))


if __name__ == "__main__":
    main()
