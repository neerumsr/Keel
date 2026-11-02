# Serving Keel-Pro

Keel-Pro (`decider-pro-1.0.0`) is an optional, opt-in model. Keel-Lite (`decider-latest`, `decider-3.0.0`) stays the
default and needs nothing below. Keel-Pro runs as a separate loopback process (the "sidecar"), and Keel's own
`/api/v1/systemone` and MCP server proxy to it only when a request pins `"model": "decider-pro-1.0.0"`.

## 1. Run the sidecar

Requirements: Python 3.12, `torch` (CUDA build for GPU), `transformers>=5.20`, and for fast Qwen3.5 linear attention on
GPU, `flash-linear-attention` (on Windows also `triton-windows`). A merged Keel-Pro model directory (config, safetensors,
tokenizer and chat template).

```powershell
python serve\keel_pro_server.py --model-dir <path to merged Keel-Pro> --port 8090 --device cuda
# CPU works too (much slower, about 1.3 s per question for the 4B): --device cpu
# On CPU the sidecar hides the Triton FLA kernels so transformers uses its pure-torch linear attention.

# 27B QLoRA release (it7 and later), as measured: 4-bit NF4 base + the LoRA adapter, about 21 GB of GPU memory
python serve\keel_pro_server.py --model-dir <Qwen3.5-27B> --adapter <keel-pro adapter> --load-4bit --port 8090
```

No 24 GB+ GPU? Use the GGUF build (Q4_K_M 16.8 GB, Q8_0 29.0 GB) with llama.cpp. It matched the measured HF run on
30 of 30 dev questions (`scripts/di/gguf_check.py`).

It prints `{"event": "ready", ...}` when the model is loaded. Check it with `GET http://127.0.0.1:8090/health`.

The sidecar binds `127.0.0.1` and has no authentication of its own. Do not bind it to another interface. Keel refuses
to send decision state to a non-loopback `KEEL_PRO_URL`.

## 2. Point Keel at it

The default URL is `http://127.0.0.1:8090`. To change the port, set `KEEL_PRO_URL` (loopback only) before
`npm run dev` / `npm start`.

```powershell
$env:KEEL_PRO_URL = "http://127.0.0.1:8091"; npm run dev
```

## 3. Ask Keel-Pro

Same System One body, with the model pinned:

```json
POST http://127.0.0.1:8080/api/v1/systemone
Authorization: Bearer <KEEL_TOKEN>
{ "model": "decider-pro-1.0.0", "state": { ... }, "questions": { ... } }
```

The answer has the usual shape and `"model": "decider-pro-1.0.0"`. When the sidecar is not running, Keel answers
`503 model_unavailable` and makes no decision. It does **not** fall back to Keel-Lite, because a pinned answer must come
from the pinned model. MCP: pass `model: "decider-pro-1.0.0"` to the decide tool.

Keel-Pro reads long contexts, so Keel's wire accepts more for this pin than for Keel-Lite: an empty `state`, states up
to 200,000 characters, instructions up to 100,000 and descriptions up to 8,000 (`PRO_LIMITS` in
`src/lib/decider/wire.ts`). Question and option counts are unchanged. For benchmark runs over HTTP, start Keel with
`KEEL_RATE_PER_MINUTE=0` to lift the 120-per-minute limit.

## How a question is asked

The sidecar has two read-out policies (`--policy`, default `letters`); serve with the one the checkpoint was trained
for. Both build their prompts in `training/pro/common.py`, the same code used for training and evaluation.

**`letters` (default, it5 onward).** The options are listed as `A. key: description` lines (single-token labels
A–Z, then two-letter labels; up to 588 options), with system prompt `LETTER_SYSTEM` and `enable_thinking=False`. Keys
that carry no meaning of their own (≤3 characters, or `option_N`-style) are hidden when a description exists. One
forward pass; the answer is the softmax over the label logits at the final position. Training shuffles option order
for half of the examples so that position carries no signal.

**`end-token` (it1–it3).** The prompt is the Decision Index `transformers` prompt. Each option is scored as the summed
log-probability of its key **followed by `<|im_end|>`**, softmaxed over options. The kit's local engine scores the bare
key, so when keys share a prefix (`option_1` and `option_10`) the shorter key always wins. Scoring the end token closes
the key and removes that bias.

`di-results.md` labels every number `kit` (bare key), `end-token` or `letters`.

- `choice`: the option keys and their descriptions.
- `score`: asked as a choice with keys `"0"`…`"n-1"` (the levels as descriptions). The score is the expected level.
- `noul`: asked with the options `false`/`true` (with your criteria text when given). `noul` = P(true).

Keel-Pro has no lexical blend and no calibration layer. Its probabilities are the model's own.

## Containers and cloud

`serve/Dockerfile` builds the sidecar image (pinned `serve/requirements.txt`), `compose.pro.yaml` runs Keel and the
sidecar on one GPU host, and `deploy/kubernetes/keel-pro.yaml` runs both in one pod so they share loopback. See
[docs/deployment.md](../../../docs/deployment.md).
