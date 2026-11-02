"""Synthetic 32 MuSR-style rows: multistep soft reasoning over a short narrative.

Framing copies the DI kit (normalize_direct.musr + layout.choice_row): state {}, instructions = story + "\n\n" +
question, criteria A/B/C... in option order. Three families after the MuSR paper's task types, generated and solved
here (no MuSR or DI file is read):
  murder: each suspect gets clues for means, motive and opportunity; only the murderer has all three.
  objects: objects move between places while people come and go; who last saw an object where.
  teams: three people, two tasks (2 + 1); skill and teamwork clues; the allocation with the best total wins.
"""
from rows import row, rng

SRC = "synthetic:keel-pro/synth_musr.py"
NAMES = ["Alice", "Bruno", "Chloe", "Dmitri", "Esme", "Farid", "Greta", "Hector", "Ingrid", "Jasper", "Keiko", "Leon", "Mira", "Nikolai", "Olga", "Pablo", "Quinn", "Rosa", "Sven", "Tara", "Umar", "Vera", "Wes", "Ximena", "Yusuf", "Zelda", "Amara", "Bastian", "Celine", "Dario"]
WEAPONS = [("a revolver", "had recently been seen at the shooting range", "owned a revolver registered in their name"), ("poison", "worked in a pharmacy with access to toxic compounds", "had studied chemistry and kept unlabeled vials at home"), ("a kitchen knife", "was a trained chef who handled knives every day", "had taken a knife-sharpening class"), ("a rope", "was an experienced sailor who tied knots for a living", "kept climbing rope in their car"), ("a crossbow", "belonged to an archery club", "had bought crossbow bolts the week before"), ("a heavy wrench", "worked as a mechanic", "kept a full toolbox in the trunk")]
PLACES = ["an old lighthouse", "a ski lodge", "a jazz club", "a botanical garden", "a parking garage", "a library basement", "a yacht marina", "a vineyard", "a bowling alley", "an art gallery"]
MOTIVES = ["stood to inherit a large sum from the victim", "had been publicly humiliated by the victim", "was being blackmailed by the victim", "had lost a business deal because of the victim", "discovered the victim was having an affair with their spouse", "was about to be exposed by the victim for fraud"]
NO_MOTIVE = ["had been friends with the victim since childhood and spoke warmly of them", "had nothing to gain from the victim's death and had just signed a project with them", "had reconciled with the victim months ago, according to several witnesses"]
NO_MEANS = ["had never handled {w} and a recent hand injury kept them from gripping anything firmly", "had no access to {w}, and records show they had never bought one", "was described by everyone as squeamish and unfamiliar with {w}"]
NO_OPP = ["was on a live video call across town at the time of the murder, confirmed by six participants", "was recorded by a toll camera two hours away when the murder happened", "was in hospital for a minor procedure all evening, as the staff confirmed"]
OPP = ["was seen near {p} shortly before the murder", "had a key to {p} and no alibi for that evening", "left {p} only minutes after the estimated time of death"]


def murder(r):
    v, *sus = r.sample(NAMES, 3 if r.random() < 0.8 else 4)
    w, means1, means2 = r.choice(WEAPONS)
    p = r.choice(PLACES)
    killer = r.randrange(len(sus))
    lines = [f"In {p}, {v} was found dead, killed with {w}. Detective {r.choice(['Winston', 'Marlow', 'Adeyemi', 'Holt', 'Sato'])} has narrowed it down to {', '.join(sus[:-1])} and {sus[-1]}."]
    for i, s in enumerate(sus):
        facts = {"means": r.choice([means1, means2]), "motive": r.choice(MOTIVES), "opp": r.choice(OPP).format(p=p)}
        if i != killer:
            miss = r.choice(["means", "motive", "opp"])
            facts[miss] = {"means": r.choice(NO_MEANS).format(w=w), "motive": r.choice(NO_MOTIVE), "opp": r.choice(NO_OPP)}[miss]
            # innocent suspects look suspicious on the other two points
        order = list(facts.items())
        r.shuffle(order)
        lines.append(" ".join(f"{s} {t}." for _, t in order))
    story = "\n\n".join(lines)
    q = "Who is the most likely murderer?"
    return story, q, sus, killer


OBJ = ["the keys", "the passport", "the notebook", "the wallet", "the headphones", "the umbrella", "the charger", "the sunglasses"]
LOC = ["the kitchen drawer", "the coat rack", "the bookshelf", "the desk", "the backpack", "the hallway cabinet", "the car glovebox", "the bedside table", "the garden shed", "the sofa cushion"]


def objects(r):
    people = r.sample(NAMES, 3)
    obj = r.choice(OBJ)
    locs = r.sample(LOC, 4)
    where = locs[0]
    present = set(people)
    seen = {p: where for p in people}
    lines = [f"{people[0]}, {people[1]} and {people[2]} share an apartment. Everyone knows {obj} are usually kept in {where}." if obj.endswith("s") else f"{people[0]}, {people[1]} and {people[2]} share an apartment. Everyone knows {obj} is usually kept in {where}."]
    for _ in range(r.randint(2, 4)):
        if r.random() < 0.5 and len(present) > 1:
            leaver = r.choice(sorted(present))
            present.discard(leaver)
            lines.append(f"{leaver} {r.choice(['left for work', 'went out for a run', 'stepped out to the shop', 'went to take a long shower', 'fell asleep in the bedroom'])}.")
        elif len(present) < 3:
            back = r.choice([p for p in people if p not in present])
            present.add(back)
            lines.append(f"{back} {r.choice(['came back home', 'returned from errands', 'woke up and joined the others'])}.")
        mover = r.choice(sorted(present))
        new = r.choice([l for l in locs if l != where])
        where = new
        for p in present:
            seen[p] = where
        watch = [p for p in present if p != mover]
        lines.append(f"{mover} moved {obj} to {where}" + (f" while {' and '.join(watch)} watched." if watch else " while alone in the room."))
    target = r.choice(people)
    q = f"Which location is the most likely place {target} would look to find {obj} given the story?"
    opts = locs[:]
    r.shuffle(opts)
    return " ".join(lines), q, opts, opts.index(seen[target])


TASKS = [("cooking", "running the front desk"), ("coding the backend", "writing documentation"), ("fieldwork", "lab analysis"), ("fundraising", "event logistics"), ("piloting the boat", "navigating"), ("set design", "lighting")]
SKILL = {2: ["is outstanding at {t}, having done it for years", "has won awards for {t}"], 1: ["has some experience with {t}", "is competent at {t} but not exceptional"], 0: ["has never done {t} and dislikes it", "struggled badly the one time they tried {t}"]}
PAIR = {1: ["{a} and {b} work together smoothly and finish each other's sentences", "{a} and {b} have collaborated well on several projects"], 0: ["{a} and {b} have rarely worked together", "{a} and {b} get along fine but have little shared history"], -1: ["{a} and {b} argued loudly at the last meeting and avoid each other", "{a} openly complains about working with {b}"]}


def teams(r):
    ppl = r.sample(NAMES, 3)
    t1, t2 = r.choice(TASKS)
    sk = {(p, t): r.choice([0, 1, 2]) for p in ppl for t in (t1, t2)}
    pair = {frozenset(c): r.choice([-1, 0, 1]) for c in ((ppl[0], ppl[1]), (ppl[0], ppl[2]), (ppl[1], ppl[2]))}
    allocs = []
    for solo in ppl:
        duo = [p for p in ppl if p != solo]
        allocs.append((solo, duo, sk[(solo, t2)] + sum(sk[(d, t1)] for d in duo) + pair[frozenset(duo)]))
    scores = sorted(a[2] for a in allocs)
    if scores[-1] == scores[-2]:
        return None
    lines = [f"As the manager, I need to assign {', '.join(ppl[:-1])} and {ppl[-1]}: two people to {t1} and one to {t2}."]
    facts = [f"{p} " + r.choice(SKILL[sk[(p, t)]]).format(t=t) + "." for p in ppl for t in (t1, t2)]
    facts += [r.choice(PAIR[v]).format(a=a, b=b) + "." for (a, b), v in ((tuple(sorted(k)), v) for k, v in pair.items())]
    r.shuffle(facts)
    story = " ".join(lines + facts)
    q = "Given the story, how would you uniquely allocate each person to make sure both tasks are accomplished efficiently?"
    r.shuffle(allocs)
    opts = [f"{t1.capitalize()}: {d[0]} and {d[1]}, {t2.capitalize()}: {s}" for s, d, _ in allocs]
    best = max(range(3), key=lambda i: allocs[i][2])
    return story, q, opts, best


def musr(cap):
    out, i, seen = [], 0, set()
    fams = [murder, objects, teams]
    while len(out) < cap and i < cap * 5:
        i += 1
        r = rng("musr", i)
        g = fams[i % 3](r)
        if not g or g[0] in seen:
            continue
        seen.add(g[0])
        story, q, opts, gold = g
        keys = [chr(65 + k) for k in range(len(opts))]
        out.append(row(32, SRC, {}, {"type": "choice", "instructions": story + "\n\n" + q, "criteria": dict(zip(keys, opts))}, keys[gold]))
    return out
