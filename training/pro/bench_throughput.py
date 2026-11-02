"""Measure CPU LoRA training throughput for Qwen3.5 sizes.

usage: python training/pro/bench_throughput.py --model C:/KeelWork/models/Qwen3.5-2B --threads 20 --seq 384 --batch 4 --top 24
"""
import argparse
import json
import time

import torch


def load(path, dtype):
    from transformers import AutoModelForCausalLM

    m = AutoModelForCausalLM.from_pretrained(path, dtype=dtype)
    return m


def add_lora(model, top, r=16):
    from peft import LoraConfig, get_peft_model

    n = model.config.num_hidden_layers
    layers = list(range(n - top, n))
    targets = ["q_proj", "k_proj", "v_proj", "o_proj", "in_proj_qkv", "in_proj_z", "out_proj", "gate_proj", "up_proj", "down_proj"]
    cfg = LoraConfig(r=r, lora_alpha=2 * r, lora_dropout=0.0, target_modules=targets, layers_to_transform=layers, layers_pattern="layers")
    return get_peft_model(model, cfg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--threads", type=int, default=20)
    ap.add_argument("--seq", type=int, default=384)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--top", type=int, default=0, help="LoRA on top-N layers (0=all)")
    ap.add_argument("--dtype", default="float32")
    ap.add_argument("--ckpt", action="store_true")
    ap.add_argument("--steps", type=int, default=3)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    dtype = getattr(torch, a.dtype)
    t0 = time.time()
    model = load(a.model, dtype)
    print("class", type(model).__name__, "load_s", round(time.time() - t0, 1), flush=True)
    top = a.top or model.config.num_hidden_layers
    model = add_lora(model, top)
    if a.ckpt:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    print("trainable", sum(p.numel() for p in params), flush=True)
    opt = torch.optim.AdamW(params, lr=1e-4)
    base = model.get_base_model()
    vocab = base.config.vocab_size
    ids = torch.randint(100, 20000, (a.batch, a.seq))
    times = []
    for s in range(a.steps):
        t = time.time()
        out = base.model(input_ids=ids, use_cache=False)
        h = out.last_hidden_state[:, -3:, :]
        logits = base.lm_head(h).float()
        loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]), torch.randint(0, vocab, (logits.shape[0] * logits.shape[1],)))
        loss.backward()
        opt.step()
        opt.zero_grad()
        times.append(time.time() - t)
        print("step", s, round(times[-1], 2), flush=True)
    best = min(times[1:]) if len(times) > 1 else times[0]
    res = dict(model=a.model, threads=a.threads, seq=a.seq, batch=a.batch, top=top, dtype=a.dtype, ckpt=a.ckpt, s_per_step=round(best, 2), ex_per_s=round(a.batch / best, 3), tok_per_s=round(a.batch * a.seq / best, 1))
    print("RESULT", json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
