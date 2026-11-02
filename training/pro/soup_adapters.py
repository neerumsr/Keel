"""Average two LoRA adapters exactly: PEFT 'cat' stacks A/B so delta = w1*dW1 + w2*dW2 (rank r1+r2)."""
import argparse, json, torch
from transformers import AutoModelForCausalLM
from peft import PeftModel

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True)
ap.add_argument("--adapters", nargs="+", required=True)
ap.add_argument("--weights", nargs="+", type=float, required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
m = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16, device_map={"": "meta"} if False else "cpu", low_cpu_mem_usage=True)
names = [f"a{i}" for i in range(len(a.adapters))]
m = PeftModel.from_pretrained(m, a.adapters[0], adapter_name=names[0])
for n, p in zip(names[1:], a.adapters[1:]):
    m.load_adapter(p, adapter_name=n)
m.add_weighted_adapter(names, a.weights, "soup", combination_type="cat")
m.set_adapter("soup")
for n in names:
    m.delete_adapter(n)
m.save_pretrained(a.out)
print(json.dumps({"saved": a.out, "adapters": a.adapters, "weights": a.weights}))
