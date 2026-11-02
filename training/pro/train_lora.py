"""Keel-Pro LoRA trainer (GPU).

Loss = LM loss on the gold option-key tokens (what the DI kit sums to score an option)
     + w_list * listwise cross-entropy over the options' first tokens (when they are distinct).
Prompts are byte-identical to the DI transformers engine (common.py). Logits are computed only at
target positions, so the 248k-token vocabulary never materializes over the full sequence.

usage:
  python training/pro/train_lora.py --model C:/KeelWork/models/Qwen3.5-4B --data C:/KeelWork/pro/data/train.jsonl.gz \
      --out C:/KeelWork/pro/runs/it1 [--max-rows N] [--epochs 1] [--lr 1e-4] [--rank 32] [--tokens 16384]
Writes <out>/adapter (PEFT), <out>/merged (bf16 HF dir, loadable by the eval tool), <out>/train-log.jsonl.
"""
import argparse
import gc
import gzip
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import build_example, build_example_letters  # noqa: E402

TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "in_proj_qkv", "in_proj_z", "out_proj", "gate_proj", "up_proj", "down_proj"]


def read_jsonl(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def encode(tok, rows, max_len, log, end_id=None, letters=False, shuffle=0.0, seed=0):
    out, skipped = [], 0
    t = time.time()
    rng = random.Random(seed)
    for i, r in enumerate(rows):
        q = r["questions"]["q1"] if "q1" in r["questions"] else next(iter(r["questions"].values()))
        gold = r["gold"]["q1"] if "q1" in r["gold"] else next(iter(r["gold"].values()))
        if letters:
            ex = build_example_letters(tok, r["state"], q, gold, max_len=max_len, rng=rng if shuffle > 0 else None, shuffle=shuffle)
        else:
            ex = build_example(tok, r["state"], q, gold, max_len=max_len, end_id=end_id)
        if ex is None:
            skipped += 1
            continue
        ex["bench"] = str(r.get("benchmark"))
        out.append(ex)
        if (i + 1) % 20000 == 0:
            log(event="encode", done=i + 1, kept=len(out), skipped=skipped, s=round(time.time() - t))
    return out, skipped


def batches(examples, tokens, seed, max_bs=64):
    """Length-bucketed batches with roughly `tokens` padded tokens each, in random order."""
    rng = random.Random(seed)
    idx = list(range(len(examples)))
    rng.shuffle(idx)
    out = []
    for c in range(0, len(idx), 4096):
        chunk = sorted(idx[c : c + 4096], key=lambda i: len(examples[i]["ids"]))
        cur, cur_max = [], 0
        for i in chunk:
            L = -(-len(examples[i]["ids"]) // 128) * 128
            if cur and (max(cur_max, L) * (len(cur) + 1) > tokens or len(cur) >= max_bs):
                out.append(cur)
                cur, cur_max = [], 0
            cur.append(i)
            cur_max = max(cur_max, L)
        if cur:
            out.append(cur)
    rng.shuffle(out)
    return out


def collate(examples, b, pad, device, multiple=128):
    L = max(len(examples[i]["ids"]) for i in b)
    L = -(-L // multiple) * multiple  # few distinct shapes, so Triton kernels are autotuned once per bucket
    ids = torch.full((len(b), L), pad, dtype=torch.long)
    lm_b, lm_p, lm_t = [], [], []
    li_b, li_p, li_opts, li_gold = [], [], [], []
    for j, i in enumerate(b):
        e = examples[i]
        ids[j, : len(e["ids"])] = torch.tensor(e["ids"])
        for p, t in zip(e["tgt_pos"], e["tgt_ids"]):
            lm_b.append(j)
            lm_p.append(p)
            lm_t.append(t)
        if e["opt_first"] is not None and len(e["opt_first"]) > 1:
            li_b.append(j)
            li_p.append(e["tgt_pos"][0])
            li_opts.append(e["opt_first"])
            li_gold.append(e["gold_idx"])
    return ids.to(device), (lm_b, lm_p, lm_t), (li_b, li_p, li_opts, li_gold)


def step_loss(model, ids, lm, li, w_list):
    base = model.get_base_model()
    h = base.model(input_ids=ids, use_cache=False).last_hidden_state
    lm_b, lm_p, lm_t = lm
    dev = ids.device
    hs = h[torch.tensor(lm_b, device=dev), torch.tensor(lm_p, device=dev)]
    logits = base.lm_head(hs).float()
    lm_loss = torch.nn.functional.cross_entropy(logits, torch.tensor(lm_t, device=dev))
    loss = lm_loss
    list_loss = torch.zeros((), device=dev)
    correct = 0
    if li[0] and w_list > 0:
        li_b, li_p, li_opts, li_gold = li
        hl = h[torch.tensor(li_b, device=dev), torch.tensor(li_p, device=dev)]
        full = base.lm_head(hl).float()
        width = max(len(o) for o in li_opts)
        opt_idx = torch.tensor([o + [o[0]] * (width - len(o)) for o in li_opts], device=dev)
        valid = torch.tensor([[j < len(o) for j in range(width)] for o in li_opts], device=dev)
        sel = full.gather(1, opt_idx).masked_fill(~valid, float("-inf"))
        gold_t = torch.tensor(li_gold, device=dev)
        list_loss = torch.nn.functional.cross_entropy(sel, gold_t)
        correct = int((sel.argmax(1) == gold_t).sum().item())
        loss = loss + w_list * list_loss
    return loss, lm_loss.detach(), list_loss.detach(), correct, len(li[0])


def load_4bit(path, attn="sdpa"):
    """QLoRA base: NF4 with double quantization, bf16 compute. Embeddings and norms stay bf16 (no fp32 upcast)."""
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig

    q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    return AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, quantization_config=q, device_map={"": 0}, attn_implementation=attn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--holdout")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--attn", default="sdpa", choices=["sdpa", "eager"], help="attention kernel; sdpa avoids materializing the seq x seq score matrix")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--alpha", type=int, default=0)
    ap.add_argument("--dropout", type=float, default=0.0)
    ap.add_argument("--tokens", type=int, default=16384, help="padded tokens per micro-batch")
    ap.add_argument("--accum", type=int, default=1)
    ap.add_argument("--w-list", type=float, default=1.0)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument("--exclude-bench", default="", help="comma-separated benchmark ids to drop (ablations)")
    ap.add_argument("--no-ckpt", action="store_true")
    ap.add_argument("--no-merge", action="store_true")
    ap.add_argument("--no-end-token", action="store_true", help="kit-faithful targets: gold key tokens only, no <|im_end|>")
    ap.add_argument("--letters", action="store_true", help="letters policy: single-token option labels, one read-out position (common.py)")
    ap.add_argument("--shuffle", type=float, default=0.5, help="letters policy: probability of permuting option order per training row")
    ap.add_argument("--qlora", action="store_true", help="NF4 4-bit base (bitsandbytes), bf16 LoRA; saves the adapter only (evaluate with eval_model.py --load-4bit --adapter)")
    ap.add_argument("--init-adapter", help="continue training this LoRA adapter instead of a fresh one (same rank/targets)")
    ap.add_argument("--skip-sample", default="", help="SEED:N - drop the rows an earlier run sampled with --seed SEED --max-rows N, so a continuation sees fresh rows")
    ap.add_argument("--start-step", type=int, default=0, help="resume: skip the plan's first N optimizer steps (use with --init-adapter <out>/adapter and the same seed/data args)")
    ap.add_argument("--extra-bench", default="", help="B:N[,B:N] - add up to N more rows of benchmark B from rows not already sampled (after --skip-sample/--max-rows)")
    ap.add_argument("--optim", choices=["adamw", "paged-adamw8bit"], default="adamw", help="paged-adamw8bit (bitsandbytes) frees optimizer memory for longer sequences")
    a = ap.parse_args()

    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / "train-log.jsonl").open("a", encoding="utf-8")

    def log(**kw):
        kw["time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        line = json.dumps(kw)
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()

    log(event="args", **vars(a))
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    # Under Windows WDDM, allocations past VRAM silently spill to system RAM and training slows ~100x; fail fast instead.
    torch.cuda.set_per_process_memory_fraction(float(os.environ.get("KEEL_MEM_FRACTION", "0.94")))
    tok = AutoTokenizer.from_pretrained(a.model)
    end_id = None if a.no_end_token else tok.convert_tokens_to_ids("<|im_end|>")
    pad = tok.pad_token_id if tok.pad_token_id is not None else 0

    drop = {x.strip() for x in a.exclude_bench.split(",") if x.strip()}
    rows = [r for r in read_jsonl(a.data) if str(r.get("benchmark")) not in drop]
    if a.skip_sample:
        s_seed, s_n = (int(x) for x in a.skip_sample.split(":"))
        if len(rows) > s_n:
            used = set(random.Random(s_seed).sample(range(len(rows)), s_n))
            rows = [r for i, r in enumerate(rows) if i not in used]
        else:
            rows = []
        log(event="skip_sample", seed=s_seed, n=s_n, remaining=len(rows))
    if a.max_rows and len(rows) > a.max_rows:
        picked = random.Random(a.seed).sample(range(len(rows)), a.max_rows)
        if a.extra_bench:
            chosen = set(picked)
            rest = [i for i in range(len(rows)) if i not in chosen]
            for spec in a.extra_bench.split(","):
                b, n = spec.split(":")
                pool = [i for i in rest if str(rows[i].get("benchmark")) == b.strip()]
                add = random.Random(f"{a.seed}:{b}").sample(pool, min(int(n), len(pool)))
                picked.extend(add)
                log(event="extra_bench", bench=b.strip(), added=len(add), pool=len(pool))
        rows = [rows[i] for i in picked]
    examples, skipped = encode(tok, rows, a.max_len, log, end_id, a.letters, a.shuffle, a.seed)
    del rows
    log(event="data", examples=len(examples), skipped_too_long=skipped, tokens=sum(len(e["ids"]) for e in examples))
    hold = []
    if a.holdout:
        hold, _ = encode(tok, list(read_jsonl(a.holdout))[:2000], a.max_len, log, end_id, a.letters, 0.0)

    if a.attn == "sdpa":
        # enable_gqa=True has no memory-efficient SDPA kernel (head_dim 256, no flash on Windows), so torch
        # falls back to the math path and materializes fp32 heads x seq x seq scores (~2.2 GB at 5k tokens).
        # Repeating K/V instead keeps the efficient kernel: 27B QLoRA peak at 5120 tokens 29.9 -> 23.4 GB.
        import transformers.integrations.sdpa_attention as sdpa_mod

        sdpa_mod.use_gqa_in_sdpa = lambda *args, **kwargs: False
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, attn_implementation=a.attn).to("cuda") if not a.qlora else load_4bit(a.model, a.attn)
    cfg = LoraConfig(r=a.rank, lora_alpha=a.alpha or 2 * a.rank, lora_dropout=a.dropout, target_modules=TARGETS)
    if a.init_adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, a.init_adapter, is_trainable=True)
    else:
        model = get_peft_model(model, cfg)
    if not a.no_ckpt:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    model.config.use_cache = False
    params = [p for p in model.parameters() if p.requires_grad]
    log(event="model", trainable=sum(p.numel() for p in params), attn=getattr(model.config, "_attn_implementation", None))
    if a.optim == "paged-adamw8bit":
        import bitsandbytes as bnb

        opt = bnb.optim.PagedAdamW8bit(params, lr=a.lr, weight_decay=0.0, betas=(0.9, 0.99))
    else:
        opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.0, betas=(0.9, 0.99))

    plan = []
    ep = 0
    while len(plan) < 1 or ep < math.ceil(a.epochs):
        bs = batches(examples, a.tokens, a.seed + ep)
        plan.extend(bs)
        ep += 1
    total_micro = int(len(batches(examples, a.tokens, a.seed)) * a.epochs)
    plan = plan[:total_micro]
    total = max(1, total_micro // a.accum)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / a.warmup) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, s / total)))))
    log(event="plan", micro_batches=total_micro, steps=total)

    def evaluate():
        if not hold:
            return None
        try:
            return _evaluate()
        except torch.OutOfMemoryError:
            pass
        model.train()
        gc.collect()
        torch.cuda.empty_cache()
        log(event="holdout_oom")
        return None

    def _evaluate():
        model.eval()
        n = c = 0
        tl = 0.0
        with torch.no_grad():
            for b in batches(hold, a.tokens, 0):
                ids, lm, li = collate(hold, b, pad, "cuda")
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    loss, lml, lsl, cor, nl = step_loss(model, ids, lm, li, a.w_list)
                tl += lml.item() * len(b)
                n += len(b)
                c += cor
        model.train()
        return dict(holdout_lm=round(tl / max(1, n), 4), holdout_first_acc=round(c / max(1, n), 4))

    model.train()
    t0 = time.time()
    seen = 0
    run = dict(loss=0.0, lm=0.0, li=0.0, cor=0, n=0, k=0)
    step = 0
    oom = 0
    if a.start_step:
        # Resume after a crash: --init-adapter holds the weights saved at this step; optimizer moments restart.
        for _ in range(a.start_step):
            sched.step()
        step = a.start_step
        plan = plan[a.start_step * a.accum :]
        log(event="resume", step=step, remaining_micro=len(plan))
    t_steps0 = step
    for mi, b in enumerate(plan):
        failed = False
        try:
            ids, lm, li = collate(examples, b, pad, "cuda")
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss, lml, lsl, cor, nl = step_loss(model, ids, lm, li, a.w_list)
            (loss / a.accum).backward()
        except torch.OutOfMemoryError as e:
            failed = str(e)[:160]
        if failed:
            # One oversized or fragmented batch must not cost hours of training: drop it and carry on.
            oom += 1
            loss = lml = lsl = ids = lm = li = None
            opt.zero_grad(set_to_none=True)
            gc.collect()
            torch.cuda.empty_cache()
            log(event="oom_skip", micro=mi, batch=len(b), max_len=max(len(examples[i]["ids"]) for i in b), total_skipped=oom, alloc_gb=round(torch.cuda.memory_allocated() / 2**30, 2), error=failed)
            if oom > 50:
                raise RuntimeError("more than 50 batches skipped for CUDA OOM; lower --tokens or --max-len")
            continue
        seen += len(b)
        run["loss"] += loss.item()
        run["lm"] += lml.item()
        run["li"] += lsl.item()
        run["cor"] += cor
        run["n"] += nl
        run["k"] += 1
        if (mi + 1) % a.accum == 0:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            if step % 25 == 0 or step == total:
                el = time.time() - t0
                log(event="train", step=step, of=total, seen=seen, loss=round(run["loss"] / run["k"], 4), lm=round(run["lm"] / run["k"], 4), list=round(run["li"] / run["k"], 4), first_acc=round(run["cor"] / max(1, run["n"]), 4), lr=sched.get_last_lr()[0], ex_s=round(seen / el, 1), eta_min=round(el / max(1, step - t_steps0) * (total - step) / 60, 1), mem_gb=round(torch.cuda.max_memory_allocated() / 2**30, 1))
                run = dict(loss=0.0, lm=0.0, li=0.0, cor=0, n=0, k=0)
            if step % 1000 == 0:
                model.save_pretrained(out / "adapter")
                log(event="saved_adapter", step=step)
                h = evaluate()
                torch.cuda.empty_cache()
                if h:
                    log(event="holdout", step=step, **h)
    h = evaluate()
    if h:
        log(event="holdout", step=step, final=True, **h)
    model.save_pretrained(out / "adapter")
    log(event="saved_adapter", minutes=round((time.time() - t0) / 60, 1))
    if not a.no_merge and not a.qlora:
        merged = model.merge_and_unload()
        merged.config.use_cache = True
        merged.save_pretrained(out / "merged", safe_serialization=True)
        tok.save_pretrained(out / "merged")
        log(event="saved_merged", path=str(out / "merged"))


if __name__ == "__main__":
    main()
