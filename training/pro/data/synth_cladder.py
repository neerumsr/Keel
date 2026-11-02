"""Synthetic 44 CLadder-style rows (causal inference yes/no over small graphs with stated probabilities).
Framing follows normalize_text.cladder: state {}, instructions = background + "\n\n" + given_info + "\n\n" +
question, criteria A="yes", B="no". Stories, graphs, numbers and answers are generated and computed here."""
from rows import rng, row

SRC = "synthetic:keel-pro/synth_cladder.py"
BG = "Imagine a self-contained, hypothetical world with only the following conditions, and without any unmentioned factors or causal relationships: "
# (name, positive group, negative group, outcome phrase, negated outcome phrase)
VARS_X = [("smoking", "smokers", "nonsmokers"), ("vaccination", "vaccinated individuals", "unvaccinated individuals"), ("studying hard", "students who study hard", "students who do not study hard"), ("exercise", "people who exercise", "people who do not exercise"), ("having a college degree", "people with a college degree", "people without a college degree"), ("drinking coffee", "coffee drinkers", "people who do not drink coffee"), ("taking the drug", "patients who take the drug", "patients who do not take the drug"), ("wearing a helmet", "riders wearing helmets", "riders without helmets"), ("having a pet", "pet owners", "people without pets"), ("xevo", "individuals with xevo", "individuals without xevo"), ("zupj", "zupj cases", "non-zupj cases"), ("tijv", "people who have tijv", "people who do not have tijv")]
VARS_Y = [("lung cancer", "no lung cancer"), ("recovery", "no recovery"), ("high exam scores", "low exam scores"), ("heart disease", "no heart disease"), ("high salary", "low salary"), ("insomnia", "no insomnia"), ("head injury", "no head injury"), ("happiness", "unhappiness"), ("rixq", "no rixq"), ("kwox", "no kwox"), ("yupt", "no yupt")]
VARS_Z = [("gender", "male", "female"), ("age", "old", "young"), ("income", "high income", "low income"), ("genotype", "carriers", "non-carriers"), ("tar deposit", "high tar deposit", "no tar deposit"), ("motivation", "motivated", "unmotivated"), ("wibl", "wibl", "no wibl")]
GRAPHS = ["chain", "confounding", "mediation", "fork", "direct"]
Q = ["marginal", "correlation", "ate", "ett"]


def pct(p):
    return f"{round(p * 100)}%"


def gen(r):
    x, xp, xn = r.choice(VARS_X)
    y, yn = r.choice(VARS_Y)
    z, zp, zn = r.choice(VARS_Z)
    if len({x, y, z}) < 3:
        return None
    g = r.choice(GRAPHS)
    edges = {"chain": [(x, z), (z, y)], "confounding": [(z, x), (z, y), (x, y)], "mediation": [(x, z), (z, y), (x, y)], "fork": [(x, y), (z, y)], "direct": [(x, y)]}[g]
    bg = BG + " ".join(f"{a[0].upper() + a[1:]} has a direct effect on {b}." for a, b in edges)
    p = lambda: round(r.uniform(0.05, 0.95), 2)
    px = p()
    qt = r.choice(Q)
    if g == "confounding":
        pz = p()
        py = {(a, c): p() for a in (0, 1) for c in (0, 1)}
        pxz = {0: p(), 1: p()}
        px1 = pz * pxz[1] + (1 - pz) * pxz[0]
        pz_x1 = pz * pxz[1] / px1
        pz_x0 = pz * (1 - pxz[1]) / (1 - px1)
        py_x = {a: (pz_x1 if a else pz_x0) * py[(a, 1)] + (1 - (pz_x1 if a else pz_x0)) * py[(a, 0)] for a in (0, 1)}
        ate = sum((pz if c else 1 - pz) * (py[(1, c)] - py[(0, c)]) for c in (0, 1))
        ett = sum((pz_x1 if c else 1 - pz_x1) * (py[(1, c)] - py[(0, c)]) for c in (0, 1))
        cond = " ".join(f"For {zp if c else zn} and {xp if a else xn}, the probability of {y} is {pct(py[(a, c)])}." for c in (0, 1) for a in (0, 1))
        if qt in ("ate",):
            given = f"The overall probability of {zp} is {pct(pz)}. " + cond
        elif qt == "ett":
            given = f"The overall probability of {zp} is {pct(pz)}. For {zn}, the probability of {x} is {pct(pxz[0])}. For {zp}, the probability of {x} is {pct(pxz[1])}. " + cond
        else:
            given = f"The overall probability of {x} is {pct(px1)}. For {xn}, the probability of {y} is {pct(py_x[0])}. For {xp}, the probability of {y} is {pct(py_x[1])}."
        marg = px1 * py_x[1] + (1 - px1) * py_x[0]
        corr = py_x[1] - py_x[0]
        pxx = px1
    else:
        py_x = {0: p(), 1: p()}
        if g == "chain":
            pzx = {0: p(), 1: p()}
            pyz = {0: p(), 1: p()}
            py_x = {a: pzx[a] * pyz[1] + (1 - pzx[a]) * pyz[0] for a in (0, 1)}
            given = f"For {xn}, the probability of {zp} is {pct(pzx[0])}. For {xp}, the probability of {zp} is {pct(pzx[1])}. For {zn}, the probability of {y} is {pct(pyz[0])}. For {zp}, the probability of {y} is {pct(pyz[1])}."
        else:
            given = f"For {xn}, the probability of {y} is {pct(py_x[0])}. For {xp}, the probability of {y} is {pct(py_x[1])}."
        if qt in ("marginal", "correlation"):
            given = f"The overall probability of {x} is {pct(px)}. " + given
        ate = ett = corr = py_x[1] - py_x[0]
        marg = px * py_x[1] + (1 - px) * py_x[0]
        pxx = px
    flip = r.random() < 0.5
    if qt == "marginal":
        if abs(marg - 0.5) < 0.02:
            return None
        q = f"Is {yn} more likely than {y} overall?" if flip else f"Is {y} more likely than {yn} overall?"
        ans = (marg < 0.5) if flip else (marg > 0.5)
    elif qt == "correlation":
        if abs(corr) < 0.02:
            return None
        q = f"Is the chance of {y} smaller when observing {x}?" if flip else f"Is the chance of {y} larger when observing {x}?"
        ans = (corr < 0) if flip else (corr > 0)
    elif qt == "ate":
        if abs(ate) < 0.02:
            return None
        q = f"Will {x} decrease the chance of {y}?" if flip else f"Will {x} increase the chance of {y}?"
        ans = (ate < 0) if flip else (ate > 0)
    else:
        if abs(ett) < 0.02:
            return None
        q = f"For {xp}, would it be less likely to see {y} if they were not {x}?" if flip else f"For {xp}, would it be more likely to see {y} if they were not {x}?"
        ans = (ett > 0) if flip else (ett < 0)
    return bg + "\n\n" + given + "\n\n" + q, ans


def cladder(cap):
    out, seen, i = [], set(), 0
    while len(out) < cap and i < cap * 10:
        i += 1
        g = gen(rng("cladder", i))
        if not g or g[0] in seen:
            continue
        seen.add(g[0])
        text, ans = g
        out.append(row(44, SRC, {}, {"type": "choice", "instructions": text, "criteria": {"A": "yes", "B": "no"}}, "A" if ans else "B"))
    return out
