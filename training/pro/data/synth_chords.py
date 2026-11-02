"""Synthetic 22 POP909-style rows: infer the chord sounding at a target beat from piano-score notes.

Framing copies the DI kit (adapters_creative.pop909): the kit's own fixed chord vocabulary and criteria (129 options,
imported from the kit), state = {target_time_beats, context_notes (notes overlapping +-4 beats), public_context},
the kit's instruction text. The music is generated here: a random key, a progression of mostly diatonic chords from
the kit's templates (plus some chromatic chords and rests), and a humanized arrangement of bass, accompaniment and
melody with non-chord tones. The label is the generated chord at the target beat. No POP909 or DI file is read.
"""
from decision_index.suite.build.adapters_creative import TEMPLATES, VOCAB

from rows import rng, row

SRC = "synthetic:keel-pro/synth_chords.py"
INSTR = "Infer the chord sounding at the target beat from the score notes and musical context. Choose its pitch-class set; MIDI pitch classes are C=0 through B=11. Equivalent chord names are grouped."
LABELS = {pc: "chord_" + str(i) for i, pc in enumerate(VOCAB)}
CRITERIA = {LABELS[pc]: ("No chord sounding at the target beat." if pc == "NoChord" else "A chord pitch-class set outside this vocabulary." if pc == "Other" else {"names": VOCAB[pc], "pitch_classes": list(pc)}) for pc in VOCAB}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
# (scale degree index, quality) weighted toward pop progressions
DIATONIC_MAJ = [(0, "M", 9), (3, "M", 8), (4, "M", 8), (5, "m", 7), (1, "m", 4), (2, "m", 2), (4, "7", 3), (0, "maj7", 2), (3, "maj7", 2), (5, "m7", 2), (1, "m7", 2), (0, "sus2", 1), (4, "sus4", 1), (6, "dim", 0.5), (6, "half-dim7", 0.5)]
DIATONIC_MIN = [(0, "m", 9), (5, "M", 7), (2, "M", 6), (6, "M", 6), (3, "m", 5), (4, "M", 3), (4, "7", 3), (0, "m7", 2), (3, "m7", 2), (1, "dim", 1), (5, "maj7", 1), (0, "mMaj7", 0.3)]
CHROMATIC = list(TEMPLATES)


def pick_chord(r, tonic, minor):
    """Return a sorted pitch-class tuple from the kit vocabulary, or None for a rest."""
    x = r.random()
    if x < 0.04:
        return None
    if x < 0.14:
        root, q = r.randrange(12), r.choice(CHROMATIC)
    else:
        table = DIATONIC_MIN if minor else DIATONIC_MAJ
        deg, q, _ = r.choices(table, weights=[w for *_, w in table])[0]
        root = (tonic + (MINOR if minor else MAJOR)[deg]) % 12
    return tuple(sorted((root + i) % 12 for i in TEMPLATES[q])), root


def note(r, pitch, start, end, tpb):
    """Humanized note in beats, rounded to the tick grid like a performance MIDI file."""
    a = max(0, round((start + r.gauss(0, 0.02)) * tpb))
    b = max(a + 1, round((end + r.gauss(0, 0.04)) * tpb))
    return a, b, pitch


def piece(r):
    tpb = r.choice([480, 480, 220, 960])
    tonic, minor = r.randrange(12), r.random() < 0.35
    scale = [(tonic + s) % 12 for s in (MINOR if minor else MAJOR)]
    start = r.choice([0, 4, 8]) + r.randrange(0, 400, 4)
    total = 40
    chords, t = [], start
    while t < start + total:
        dur = r.choices([1, 2, 4, 8], weights=[1, 5, 8, 2])[0]
        c = pick_chord(r, tonic, minor)
        chords.append((t, t + dur, c))
        t += dur
    notes = []
    style = r.choice(["block", "arp", "alberti", "pad"])
    for a, b, c in chords:
        if c is None:
            continue
        pcs, root = c
        bass = 36 + (root - 36) % 12
        if r.random() < 0.85:
            notes.append(note(r, bass, a, min(b, a + r.choice([1, 2, b - a])), tpb))
        voice = sorted(48 + (p - 48) % 12 + (12 if r.random() < 0.3 else 0) for p in pcs)
        if len(pcs) >= 3 and r.random() < 0.15:
            voice = [v for v in voice if (v - root) % 12 != 7] or voice  # omitted fifth
        beat = a
        while beat < b:
            if style == "block":
                for v in voice:
                    notes.append(note(r, v, beat, beat + r.choice([0.5, 1, 1]), tpb))
                beat += 1
            elif style == "pad":
                for v in voice:
                    notes.append(note(r, v, a, b, tpb))
                beat = b
            else:
                seq = voice if style == "arp" else [voice[0], voice[-1], voice[len(voice) // 2], voice[-1]]
                for k, v in enumerate(seq):
                    s = beat + k * 0.5
                    if s < b:
                        notes.append(note(r, v, s, s + 0.5, tpb))
                beat += len(seq) * 0.5
        # melody: mostly chord tones on strong beats, scale tones between
        m = a
        while m < b:
            d = r.choice([0.5, 0.5, 1, 1, 1.5, 2])
            strong = abs(m - round(m)) < 1e-9
            pool = list(pcs) if (strong and r.random() < 0.75) else scale
            pc = r.choice(pool)
            notes.append(note(r, 60 + (pc - 60) % 12 + r.choice([0, 0, 12]), m, min(b, m + d), tpb))
            m += d
    return tpb, chords, notes


def chords(cap):
    out, i = [], 0
    while len(out) < cap and i < cap * 4:
        i += 1
        r = rng("chords", i)
        tpb, prog, notes = piece(r)
        lo, hi = prog[0][0] + 4, prog[-1][1] - 4
        grid = [t for t in range(lo - lo % 4 + 2, hi, 4) if lo <= t <= hi]
        if not grid:
            continue
        for t in r.sample(grid, min(2, len(grid))):
            cur = next((c for a, b, c in prog if a <= t < b), None)
            gold = LABELS["NoChord"] if cur is None else LABELS[cur[0]]
            ctx = [{"pitch": p, "pitch_class": p % 12, "start_beat": a / tpb, "end_beat": b / tpb} for a, b, p in sorted(notes, key=lambda n: (n[1], n[2])) if a < (t + 4) * tpb and b > (t - 4) * tpb]
            if not ctx:
                continue
            state = {"target_time_beats": t, "context_notes": ctx, "public_context": {"ticks_per_beat": tpb, "key_signatures": [], "time_signatures": [] if r.random() < 0.5 else [{"beat": 0.0, "numerator": 4, "denominator": 4}]}}
            out.append(row(22, SRC, state, {"type": "choice", "instructions": INSTR, "criteria": dict(CRITERIA)}, gold))
    return out[:cap]
