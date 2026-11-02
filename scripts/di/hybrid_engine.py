"""Exact option scoring for hybrid (linear-attention) causal LMs such as Qwen3.5, for the Decision Index kit.

The kit's reference `transformers` engine scores all options in one pass with a block-diagonal 4D mask and
reuses a cropped KV cache across questions. Neither is possible for Gated-DeltaNet / linear-attention layers
(their recurrent state cannot be masked per option or cropped), and on Qwen3.5 the reference engine raises
`has_previous_state can only be called on LinearAttention layers`.

This engine keeps everything else identical to the reference engine (same `render_prompt`, system prompt,
chat template, option-key tokenization, context-limit refusal, summed key log-probability, softmax over
options) and changes only the computation:
  1. one forward pass over the prompt (fresh cache per question, no cross-question prefix reuse; prompts longer than
     `prefill_chunk` tokens are fed in chunks through the cache, which is the same computation with bounded memory);
  2. the first key token of every option is read from the last prompt position;
  3. remaining key tokens are scored by continuing a copy of the prompt cache, batched over options.
Result equals naive per-option scoring (checked in `selftest`).

Use: python -m decision_index run --engine hybrid_engine:ExactTransformersEngine --model <dir> --option threads=10 ...
(with this file's directory on PYTHONPATH).
"""
import copy
import os

from decision_index.engines.base import Unsupported
from decision_index.engines.transformers_engine import TransformersEngine


def _repeat_cache(cache, n):
    torch = __import__("torch")

    def rep(t):
        if isinstance(t, torch.Tensor) and t.dim() > 0 and t.shape[0] == 1:
            return t.repeat_interleave(n, dim=0)
        if isinstance(t, list):
            return [rep(x) for x in t]
        if isinstance(t, dict):
            return {k: rep(v) for k, v in t.items()}
        return t

    # transformers <5.20 stores one tensor per layer; 5.20+ stores lists/dicts indexed by state_idx.
    for layer in getattr(cache, "layers", []):
        for name in ("keys", "values", "conv_states", "recurrent_states"):
            t = getattr(layer, name, None)
            if t is not None:
                setattr(layer, name, rep(t))
    return cache


class ExactTransformersEngine(TransformersEngine):
    name = "transformers-exact"
    latency = "CPU in-process request wall time including prompt construction; one prompt pass per question (no cross-question prefix reuse); excludes model loading."

    def __init__(self, threads=None, option_batch=64, cache_token_budget=131072, prefill_chunk=4096, end_token=False, letters=False, load_4bit=False, adapter=None, tta=1, prefix_share=True, prefix_min=64, **options):
        import torch

        threads = int(threads or os.environ.get("DI_THREADS", 0) or 0)
        if threads:
            torch.set_num_threads(threads)
            try:
                torch.set_num_interop_threads(max(1, min(threads, 4)))
            except RuntimeError:
                pass
        options["cache_prefix"] = False
        try:
            # Same fix as training/pro/train_lora.py: with enable_gqa=True and head_dim 256, Windows torch has no
            # flash kernel and the memory-efficient kernel rejects GQA, so SDPA fell back to the slow math kernel.
            # Repeating K/V instead keeps the identical computation on the efficient kernel.
            import transformers.integrations.sdpa_attention as _sdpa

            _sdpa.use_gqa_in_sdpa = lambda *a, **k: False
        except Exception:
            pass
        load_4bit = str(load_4bit).lower() in ("1", "true", "yes")
        if load_4bit or adapter:
            # QLoRA checkpoints (training/pro/train_lora.py --qlora): NF4 base as trained, LoRA adapter kept unmerged.
            import transformers

            orig = transformers.AutoModelForCausalLM

            class _Load:
                @staticmethod
                def from_pretrained(path, **kw):
                    if load_4bit:
                        kw["quantization_config"] = transformers.BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
                        kw["device_map"] = {"": 0}
                    m = orig.from_pretrained(path, **kw)
                    if adapter:
                        from peft import PeftModel

                        m = PeftModel.from_pretrained(m, adapter)
                        if not load_4bit:
                            m = m.merge_and_unload()
                    if load_4bit:
                        m.to = lambda *a, **k: m  # placed by device_map; 4-bit weights cannot be moved
                    return m

            transformers.AutoModelForCausalLM = _Load
            try:
                super().__init__(**options)
            finally:
                transformers.AutoModelForCausalLM = orig
        else:
            super().__init__(**options)
        self.option_batch = int(option_batch)
        self.prefix_min = int(prefix_min)
        self.cache_token_budget = int(cache_token_budget)
        self.prefill_chunk = int(prefill_chunk)
        # Keel-Pro serving policy: score "key then end of turn", i.e. P(the reply is exactly this key). Without it a key
        # that is a token prefix of another (option_1 vs option_10) always outscores the longer one.
        self.end_token = str(end_token).lower() in ("1", "true", "yes")
        self.end_id = self.tok.convert_tokens_to_ids("<|im_end|>") if self.end_token else None
        if self.end_token:
            self.name = "transformers-exact-endtoken"
        if torch.cuda.is_available():
            # Windows WDDM spills past-VRAM allocations into system RAM (~100x slower); OOM instead and back off.
            torch.cuda.set_per_process_memory_fraction(0.94)
        self.provenance.update(
            kind="transformers-exact",
            threads=torch.get_num_threads(),
            prefix_cache=False,
            policy="Kit reference prompt and scoring (decision_index.engines.transformers_engine.render_prompt, SYSTEM_PROMPT, chat template, summed option-key log-probability, softmax over options, Unsupported above the context limit, no truncation, no option filtering). Computed exactly for hybrid linear-attention models: one prompt pass per question, first key token from the last prompt position, later key tokens by continuing a copy of the prompt cache batched over options.",
        )
        if self.end_token:
            self.provenance.update(kind="transformers-exact-endtoken", end_token="<|im_end|>", policy=self.provenance["policy"] + " Keel-Pro serving policy: each option key is scored with the end-of-turn token appended (P(reply == key)), as serve/keel_pro_server.py does.")
        self.letters = str(letters).lower() in ("1", "true", "yes")
        if self.letters:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "training" / "pro"))
            import common

            self._common = common
            self.name = "transformers-letters"
            self.provenance.update(kind="transformers-letters", policy="Keel-Pro letters serving policy (training/pro/common.py prompt_ids_letters): options shown in the given order with single-token labels A..Z, AA..; thinking disabled; one prompt pass; option probabilities are the softmax over the label logits at the answer position. Unsupported above the context limit, no truncation, no option filtering.")
        if load_4bit or adapter:
            self.provenance.update(quantization="bitsandbytes-nf4-double" if load_4bit else None, adapter=str(adapter) if adapter else None)
        self.tta = max(1, int(tta))
        if self.letters and self.tta > 1:
            self.provenance.update(tta=self.tta, policy=self.provenance["policy"] + f" Order averaging: probabilities are the mean over {self.tta} option orders (as given, reversed, then fixed-seed shuffles).")
        self.prefix_share = self.letters and str(prefix_share).lower() in ("1", "true", "yes")
        if self.prefix_share:
            self.provenance.update(prefix_share=True, policy=self.provenance["policy"] + " Multi-question requests: the token prefix shared by all questions' prompts (system + state) is run once; each question's remaining tokens continue a copy of that cache, batched across questions with right padding (causal, so padding never reaches a scored position). Same prompts and read-out as one pass per question.")

    def _letters_shared(self, state, questions):
        torch = self.torch
        items = []
        for k, q in questions.items():
            if q["type"] not in ("choice", "noul"):
                raise Unsupported("Unsupported question type " + str(q["type"]))
            try:
                ids, keys, lids = self._common.prompt_ids_letters(self.tok, state, q, self._common.option_keys(q))
            except ValueError as e:
                raise Unsupported(str(e))
            if len(ids) + 1 > self.limit:
                raise Unsupported(f"prompt of {len(ids)} tokens plus option exceeds the {self.limit}-token context limit")
            items.append((k, q, ids, keys, lids))
        n = len(os.path.commonprefix([it[2] for it in items]))
        n = min(n, min(len(it[2]) for it in items) - 1)
        if n < self.prefix_min:
            return self._letters_each(items)
        answers, raw = {}, {}
        with torch.inference_mode():
            base = self._prefill(items[0][2][:n]).past_key_values
            pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else 0
            # Shortest suffixes first; a batch grows while padding stays under 25% of its tokens, so padding waste
            # does not undo the shared-prefix saving on rows whose questions differ in length (retrieval candidates).
            order = sorted(items, key=lambda it: len(it[2]))
            batches, cur = [], []
            for it in order:
                ln = len(it[2]) - n
                cap = max(1, min(self.option_batch, self.cache_token_budget // max(1, len(it[2]))))
                if cur and (len(cur) >= cap or (len(cur) + 1) * ln > 1.25 * (sum(len(c[2]) - n for c in cur) + ln)):
                    batches.append(cur)
                    cur = []
                cur.append(it)
            batches.append(cur)
            while batches:
                part = batches.pop(0)
                sfx = [it[2][n:] for it in part]
                w = max(len(x) for x in sfx)
                feed = torch.tensor([x + [pad] * (w - len(x)) for x in sfx], device=self.device)
                last = torch.tensor([len(x) - 1 for x in sfx], device=self.device)
                try:
                    cache = _repeat_cache(copy.deepcopy(base), len(part))
                    out = self.model(input_ids=feed, past_key_values=cache, use_cache=True, logits_to_keep=torch.unique(last))
                except torch.OutOfMemoryError:
                    cache = out = None
                    if len(part) == 1:
                        raise
                    torch.cuda.empty_cache()
                    h = len(part) // 2
                    batches[:0] = [part[:h], part[h:]]
                    continue
                cols = torch.unique(last)
                for b, (k, q, ids, keys, lids) in enumerate(part):
                    j = int((cols == last[b]).nonzero()[0, 0])
                    logits = out.logits[b, j].float()
                    lp = torch.log_softmax(logits, -1)[torch.tensor(lids, device=logits.device)]
                    probs = dict(zip(keys, torch.softmax(lp, -1).tolist()))
                    self._emit(answers, raw, k, q, keys, probs, len(ids), n)
                del cache, out
        answers = {k: answers[k] for k in questions}
        raw = {k: raw[k] for k in questions}
        return {"model": self.model_id, "answers": answers, "usage": {"input_tokens": sum(v["prompt_tokens"] for v in raw.values())}}, raw

    def _letters_each(self, items):
        torch = self.torch
        answers, raw = {}, {}
        for k, q, ids, keys, lids in items:
            with torch.inference_mode():
                logits = self._prefill(ids).logits[0, -1].float()
            lp = torch.log_softmax(logits, -1)[torch.tensor(lids, device=logits.device)]
            self._emit(answers, raw, k, q, keys, dict(zip(keys, torch.softmax(lp, -1).tolist())), len(ids), 0)
        return {"model": self.model_id, "answers": answers, "usage": {"input_tokens": sum(v["prompt_tokens"] for v in raw.values())}}, raw

    @staticmethod
    def _emit(answers, raw, k, q, keys, probs, n_tok, cached):
        choice = max(keys, key=lambda x: probs[x])
        raw[k] = {"option_probs": probs, "orders": 1, "prompt_tokens": n_tok, "cached_prefix_tokens": cached}
        if q["type"] == "choice":
            answers[k] = {"type": "choice", "choice": choice, "probabilities": probs}
        else:
            answers[k] = {"type": "noul", "noul": probs["true"]}

    def __call__(self, state, questions):
        if not self.letters:
            return super().__call__(state, questions)
        torch = self.torch
        if self.prefix_share and self.tta == 1 and len(questions) > 1:
            try:
                return self._letters_shared(state, questions)
            except torch.OutOfMemoryError:
                # Very long states (e.g. 39k-token ToolRet rows): the shared cache plus a suffix batch can exceed VRAM.
                # Free it and score one question at a time (chunked prefill), same prompts and read-out.
                import gc

                gc.collect()
                torch.cuda.empty_cache()
        answers, raw = {}, {}
        for k, q in questions.items():
            if q["type"] not in ("choice", "noul"):
                raise Unsupported("Unsupported question type " + str(q["type"]))
            keys0 = self._common.option_keys(q)
            orders = [keys0]
            if self.tta > 1 and len(keys0) > 1:
                import random

                orders.append(keys0[::-1])
                rng = random.Random(len(keys0))
                while len(orders) < self.tta:
                    o = list(keys0)
                    rng.shuffle(o)
                    orders.append(o)
            acc = dict.fromkeys(keys0, 0.0)
            n_tok = 0
            for order in orders:
                try:
                    ids, keys, lids = self._common.prompt_ids_letters(self.tok, state, q, order)
                except ValueError as e:
                    raise Unsupported(str(e))
                if len(ids) + 1 > self.limit:
                    raise Unsupported(f"prompt of {len(ids)} tokens plus option exceeds the {self.limit}-token context limit")
                with torch.inference_mode():
                    logits = self._prefill(ids).logits[0, -1].float()
                lp = torch.log_softmax(logits, -1)[torch.tensor(lids, device=logits.device)]
                for key, p in zip(keys, torch.softmax(lp, -1).tolist()):
                    acc[key] += p / len(orders)
                n_tok += len(ids)
            probs = acc
            choice = max(keys0, key=lambda x: probs[x])
            raw[k] = {"option_probs": probs, "orders": len(orders), "prompt_tokens": n_tok, "cached_prefix_tokens": 0}
            if q["type"] == "choice":
                answers[k] = {"type": "choice", "choice": choice, "probabilities": probs}
            else:
                answers[k] = {"type": "noul", "noul": probs["true"]}
        return {"model": self.model_id, "answers": answers, "usage": {"input_tokens": sum(v["prompt_tokens"] for v in raw.values())}}, raw

    def _option_ids(self, keys):
        out = super()._option_ids(keys)
        return [o + [self.end_id] for o in out] if self.end_token else out

    def _prefill(self, q_ids):
        """Prompt forward. Long prompts go in chunks through the cache (same math), because SDPA here falls back to a
        kernel that materializes the full L x L attention matrix (15 GB per layer at 22k tokens)."""
        torch = self.torch
        cache = None
        for s in range(0, len(q_ids), self.prefill_chunk):
            chunk = torch.tensor([q_ids[s : s + self.prefill_chunk]], device=self.device)
            out = self.model(input_ids=chunk, past_key_values=cache, use_cache=True, logits_to_keep=1)
            cache = out.past_key_values
        return out

    def _score_options(self, p, q_ids, options):
        torch = self.torch
        with torch.inference_mode():
            out = self._prefill(q_ids)
            first = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
            base = out.past_key_values
            scores = [first[o[0]].item() for o in options]
            multi = [i for i, o in enumerate(options) if len(o) > 1]
            # Each option row holds a full copy of the prompt cache; bound copies x prompt length so long prompts
            # (e.g. 15k-token ToolRet rows) do not exhaust VRAM. Halve and retry on OOM. Results are unchanged.
            batch = max(1, min(self.option_batch, self.cache_token_budget // max(1, len(q_ids))))
            s = 0
            while s < len(multi):
                idx = multi[s : s + batch]
                try:
                    part = self._continue(base, idx, options)
                except torch.OutOfMemoryError:
                    if batch == 1:
                        raise
                    torch.cuda.empty_cache()
                    batch = max(1, batch // 2)
                    continue
                for i, v in part.items():
                    scores[i] += v
                s += len(idx)
        return scores

    def _continue(self, base, idx, options):
        torch = self.torch
        width = max(len(options[i]) for i in idx) - 1
        pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else 0
        feed = [options[i][:-1] + [pad] * (width - (len(options[i]) - 1)) for i in idx]
        cache = _repeat_cache(copy.deepcopy(base), len(idx))
        o2 = self.model(input_ids=torch.tensor(feed, device=self.device), past_key_values=cache, use_cache=True)
        lp = torch.log_softmax(o2.logits.float(), dim=-1)
        out = {}
        for b, i in enumerate(idx):
            o = options[i]
            out[i] = sum(lp[b, j, o[j + 1]].item() for j in range(len(o) - 1))
        del cache, o2, lp
        return out

    def reset_cache(self):
        pass


def selftest(model="Qwen/Qwen3.5-0.8B", threads=8):
    import torch

    e = ExactTransformersEngine(model=model, threads=threads)
    q = {"type": "choice", "instructions": "What is the customer's intent?", "criteria": {"card_arrival": "card arrival", "card_linking": "link card", "exchange_rate": "exchange rate", "lost_or_stolen_card": "lost card", "A": "short key"}}
    st = "I still have not received my new card, when will it arrive?"
    ids = e._prompt_ids(st, q)
    opts = e._option_ids(list(q["criteria"]))
    got = e._score_options(0, ids, opts)
    worst = 0.0
    for o, g in zip(opts, got):
        with torch.inference_mode():
            lp = torch.log_softmax(e.model(input_ids=torch.tensor([ids + o], device=e.device)).logits[0].float(), -1)
        ref = sum(lp[len(ids) - 1 + i, o[i]].item() for i in range(len(o)))
        worst = max(worst, abs(ref - g))
        print(len(o), round(g, 5), round(ref, 5))
    print("max abs diff", worst)
    return worst


if __name__ == "__main__":
    import sys

    selftest(*(sys.argv[1:2] or []))
