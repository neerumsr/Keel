"""train-2 trainer: larger cross-encoders (teacher / Keel-3-Pro) and KD students on CPU.

Reuses the loss/eval of train.py and adds what a CPU time budget needs:
multiple train files, per-file subsampling, a wall-clock budget, optional frozen
word embeddings (DeBERTa-v3 has a 128k vocab), precomputed teacher margins
(--teacher-labels, from t2_label.py) and a quick raw-margin check on the
in-repo holdout/open fixtures (training/data/evals.json, never trained on).

    python training/keel/t2_train.py --base models/teacher-deberta-xsmall --out training/runs/t2-dxs \
        --train training/data/train.jsonl --minutes 80 --threads 12
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
import time

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.hypothesis import hypotheses, state_text  # noqa: E402
from keel.train import evaluate, group_loss, margins_for, to_pairs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_jsonl(path: pathlib.Path) -> list[dict]:
    # split on "\n" only: str.splitlines() also splits on U+2028/U+0085 inside JSON strings (civil_comments)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def group_key(row: dict) -> str:
    if row.get("family") == "nli":
        return "nli\t" + row["state"] + "\t" + row["pair"]
    return state_text(row["state"]) + "\t" + json.dumps(row["question"], sort_keys=True)


def load_train(specs: list[str], rng: random.Random) -> list[dict]:
    """spec = path[:max_groups]."""
    rows: list[dict] = []
    for spec in specs:
        path, _, cap = spec.partition("::")
        part = load_jsonl(pathlib.Path(path))
        rng.shuffle(part)
        if cap:
            part = part[: int(cap)]
        print(f"train file {path}: {len(part)} groups", flush=True)
        rows += part
    return rows


@torch.no_grad()
def fixture_check(model, tok, max_len: int, device: str) -> dict:
    """Raw-margin accuracy on holdout/holdoutB/open (no temperature, no lexical blend)."""
    model.eval()
    data = json.loads((ROOT / "training/data/evals.json").read_text(encoding="utf-8"))
    out = {}
    for suite in ["holdout", "holdoutB", "open"]:
        ok = tot = safety = 0
        for case in data[suite]:
            probs = {}
            for qid, q in case["questions"].items():
                hs = hypotheses(q)
                st = state_text(case["state"])
                enc = tok([st] * len(hs), hs, padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(device)
                lg = model(**enc).logits
                m = lg[:, 0] - lg[:, 1]
                if q["type"] == "noul":
                    probs[qid] = ("noul", float(torch.sigmoid(m[0] - m[1])), q)
                else:
                    probs[qid] = (q["type"], F.softmax(m, 0).tolist(), q)
            ex = case["expect"]
            if "choice" in ex:
                kind, p, q = probs[ex["choice"]["id"]]
                keys = list(q["criteria"].keys())
                pick = keys[p.index(max(p))]
                ok += int(pick == ex["choice"]["key"])
                tot += 1
                if "safetyMiss" in ex and pick in ex["safetyMiss"]["keys"]:
                    safety += 1
            if "score" in ex:
                kind, p, q = probs[ex["score"]["id"]]
                ev = sum(i * x for i, x in enumerate(p))
                ok += int(ex["score"].get("min", -1e9) <= ev <= ex["score"].get("max", 1e9))
                tot += 1
            if "noul" in ex:
                kind, p, q = probs[ex["noul"]["id"]]
                ok += int(ex["noul"].get("min", -1e9) <= p <= ex["noul"].get("max", 1e9))
                tot += 1
        out[suite] = {"acc": round(ok / max(1, tot), 4), "n": tot, "safety": safety}
    model.train()
    return out


def load_teacher_labels(path: str | None) -> dict[str, list[float]]:
    if not path:
        return {}
    table = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8").split("\n"):
        if line.strip():
            r = json.loads(line)
            table[r["key"]] = r["margins"]
    print(f"teacher labels: {len(table)} groups", flush=True)
    return table


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--train", nargs="+", default=[str(ROOT / "training/data/train.jsonl")], help="path or path::max_groups")
    ap.add_argument("--dev", default=str(ROOT / "training/data/dev.jsonl"))
    ap.add_argument("--dev-max", type=int, default=0, help="cap dev groups for faster evals (0 = all)")
    ap.add_argument("--epochs", type=float, default=1)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--minutes", type=float, default=85, help="wall-clock budget; schedule assumes it is the binding limit")
    ap.add_argument("--sec-per-step", type=float, default=0, help="if >0, size the LR schedule as minutes*60/sec_per_step")
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--pairs-per-batch", type=int, default=64)
    ap.add_argument("--max-len", type=int, default=160)
    ap.add_argument("--pointwise", type=float, default=0.5)
    ap.add_argument("--freeze-embeddings", action="store_true")
    ap.add_argument("--freeze-layers", type=int, default=0, help="freeze the bottom N encoder layers")
    ap.add_argument("--teacher-labels", default=None, help="jsonl {key, margins} from t2_label.py")
    ap.add_argument("--kd", type=float, default=0.5)
    ap.add_argument("--kd-temp", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--eval-every", type=int, default=300)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    device = "cpu"
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForSequenceClassification.from_pretrained(args.base, dtype=torch.float32).to(device)
    if args.freeze_embeddings:
        emb = model.get_input_embeddings()
        emb.weight.requires_grad_(False)
    if args.freeze_layers:
        enc = getattr(model, model.base_model_prefix).encoder
        for layer in enc.layer[: args.freeze_layers]:
            layer.requires_grad_(False)
    params = [p for p in model.parameters() if p.requires_grad]
    print(f"trainable params {sum(p.numel() for p in params) / 1e6:.1f}M of {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M", flush=True)

    train_rows = load_train(args.train, rng)
    dev_rows = load_jsonl(pathlib.Path(args.dev))
    if args.dev_max:
        dev_rows = random.Random(1).sample(dev_rows, min(args.dev_max, len(dev_rows)))
    tlabels = load_teacher_labels(args.teacher_labels)

    pairs_total = sum(len(to_pairs(r)[1]) for r in train_rows)
    total_steps = int(math.ceil(pairs_total / args.pairs_per_batch) * args.epochs)
    if args.max_steps:
        total_steps = min(total_steps, args.max_steps)
    if args.sec_per_step > 0:
        total_steps = min(total_steps, int(args.minutes * 60 / args.sec_per_step))
    warmup = max(1, int(0.06 * total_steps))
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warmup) * max(0.02, (total_steps - s) / max(1, total_steps - warmup))
    )
    print(f"train_groups={len(train_rows)} pairs={pairs_total} steps={total_steps} budget={args.minutes}m", flush=True)

    log = []
    fx0 = fixture_check(model, tok, args.max_len, device)
    print("fixtures@0", json.dumps(fx0), flush=True)
    log.append({"step": 0, "fixtures": fx0})
    best = None
    step = 0
    started = time.time()
    deadline = started + args.minutes * 60
    stop = False

    def do_eval():
        nonlocal best
        metrics = evaluate(model, tok, dev_rows, args.max_len, device, args.pairs_per_batch)
        metrics["step"] = step
        metrics["minutes"] = round((time.time() - started) / 60, 1)
        metrics["fixtures"] = fixture_check(model, tok, args.max_len, device)
        log.append(metrics)
        print("dev", json.dumps(metrics), flush=True)
        if best is None or metrics["loss"] < best:
            best = metrics["loss"]
            model.save_pretrained(out / "best")
            tok.save_pretrained(out / "best")
        (out / "log.json").write_text(json.dumps(log, indent=1))

    model.train()
    while not stop:
        for batch_rows in _row_batches(train_rows, args.pairs_per_batch, rng):
            batch = [to_pairs(r) for r in batch_rows]
            m = margins_for(model, tok, batch, args.max_len, device)
            tm = None
            if tlabels:
                tm_list = []
                for r, (_, hs, _, _) in zip(batch_rows, batch):
                    t = tlabels.get(group_key(r))
                    tm_list += (t if t is not None and len(t) == len(hs) else [float("nan")] * len(hs))
                tm = torch.tensor(tm_list, dtype=m.dtype) / args.kd_temp
            loss = _loss(m, batch, args.pointwise, tm, args.kd, args.kd_temp)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            step += 1
            if step % 25 == 0:
                el = time.time() - started
                print(f"step {step}/{total_steps} loss {float(loss):.4f} {el / step:.2f} s/step elapsed {el / 60:.1f}m", flush=True)
            if step % args.eval_every == 0:
                do_eval()
            if step >= total_steps or time.time() > deadline:
                stop = True
                break
    do_eval()
    (out / "done.json").write_text(
        json.dumps({"best_dev_loss": best, "steps": step, "minutes": (time.time() - started) / 60, "args": vars(args)}, indent=1)
    )
    print("done", best, flush=True)


def _row_batches(rows, ppb, rng, pool=48):
    """Shuffled batches, length-bucketed within pools of ~`pool` batches to cut padding on CPU."""
    order = list(range(len(rows)))
    rng.shuffle(order)
    size = lambda i: len(to_pairs(rows[i])[1])
    est = lambda i: len(state_text(rows[i]["state"])) if rows[i].get("family") != "nli" else len(rows[i]["state"])
    chunk = []
    pairs = 0
    for idx, i in enumerate(order):
        chunk.append(i)
        pairs += size(i)
        if pairs >= ppb * pool or idx == len(order) - 1:
            chunk.sort(key=est)
            out, batch, count = [], [], 0
            for j in chunk:
                batch.append(rows[j])
                count += size(j)
                if count >= ppb:
                    out.append(batch)
                    batch, count = [], 0
            if batch:
                out.append(batch)
            rng.shuffle(out)
            yield from out
            chunk, pairs = [], 0


def _loss(m, batch, pointwise_w, tm, kd_w, kd_temp):
    """group_loss, but KD skips groups without teacher margins (NaN) and uses temperature."""
    if tm is None:
        return group_loss(m, batch, pointwise_w)
    base = group_loss(m, batch, pointwise_w)
    kd_terms = []
    off = 0
    for _, hs, _, qtype in batch:
        n = len(hs)
        t = tm[off : off + n]
        s = m[off : off + n]
        off += n
        if torch.isnan(t).any():
            continue
        if qtype == "nli":
            pt = torch.sigmoid(t)
            kd_terms.append(F.binary_cross_entropy_with_logits(s / kd_temp, pt))
        else:
            kd_terms.append(F.kl_div(F.log_softmax(s / kd_temp, 0), F.softmax(t, 0), reduction="sum") * kd_temp**2)
    if not kd_terms:
        return base
    return base + kd_w * torch.stack(kd_terms).mean()


if __name__ == "__main__":
    main()
