"""Synthetic 23 CFColor-style rows: which of two five-color palettes would this user rate higher, given their history?

Framing copies the DI kit (adapters_creative.cfcolor): state = {history: [{colors, rating}] (4-8 entries),
rating_scale}, one choice question with criteria {"A": [hex x5], "B": [hex x5]}. CFColor's own ratings carry no stated
licence and are not used. Instead each synthetic user has hidden taste weights over palette features (lightness,
saturation, warmth, contrast, hue spread). Ratings are 1-5 from those weights plus noise; target pairs differ by at
least 2 noiseless rating points, as the kit requires. The model must infer the taste from the history.
"""
import colorsys

from rows import rng, row

SRC = "synthetic:keel-pro/synth_color.py"
INSTR = "Which five-color palette would this user rate more highly, given their earlier ratings?"
SCALE = "1 = lowest preference; 5 = highest preference"


def palette(g):
    kind = g.choice(["analogous", "mono", "complement", "random", "triad"])
    h0 = g.random()
    s0, l0 = g.uniform(0.1, 1.0), g.uniform(0.15, 0.85)
    out = []
    for i in range(5):
        if kind == "analogous":
            h = h0 + g.uniform(-0.08, 0.08)
        elif kind == "mono":
            h = h0 + g.uniform(-0.02, 0.02)
        elif kind == "complement":
            h = h0 + (0.5 if i % 2 else 0) + g.uniform(-0.04, 0.04)
        elif kind == "triad":
            h = h0 + (i % 3) / 3 + g.uniform(-0.03, 0.03)
        else:
            h = g.random()
        s = min(1, max(0, s0 + g.uniform(-0.25, 0.25)))
        l = min(0.95, max(0.05, l0 + g.uniform(-0.3, 0.3)))
        out.append(colorsys.hls_to_rgb(h % 1, l, s))
    return out


def features(p):
    hls = [colorsys.rgb_to_hls(*c) for c in p]
    light = sum(x[1] for x in hls) / 5
    sat = sum(x[2] for x in hls) / 5
    warm = sum((1 if (x[0] < 0.17 or x[0] > 0.9) else -1 if 0.45 < x[0] < 0.75 else 0) * x[2] for x in hls) / 5
    contrast = max(x[1] for x in hls) - min(x[1] for x in hls)
    import math

    vx = sum(math.cos(2 * math.pi * x[0]) * x[2] for x in hls) / 5
    vy = sum(math.sin(2 * math.pi * x[0]) * x[2] for x in hls) / 5
    spread = 1 - min(1, math.hypot(vx, vy) / max(1e-6, sat))
    return [light - 0.5, sat - 0.5, warm, contrast - 0.4, spread - 0.4]


def hexes(p):
    return ["#" + "".join(f"{int(round(v * 255)):02x}" for v in c) for c in p]


def user(g):
    w = [g.gauss(0, 1) for _ in range(5)]
    for k in g.sample(range(5), g.randint(1, 3)):
        w[k] *= 3  # a few dominant tastes
    return w, g.uniform(-0.5, 0.5)


def true_rating(w, b, p):
    return 3 + b + 1.6 * sum(a * f for a, f in zip(w, features(p)))


def clamp(x):
    return int(min(5, max(1, round(x))))


def color(cap):
    out, i = [], 0
    while len(out) < cap and i < cap * 20:
        i += 1
        g = rng("color", i)
        w, b = user(g)
        hist = []
        for _ in range(g.randint(4, 8)):
            p = palette(g)
            hist.append({"colors": hexes(p), "rating": clamp(true_rating(w, b, p) + g.gauss(0, 0.5))})
        if len({h["rating"] for h in hist}) < 2:
            continue
        for _ in range(40):
            pa, pb = palette(g), palette(g)
            ra, rb = clamp(true_rating(w, b, pa)), clamp(true_rating(w, b, pb))
            if abs(ra - rb) >= 2:
                break
        else:
            continue
        q = {"type": "choice", "instructions": INSTR, "criteria": {"A": hexes(pa), "B": hexes(pb)}}
        out.append(row(23, SRC, {"history": hist, "rating_scale": SCALE}, q, "A" if ra > rb else "B"))
    return out
