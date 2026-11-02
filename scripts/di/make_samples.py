"""Build the disjoint dev and report samples of the DI 0.3 suite (CONTRACT.md Phase 3).

Per benchmark, whole case groups are ranked by a seeded hash (as in the kit's `suite sample`), then
the dev sample takes groups until it holds >= --dev rows and the report sample takes the following
groups until it holds >= --report rows. Benchmarks with fewer rows than dev + report are split 1:2 by
rows. Exclusions and edition read-time skips are applied, so every sampled row is a scored row.

usage: python scripts/di/make_samples.py [--suite-dir C:/KeelWork/decision-index/suite-0.3]
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

from decision_index.suite.io import Suite, dumps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite-dir", default="C:/KeelWork/decision-index/suite-0.3")
    ap.add_argument("--out-dir", default="C:/KeelWork/di-samples")
    ap.add_argument("--dev", type=int, default=40)
    ap.add_argument("--report", type=int, default=80)
    ap.add_argument("--seed", type=int, default=20261030)
    a = ap.parse_args()

    suite = Suite(a.suite_dir, "0.3")
    groups = collections.defaultdict(list)
    for r in suite.rows(apply_exclusions=True):
        e = r["_evaluation"]
        groups[(e["catalog_id"], e["group_id"])].append(r)
    by_bench = collections.defaultdict(list)
    for (cid, gid), rows in groups.items():
        by_bench[cid].append((hashlib.sha256(f"{a.seed}:{cid}:{gid}".encode()).hexdigest(), rows))

    picked = {"dev": [], "report": []}
    stats = {}
    for cid in sorted(by_bench):
        ranked = [rows for _, rows in sorted(by_bench[cid], key=lambda t: t[0])]
        total = sum(len(g) for g in ranked)
        dev_target, rep_target = a.dev, a.report
        if total < a.dev + a.report:
            dev_target, rep_target = max(1, total // 3), total
        i, n = 0, {"dev": 0, "report": 0}
        for name, target in (("dev", dev_target), ("report", rep_target)):
            while i < len(ranked) and n[name] < target:
                picked[name].extend(ranked[i])
                n[name] += len(ranked[i])
                i += 1
        stats[cid] = {"rows": total, "groups": len(ranked), **n}

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ids = {}
    for name, rows in picked.items():
        with gzip.open(out / f"{name}.jsonl.gz", "wt", encoding="utf-8") as f:
            for r in rows:
                f.write(dumps(r) + "\n")
        ids[name] = {r["_evaluation"]["run_id"] for r in rows}
    assert not ids["dev"] & ids["report"], "dev and report overlap"
    meta = {"seed": a.seed, "suite": a.suite_dir, "dev_rows": len(picked["dev"]), "report_rows": len(picked["report"]),
            "benchmarks": len(stats), "per_benchmark": stats}
    (out / "samples.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: v for k, v in meta.items() if k != "per_benchmark"}))


if __name__ == "__main__":
    main()
