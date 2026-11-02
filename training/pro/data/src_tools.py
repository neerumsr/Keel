"""Tools & automation: 1 BFCL tool-name selection (ToolACE), 3 API-Bank tool selection (API-Bank training data),
62 When2Call MCQ (When2Call train pref/sft, assembled into 4-way MCQ)."""
import ast
import json
import re
from pathlib import Path

from rows import RAW, guard, letters, rng, row, sample

from decision_index.suite.build.adapters_added import WHEN2CALL_INSTRUCTIONS
from decision_index.suite.build.adapters_selection import apibank_catalog

REV = {
    "toolace": "Team-ACE/ToolACE@6bda777c88d21e5a204703c1ee45597a8fa4f734",
    "apibank_train": "liminghao1630/API-Bank@12e8158b7628c168f07e8f31fbbe3445e99f44cf",
    "apibank_repo": "AlibabaResearch/DAMO-ConvAI@188835d4f9948563a6b9c8ac50cd0f3ae4021ed6",
    "when2call": "nvidia/When2Call@0582f7749df63a96fdc3070932e83e72396ace53",
}

BFCL_INSTRUCTIONS = "Given the complete user conversation and the published function schemas in state, mark each " "candidate tool yes if it should be invoked to answer the request, or no otherwise. " "This evaluates tool-name selection only; do not produce arguments or call ordering.\n\n"
BFCL_CRITERIA = {"yes": "Invoke this tool.", "no": "Do not invoke this tool."}
TOOLACE_MARK = "Here is a list of functions in JSON format that you can invoke:\n"


def bfcl(cap):
    """One row per (sample, candidate tool), the per-question projection of the kit's multi-question BFCL row.
    ToolACE first user turn -> first assistant reply (must be a call list); gold = tools named in that reply.
    35% of samples use the gold-only function list (like BFCL simple), the rest the full ToolACE list."""
    src = REV["toolace"] + ":data.json"
    data = json.loads(guard(RAW / "hf/toolace/data.json").read_text(encoding="utf-8"))
    out = []
    for i, x in enumerate(data):
        conv = x["conversations"]
        s = x["system"]
        if TOOLACE_MARK not in s or len(conv) < 2 or conv[0]["from"] != "user" or conv[1]["from"] != "assistant":
            continue
        try:
            funcs, _ = json.JSONDecoder().raw_decode(s.split(TOOLACE_MARK, 1)[1].lstrip())
        except json.JSONDecodeError:
            continue
        funcs = [{k: v for k, v in f.items() if not (k == "required" and v is None)} for f in funcs if isinstance(f, dict) and f.get("name")]
        reply = conv[1]["value"].strip()
        if not funcs or not (reply.startswith("[") and "(" in reply):
            continue
        names = [f["name"] for f in funcs]
        if len(set(names)) != len(names):
            continue
        needed = {n for n in names if re.search(r"(^\[|,\s*)" + re.escape(n) + r"\(", reply)}
        if not needed:
            continue
        r = rng("bfcl", i)
        if r.random() < 0.35:
            funcs = [f for f in funcs if f["name"] in needed]
        state = {"conversation": [[{"role": "user", "content": conv[0]["value"]}]], "functions": funcs, "task": "BFCL tool-name selection"}
        for f in funcs:
            name = f["name"]
            out.append(row(1, src, state, {"type": "choice", "instructions": BFCL_INSTRUCTIONS + f"\n\nCandidate tool: {name}", "criteria": BFCL_CRITERIA}, "yes" if name in needed else "no"))
    return sample(out, cap, "bfcl")


APIBANK_INSTRUCTIONS = "Select the single API tool to invoke for the dialogue prefix in state. Use the published catalog in state. Do not infer arguments or use the current/future API result."


def _literal(s):
    s = s.strip()
    for f in (json.loads, ast.literal_eval):
        try:
            return f(s)
        except Exception:
            pass
    return s


def _apibank_parse(text):
    """Split API-Bank training input into API specs and dialogue turns in the lv1-lv2-samples turn format."""
    specs, turns = [], []
    body = text.rsplit("Generate API Request:", 1)[0]
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{") and '"apiCode"' in line:
            try:
                specs.append(json.loads(line))
            except json.JSONDecodeError:
                return None, None
        elif line.startswith("User:"):
            turns.append({"role": "User", "text": line[5:].strip()})
        elif line.startswith("AI:"):
            turns.append({"role": "AI", "text": line[3:].strip()})
        elif line.startswith("API-Request:"):
            m = re.match(r"API-Request:\s*\[(\w+)\((.*?)\)\]\s*->\s*(.*)$", line)
            if not m:
                return None, None
            params = {k: v for k, v in re.findall(r"(\w+)\s*=\s*'([^']*)'", m.group(2))}
            turns.append({"role": "API", "api_name": m.group(1), "param_dict": params, "result": {"api_name": m.group(1), "input": params, "output": _literal(m.group(3)), "exception": None}})
        elif turns:
            key = "text" if "text" in turns[-1] else None
            if not key:
                return None, None
            turns[-1][key] += "\n" + line
    return specs, turns


def apibank(cap):
    """Catalog = the kit's published API-Bank catalog (apis/*.py, same as DI) plus the APIs given in the training
    sample, sorted by name; option keys shuffled like the kit."""
    catalog = apibank_catalog(guard(RAW / "repos/apibank/api-bank"))
    out = []
    for fname in ("lv1-api-train.json", "lv2-api-train.json"):
        src = REV["apibank_train"] + f":training-data/{fname}"
        data = json.loads(guard(RAW / "hf/apibank_train/training-data" / fname).read_text(encoding="utf-8"))
        for i, x in enumerate(data):
            m = re.match(r"API-Request:\s*\[(\w+)\(", x["output"].strip())
            specs, turns = _apibank_parse(x["input"])
            if not m or specs is None or not turns:
                continue
            tools = dict(catalog)
            for s in specs:
                name = s.get("apiCode")
                if not name or name in catalog:
                    continue
                resp = s.get("response", {})
                tools[name] = {"name": name, "description": s.get("description", ""), "input_parameters": s.get("parameters", {}), "output_parameters": resp.get("data", resp) if isinstance(resp, dict) else resp}
            gold = m.group(1)
            if gold not in tools:
                continue
            names = sorted(tools)
            order = list(range(len(names)))
            rng("apibank", fname, i).shuffle(order)
            labels = {f"option_{k}": names[j] for k, j in enumerate(order)}
            goldkey = next(k for k, v in labels.items() if v == gold)
            state = {"dialogue": turns, "available_tools": [tools[n] for n in names], "task": "API-Bank current API tool selection"}
            out.append(row(3, src, state, {"type": "choice", "instructions": APIBANK_INSTRUCTIONS, "criteria": labels}, goldkey))
    return sample(out, cap, "apibank")


W2C_ORDER = ["direct", "tool_call", "request_for_info", "cannot_answer"]
W2C_RFI = [
    "Could you please provide more details so I can help with that?",
    "To help you with this, I need a bit more information. Could you specify the missing details?",
    "Before I proceed, could you clarify which specific values you would like me to use?",
    "I'd be happy to help. Can you tell me the exact parameters you have in mind?",
    "Could you share the specific information required to complete this request?",
]
W2C_CANNOT = [
    "I'm sorry, but I can't help with that using the tools I have available.",
    "Apologies, but I'm unable to perform that request with my current capabilities.",
    "Unfortunately, I don't have the ability to provide that information.",
    "I'm sorry, I can't assist with that request as it is beyond my available functions.",
    "Sorry, I'm not able to complete that task with the tools provided.",
]


def _w2c_type(t):
    if "<TOOLCALL>" in t:
        return "tool_call"
    if re.search(r"\b(sorry|apolog|unable|can't|cannot|not able|don't have (the )?(ability|access|capabilit))", t.lower()):
        return "cannot_answer"
    if "?" in t:
        return "request_for_info"
    return "direct"


def _w2c_toolcall(tools, r):
    t = r.choice(tools)
    props = (t.get("parameters") or {}).get("properties") or {}
    args = {k: v["default"] for k, v in props.items() if isinstance(v, dict) and v.get("default") not in (None, "")}
    return "<TOOLCALL>" + json.dumps([{"name": t.get("name"), "arguments": args}]) + "</TOOLCALL>"


def when2call(cap):
    """Gold = the preferred (chosen) response type of a When2Call train preference pair. Options: one response per
    type (A direct, B tool_call, C request_for_info, D cannot_answer, the kit order). Natural responses for the same
    question (pref chosen/rejected, sft) are used where available; only questions with a natural direct answer are
    kept. Missing request_for_info/cannot_answer options use paraphrase templates and a missing tool_call option is a
    call to one of the listed tools with its default arguments."""
    base = guard(RAW / "hf/when2call/train")
    pref = [json.loads(l) for l in (base / "when2call_train_pref.jsonl").open(encoding="utf-8")]
    sft = [json.loads(l) for l in (base / "when2call_train_sft.jsonl").open(encoding="utf-8")]
    natural = {}
    for x in pref:
        q = x["messages"][-1]["content"]
        for resp in (x["chosen_response"]["content"], x["rejected_response"]["content"]):
            natural.setdefault(q, {}).setdefault(_w2c_type(resp), resp)
    for x in sft:
        q = x["messages"][0]["content"]
        natural.setdefault(q, {}).setdefault(_w2c_type(x["messages"][-1]["content"]), x["messages"][-1]["content"])
    keys = letters(4)
    out, seen = [], set()
    src = REV["when2call"] + ":train/when2call_train_pref.jsonl (+ train/when2call_train_sft.jsonl)"
    for i, x in enumerate(pref):
        if len(x["messages"]) != 1:
            continue
        q = x["messages"][0]["content"]
        gold = _w2c_type(x["chosen_response"]["content"])
        if q in seen or "direct" not in natural.get(q, {}):
            continue
        seen.add(q)
        tools = [json.loads(t) for t in x["tools"]]
        r = rng("when2call", i)
        ans = dict(natural[q])
        ans[gold] = x["chosen_response"]["content"]
        if "tool_call" not in ans:
            if not tools:
                continue
            ans["tool_call"] = _w2c_toolcall(tools, r)
        ans.setdefault("request_for_info", r.choice(W2C_RFI))
        ans.setdefault("cannot_answer", r.choice(W2C_CANNOT))
        crit = dict(zip(keys, (ans[k] for k in W2C_ORDER)))
        out.append(row(62, src, {"tools": tools, "question": q}, {"type": "choice", "instructions": WHEN2CALL_INSTRUCTIONS, "criteria": crit}, keys[W2C_ORDER.index(gold)]))
    return sample(out, cap, "when2call")
