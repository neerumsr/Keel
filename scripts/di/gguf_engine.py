"""Decision Index engine for a Keel-Pro GGUF served by llama.cpp's llama-server (the fast serving path).

Same letters policy as hybrid_engine.py letters=1 (training/pro/common.py prompt_ids_letters): the prompt is sent as
token ids to /completion with n_predict=1; option probabilities are the softmax over the label-token probabilities at
the answer position. llama-server reports the top --top tokens only; a label outside them gets the smallest reported
probability (an upper bound on its true value) before renormalising. cache_prompt lets the server reuse the shared
system + state prefix across the questions of one request.

usage (llama-server already running with the GGUF):
  python -m decision_index run --rows <gz> --out <dir> --engine gguf_engine:GgufLettersEngine \
    --option url=http://127.0.0.1:8093 --option tokenizer=<hf model dir>
"""
import sys
from pathlib import Path

from decision_index.engines.base import Engine, Unsupported

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "training" / "pro"))
import common  # noqa: E402


class GgufLettersEngine(Engine):
    name = "llama-server-letters"
    latency = "HTTP wall time against a local llama-server (/completion, one call per question), including prompt construction; excludes server startup."

    def __init__(self, url="http://127.0.0.1:8093", tokenizer=None, top=200, cache_prompt=True, timeout=600, model_id="keel-pro", **options):
        super().__init__(**options)
        import httpx
        from transformers import AutoTokenizer

        if not tokenizer:
            raise ValueError("GgufLettersEngine needs tokenizer=<hf model dir> to build the letters prompt")
        self.tok = AutoTokenizer.from_pretrained(tokenizer)
        self.client = httpx.Client(base_url=url, timeout=float(timeout))
        self.top = int(top)
        self.cache_prompt = str(cache_prompt).lower() in ("1", "true", "yes")
        self.model_id = model_id
        props = self.client.get("/props").json()
        gen = props.get("default_generation_settings", {})
        self.limit = int(gen.get("n_ctx") or props.get("n_ctx") or 0) or None
        self.provenance = {
            "kind": "llama-server-letters",
            "url": url,
            "model_path": props.get("model_path"),
            "build": props.get("build_info"),
            "n_ctx": self.limit,
            "top": self.top,
            "cache_prompt": self.cache_prompt,
            "policy": "Keel-Pro letters serving policy (training/pro/common.py prompt_ids_letters) on a GGUF via llama-server: options shown in the given order with single-token labels; thinking disabled; one /completion call per question with n_predict=1; option probabilities are the label-token probabilities at the answer position renormalised over the labels (labels outside the reported top tokens take the smallest reported probability). Unsupported above the server context, no truncation, no option filtering.",
        }

    def _probs(self, ids, keys, lids):
        r = self.client.post("/completion", json={"prompt": ids, "n_predict": 1, "n_probs": self.top, "temperature": 0, "cache_prompt": self.cache_prompt})
        if r.status_code >= 400:
            if "context" in r.text.lower():
                raise Unsupported(r.text)
            r.raise_for_status()
        body = r.json()
        first = body["completion_probabilities"][0]
        top = first.get("top_logprobs") or first.get("top_probs") or []
        import math

        seen = {}
        for t in top:
            seen[t["id"]] = math.exp(t["logprob"]) if "logprob" in t else t["prob"]
        floor = min(seen.values()) if seen else 1.0
        p = [seen.get(i, floor) for i in lids]
        z = sum(p)
        return dict(zip(keys, (x / z for x in p))), body.get("timings", {})

    def __call__(self, state, questions):
        answers, raw = {}, {}
        for k, q in questions.items():
            if q["type"] not in ("choice", "noul"):
                raise Unsupported("Unsupported question type " + str(q["type"]))
            try:
                ids, keys, lids = common.prompt_ids_letters(self.tok, state, q, common.option_keys(q))
            except ValueError as e:
                raise Unsupported(str(e))
            if self.limit and len(ids) + 1 > self.limit:
                raise Unsupported(f"prompt of {len(ids)} tokens plus option exceeds the {self.limit}-token context limit")
            probs, timings = self._probs(ids, keys, lids)
            raw[k] = {"option_probs": probs, "prompt_tokens": len(ids), "evaluated_tokens": timings.get("prompt_n"), "prompt_ms": timings.get("prompt_ms")}
            if q["type"] == "choice":
                answers[k] = {"type": "choice", "choice": max(keys, key=lambda x: probs[x]), "probabilities": probs}
            else:
                answers[k] = {"type": "noul", "noul": probs["true"]}
        return {"model": self.model_id, "answers": answers, "usage": {"input_tokens": sum(v["prompt_tokens"] for v in raw.values())}}, raw

    def close(self):
        self.client.close()
