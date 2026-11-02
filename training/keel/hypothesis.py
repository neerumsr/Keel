"""Keel-2 hypothesis spec — mirror of src/lib/decider/hypothesis.ts. Keep them identical."""
from __future__ import annotations

import json
import re
from typing import Any

HYPOTHESIS_VERSION = 1


def human_key(key: str) -> str:
    return re.sub(r"[_:-]+", " ", key).strip()


def _join(instructions: str, answer: str, detail: str) -> str:
    head = f"{instructions.strip()} Answer: {answer.strip()}."
    tail = detail.strip()
    return f"{head} {tail}" if tail else head


def render(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, indent=2)


def state_text(state: Any) -> str:
    """Same as wire.ts: strings pass through, JSON values are compact-stringified."""
    if isinstance(state, str):
        s = state.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.dumps(json.loads(s), separators=(",", ":"), ensure_ascii=False)
            except json.JSONDecodeError:
                return state
        return state
    return json.dumps(state, separators=(",", ":"), ensure_ascii=False)


def hypotheses(question: dict) -> list[str]:
    """question uses the wire shape: {type, instructions, criteria}."""
    qtype = question["type"]
    instructions = render(question["instructions"]).strip()
    criteria = question.get("criteria")
    if qtype == "choice":
        return [_join(instructions, human_key(k), render(v).strip() if v is not None else "") for k, v in criteria.items()]
    if qtype == "score":
        levels = criteria if isinstance(criteria, list) else [criteria[k] for k in sorted(criteria, key=lambda x: int(x))]
        return [_join(instructions, render(level).strip(), "") for level in levels]
    c = criteria or {}
    yes = render(c.get("true")).strip()[:400]
    no = render(c.get("false")).strip()[:400]
    return [_join(instructions, "yes", yes), _join(instructions, "no", no)]
