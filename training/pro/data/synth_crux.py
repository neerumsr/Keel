"""Synthetic 43 CRUXEval-style rows: small Python functions generated from templates here, executed locally to get
the gold output; distractors are outputs of mutated variants of the same function on the same input plus simple
value perturbations. Framing follows adapters_selection.crux: state {code, input, task}, option_i = repr(value),
2-10 distinct candidates."""
import random

from rows import rng, row

SRC = "synthetic:keel-pro/synth_crux.py"
INSTR = "Choose the correct output of f called with the supplied input arguments. Candidates are Python literal values."
WORDS = ["apple", "banana", "cherry", "delta", "echo", "fox", "grape", "hotel", "india", "kilo", "lima", "mango", "nova", "oscar", "papa", "quartz", "romeo", "sierra", "tango", "umbra", "victor", "whisky", "xray", "yankee", "zulu"]


def rstr(r, lo=3, hi=12, alpha="abcdefghijklmnopqrstuvwxyz"):
    return "".join(r.choice(alpha) for _ in range(r.randint(lo, hi)))


def rlist(r, lo=2, hi=8, a=-9, b=20):
    return [r.randint(a, b) for _ in range(r.randint(lo, hi))]


# Each template: (code with {placeholders}, sampler(r) -> (params dict, args tuple), variants(params, r) -> list of params)
T = []


def tpl(code):
    def deco(fn):
        T.append((code, fn))
        return fn

    return deco


@tpl("def f(text, ch):\n    count = 0\n    for c in text:\n        if c {op} ch:\n            count += {inc}\n    return count")
def _(r):
    t = rstr(r, 5, 14, "abcde")
    return {"op": r.choice(["==", "!=", "<", ">"]), "inc": r.choice([1, 2])}, (t, r.choice("abcde")), [{"op": o} for o in ["==", "!=", "<", ">"]] + [{"inc": 1}, {"inc": 2}]


@tpl("def f(nums):\n    result = []\n    for i in range(len(nums)):\n        if nums[i] % {m} == {k}:\n            result.append(nums[i] {op} {c})\n    return result")
def _(r):
    m = r.choice([2, 3])
    return {"m": m, "k": r.randrange(m), "op": r.choice(["+", "*", "-"]), "c": r.randint(1, 4)}, (rlist(r),), [{"k": k} for k in range(m)] + [{"op": o} for o in "+*-"] + [{"c": c} for c in range(0, 5)]


@tpl("def f(s):\n    return s{slc}.{meth}()")
def _(r):
    w = r.choice(WORDS) + r.choice([" ", "-", "_", ""]) + r.choice(WORDS).upper()
    slcs = ["[::-1]", "[1:]", "[:-1]", "[::2]", "[2:6]", ""]
    meths = ["upper", "lower", "swapcase", "title", "capitalize", "strip"]
    return {"slc": r.choice(slcs), "meth": r.choice(meths)}, (w,), [{"slc": s} for s in slcs] + [{"meth": m} for m in meths]


@tpl("def f(d, key):\n    d = dict(d)\n    if key in d:\n        d[key] {op}= {c}\n    else:\n        d[key] = {default}\n    return sorted(d.items())")
def _(r):
    ks = r.sample(WORDS[:8], r.randint(2, 4))
    d = {k: r.randint(0, 9) for k in ks}
    key = r.choice(ks + [r.choice(WORDS[:8])])
    return {"op": r.choice(["+", "*", "-"]), "c": r.randint(2, 5), "default": r.randint(0, 3)}, (d, key), [{"op": o} for o in "+*-"] + [{"c": c} for c in range(1, 6)] + [{"default": x} for x in range(4)]


@tpl("def f(nums, n):\n    nums = list(nums)\n    for _ in range(n):\n        nums.{m1}(nums.{m2}({idx}))\n    return nums")
def _(r):
    p = {"m1": r.choice(["append", "reverse"]), "m2": "pop", "idx": r.choice([0, -1, 1])}
    if p["m1"] == "reverse":
        p = {"m1": "append", "m2": "pop", "idx": p["idx"]}
    return p, (rlist(r, 3, 7), r.randint(1, 4)), [{"idx": i} for i in [0, -1, 1, 2]]


@tpl("def f(text, sep):\n    parts = text.split(sep)\n    return {join!r}.join(p{tr} for p in parts{slc})")
def _(r):
    sep = r.choice([",", " ", "-", "a"])
    text = sep.join(r.sample(WORDS, r.randint(2, 5)))
    trs = ["[::-1]", "[0]", ".upper()", "[:2]", ""]
    slcs = ["", "[::-1]", "[1:]", "[:-1]"]
    return {"join": r.choice(["", "-", " ", "+"]), "tr": r.choice(trs), "slc": r.choice(slcs)}, (text, sep), [{"tr": t} for t in trs] + [{"slc": s} for s in slcs] + [{"join": j} for j in ["", "-", " ", "+"]]


@tpl("def f(n):\n    total = {init}\n    while n > 0:\n        total {op}= n % {base}\n        n //= {base}\n    return total")
def _(r):
    return {"init": r.choice([0, 1]), "op": r.choice(["+", "*"]), "base": r.choice([2, 10, 3])}, (r.randint(5, 9999),), [{"init": i} for i in [0, 1]] + [{"op": o} for o in "+*-"] + [{"base": b} for b in [2, 3, 10]]


@tpl("def f(a, b):\n    common = [x for x in a if x {cond} b]\n    return {ret}")
def _(r):
    rets = ["common", "len(common)", "sorted(set(common))", "common[::-1]", "sum(common)"]
    return {"cond": r.choice(["in", "not in"]), "ret": r.choice(rets)}, (rlist(r, 3, 8, 0, 9), rlist(r, 3, 8, 0, 9)), [{"cond": c} for c in ["in", "not in"]] + [{"ret": x} for x in rets]


@tpl("def f(text):\n    out = ''\n    for i, c in enumerate(text):\n        if i % {m} == {k}:\n            out += c.{meth}()\n        else:\n            out += c\n    return out")
def _(r):
    m = r.choice([2, 3])
    return {"m": m, "k": r.randrange(m), "meth": r.choice(["upper", "swapcase"])}, (r.choice(WORDS) + r.choice(WORDS),), [{"k": k} for k in range(3)] + [{"m": x} for x in [2, 3, 4]] + [{"meth": x} for x in ["upper", "swapcase", "lower"]]


@tpl("def f(nums):\n    nums = sorted(nums{key})\n    return nums[{i}:{j}]")
def _(r):
    keys = ["", ", reverse=True", ", key=abs", ", key=lambda x: -x % 5"]
    return {"key": r.choice(keys), "i": r.randint(0, 2), "j": r.randint(3, 6)}, (rlist(r, 4, 9),), [{"key": k} for k in keys] + [{"i": i} for i in range(3)] + [{"j": j} for j in range(3, 7)]


@tpl("def f(text, old, new):\n    return text.replace(old, new{cnt}){post}")
def _(r):
    text = r.choice(WORDS) + r.choice(WORDS) + r.choice(WORDS)
    old = r.choice([c for c in text])
    posts = ["", ".upper()", "[::-1]", ".count({0!r})".format(old), ".find('a')"]
    return {"cnt": r.choice(["", ", 1", ", 2"]), "post": r.choice(posts)}, (text, old, r.choice(["", "x", "zz", "#"])), [{"cnt": c} for c in ["", ", 1", ", 2"]] + [{"post": p} for p in posts]


@tpl("def f(items):\n    seen = {{}}\n    for x in items:\n        seen[x] = seen.get(x, {start}) + {inc}\n    return {ret}")
def _(r):
    rets = ["seen", "max(seen.values())", "len(seen)", "sorted(seen, key=seen.get)[-1]", "list(seen.items())[:2]"]
    return {"start": r.choice([0, 1]), "inc": r.choice([1, 2]), "ret": r.choice(rets)}, ([r.choice("abcd") for _ in range(r.randint(4, 9))],), [{"start": s} for s in [0, 1]] + [{"inc": i} for i in [1, 2]] + [{"ret": x} for x in rets]


@tpl("def f(s, n):\n    return s{a}.{pad}(n, {fill!r}){b}")
def _(r):
    pads = ["ljust", "rjust", "center", "zfill"]
    p = {"a": r.choice(["", ".strip()", "[::-1]"]), "pad": r.choice(pads[:3]), "fill": r.choice(["*", "0", "-"]), "b": r.choice(["", "[:5]", ".upper()"])}
    return p, (r.choice(WORDS), r.randint(4, 12)), [{"pad": x} for x in pads[:3]] + [{"a": x} for x in ["", ".strip()", "[::-1]"]] + [{"b": x} for x in ["", "[:5]", ".upper()"]]


@tpl("def f(matrix):\n    return [{agg}(row{sl}) for row in matrix{msl}]")
def _(r):
    m = [rlist(r, 3, 3, 0, 9) for _ in range(r.randint(2, 4))]
    aggs = ["sum", "max", "min", "len", "sorted"]
    return {"agg": r.choice(aggs), "sl": r.choice(["", "[1:]", "[::-1]"]), "msl": r.choice(["", "[::-1]", "[1:]"])}, (m,), [{"agg": a} for a in aggs] + [{"sl": x} for x in ["", "[1:]", "[::-1]"]] + [{"msl": x} for x in ["", "[::-1]", "[1:]"]]


@tpl("def f(text):\n    if text.{pred}():\n        return text{a}\n    elif {cond}:\n        return text{b}\n    return {fallback!r}")
def _(r):
    text = r.choice([r.choice(WORDS), r.choice(WORDS).upper(), str(r.randint(0, 999)), r.choice(WORDS) + " " + r.choice(WORDS), r.choice(WORDS).title()])
    preds = ["isalpha", "isdigit", "isupper", "islower", "istitle"]
    conds = ["len(text) > 4", "' ' in text", "text[0] in 'aeiou'", "text.endswith('a')"]
    tr = ["[::-1]", "[0]", "[-2:]", ".title()", " * 2"]
    return {"pred": r.choice(preds), "a": r.choice(tr), "cond": r.choice(conds), "b": r.choice(tr), "fallback": r.choice(["", "none", "?"])}, (text,), [{"pred": p} for p in preds] + [{"cond": c} for c in conds] + [{"a": t} for t in tr] + [{"b": t} for t in tr]


def run(code, args):
    ns = {}
    exec(code, {"__builtins__": {"range": range, "len": len, "sorted": sorted, "sum": sum, "max": max, "min": min, "abs": abs, "set": set, "list": list, "dict": dict, "enumerate": enumerate, "str": str}}, ns)
    return ns["f"](*[eval(repr(a)) for a in args])


def literal_ok(v):
    try:
        return eval(repr(v), {"__builtins__": {}}) == v
    except Exception:
        return False


def perturb(v, r):
    if isinstance(v, bool):
        return [not v]
    if isinstance(v, int):
        return [v + 1, v - 1, v * 2, -v]
    if isinstance(v, str):
        return [v[::-1], v.upper(), v[1:], v + v[-1:]] if v else ["", " "]
    if isinstance(v, list):
        out = [v[::-1], v[1:], v[:-1]]
        return out
    return []


def crux(cap):
    out, seen = [], set()
    i = 0
    while len(out) < cap and i < cap * 10:
        i += 1
        r = rng("crux", i)
        code_t, sampler = T[i % len(T)]
        params, args, variants = sampler(r)
        code = code_t.format(**params)
        try:
            gold = run(code, args)
        except Exception:
            continue
        if not literal_ok(gold) or (code, repr(args)) in seen or len(repr(gold)) > 200:
            continue
        seen.add((code, repr(args)))
        vals = [gold]
        r.shuffle(variants)
        for v in variants:
            try:
                alt = run(code_t.format(**{**params, **v}), args)
            except Exception:
                continue
            if literal_ok(alt) and alt not in vals and type(alt) is type(gold) and len(repr(alt)) <= 200:
                vals.append(alt)
        for alt in perturb(gold, r):
            if literal_ok(alt) and alt not in vals:
                vals.append(alt)
        k = min(len(vals), r.choice([2, 3, 4, 4, 5, 5, 6, 8, 10]))
        if k < 2:
            continue
        vals = [vals[0]] + r.sample(vals[1:], k - 1)
        r.shuffle(vals)
        inp = ", ".join(repr(a) for a in args)
        crit = {f"option_{j}": repr(v) for j, v in enumerate(vals)}
        if len(set(crit.values())) != len(crit):
            continue
        out.append(row(43, SRC, {"code": code, "input": inp, "task": "CRUXEval output selection"}, {"type": "choice", "instructions": INSTR, "criteria": crit}, f"option_{vals.index(gold)}"))
    return out
