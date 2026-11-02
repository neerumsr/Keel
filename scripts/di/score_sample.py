"""Score a DI run on a fixed sample with the kit's own scorers, plus a group-bootstrap 95% CI.

The kit's `score_run_v02` iterates `suite.rows()`, so restricting the suite to the sample rows gives the
sample estimate of the public index with exactly the board's math (coverage, chance correction, gold
weights, area weights). For the CI, whole case groups are resampled with replacement inside each
benchmark (stratified, like the sample itself); duplicated groups get suffixed run/group ids so linked
cases stay whole.

usage: python scripts/di/score_sample.py --results <run>/results.jsonl --sample C:/KeelWork/di-samples/dev.jsonl.gz
                                          [--suite-dir C:/KeelWork/decision-index/suite-0.3] [--boot 200] [--out <dir>]
"""
import argparse
import collections
import contextlib
import io
import json
import random
import tempfile
from pathlib import Path

from decision_index.pipeline import score_run_v02
from decision_index.scoring.report import load_results
from decision_index.suite.io import Suite, read_jsonl

MISSING = {45: "HLE (gated, not built): scored 0"}


class SampleSuite(Suite):
    def __init__(self, directory, rows):
        super().__init__(directory)
        self._rows = rows

    def rows(self, apply_exclusions=False):
        return iter(self._rows)


def score(suite_dir, rows, results, out):
    suite = SampleSuite(suite_dir, rows)
    with contextlib.redirect_stdout(io.StringIO()):
        s = score_run_v02(suite, results, "sample", Path(out))
    return s


def boot_rows(rows, results, rng):
    by_b = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        e = r["_evaluation"]
        by_b[e["catalog_id"]][e["group_id"]].append(r)
    new_rows, new_res = [], {}
    for b, groups in by_b.items():
        gids = list(groups)
        for k in range(len(gids)):
            g = gids[rng.randrange(len(gids))]
            for r in groups[g]:
                e = dict(r["_evaluation"])
                rid = f'{e["run_id"]}#b{k}'
                e["run_id"], e["group_id"] = rid, f'{e["group_id"]}#b{k}'
                nr = dict(r, _evaluation=e, id=f'{r.get("id")}#b{k}')
                new_rows.append(nr)
                if r["_evaluation"]["run_id"] in results:
                    res = dict(results[r["_evaluation"]["run_id"]])
                    res["run_id"] = rid
                    new_res[rid] = res
    return new_rows, new_res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--suite-dir", default="C:/KeelWork/decision-index/suite-0.3")
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = list(read_jsonl(a.sample))
    results = load_results(a.results)
    out = Path(a.out or Path(a.results).parent)
    s = score(a.suite_dir, rows, results, out)
    point = s["decision_index"] if "decision_index" in s else s["index"]
    rng = random.Random(a.seed)
    vals = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(a.boot):
            br, bres = boot_rows(rows, results, rng)
            vals.append(score(a.suite_dir, br, bres, td)["decision_index"])
    vals.sort()
    ci = [vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]] if vals else None
    per = {n: {k: b.get(k) for k in ("skill", "raw", "coverage")} for n, b in s.get("index_benchmarks", {}).items() if b.get("in_index", True)}
    lat = s.get("latency_ms", {})
    summary = {"public_index": point, "ci95": ci, "boot": a.boot, "rows": len(rows), "answered": sum(1 for r in rows if results.get(r["_evaluation"]["run_id"], {}).get("status") == "ok"),
               "areas": [{k: x[k] for k in ("id", "skill", "coverage")} for x in s["areas"]], "per_benchmark": per, "latency_ms": lat, "missing": MISSING}
    (out / "sample-score.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("public_index", "ci95", "rows", "answered", "areas", "latency_ms")}, indent=1))


if __name__ == "__main__":
    main()
