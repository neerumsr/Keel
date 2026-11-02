"""Profile one LoRA training step on GPU for a Qwen3.5 model (forward/backward split, tokens/s).

usage: python training/pro/profile_step.py --model C:/KeelWork/models/Qwen3.5-4B --bs 16 --seq 512 [--no-ckpt] [--steps 6]
"""
import argparse
import time

import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--seq", type=int, default=512)
    ap.add_argument("--no-ckpt", action="store_true")
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--rank", type=int, default=32)
    a = ap.parse_args()
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM

    from train_lora import TARGETS

    m = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16).cuda()
    m = get_peft_model(m, LoraConfig(r=a.rank, lora_alpha=2 * a.rank, target_modules=TARGETS))
    if not a.no_ckpt:
        m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        m.enable_input_require_grads()
    m.train()
    base = m.get_base_model()
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=1e-5)
    ids = torch.randint(100, 20000, (a.bs, a.seq), device="cuda")
    for s in range(a.steps):
        torch.cuda.synchronize()
        t0 = time.time()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            h = base.model(input_ids=ids, use_cache=False).last_hidden_state
            loss = base.lm_head(h[:, -2:]).float().logsumexp(-1).mean()
        torch.cuda.synchronize()
        t1 = time.time()
        loss.backward()
        opt.step()
        opt.zero_grad()
        torch.cuda.synchronize()
        t2 = time.time()
        print(f"step {s} fwd {t1 - t0:.2f}s bwd {t2 - t1:.2f}s tok/s {a.bs * a.seq / (t2 - t0):.0f} mem {torch.cuda.max_memory_allocated() / 2**30:.1f}GB", flush=True)


if __name__ == "__main__":
    main()
