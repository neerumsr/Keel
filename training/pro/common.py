"""Shared prompt + example construction for Keel-Pro.

The prompt is byte-identical to the Decision Index `transformers` engine
(decision_index/engines/transformers_engine.py, MIT) so training matches inference.
"""
import json

SYSTEM_PROMPT = "You are a decision engine. Read the state, then answer the question by replying with exactly one option key from the list. Do not explain."
END = "<|im_end|>"


def text(x):
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def render_prompt(state, question):
    lines = ["State:", text(state) if state not in ("", None, {}, []) else "(empty)", "", "Question:", text(question.get("instructions", "")), "", "Options:"]
    criteria = question["criteria"] if question["type"] == "choice" else {"false": "False", "true": "True"}
    for key, description in criteria.items():
        lines.append(f"{key}: {key if description is None else text(description)}")
    lines += ["", "Reply with exactly one option key."]
    return "\n".join(lines)


def option_keys(question):
    return list(question["criteria"]) if question["type"] == "choice" else ["false", "true"]


def prompt_ids(tok, state, question):
    body = render_prompt(state, question)
    prompt = tok.apply_chat_template([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": body}], tokenize=False, add_generation_prompt=True)
    return tok(prompt, add_special_tokens=False)["input_ids"]


_key_cache = {}


def key_ids(tok, key, end_id=None):
    """Option key tokens exactly as the kit scores them with a chat template: tok(key), no end token."""
    k = (id(tok), key)
    if k not in _key_cache:
        _key_cache[k] = tok(key, add_special_tokens=False)["input_ids"]
    return _key_cache[k]


def truncate_state(tok, state, max_chars):
    """Shorten long string/JSON states for training only (inference never truncates)."""
    s = text(state)
    if len(s) <= max_chars:
        return state
    if isinstance(state, str):
        return state[: max_chars // 2] + " ... " + state[-max_chars // 2 :]
    return s[: max_chars // 2] + " ... " + s[-max_chars // 2 :]


# ---- Keel-Pro "letters" serving policy -------------------------------------------------------------------------
# Options are shown with single-token labels (A..Z, then single-token letter pairs AA, AB, ...). One forward pass over
# the prompt; the option distribution is the softmax of the label logits at the first answer position. No multi-token
# keys, so no prefix bias (option_1 vs option_10) and no length bias. Thinking is disabled in the chat template.
LETTER_SYSTEM = "You are a decision engine. Read the state, then answer the question by replying with the label of exactly one option. Do not explain."
_label_cache = {}


def labels(tok):
    """Ordered single-token labels and their ids (A..Z then two-letter pairs that encode as one token)."""
    k = id(tok)
    if k not in _label_cache:
        import string

        cand = list(string.ascii_uppercase) + [a + b for a in string.ascii_uppercase for b in string.ascii_uppercase]
        labs, ids = [], []
        for c in cand:
            t = tok(c, add_special_tokens=False)["input_ids"]
            if len(t) == 1:
                labs.append(c)
                ids.append(t[0])
        _label_cache[k] = (labs, ids)
    return _label_cache[k]


def render_prompt_letters(state, question, order, labs):
    lines = ["State:", text(state) if state not in ("", None, {}, []) else "(empty)", "", "Question:", text(question.get("instructions", "")), "", "Options:"]
    criteria = question["criteria"] if question["type"] == "choice" else {"false": "False", "true": "True"}
    for lab, key in zip(labs, order):
        d = criteria[key]
        d = None if d is None else text(d)
        if d is None or d == key:
            lines.append(f"{lab}. {key}")
        elif _opaque(key):
            lines.append(f"{lab}. {d}")
        else:
            lines.append(f"{lab}. {key}: {d}")
    lines += ["", "Reply with exactly one option label."]
    return "\n".join(lines)


def _opaque(key):
    """Short or numbered keys (A, 3, option_7) carry no meaning and would clash with the labels; show only the text."""
    import re

    return len(key) <= 3 or re.fullmatch(r"(option|opt|choice|answer)[_ -]?\d+", key, re.I) is not None


def prompt_ids_letters(tok, state, question, order=None):
    """Return (prompt ids, option keys in shown order, label token ids). Raises ValueError if too many options."""
    keys = option_keys(question)
    order = list(order) if order is not None else keys
    labs, lids = labels(tok)
    if len(order) > len(labs):
        raise ValueError(f"{len(order)} options exceed the {len(labs)} single-token labels")
    body = render_prompt_letters(state, question, order, labs)
    prompt = tok.apply_chat_template([{"role": "system", "content": LETTER_SYSTEM}, {"role": "user", "content": body}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return tok(prompt, add_special_tokens=False)["input_ids"], order, lids[: len(order)]


def build_example_letters(tok, state, question, gold, max_len=768, rng=None, shuffle=0.5):
    """Letters policy example. With probability `shuffle` the option order is permuted (training only) so the model
    cannot learn a positional prior on labels. Target: the gold label at the last prompt position."""
    keys = option_keys(question)
    if question["type"] == "noul":
        gold = "true" if gold in (True, "true", 1) else "false"
    if gold not in keys:
        return None
    order = list(keys)
    if rng is not None and rng.random() < shuffle:
        rng.shuffle(order)
    try:
        p, order, lids = prompt_ids_letters(tok, state, question, order)
    except ValueError:
        return None
    if len(p) > max_len:
        return None
    gi = order.index(gold)
    return {"ids": p, "tgt_pos": [len(p) - 1], "tgt_ids": [lids[gi]], "opt_first": lids, "gold_idx": gi}


def build_example(tok, state, question, gold, max_len=768, end_id=None):
    """Return dict(ids, tgt_pos, tgt_ids, opt_first, gold_idx) or None if too long.

    tgt_*: teacher-forced gold key tokens (LM loss; the kit scores the summed key-token log-probability). With end_id
    the end-of-turn token is a target too, matching the Keel-Pro serving policy P(reply == key).
    opt_first: first token of every option when all distinct (single-position listwise loss).
    """
    keys = option_keys(question)
    if question["type"] == "noul":
        gold = "true" if gold in (True, "true", 1) else "false"
    if gold not in keys:
        return None
    p = prompt_ids(tok, state, question)
    g = key_ids(tok, gold) + ([end_id] if end_id is not None else [])
    ids = p + g[:-1]
    if len(ids) > max_len:
        return None
    tgt_pos = list(range(len(p) - 1, len(p) - 1 + len(g)))
    firsts = [key_ids(tok, k)[0] for k in keys]
    opt_first = firsts if len(set(firsts)) == len(firsts) else None
    return {"ids": ids, "tgt_pos": tgt_pos, "tgt_ids": g, "opt_first": opt_first, "gold_idx": keys.index(gold)}
