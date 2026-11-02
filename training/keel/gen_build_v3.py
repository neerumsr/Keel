"""Build Keel data v3.

    python training/keel/gen_build_v3.py --n 300000 --seed 7 --out training/data/v3

Mix (fractions of --n):
  * LLM-authored seed banks (training/data/v3/seeds/*.jsonl) expanded into many
    views each (option renaming/shuffling, 2-12 options, 2-10 score levels,
    none-fits, injection + long-context wrappers, label yes/no reframes)
  * programmatic compositional seeds (gen_prog.py), one view each
  * v2 families (families.py) so earlier skills do not regress
  * labeled-50 copies (in-sample, as build_data.py) and MNLI replay
  * optional public TRAIN splits when training/data/public/READY.json exists
Dev = groups whose *seed* hashes into the dev bucket (dev states never appear in train).
Every generated state sharing a 6-gram with holdout / holdout-b / open eval states is
dropped, then re-checked as a hard failure.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import pathlib
import random
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel import families as v2  # noqa: E402
from keel.families_v3 import expand, seed_text, valid_seed  # noqa: E402
from keel.gen_prog import prog_seed  # noqa: E402
from keel.gen_open import open_group  # noqa: E402
from keel.gen_safety import safety_group  # noqa: E402
from keel.gen_safety2 import principle_group  # noqa: E402
import keel.gen_safety_more  # noqa: E402,F401  (extends the safety pools)
from keel.hypothesis import hypotheses, state_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "training" / "data"
PREFIX = re.compile(r"^(?:[A-Z][\w' ]{0,24}?[,:\-]\s+)")


def grams(text: str, n: int = 6) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def core(text: str) -> str:
    return " ".join(re.findall(r"\w+", PREFIX.sub("", text).lower()))


def bucket(text: str, mod: int) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16) % mod


SUFFIX = re.compile(r"(?<=[.!?])\s+([^.!?]{1,24}[.!?])$")


def strip_boilerplate(rows: list[dict], info: collections.Counter) -> None:
    """Remove mechanically repeated lead-ins / tails an author bolted onto many states."""
    pre, suf = collections.Counter(), collections.Counter()
    for s in rows:
        if isinstance(s["state"], str):
            m = PREFIX.match(s["state"])
            if m:
                pre[m.group(0).strip()] += 1
            m = SUFFIX.search(s["state"])
            if m:
                suf[m.group(1).strip()] += 1
    bad_pre = {k for k, v in pre.items() if v >= 8}
    bad_suf = {k for k, v in suf.items() if v >= 8}
    for s in rows:
        st = s["state"]
        if not isinstance(st, str):
            continue
        m = PREFIX.match(st)
        if m and m.group(0).strip() in bad_pre:
            rest = st[m.end():]
            st = rest[:1].upper() + rest[1:]
            info["stripped_prefix"] += 1
        m = SUFFIX.search(st)
        if m and m.group(1).strip() in bad_suf:
            st = st[: m.start()]
            info["stripped_suffix"] += 1
        s["state"] = st.strip()


def load_seeds(seed_dir: pathlib.Path) -> tuple[list[dict], dict]:
    seeds, info = [], collections.Counter()
    seen = set()
    for f in sorted(seed_dir.glob("*.jsonl")):
        raw = []
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError:
                info["bad_json"] += 1
        strip_boilerplate(raw, info)
        for s in raw:
            if not valid_seed(s):
                info["invalid"] += 1
                continue
            key = (s["task"], core(seed_text(s)))
            if key in seen:
                info["dup"] += 1
                continue
            seen.add(key)
            s["_src"] = f.stem
            seeds.append(s)
    info["kept"] = len(seeds)
    return seeds, dict(info)


def eval_groups(case: dict, copies: int) -> list[dict]:
    out = []
    exp = case["expect"]
    for qid, q in case["questions"].items():
        target = None
        if exp.get("choice") and exp["choice"]["id"] == qid:
            keys = list(q["criteria"].keys())
            if exp["choice"].get("maxConfidence") is not None:
                target = [1 / len(keys)] * len(keys)
            else:
                target = [0.96 if k == exp["choice"]["key"] else 0.04 / (len(keys) - 1) for k in keys]
        elif exp.get("score") and exp["score"]["id"] == qid:
            target = v2.ordinal(len(q["criteria"]), (exp["score"]["min"] + exp["score"]["max"]) / 2, 0.4)
        elif exp.get("noul") and exp["noul"]["id"] == qid:
            p = 0.9 if exp["noul"].get("min") is not None else 0.1
            target = [p, 1 - p]
        if target is not None:
            out.extend({"family": "labeled50", "state": case["state"], "question": q, "target": target} for _ in range(copies))
    return out


def nli_replay(n: int, seed: int) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset("nyu-mll/glue", "mnli", split="train").shuffle(seed=seed).select(range(n))
    return [{"family": "nli", "state": r["premise"], "pair": r["hypothesis"], "label": 1.0 if r["label"] == 0 else 0.0} for r in ds]


def public_rows(limit: int, rng: random.Random) -> tuple[list[dict], list[str]]:
    ready = DATA / "public" / "READY.json"
    if not ready.exists() or limit <= 0:
        return [], []
    meta = json.loads(ready.read_text(encoding="utf-8"))
    files = meta.get("files") or meta.get("train") or []
    if isinstance(files, dict):
        files = list(files.values())
    rows, used = [], []
    for f in files:
        p = pathlib.Path(f)
        p = p if p.is_absolute() else (ROOT / p if (ROOT / p).exists() else DATA / "public" / p)
        if not p.exists() or "test" in p.name.lower():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "question" in r and "target" in r and "state" in r:
                r.setdefault("family", f"public_{p.stem}")
                rows.append(r)
        used.append(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p))
    rng.shuffle(rows)
    return rows[:limit], used


SAFETY_HINTS = ("agent_action", "is_security_risk", "change_risk", "moderation", "has_threat", "is_phishing", "contains_injection", "injection", "has_secret", "has_pii", "v3o_gate", "v3s_")


def core_subset(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Family-balanced sample (water-filling quotas); safety-gating families get double weight."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["family"]].append(r)
    w = {f: (2.0 if any(h in f for h in SAFETY_HINTS) else 1.0) for f in by}
    quota = {f: 0 for f in by}
    left, active = n, set(by)
    while left > 0 and active:
        tw = sum(w[f] for f in active)
        give = {f: max(1, int(left * w[f] / tw)) for f in active}
        for f in list(active):
            g = min(give[f], len(by[f]) - quota[f], left)
            quota[f] += g
            left -= g
            if quota[f] >= len(by[f]):
                active.discard(f)
            if left <= 0:
                break
    out = []
    for f, q in quota.items():
        out += rng.sample(by[f], q)
    rng.shuffle(out)
    return out


def ok_group(g: dict) -> bool:
    q = g["question"]
    try:
        hs = hypotheses(q)
    except Exception:
        return False
    t = g["target"]
    return len(hs) == len(t) and 2 <= len(hs) <= 12 and abs(sum(t) - 1) < 1e-3 and all(x >= 0 for x in t)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300000, help="target generated groups (before labeled50 / nli / public)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(DATA / "v3"))
    ap.add_argument("--seeds", default=None, help="seed bank dir (default <out>/seeds)")
    ap.add_argument("--llm-frac", type=float, default=0.45)
    ap.add_argument("--v2-frac", type=float, default=0.08)
    ap.add_argument("--open-frac", type=float, default=0.2, help="generic open-domain questions (gen_open.py)")
    ap.add_argument("--safety-frac", type=float, default=0.12, help="safety-category + principle groups (gen_safety*.py)")
    ap.add_argument("--ood-tasks", default="email_urgency,model_route,wants_refund,v3o_degree_politeness,v3o_mention_apology",
                    help="tasks/families held out of train entirely and written to dev_ood.jsonl (leave-family-out calibration)")
    ap.add_argument("--ood-max", type=int, default=4000)
    ap.add_argument("--core", type=int, default=80000, help="family-balanced, safety-weighted subset written to core.jsonl (0 = off)")
    ap.add_argument("--max-views", type=int, default=60)
    ap.add_argument("--nli", type=int, default=-1, help="MNLI replay rows (-1 = 5%% of n, max 30000)")
    ap.add_argument("--public", type=int, default=-1, help="public train rows to mix (-1 = all listed in READY, max 15%% of n)")
    ap.add_argument("--labeled-copies", type=int, default=6)
    ap.add_argument("--dev-max", type=int, default=6000)
    ap.add_argument("--version", type=int, default=0, help="if >0, write READY.json with this version")
    args = ap.parse_args()
    t0 = time.time()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    evals = json.loads((DATA / "evals.json").read_text(encoding="utf-8"))
    blocked: set = set()
    for suite in ("holdout", "holdoutB", "open"):
        for case in evals[suite]:
            blocked |= grams(state_text(case["state"]))

    seeds, seed_info = load_seeds(pathlib.Path(args.seeds) if args.seeds else out / "seeds")
    clean = []
    for s in seeds:
        if grams(seed_text(s)) & blocked:
            seed_info["contaminated_seed"] = seed_info.get("contaminated_seed", 0) + 1
        else:
            clean.append(s)
    seeds = clean

    rows_train: list[dict] = []
    rows_dev: list[dict] = []
    rows_ood: list[dict] = []
    ood = {t for t in args.ood_tasks.split(",") if t}
    seen: set[str] = set()
    counts = collections.Counter()

    def add(g: dict, dev: bool, task: str = "") -> None:
        g.pop("_src", None)
        key = json.dumps([g["state"], g["question"]], sort_keys=True, ensure_ascii=False)
        if key in seen:
            counts["dup"] += 1
            return
        seen.add(key)
        if not ok_group(g):
            counts["malformed"] += 1
            return
        if grams(state_text(g["state"])) & blocked:
            counts["contaminated"] += 1
            return
        if task in ood or g["family"] in ood:
            if len(rows_ood) < args.ood_max:
                rows_ood.append(g)
            counts["ood"] += 1
            return
        (rows_dev if dev else rows_train).append(g)
        counts["kept"] += 1

    # 1. LLM seed banks, many views each
    n_llm = int(args.n * args.llm_frac) if seeds else 0
    by_task = collections.Counter(s["task"] for s in seeds)
    weight = {t: (2.0 if c <= 300 else 1.0) for t, c in by_task.items()}
    wsum = sum(weight[s["task"]] for s in seeds)
    views = max(3, min(args.max_views, round(n_llm / max(1.0, wsum)))) if seeds else 0
    for s in seeds:
        dev = bucket(core(seed_text(s)), 25) == 0
        # rarer tasks get a few more views so the label space stays balanced
        v = min(args.max_views, round(views * weight[s["task"]]))
        for _ in range(v):
            g = expand(rng, s)
            g["src"] = s.get("_src", "seed")
            add(g, dev, s["task"])
    counts["llm_target"] = n_llm

    # 2. programmatic seeds
    n_prog = int(args.n * (1 - args.llm_frac - args.v2_frac - args.open_frac - args.safety_frac)) if seeds else int(args.n * (1 - args.v2_frac - args.open_frac - args.safety_frac))
    made = 0
    tries = 0
    while made < n_prog and tries < n_prog * 3:
        tries += 1
        s = prog_seed(rng)
        g = expand(rng, s, family=f"v3p_{s['task']}")
        g["src"] = "prog"
        before = counts["kept"]
        add(g, bucket(core(seed_text(s)), 40) == 0, s["task"])
        made += counts["kept"] - before

    # 2b. generic open-domain questions
    n_open = int(args.n * args.open_frac)
    made = tries = 0
    while made < n_open and tries < n_open * 3:
        tries += 1
        g = open_group(rng)
        before = counts["kept"]
        add(g, bucket(core(state_text(g["state"])), 40) == 0)
        made += counts["kept"] - before

    # 2c. safety categories (generic taxonomy) + principle generators, with over-caution counter-examples
    n_safe = int(args.n * args.safety_frac)
    made = tries = 0
    while made < n_safe and tries < n_safe * 4:
        tries += 1
        g = safety_group(rng) if rng.random() < 0.5 else principle_group(rng)
        g["src"] = "safety"
        before = counts["kept"]
        add(g, bucket(core(state_text(g["state"])), 40) == 0)
        made += counts["kept"] - before
    counts["safety_made"] = made

    # 3. v2 families (fresh draws)
    n_v2 = int(args.n * args.v2_frac)
    for g in v2.generate(n_v2, args.seed + 1):
        g["src"] = "v2"
        add(g, rng.random() < 0.02)

    # dev cap
    rng.shuffle(rows_dev)
    spill = rows_dev[args.dev_max :]
    rows_dev = rows_dev[: args.dev_max]
    counts["dev_spill_dropped"] = len(spill)  # not moved to train: their seeds are dev-bucket states

    # 4. labeled50, MNLI, public
    labeled = [r for case in evals["labeled"] for r in eval_groups(case, args.labeled_copies)]
    rows_train += labeled
    n_nli = args.nli if args.nli >= 0 else min(30000, args.n // 20)
    nli_rows: list[dict] = []
    if n_nli:
        try:
            nli_rows = nli_replay(n_nli, args.seed)
        except Exception as e:  # offline / missing dataset
            print(f"warning: MNLI replay skipped: {e}", flush=True)
    rows_train += nli_rows
    n_pub = args.public if args.public >= 0 else int(args.n * 0.15)
    pub, pub_files = public_rows(n_pub, rng)
    pub_kept = []
    for r in pub:
        if grams(state_text(r["state"])) & blocked:
            counts["public_contaminated"] += 1
            continue
        pub_kept.append(r)
    rows_train += pub_kept
    rng.shuffle(rows_train)

    for r in rows_train + rows_dev:
        if "question" in r and r["family"] != "labeled50" and grams(state_text(r["state"])) & blocked:
            raise SystemExit("contamination: a training state overlaps a held-out/open eval state")

    with (out / "train.jsonl").open("w", encoding="utf-8") as f:
        for r in rows_train:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (out / "dev.jsonl").open("w", encoding="utf-8") as f:
        for r in rows_dev:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (out / "dev_ood.jsonl").open("w", encoding="utf-8") as f:
        for r in rows_ood:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts["dev_ood"] = len(rows_ood)
    core_rows = core_subset(rows_train, args.core, random.Random(args.seed + 5)) if args.core else []
    if core_rows:
        with (out / "core.jsonl").open("w", encoding="utf-8") as f:
            for r in core_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts["core"] = len(core_rows)

    write_stats(out, rows_train, rows_dev, counts, seed_info, by_task, views, len(nli_rows), pub_files, len(pub_kept), args, time.time() - t0)
    if args.version:
        fams = collections.Counter(r["family"] for r in rows_train)
        ready = {"version": args.version, "groups": len(rows_train), "dev_groups": len(rows_dev),
                 "files": {"train": (out / "train.jsonl").relative_to(ROOT).as_posix(), "dev": (out / "dev.jsonl").relative_to(ROOT).as_posix(), "dev_ood": (out / "dev_ood.jsonl").relative_to(ROOT).as_posix(), "stats": (out / "stats.md").relative_to(ROOT).as_posix(), **({"core": (out / "core.jsonl").relative_to(ROOT).as_posix()} if core_rows else {})},
                 "families": len(fams), "createdAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "builder": f"python training/keel/gen_build_v3.py --n {args.n} --seed {args.seed} --out {out.relative_to(ROOT).as_posix()} --version {args.version}",
                 "ood_families": sorted(ood), "includes_public": bool(pub_files), "core_groups": len(core_rows), "notes": "core.jsonl = family-balanced, safety-weighted subset of train for compute-limited runs. train.jsonl already includes public TRAIN rows (training/data/public) and MNLI replay; do not mix them again. dev_ood.jsonl = families held out of train entirely (leave-family-out calibration). Same jsonl schema as v1/v2 (train.py --train/--dev). Extra keys 'src','tag' are ignored by train.py. Contamination filter (6-gram vs holdout/holdoutB/open) on."}
        (out / "READY.json").write_text(json.dumps(ready, indent=1), encoding="utf-8")
    print(f"train={len(rows_train)} dev={len(rows_dev)} seeds={len(seeds)} views/seed={views} {dict(counts)} in {time.time() - t0:.0f}s", flush=True)


def write_stats(out, train, dev, counts, seed_info, by_task, views, n_nli, pub_files, n_pub, args, secs):
    fams = collections.Counter(r["family"] for r in train)
    qtype = collections.Counter(r["question"]["type"] if "question" in r else "nli" for r in train)
    src = collections.Counter(r.get("src", "-") for r in train)
    tags = collections.Counter(r.get("tag", "-") for r in train if "question" in r)
    nopt = collections.Counter(len(r["target"]) for r in train if "question" in r)
    lens = [len(state_text(r["state"]).split()) for r in train]
    uniq_states = len({state_text(r["state"]) for r in train})
    gold = collections.defaultdict(collections.Counter)
    for r in train:
        if "question" in r and r["question"]["type"] in ("choice", "noul"):
            t = r["target"]
            gold[r["family"]]["abstain" if max(t) < 0.5 else ("pos%d" % t.index(max(t)) if r["question"]["type"] == "choice" else ("yes" if t[0] >= 0.5 else "no"))] += 1
    total_gen = counts.get("kept", 0) + counts.get("dup", 0) + counts.get("contaminated", 0) + counts.get("malformed", 0)
    L = [f"# Keel data v3 stats", "", f"Built {dt.datetime.now().isoformat(timespec='seconds')} in {secs:.0f}s with `--n {args.n} --seed {args.seed}`.", "",
         f"- train groups: **{len(train)}** · dev groups: **{len(dev)}** (dev states come from held-back seeds; never in train)",
         f"- seed banks: {seed_info} · views per seed: {views} · tasks: {dict(by_task)}",
         f"- generated {total_gen}: dedupe dropped {counts.get('dup', 0)} ({100 * counts.get('dup', 0) / max(1, total_gen):.1f}%), "
         f"6-gram contamination dropped {counts.get('contaminated', 0)}, malformed {counts.get('malformed', 0)}, dev overflow dropped {counts.get('dev_spill_dropped', 0)}",
         f"- MNLI replay: {n_nli} · public rows: {n_pub} from {pub_files or 'none (no training/data/public/READY.json)'}",
         f"- state length (words): mean {sum(lens) / max(1, len(lens)):.1f}, p50 {sorted(lens)[len(lens) // 2]}, p95 {sorted(lens)[int(len(lens) * 0.95)]}, max {max(lens)}",
         f"- unique state texts in train: {uniq_states}",
         f"- question types: {dict(qtype)}", f"- options/levels per question: {dict(sorted(nopt.items()))}",
         f"- sources: {dict(src)}", f"- tags: {dict(tags.most_common())}", "",
         "Note: unlike v1/v2, v3 deliberately covers open-domain tasks (sentiment, intent, moderation, PII, leads, clauses...). open-60 is therefore no longer "
         "*domain*-out-of-distribution; it stays *state*-disjoint via the 6-gram filter. Blind (data-1) is the honest generalization test.", "",
         "| family | groups | label balance (argmax position / yes-no / abstain) |", "|---|---:|---|"]
    for fam, c in fams.most_common():
        bal = ", ".join(f"{k}:{v}" for k, v in sorted(gold[fam].items())) if fam in gold else ""
        L.append(f"| {fam} | {c} | {bal} |")
    (out / "stats.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
