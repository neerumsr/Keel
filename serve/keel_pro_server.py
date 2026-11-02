"""Keel-Pro sidecar: serves a Keel-Pro (Qwen3.5 + LoRA, merged) model to Keel's /api/v1/systemone on loopback.

Keel validates the System One request and formats the answer; this process only turns each question into option
probabilities, with exactly the prompt and scoring the model was trained and measured with (training/pro/common.py).
Two policies (--policy, must match training):
  letters (default): options shown with single-token labels A..Z, AA..; one prompt pass; softmax over the label
    logits at the answer position (train_lora.py --letters; hybrid_engine.py letters=1).
  end-token: the Decision Index `transformers` prompt; summed log-probability of each option key followed by
    <|im_end|>, softmaxed over options. The end token stops a key that is a prefix of another (option_1 / option_10)
    from always winning.
Score questions are asked as choices keyed "0".."n-1"; noul questions as the options false/true.

usage: python serve/keel_pro_server.py --model-dir <merged model dir> [--port 8090] [--device cuda] [--policy letters]
       python serve/keel_pro_server.py --model-dir <base dir> --adapter <adapter dir> [--load-4bit]   (QLoRA runs)
  GET  /health      -> {"model": ..., "ready": true}
  POST /v1/weights  {"state": <json>, "questions": [Keel normalized questions]}
                    -> {"model": ..., "weights": {qid: {key: percent} | {"yes": percent}}, "latency_ms": ...}
See artifacts/parity/pro/SERVE.md.
"""
import argparse
import copy
import json
import math
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training" / "pro"))
from common import key_ids, prompt_ids, prompt_ids_letters  # noqa: E402

MODEL_ID = "decider-pro-1.0.0"
MAX_BODY = 16 << 20  # Keel caps the Pro pin at 200k-char states and 100k-char instructions (wire.ts PRO_LIMITS)


def _repeat_cache(cache, n):
    """Repeat a batch-1 transformers cache n times (handles 5.20+ per-state lists/dicts of linear-attention layers)."""
    import torch

    def rep(t):
        if isinstance(t, torch.Tensor) and t.dim() > 0 and t.shape[0] == 1:
            return t.repeat_interleave(n, dim=0)
        if isinstance(t, list):
            return [rep(x) for x in t]
        if isinstance(t, dict):
            return {k: rep(v) for k, v in t.items()}
        return t

    for layer in getattr(cache, "layers", []):
        for name in ("keys", "values", "conv_states", "recurrent_states"):
            t = getattr(layer, name, None)
            if t is not None:
                setattr(layer, name, rep(t))
    return cache


def as_di_question(q):
    """Keel's normalized question -> the DI question shape that render_prompt expects."""
    if q["type"] == "noul":
        if q.get("yes") or q.get("no"):
            criteria = {"false": q.get("no") or "False", "true": q.get("yes") or "True"}
            return {"type": "choice", "instructions": q.get("instructions", ""), "criteria": criteria}
        return {"type": "noul", "instructions": q.get("instructions", "")}
    if q["type"] == "choice":
        criteria = {o["key"]: (o.get("description") or None) for o in q["options"]}
    else:
        criteria = {str(i): level for i, level in enumerate(q["levels"])}
    return {"type": "choice", "instructions": q.get("instructions", ""), "criteria": criteria}


class Scorer:
    def __init__(self, model_dir, device, policy="letters", adapter=None, load_4bit=False):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        try:
            # GQA through SDPA with head_dim 256 falls back to the slow math kernel on Windows torch; repeating K/V
            # keeps the identical computation on the efficient kernel (same fix as scripts/di/hybrid_engine.py).
            import transformers.integrations.sdpa_attention as _sdpa

            _sdpa.use_gqa_in_sdpa = lambda *a, **k: False
        except Exception:
            pass
        self.torch = torch
        self.device = device
        self.policy = policy
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
        if load_4bit:
            from transformers import BitsAndBytesConfig

            q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
            self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16, quantization_config=q, device_map={"": 0})
        else:
            self.model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype).to(device)
        if adapter:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter)
            if not load_4bit:
                self.model = self.model.merge_and_unload()
        self.model.eval()
        self.end_id = self.tok.convert_tokens_to_ids("<|im_end|>")
        self.pad_id = self.tok.pad_token_id if self.tok.pad_token_id is not None else 0
        self.lock = threading.Lock()

    def option_probs(self, state, question):
        if self.policy == "letters":
            return self.letter_probs(state, question)
        torch = self.torch
        keys = list(question["criteria"]) if question["type"] == "choice" else ["false", "true"]
        p = prompt_ids(self.tok, state, question)
        # Serving policy (as measured, scripts/di/hybrid_engine.py end_token=1): score "key then end of turn", so a key
        # that is a token prefix of another (option_1 / option_10) cannot win by being shorter.
        opts = [key_ids(self.tok, k) + [self.end_id] for k in keys]
        with self.lock, torch.inference_mode():
            cache, out = None, None
            for s in range(0, len(p), 4096):
                out = self.model(input_ids=torch.tensor([p[s : s + 4096]], device=self.device), past_key_values=cache, use_cache=True, logits_to_keep=1)
                cache = out.past_key_values
            first = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
            scores = [first[o[0]].item() for o in opts]
            batch = max(1, min(64, 131072 // max(1, len(p))))
            for s in range(0, len(opts), batch):
                idx = list(range(s, min(len(opts), s + batch)))
                width = max(len(opts[i]) for i in idx) - 1
                feed = [opts[i][:-1] + [self.pad_id] * (width - len(opts[i]) + 1) for i in idx]
                c = _repeat_cache(copy.deepcopy(cache), len(idx))
                lp = torch.log_softmax(self.model(input_ids=torch.tensor(feed, device=self.device), past_key_values=c, use_cache=True).logits.float(), dim=-1)
                for b, i in enumerate(idx):
                    o = opts[i]
                    scores[i] += sum(lp[b, j, o[j + 1]].item() for j in range(len(o) - 1))
                del c, lp
        m = max(scores)
        e = [math.exp(s - m) for s in scores]
        z = sum(e)
        return dict(zip(keys, (x / z for x in e)))

    def letter_probs(self, state, question):
        """Letters policy (as measured, scripts/di/hybrid_engine.py letters=1): options shown with single-token labels,
        one prompt pass, softmax over the label logits at the answer position."""
        torch = self.torch
        p, keys, lids = prompt_ids_letters(self.tok, state, question)
        with self.lock, torch.inference_mode():
            cache, out = None, None
            for s in range(0, len(p), 4096):
                out = self.model(input_ids=torch.tensor([p[s : s + 4096]], device=self.device), past_key_values=cache, use_cache=True, logits_to_keep=1)
                cache = out.past_key_values
            sel = out.logits[0, -1].float()[torch.tensor(lids, device=self.device)]
            pr = torch.softmax(sel, -1).tolist()
        return dict(zip(keys, pr))

    def letter_probs_many(self, state, questions):
        """Letters policy for a multi-question request: the token prefix shared by every question's prompt (system +
        state) is run once, then each question's remaining tokens continue a copy of that cache. Same prompts and
        read-out as letter_probs per question; the state is no longer re-read for every question."""
        torch = self.torch
        built = [prompt_ids_letters(self.tok, state, q) for q in questions]
        n = min(len(os.path.commonprefix([b[0] for b in built])), min(len(b[0]) for b in built) - 1)
        if n < 64:
            return [self.letter_probs(state, q) for q in questions]
        with self.lock, torch.inference_mode():
            base = None
            for s in range(0, n, 4096):
                base = self.model(input_ids=torch.tensor([built[0][0][s : min(n, s + 4096)]], device=self.device), past_key_values=base, use_cache=True, logits_to_keep=1).past_key_values
            # Suffixes continue copies of the prefix cache in right-padded batches (causal, so padding never reaches a
            # read position); shortest first, a batch closes at 32 rows, 131k tokens, or 25% padding.
            order = sorted(range(len(built)), key=lambda i: len(built[i][0]))
            batches, cur = [], []
            for i in order:
                ln = len(built[i][0]) - n
                cap = max(1, min(32, 131072 // len(built[i][0])))
                if cur and (len(cur) >= cap or (len(cur) + 1) * ln > 1.25 * (sum(len(built[c][0]) - n for c in cur) + ln)):
                    batches.append(cur)
                    cur = []
                cur.append(i)
            batches.append(cur)
            out = [None] * len(built)
            while batches:
                part = batches.pop(0)
                sfx = [built[i][0][n:] for i in part]
                w = max(map(len, sfx))
                last = torch.tensor([len(x) - 1 for x in sfx], device=self.device)
                cols = torch.unique(last)
                try:
                    cache = _repeat_cache(copy.deepcopy(base), len(part))
                    res = self.model(input_ids=torch.tensor([x + [self.pad_id] * (w - len(x)) for x in sfx], device=self.device), past_key_values=cache, use_cache=True, logits_to_keep=cols)
                except torch.OutOfMemoryError:
                    cache = res = None
                    if len(part) == 1:
                        raise
                    torch.cuda.empty_cache()
                    batches[:0] = [part[: len(part) // 2], part[len(part) // 2 :]]
                    continue
                for b, i in enumerate(part):
                    _, keys, lids = built[i]
                    j = int((cols == last[b]).nonzero()[0, 0])
                    sel = res.logits[b, j].float()[torch.tensor(lids, device=self.device)]
                    out[i] = dict(zip(keys, torch.softmax(sel, -1).tolist()))
                del cache, res
        return out

    def weights(self, state, questions):
        bag = {}
        dq = [as_di_question(q) for q in questions]
        many = self.letter_probs_many(state, dq) if self.policy == "letters" and len(dq) > 1 else None
        for i, q in enumerate(questions):
            probs = many[i] if many else self.option_probs(state, dq[i])
            bag[q["id"]] = {"yes": probs["true"] * 100} if q["type"] == "noul" else {k: v * 100 for k, v in probs.items()}
        return bag


def make_handler(scorer):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"model": MODEL_ID, "ready": True})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/weights":
                return self._send(404, {"error": "not found"})
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._send(413 if n > MAX_BODY else 400, {"error": "body required (max 16 MiB)"})
            try:
                body = json.loads(self.rfile.read(n))
                questions = body["questions"]
                assert isinstance(questions, list) and questions
            except Exception:
                return self._send(400, {"error": "expected {state, questions: [...]}"})
            t = time.perf_counter()
            try:
                bag = scorer.weights(body.get("state"), questions)
            except (KeyError, TypeError, ValueError) as e:
                return self._send(400, {"error": f"bad question: {e}"})
            self._send(200, {"model": MODEL_ID, "weights": bag, "latency_ms": round((time.perf_counter() - t) * 1000, 2)})

        def log_message(self, *args):
            pass

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--host", default="127.0.0.1", help="keep loopback: the sidecar has no auth of its own")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--policy", choices=["letters", "end-token"], default="letters", help="must match how the model was trained (train_lora.py --letters)")
    ap.add_argument("--adapter", help="LoRA adapter dir applied on top of --model-dir (QLoRA runs save only the adapter)")
    ap.add_argument("--load-4bit", action="store_true", help="load --model-dir as an NF4 base, as QLoRA runs were trained and measured (CUDA only)")
    a = ap.parse_args()
    if a.load_4bit and not a.device.startswith("cuda"):
        ap.error("--load-4bit needs --device cuda")
    if not a.device.startswith("cuda"):
        # FLA / causal-conv1d kernels are Triton (CUDA only); hiding them makes transformers use its torch path.
        for mod in ("fla", "causal_conv1d"):
            sys.modules[mod] = None
    scorer = Scorer(a.model_dir, a.device, a.policy, a.adapter, a.load_4bit)
    server = ThreadingHTTPServer((a.host, a.port), make_handler(scorer))
    print(json.dumps({"event": "ready", "model": MODEL_ID, "policy": a.policy, "url": f"http://{a.host}:{a.port}"}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
