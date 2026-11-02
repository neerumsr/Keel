"""Train a Keel-2 cross-encoder.

    python training/keel/train.py --base models/base-xd6 --out training/runs/xd6 --epochs 3
    python training/keel/train.py --base models/keel-base --out training/runs/deberta --epochs 2 --lr 3e-5   # teacher
    python training/keel/train.py --base models/base-xd6 --out training/runs/xd6-kd --teacher training/runs/deberta/best --kd 0.5

Every question is a group of (state, hypothesis) pairs. Loss per group:
  listwise  = cross-entropy between softmax(margins) and the soft target
  pointwise = BCE(sigmoid(margin_j), t_j) so absolute entailment stays meaningful
              (this is what lets the runtime abstain on low-signal states)
  kd        = optional KL to a teacher's group distribution
  ordinal   = optional (--ordinal W) for score groups: squared EMD between the
              predicted and target CDFs plus squared expected-level error
margin = logit(entailment) - logit(not_entailment), same as the Node runtime.
Runs on CUDA when available, otherwise --threads CPU cores.

Optional knobs (all off by default, so older commands behave as before):
  --extra-train a.jsonl b.jsonl@0.5   extra training files; @k repeats (k>1) or subsamples (k<1)
  --label-smoothing e                 mix soft targets toward uniform
  --shuffle-options p                 permute choice options with probability p (order augmentation)
  --hard-neg w                        weight groups by 1 + w * (1 - p_gold) (hard-example emphasis)
  --schedule cosine --warmup 0.06     LR schedule
  --grad-accum n                      gradient accumulation
  --ema 0.999                         keep an EMA of weights; evaluate/save the EMA copy
  --dev-max n                         cap dev groups per eval (stratified by order)
  --pointwise-noul w                  separate pointwise weight for noul groups
  --bucket n                          length-bucketed batches (windows of n batches) to cut padding
  --teacher-labels f.jsonl --kd-temp 2  KD from precomputed teacher margins (t2_label.py format)
  --safety-neg w                      unlikelihood on above-target mass of low-target (<0.2) options in safety families (--safety-families regex)
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import pathlib
import random
import re
import sys
import time

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from keel.hypothesis import hypotheses, state_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def load_extra(spec: str, rng: random.Random) -> list[dict]:
    path, _, factor = spec.partition("@")
    rows = load_jsonl(pathlib.Path(path))
    k = float(factor) if factor else 1.0
    whole, frac = int(k), k - int(k)
    out = rows * whole
    if frac > 0:
        out += rng.sample(rows, int(round(frac * len(rows))))
    return out


def to_pairs(row: dict) -> tuple[str, list[str], list[float], str]:
    if row.get("family") == "nli":
        return row["state"], [row["pair"]], [row["label"]], "nli"
    return state_text(row["state"]), hypotheses(row["question"]), row["target"], row["question"]["type"]


def shuffled(row: dict, rng: random.Random) -> dict:
    """Same question with choice options in a random order (targets permuted alongside)."""
    q = row["question"]
    items = list(q["criteria"].items())
    order = list(range(len(items)))
    rng.shuffle(order)
    new_q = dict(q)
    new_q["criteria"] = {items[i][0]: items[i][1] for i in order}
    new = dict(row)
    new["question"] = new_q
    new["target"] = [row["target"][i] for i in order]
    if row.get("_tm") is not None:
        new["_tm"] = [row["_tm"][i] for i in order]
    return new


class Batch(list):
    """List of to_pairs() tuples plus per-group teacher margins (or None) and family names."""

    tms: list
    families: list


def teacher_key(row: dict) -> str:
    """Same key as t2_train.group_key / t2_label.py."""
    if row.get("family") == "nli":
        return "nli\t" + row["state"] + "\t" + row["pair"]
    return state_text(row["state"]) + "\t" + json.dumps(row["question"], sort_keys=True)


def attach_teacher_labels(rows: list[dict], paths: list[str]) -> int:
    table = {}
    for path in paths:
        for line in pathlib.Path(path).read_text(encoding="utf-8").split("\n"):
            if line.strip():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:  # a file still being written may end mid-line
                    continue
                table[r["key"]] = r["margins"]
    hit = 0
    for row in rows:
        t = table.get(teacher_key(row))
        if t is not None and len(t) == len(to_pairs(row)[1]):
            row["_tm"] = t
            hit += 1
    return hit


def bucketed(rows: list[dict], order: list[int], pairs_per_batch: int, window: int, rng: random.Random) -> list[int]:
    """Sort each window of shuffled rows by text length, so padding stays small, then shuffle the
    resulting batches. Same groups, same epoch; only the batch composition changes."""
    out: list[int] = []
    size = max(1, window * pairs_per_batch // 3)
    for start in range(0, len(order), size):
        chunk = sorted(order[start : start + size], key=lambda i: len(str(rows[i].get("state"))) + len(json.dumps(rows[i].get("question", rows[i].get("pair", "")))) // 3)
        groups, cur, count = [], [], 0
        for i in chunk:
            cur.append(i)
            count += len(rows[i]["target"]) if "target" in rows[i] else 1
            if count >= pairs_per_batch:
                groups.append(cur)
                cur, count = [], 0
        if cur:
            groups.append(cur)
        rng.shuffle(groups)
        for g in groups:
            out += g
    return out


def batches(rows: list[dict], pairs_per_batch: int, rng: random.Random, shuffle: bool = True, shuffle_options: float = 0.0, bucket: int = 0):
    order = list(range(len(rows)))
    if shuffle:
        rng.shuffle(order)
        if bucket > 0:
            order = bucketed(rows, order, pairs_per_batch, bucket, rng)
    def fresh() -> Batch:
        b = Batch()
        b.tms, b.families = [], []
        return b

    batch, count = fresh(), 0
    for i in order:
        row = rows[i]
        if shuffle_options > 0 and row.get("question", {}).get("type") == "choice" and isinstance(row["question"].get("criteria"), dict) and rng.random() < shuffle_options:
            row = shuffled(row, rng)
        p = to_pairs(row)
        batch.append(p)
        batch.tms.append(row.get("_tm"))
        batch.families.append(row.get("family", ""))
        count += len(p[1])
        if count >= pairs_per_batch:
            yield batch
            batch, count = fresh(), 0
    if batch:
        yield batch


def margins_for(model, tok, batch, max_len, device):
    premises, hyps = [], []
    for state, hs, _, _ in batch:
        premises += [state] * len(hs)
        hyps += hs
    enc = tok(premises, hyps, padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(device)
    logits = model(**enc).logits
    return logits[:, 0] - logits[:, 1]


def group_loss(margins, batch, pointwise_w, teacher_margins=None, kd_w=0.0, ordinal_w=0.0, smoothing=0.0, hard_neg=0.0, pointwise_noul=None, kd_temp=1.0, safety_neg=0.0, safety_re=None):
    """teacher_margins: aligned tensor (in-process teacher), or None to use batch.tms (precomputed labels)."""
    losses = []
    tms = getattr(batch, "tms", None)
    families = getattr(batch, "families", None)
    off = 0
    for gi, (_, hs, target, qtype) in enumerate(batch):
        m = margins[off : off + len(hs)]
        t = torch.tensor(target, dtype=m.dtype, device=m.device)
        if qtype == "nli":
            losses.append(F.binary_cross_entropy_with_logits(m, t))
        else:
            peak = float(max(target))
            lt = (1 - smoothing) * t + smoothing / len(hs) if smoothing > 0 else t
            logp = F.log_softmax(m, dim=0)
            listwise = -(lt * logp).sum()
            point_t = t if peak >= 0.5 else torch.zeros_like(t)
            pointwise = F.binary_cross_entropy_with_logits(m, point_t)
            pw = pointwise_noul if (qtype == "noul" and pointwise_noul is not None) else pointwise_w
            loss = listwise + pw * pointwise
            if ordinal_w > 0 and qtype == "score" and len(hs) > 1:
                p = logp.exp()
                emd = ((torch.cumsum(p, 0) - torch.cumsum(t, 0)) ** 2).sum() / (len(hs) - 1)
                lv = torch.arange(len(hs), dtype=m.dtype, device=m.device) / (len(hs) - 1)
                loss = loss + ordinal_w * (emd + ((p * lv).sum() - (t * lv).sum()) ** 2)
            tm = None
            if kd_w > 0:
                if teacher_margins is not None:
                    tm = teacher_margins[off : off + len(hs)]
                elif tms is not None and tms[gi] is not None:
                    tm = torch.tensor(tms[gi], dtype=m.dtype, device=m.device)
            if tm is not None:
                if kd_temp == 1.0:
                    loss = loss + kd_w * F.kl_div(logp, F.softmax(tm, 0), reduction="sum")
                else:
                    loss = loss + kd_w * kd_temp**2 * F.kl_div(F.log_softmax(m / kd_temp, 0), F.softmax(tm / kd_temp, 0), reduction="sum")
            if safety_neg > 0 and peak >= 0.5 and families is not None and safety_re is not None and safety_re.search(families[gi] or ""):
                # unlikelihood on mass above target for low-target options (< 0.2: wrong/harmful branches)
                bad = t < 0.2
                if bool(bad.any()):
                    excess = (logp.exp()[bad] - t[bad]).clamp(min=0, max=1 - 1e-4)
                    loss = loss + safety_neg * (-torch.log1p(-excess)).sum()
            if hard_neg > 0 and peak >= 0.5:
                gold = int(torch.argmax(t))
                loss = loss * (1 + hard_neg * (1 - float(logp[gold].exp())))
            losses.append(loss)
        off += len(hs)
    return torch.stack(losses).mean()


@torch.no_grad()
def evaluate(model, tok, rows, max_len, device, ppb):
    was_training = model.training
    model.eval()
    stats = {"choice": [0, 0], "score_mae": [0.0, 0], "noul": [0, 0], "ambiguous_maxp": [0.0, 0], "loss": [0.0, 0]}
    rng = random.Random(0)
    for batch in batches(rows, ppb, rng, shuffle=False):
        m = margins_for(model, tok, batch, max_len, device)
        stats["loss"][0] += float(group_loss(m, batch, 0.5)) * len(batch)
        stats["loss"][1] += len(batch)
        off = 0
        for _, hs, target, qtype in batch:
            g = m[off : off + len(hs)]
            off += len(hs)
            p = F.softmax(g, 0).tolist()
            if max(target) < 0.5 and qtype != "nli":
                stats["ambiguous_maxp"][0] += max(p)
                stats["ambiguous_maxp"][1] += 1
            elif qtype == "choice":
                stats["choice"][0] += int(p.index(max(p)) == target.index(max(target)))
                stats["choice"][1] += 1
            elif qtype == "score":
                ev = sum(i * x for i, x in enumerate(p))
                tv = sum(i * x for i, x in enumerate(target))
                stats["score_mae"][0] += abs(ev - tv)
                stats["score_mae"][1] += 1
            elif qtype == "noul":
                stats["noul"][0] += int((p[0] >= 0.5) == (target[0] >= 0.5))
                stats["noul"][1] += 1
    if was_training:
        model.train()
    return {k: (v[0] / v[1] if v[1] else None) for k, v in stats.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--train", default=str(ROOT / "training/data/train.jsonl"))
    ap.add_argument("--dev", default=str(ROOT / "training/data/dev.jsonl"))
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=6e-5)
    ap.add_argument("--pairs-per-batch", type=int, default=64)
    ap.add_argument("--max-len", type=int, default=160)
    ap.add_argument("--pointwise", type=float, default=0.5)
    ap.add_argument("--teacher", default=None)
    ap.add_argument("--kd", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 8)
    ap.add_argument("--eval-every", type=int, default=400)
    ap.add_argument("--extra-train", nargs="*", default=[], help="extra jsonl files; path@k repeats/subsamples")
    ap.add_argument("--ordinal", type=float, default=0.0, help="weight of ordinal (EMD + expected-level) loss on score groups")
    ap.add_argument("--label-smoothing", type=float, default=0.0)
    ap.add_argument("--shuffle-options", type=float, default=0.0, help="probability of permuting choice options")
    ap.add_argument("--hard-neg", type=float, default=0.0, help="group weight 1 + w * (1 - p_gold)")
    ap.add_argument("--schedule", choices=["linear", "cosine"], default="linear")
    ap.add_argument("--warmup", type=float, default=0.05, help="warmup fraction of total steps")
    ap.add_argument("--grad-accum", type=int, default=1)
    ap.add_argument("--ema", type=float, default=0.0, help="EMA decay (0 = off); evaluation/saving uses the EMA weights")
    ap.add_argument("--dev-max", type=int, default=0, help="cap dev groups per eval (0 = all)")
    ap.add_argument("--bucket", type=int, default=0, help="length-bucket batches within windows of N batches (0 = off)")
    ap.add_argument("--pointwise-noul", type=float, default=None, help="pointwise weight for noul groups (default: --pointwise)")
    ap.add_argument("--teacher-labels", nargs="+", default=None, help="one or more precomputed teacher margins jsonl {key, margins} (t2_label.py format)")
    ap.add_argument("--kd-temp", type=float, default=1.0)
    ap.add_argument("--safety-neg", type=float, default=0.0, help="unlikelihood weight on target-0 options in safety families")
    ap.add_argument("--safety-families", default=r"gate|moderation|security|injection|threat|phishing", help="regex for --safety-neg families")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForSequenceClassification.from_pretrained(args.base, dtype=torch.float32).to(device)
    teacher = None
    if args.teacher:
        teacher = AutoModelForSequenceClassification.from_pretrained(args.teacher, dtype=torch.float32).to(device).eval()
        teacher_tok = AutoTokenizer.from_pretrained(args.teacher)

    rng = random.Random(args.seed)
    train_rows = load_jsonl(pathlib.Path(args.train))
    for spec in args.extra_train:
        extra = load_extra(spec, rng)
        print(f"extra {spec}: {len(extra)} groups", flush=True)
        train_rows += extra
    if args.teacher_labels:
        print(f"teacher labels: {attach_teacher_labels(train_rows, args.teacher_labels)} groups matched", flush=True)
    safety_re = re.compile(args.safety_families) if args.safety_neg > 0 else None
    dev_rows = load_jsonl(pathlib.Path(args.dev))
    if args.dev_max and len(dev_rows) > args.dev_max:
        dev_rows = dev_rows[:: math.ceil(len(dev_rows) / args.dev_max)]
    pairs_total = sum(len(to_pairs(r)[1]) for r in train_rows)
    steps_per_epoch = math.ceil(pairs_total / args.pairs_per_batch / args.grad_accum)
    total_steps = int(steps_per_epoch * args.epochs)
    warmup = max(1, int(args.warmup * total_steps))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)

    def lr_lambda(s: int) -> float:
        if s < warmup:
            return (s + 1) / warmup
        frac = (s - warmup) / max(1, total_steps - warmup)
        if args.schedule == "cosine":
            return 0.5 * (1 + math.cos(math.pi * min(1.0, frac)))
        return max(0.0, 1 - frac)

    if args.schedule == "linear" and args.warmup == 0.05:
        sched = torch.optim.lr_scheduler.LambdaLR(
            opt, lambda s: min(1.0, (s + 1) / warmup) * max(0.0, (total_steps - s) / max(1, total_steps - warmup))
        )
    else:
        sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda)
    ema = None
    if args.ema > 0:
        ema = copy.deepcopy(model).eval()
        for p_ in ema.parameters():
            p_.requires_grad_(False)
    print(f"device={device} threads={args.threads} train_groups={len(train_rows)} dev_groups={len(dev_rows)} pairs={pairs_total} steps={total_steps}", flush=True)

    best = None
    step = 0
    started = time.time()
    log = []
    model.train()
    micro = 0
    while step < total_steps:
        for batch in batches(train_rows, args.pairs_per_batch, rng, shuffle_options=args.shuffle_options, bucket=args.bucket):
            m = margins_for(model, tok, batch, args.max_len, device)
            tm = None
            if teacher is not None:
                with torch.no_grad():
                    tm = margins_for(teacher, teacher_tok, batch, args.max_len, device)
            loss = group_loss(m, batch, args.pointwise, tm, args.kd if (teacher is not None or args.teacher_labels) else 0.0, args.ordinal, args.label_smoothing, args.hard_neg, args.pointwise_noul, args.kd_temp, args.safety_neg, safety_re)
            (loss / args.grad_accum).backward()
            micro += 1
            if micro % args.grad_accum:
                continue
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            if ema is not None:
                with torch.no_grad():
                    for pe, pm in zip(ema.parameters(), model.parameters()):
                        pe.mul_(args.ema).add_(pm.detach(), alpha=1 - args.ema)
                    for be, bm in zip(ema.buffers(), model.buffers()):
                        be.copy_(bm)
            step += 1
            if step % 50 == 0:
                rate = step / (time.time() - started)
                print(f"step {step}/{total_steps} loss {float(loss):.4f} {rate:.2f} it/s eta {(total_steps - step) / rate / 60:.1f}m", flush=True)
            if step % args.eval_every == 0 or step >= total_steps:
                judged = ema if ema is not None else model
                metrics = evaluate(judged, tok, dev_rows, args.max_len, device, args.pairs_per_batch)
                metrics["step"] = step
                log.append(metrics)
                print("dev", json.dumps(metrics), flush=True)
                if best is None or metrics["loss"] < best:
                    best = metrics["loss"]
                    judged.save_pretrained(out / "best")
                    tok.save_pretrained(out / "best")
                (out / "log.json").write_text(json.dumps(log, indent=1))
            if step >= total_steps:
                break
    (ema if ema is not None else model).save_pretrained(out / "last")
    tok.save_pretrained(out / "last")
    (out / "done.json").write_text(json.dumps({"best_dev_loss": best, "steps": step, "minutes": (time.time() - started) / 60, "args": vars(args)}, indent=1))
    print("done", best, flush=True)


if __name__ == "__main__":
    main()
