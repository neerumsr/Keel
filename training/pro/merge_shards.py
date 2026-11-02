"""Merge a LoRA adapter into a base checkpoint one safetensors shard at a time (W += B @ A * alpha / r).

Used for QLoRA runs (train_lora.py --qlora), where the base is too large to merge in memory: peak RAM is one shard.
The output keeps the base layout (same shard names, index, config, tokenizer, vision tower and MTP weights), so
llama.cpp's convert_hf_to_gguf.py and transformers load it like the original.

    python merge_shards.py --base C:/KeelWork/models/Qwen3.5-27B --adapter runs/it7/adapter --out runs/it7/merged
"""
import argparse
import json
import re
import shutil
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file


def adapter_deltas(adapter):
    cfg = json.loads((adapter / "adapter_config.json").read_text())
    r, alpha = cfg["r"], cfg["lora_alpha"]
    scale = alpha / (r ** 0.5) if cfg.get("use_rslora") else alpha / r
    st = {}
    with safe_open(adapter / "adapter_model.safetensors", "pt") as f:
        for k in f.keys():
            st[k] = f.get_tensor(k)
    mods = {}
    for k in st:
        m = re.fullmatch(r"base_model\.model\.(.+)\.lora_A(?:\.default)?\.weight", k)
        if m:
            b = k.replace(".lora_A", ".lora_B")
            mods[m.group(1)] = (st[k], st[b])
    return mods, scale


def base_key(module, keys):
    """Adapter module path (model.layers.3.self_attn.q_proj) -> base weight key (model.language_model.layers...)."""
    m = re.search(r"layers\.\d+\..+$", module)
    tail = (m.group(0) if m else module) + ".weight"
    hits = [k for k in keys if (k == tail or k.endswith("." + tail)) and not k.startswith("mtp.")]
    if len(hits) != 1:
        raise KeyError(f"{module}: {len(hits)} base keys match {tail}: {hits[:4]}")
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base, adapter, out = Path(a.base), Path(a.adapter), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mods, scale = adapter_deltas(adapter)
    shards = sorted(base.glob("*.safetensors"))
    keys = {}
    for s in shards:
        with safe_open(s, "pt") as f:
            for k in f.keys():
                keys[k] = s
    plan = {}
    for mod, ab in mods.items():
        plan.setdefault(keys[base_key(mod, keys)], {})[base_key(mod, keys)] = ab
    done = 0
    for s in shards:
        with safe_open(s, "pt") as f:
            meta = f.metadata()
            tensors = {k: f.get_tensor(k) for k in f.keys()}
        for k, (A, B) in plan.get(s, {}).items():
            w = tensors[k]
            tensors[k] = (w.float() + (B.float() @ A.float()) * scale).to(w.dtype)
            done += 1
        save_file(tensors, out / s.name, metadata=meta)
        del tensors
        print(f"{s.name}: merged {len(plan.get(s, {}))}", flush=True)
    for p in base.iterdir():
        if p.is_file() and p.suffix != ".safetensors" and p.name not in ("README.md",):
            shutil.copy2(p, out / p.name)
    print(json.dumps({"merged_modules": done, "adapter_modules": len(mods), "scale": scale, "out": str(out)}))
    if done != len(mods):
        raise SystemExit("not every adapter module was merged")


if __name__ == "__main__":
    main()
