---
license: apache-2.0
base_model: neerumsr/keel-pro
base_model_relation: quantized
library_name: gguf
pipeline_tag: text-classification
language: [en]
tags: [decision-model, gguf, llama.cpp, qwen3.5, decision-index, routing, agents, llm-as-judge, keel]
---

# Keel-Pro GGUF

llama.cpp builds of [Keel-Pro](https://huggingface.co/neerumsr/keel-pro). Keel-Pro is an open-weight decision model:
give it a `state` and a typed question (`choice`, `score`, yes/no) and it returns a probability over the options. It
scores **62.73** on the full Decision Index 0.3 public suite (139,677 requests, self-reported, gated HLE counted as 0).
These files are the Keel-Pro LoRA merged into Qwen/Qwen3.5-27B, then quantized.

| File | Size | Agreement with the measured model* | Median per question, RTX 5090 |
|---|---:|---:|---:|
| `keel-pro-Q4_K_M.gguf` | 16.8 GB | 30 / 30 | 242 ms |
| `keel-pro-Q8_0.gguf` | 29.0 GB | 30 / 30 | 243 ms |

With all layers on the GPU, you need the file size plus room for the context.

\* Same option picked as the measured run (4-bit NF4 base + adapter, transformers) on 30 single-choice dev questions,
with `scripts/di/gguf_check.py` and llama.cpp b12029 (`llama-server -ngl 99`). That is a fidelity check, not a
separate Decision Index score: the 62.73 was measured with the adapter, not with these files. CPU-only llama-server
(12 threads) takes about 15 s per question.

## How Keel-Pro is asked

Keel-Pro is not a chat model. It reads one forward pass and scores single-token option labels (the `letters` read-out):
the options are shown as `A. key: description` lines under a fixed system prompt, with thinking disabled, and the
answer is the softmax over the label tokens at the last position. Use the same prompt code it was trained with
(`training/pro/common.py` in the [Keel repo](https://github.com/neerumsr/Keel)):

```bash
hf download neerumsr/keel-pro-GGUF keel-pro-Q4_K_M.gguf --local-dir models
llama-server -m models/keel-pro-Q4_K_M.gguf -ngl 99 -c 8192 --port 8091
```

```python
# from the root of a Keel checkout: pip install transformers
import json, math, sys, urllib.request
sys.path.insert(0, "training/pro")
from transformers import AutoTokenizer
from common import prompt_ids_letters

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-27B")
question = {"type": "choice", "instructions": "Which team handles this?",
            "criteria": {"billing": "payments and invoices", "tech": "bugs and outages", "account": "login and profile"}}
ids, order, label_ids = prompt_ids_letters(tok, {"ticket": "I was charged twice this month"}, question)

body = {"prompt": ids, "n_predict": 1, "n_probs": 100, "temperature": 0, "cache_prompt": False}
req = urllib.request.Request("http://127.0.0.1:8091/completion", json.dumps(body).encode(), {"Content-Type": "application/json"})
top = json.load(urllib.request.urlopen(req))["completion_probabilities"][0]
top = top.get("top_logprobs") or top["top_probs"]
logp = {t["id"]: t["logprob"] if "logprob" in t else math.log(max(t["prob"], 1e-12)) for t in top}
scores = {k: math.exp(logp[i]) for k, i in zip(order, label_ids) if i in logp}
total = sum(scores.values())
print({k: round(v / total, 4) for k, v in scores.items()})
```

llama-server returns only the top `n_probs` tokens, so the probabilities above are renormalized over the labels that
appear there. For `score` questions ask the levels as options `"0"`…`"n-1"` and take the expected level; for yes/no
ask the options `false`/`true`. [SERVE.md](https://github.com/neerumsr/Keel/blob/main/artifacts/parity/pro/SERVE.md)
has the details.

For the full Keel API (System One wire, MCP server, on/off switch), run the adapter with Keel's sidecar instead; see
the [Keel-Pro model card](https://huggingface.co/neerumsr/keel-pro) and the
[deployment guide](https://github.com/neerumsr/Keel/blob/main/docs/deployment.md). Keel's sidecar does not load GGUF
files today.

## Limitations

Same as [Keel-Pro](https://huggingface.co/neerumsr/keel-pro#limitations): English only, weakest on reasoning-heavy and
arts benchmarks, no calibration layer, not a safety classifier. Quantization was checked on 30 questions only.

## License

Apache-2.0. The Qwen3.5 base is Apache-2.0; its notice is kept in `NOTICE`.
