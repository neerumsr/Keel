"""Synthetic BBH-style rows (58) for procedurally checkable task families. Framing follows the kit's bbh():
state = full task text, instructions = CHOICE, criteria parsed from the trailing "Options:" block ("(A) ..." keys,
or "- x" lines keyed by their text), boolean_expressions/web_of_lies/sports-style tasks without an options block
use the kit's BBH_UNLISTED label sets. All texts are produced by this generator; no BBH examples are read."""
import datetime as dt
import itertools
import re

from rows import rng, row

from decision_index.suite.build.adapters_added import BBH_UNLISTED, CHOICE

SRC = "synthetic:keel-pro/synth_bbh.py"
NAMES = ["Alice", "Bob", "Claire", "Dave", "Eve", "Fred", "Gertrude", "Hannah", "Ivan", "Julia", "Kevin", "Lena", "Mike", "Nora", "Oscar", "Paula", "Quentin", "Rita", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xavier", "Yara", "Zoe", "Amberly", "Bernita", "Christie", "Delfina", "Elanor", "Fidel", "Gwenn", "Helene", "Inga", "Jamey", "Kandi", "Leda", "Millicent", "Osvaldo", "Phoebe", "Raymond", "Sherrie", "Tamika", "Ka", "Jaymie", "Vina", "Shalonda", "Ryan", "Jerry", "Shenna", "Audrie", "Maybelle", "Willian", "Lorine", "Antwan", "Crista", "Teressa", "Alejandro", "Andree"]
COLORS = ["red", "orange", "yellow", "green", "blue", "brown", "magenta", "fuchsia", "mauve", "teal", "turquoise", "burgundy", "silver", "gold", "black", "grey", "purple", "pink"]


def letters(n):
    return [f"({chr(65 + i)})" for i in range(n)]


def mc(text, options, gold_index):
    keys = letters(len(options))
    body = text + "\nOptions:\n" + "\n".join(f"{k} {o}" for k, o in zip(keys, options))
    return body, dict(zip(keys, options)), keys[gold_index]


def dash(text, options, gold):
    return text + "\nOptions:\n" + "\n".join(f"- {o}" for o in options), {o: o for o in options}, gold


def boolean_expressions(r):
    def gen(d):
        if d == 0 or r.random() < 0.3:
            return r.choice(["True", "False"])
        k = r.random()
        if k < 0.25:
            return "not " + gen(d - 1)
        if k < 0.45:
            return "( " + gen(d - 1) + " )"
        return gen(d - 1) + r.choice([" and ", " or "]) + gen(d - 1)

    while True:
        e = gen(3)
        if 5 <= len(e.split()) <= 11:
            break
    v = str(eval(e))
    return e + " is", {k: k for k in BBH_UNLISTED["boolean_expressions"]}, v


def web_of_lies(r):
    ppl = r.sample(NAMES, r.randint(3, 5))
    truth = r.random() < 0.5
    parts = [f"{ppl[0]} {'tells the truth' if truth else 'lies'}."]
    for a, b in zip(ppl, ppl[1:]):
        says_truth = r.random() < 0.5
        parts.append(f"{b} says {a} {'tells the truth' if says_truth else 'lies'}.")
        truth = truth == says_truth
    return "Question: " + " ".join(parts) + f" Does {ppl[-1]} tell the truth?", {k: k for k in BBH_UNLISTED["web_of_lies"]}, "Yes" if truth else "No"


def navigate(r):
    face = r.random() < 0.5
    x = y = 0
    d = 0
    steps = []
    for _ in range(r.randint(3, 8)):
        n = r.randint(1, 10)
        if face:
            k = r.choice(["forward", "backward", "left", "right"])
            dx, dy = {"forward": (0, 1), "backward": (0, -1), "left": (-1, 0), "right": (1, 0)}[k]
            x, y = x + dx * n, y + dy * n
            steps.append(f"Take {n} step{'s' if n > 1 else ''} {k}.")
        else:
            if r.random() < 0.35:
                t = r.choice(["Turn left.", "Turn right.", "Turn around."])
                d = (d + {"Turn left.": 3, "Turn right.": 1, "Turn around.": 2}[t]) % 4
                steps.append(t)
                continue
            dx, dy = [(0, 1), (1, 0), (0, -1), (-1, 0)][d]
            x, y = x + dx * n, y + dy * n
            steps.append(f"Take {n} step{'s' if n > 1 else ''}.")
    if r.random() < 0.55 and (x, y) != (0, 0):
        if face:
            if x:
                steps.append(f"Take {abs(x)} step{'s' if abs(x) > 1 else ''} {'left' if x > 0 else 'right'}.")
            if y:
                steps.append(f"Take {abs(y)} step{'s' if abs(y) > 1 else ''} {'backward' if y > 0 else 'forward'}.")
            x = y = 0
    text = "If you follow these instructions, do you return to the starting point? " + ("Always face forward. " if face else "") + " ".join(steps)
    return dash(text, ["Yes", "No"], "Yes" if (x, y) == (0, 0) else "No")


SHUFFLE_SETUPS = [
    ("are playing a game. At the start of the game, they are each holding a ball:", "has a {} ball", "pairs of players trade balls", "swap balls", "has the", "{} ball", COLORS),
    ("are dancers at a square dance. At the start of a song, they each have a partner:", "is dancing with {}", "pairs of dancers trade partners", "switch partners", "is dancing with", "{}", ["Patrick", "Sam", "Jamie", "Lola", "Melissa", "Ophelia", "Rodrigo", "Izzi", "Karl", "Helga"]),
    ("are friends and avid readers who occasionally trade books. At the start of the semester, they each buy one new book:", "gets {}", "they swap books", "swap books", "has", "{}", ["Frankenstein", "The Odyssey", "Ulysses", "Moby Dick", "Catch-22", "Lolita", "Hound of the Baskervilles", "The Pearl", "The Fellowship of the Ring", "The Great Gatsby"]),
    ("are on the same team in a soccer match. At the start of the match, they are each assigned to a position:", "is playing {}", "the team members occasionally swap positions", "trade positions", "is playing", "{}", ["goalkeeper", "left winger", "right winger", "striker", "center midfielder", "benchwarmer", "cheerleader", "fullback", "left midfielder", "sweeper"]),
]


def tracking_shuffled_objects(r):
    n = r.choice([3, 5, 7])
    ppl = r.sample(NAMES[:26], n)
    intro, has, prog, verb, end, obj, pool = r.choice(SHUFFLE_SETUPS)
    items = r.sample(pool, n)
    hold = dict(zip(ppl, items))
    listing = ", ".join(f"{p} {has.format(i)}" for p, i in zip(ppl, items))
    k = listing.rfind(", ")
    listing = listing[:k] + ", and " + listing[k + 2:]
    swaps = []
    for _ in range(n):
        a, b = r.sample(ppl, 2)
        hold[a], hold[b] = hold[b], hold[a]
        swaps.append(f"{a} and {b} {verb}")
    seq = "First, " + swaps[0] + ". " + " ".join(f"Then, {s}." for s in swaps[1:-1]) + f" Finally, {swaps[-1]}."
    who = r.choice(ppl)
    names = ", ".join(ppl[:-1]) + ", and " + ppl[-1]
    text = f"{names} {intro} {listing}.\nAs the {'game' if 'game' in intro else 'semester' if 'semester' in intro else 'match' if 'match' in intro else 'dance'} progresses, {prog}. {seq} At the end of the {'game' if 'game' in intro else 'semester' if 'semester' in intro else 'match' if 'match' in intro else 'dance'}, {who} {end}"
    return mc(text, [obj.format(i) for i in items], items.index(hold[who]))


def _ord(k, n, first, last, mid):
    return first if k == 0 else last if k == n - 1 else mid.format(o=ORD[k])


DEDUCTION_SETS = [
    ("On a shelf, there are {n} books: {items}.", ["red", "blue", "green", "white", "orange", "purple", "black", "yellow", "gray", "brown"], lambda c: f"a {c} book", lambda c: f"The {c} book",
     lambda o, k, n: f"{o} is the " + _ord(k, n, "leftmost", "rightmost", "{o} from the left"), lambda a, b: f"{a} is to the left of the {b[4:].lower() if b.startswith('The ') else b}"),
    ("In a golf tournament, there were {n} golfers: {items}.", NAMES[:30], lambda c: c, lambda c: c,
     lambda o, k, n: f"{o} finished " + _ord(k, n, "first", "last", "{o}"), lambda a, b: f"{a} finished above {b}"),
    ("In an antique car show, there are {n} vehicles: {items}.", ["sedan", "convertible", "tractor", "minivan", "limousine", "bus", "truck", "motorcyle", "station wagon", "hatchback"], lambda c: f"a {c}", lambda c: f"The {c}",
     lambda o, k, n: f"{o} is the " + _ord(k, n, "newest", "oldest", "{o}-newest"), lambda a, b: f"{a} is newer than the {b[4:]}"),
    ("A fruit stand sells {n} fruits: {items}.", ["apples", "peaches", "mangoes", "kiwis", "plums", "pears", "oranges", "watermelons", "cantaloupes", "loquats"], lambda c: c, lambda c: f"The {c}",
     lambda o, k, n: f"{o} are the " + _ord(k, n, "cheapest", "most expensive", "{o}-cheapest"), lambda a, b: f"{a} are less expensive than the {b[4:]}"),
]
ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh"]
NUM = {3: "three", 5: "five", 7: "seven"}


def logical_deduction(r):
    n = r.choice([3, 5, 7])
    intro, pool, listed, subj, pos_t, rel_t = r.choice(DEDUCTION_SETS)
    objs = r.sample(pool, n)
    order = objs[:]
    r.shuffle(order)
    pos = {o: i for i, o in enumerate(order)}
    facts = [(pos_t(subj(o), pos[o], n), ("pos", o, pos[o])) for o in objs]
    facts += [(rel_t(subj(a), subj(b)), ("lt", a, b)) for a in objs for b in objs if a != b and pos[a] < pos[b]]
    r.shuffle(facts)
    space = list(itertools.permutations(range(n)))
    ok = lambda p, c: (c[0] == "pos" and p[objs.index(c[1])] == c[2]) or (c[0] == "lt" and p[objs.index(c[1])] < p[objs.index(c[2])])
    used = []
    for f in facts:
        nxt = [p for p in space if ok(p, f[1])]
        if len(nxt) < len(space):
            used.append(f)
            space = nxt
        if len(space) == 1:
            break
    if len(space) != 1:
        return None
    k = r.randrange(n)
    q = order[k]
    items = ", ".join(listed(o) for o in objs[:-1]) + ", and " + listed(objs[-1])
    text = f"The following paragraphs each describe a set of {NUM[n]} objects arranged in a fixed order. The statements are logically consistent within each paragraph. " + intro.format(n=NUM[n], items=items) + " " + " ".join(f[0] + "." for f in used)
    return mc(text, [pos_t(subj(o), k, n) for o in objs], objs.index(q))


def date_understanding(r):
    base = dt.date(r.randint(1940, 2030), r.randint(1, 12), r.randint(1, 28))
    kind = r.choice(["today", "tomorrow", "yesterday", "week", "month", "year", "days", "dayafter"])
    ctx = f"Today is {base:%m/%d/%Y}."
    q = {"today": ("What is the date today", 0), "tomorrow": ("What is the date tomorrow", 1), "yesterday": ("What is the date yesterday", -1), "week": ("What is the date one week from today", 7), "dayafter": ("What is the date 24 hours later", 1)}
    if kind in q:
        qt, delta = q[kind]
        ans = base + dt.timedelta(days=delta)
    elif kind == "days":
        delta = r.choice([-10, -3, 2, 3, 10, 30])
        qt = f"What is the date {abs(delta)} days {'ago' if delta < 0 else 'from today'}"
        ans = base + dt.timedelta(days=delta)
    elif kind == "month":
        qt = "What is the date one month ago"
        m = base.month - 1 or 12
        ans = dt.date(base.year - (base.month == 1), m, base.day)
    else:
        qt = "What is the date one year ago from today"
        ans = dt.date(base.year - 1, base.month, base.day)
    fmtd = lambda d: f"{d:%m/%d/%Y}"
    opts = {fmtd(ans)}
    while len(opts) < 6:
        f = r.choice([lambda d: d + dt.timedelta(days=r.choice([-1, 1, 2, -7, 7])), lambda d: d.replace(year=d.year + r.choice([-1, 1])), lambda d: dt.date(d.year, d.day, d.month) if d.day <= 12 else d + dt.timedelta(days=30)])
        try:
            opts.add(fmtd(f(ans)))
        except ValueError:
            pass
    opts = list(opts)
    r.shuffle(opts)
    return mc(f"{ctx} {qt} in MM/DD/YYYY?", opts, opts.index(fmtd(ans)))


ADJ = [("opinion", ["good", "terrible", "lovely", "obnoxious", "nice", "silly", "awful", "wonderful", "mysterious", "ridiculous"]), ("size", ["big", "small", "tiny", "enormous", "massive", "little", "large", "huge"]), ("age", ["old", "new", "ancient", "old-fashioned", "brand-new", "archaic"]), ("shape", ["square", "circular", "triangular", "rectangular", "spherical"]), ("color", ["red", "blue", "green", "white", "black", "gray", "brown", "purple", "pink"]), ("origin", ["American", "Chinese", "Mexican", "Japanese", "Brazilian", "German", "Turkish", "Indian", "Russian", "Egyptian"]), ("material", ["wool", "plastic", "paper", "steel", "glass", "leather", "cloth", "wood", "rubber", "iron"]), ("purpose", ["smoking", "hiking", "drinking", "exercise", "eating", "walking", "snorkeling", "whittling"])]
NOUNS = ["ship", "knife", "shoe", "sweater", "car", "box", "table", "dog", "cat", "house", "baby", "monkey", "bicycle", "match", "computer", "chair", "canvas"]


def hyperbaton(r):
    cats = sorted(r.sample(range(len(ADJ)), r.randint(2, 4)))
    adjs = [r.choice(ADJ[c][1]) for c in cats]
    noun = r.choice(NOUNS)
    good = " ".join(adjs + [noun])
    for _ in range(10):
        bad_order = adjs[:]
        r.shuffle(bad_order)
        if bad_order != adjs:
            break
    else:
        return None
    bad = " ".join(bad_order + [noun])
    opts = [good, bad] if r.random() < 0.5 else [bad, good]
    return mc("Which sentence has the correct adjective order:", opts, opts.index(good))


OBJS = ["pen", "pencil", "cup", "mug", "notebook", "keychain", "stress ball", "fidget spinner", "sheet of paper", "booklet", "puzzle", "teddy bear", "plate", "dog leash", "cat toy", "envelope", "jug", "bracelet", "scrunchiephone charger", "_"]
COLOR18 = ["red", "orange", "yellow", "green", "blue", "brown", "magenta", "fuchsia", "mauve", "teal", "turquoise", "burgundy", "silver", "gold", "black", "grey", "purple", "pink"]
SURF = ["desk", "table", "floor", "nightstand"]


def colored_objects(r):
    n = r.randint(3, 6)
    objs = r.sample(OBJS[:-1], n)
    cols = [r.choice(COLOR18) for _ in objs]
    items = [f"a {c} {o}" for c, o in zip(cols, objs)]
    k = r.choice(["color", "left", "right", "count_not"])
    arranged = r.random() < 0.5 and k in ("left", "right")
    lst = ", ".join(items[:-1]) + ", and " + items[-1]
    intro = f"On the {r.choice(SURF)}, " + (f"you see the following items arranged in a row: {lst}." if arranged else f"you see {lst}.")
    if k == "color" or (k in ("left", "right") and not arranged):
        i = r.randrange(n)
        return mc(f"{intro} What is the color of the {objs[i]}?", COLOR18, COLOR18.index(cols[i]))
    if k in ("left", "right"):
        i = r.randrange(n - 1) + (k == "left")
        j = i - 1 if k == "left" else i + 1
        return mc(f"{intro} What is the color of the item directly to the {k} of the {objs[i]}?", COLOR18, COLOR18.index(cols[j]))
    c = r.choice(cols)
    cnt = sum(x != c for x in cols)
    nums = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen"]
    return mc(f"{intro} How many non-{c} items do you see?", nums[:7], cnt)


def temporal_sequences(r):
    p = r.choice(NAMES[:26])
    place = r.choice(["the beach", "the park", "the bakery", "the museum", "the gym", "the library", "the swimming pool", "the movies", "the dance studio", "the art studio"])
    hours = list(range(5, 22))
    start = r.randint(5, 9)
    end = r.randint(start + 5, min(start + 10, 22))
    slots = list(range(start, end))
    free = r.choice(slots)
    t = start
    seen = []
    acts = ["buying clothes at the mall", "walking in the garden", "taking photos near the Eiffel Tower", "working at the office", "watching a movie at the theater", "sitting on a rooftop", "getting a coffee at the cafe", "reading at the library", "playing tennis at the tennis court", "stretching at a yoga studio"]
    r.shuffle(acts)
    fmt = lambda h: f"{(h % 12) or 12}{'am' if h < 12 else 'pm'}"
    clauses = [f"{p} woke up at {fmt(start)}."]
    ai = 0
    h = start
    while h < end:
        if h == free:
            h += 1
            continue
        h2 = h + 1
        while h2 < end and h2 != free and r.random() < 0.4:
            h2 += 1
        who = r.choice([x for x in NAMES[:26] if x != p])
        clauses.append(f"{who} saw {p} {acts[ai % len(acts)]} from {fmt(h)} to {fmt(h2)}.")
        ai += 1
        h = h2
    clauses.append(f"{place[0].upper() + place[1:]} was closed after {fmt(end)}.")
    gold = f"{fmt(free)} to {fmt(free + 1)}"
    opts = {gold}
    pool = [f"{fmt(a)} to {fmt(a + 1)}" for a in range(start, end) if a != free]
    for o in r.sample(pool, min(3, len(pool))):
        opts.add(o)
    opts = list(opts)
    r.shuffle(opts)
    text = f"Today, {p} went to {place}. Between what times could they have gone?\nWe know that:\n" + "\n".join(clauses) + f"\nBetween what times could {p} have gone to {place}?"
    return mc(text, opts, opts.index(gold))


PENG_HEADER = "Here is a table where the first line is a header and each subsequent line is a penguin:  name, age, height (cm), weight (kg) "


def penguins(r):
    names = r.sample(["Louis", "Bernard", "Vincent", "Gwen", "James", "Ruby", "Pingu", "Otto", "Mabel", "Skipper", "Rico", "Kowalski", "Gloria", "Mumble"], r.randint(4, 6))
    data = [(n, r.randint(2, 12), r.randint(40, 100), r.randint(5, 25)) for n in names]
    table = "\n" + "\n".join(f"{n}, {a}, {h}, {w}" for n, a, h, w in data)
    k = r.choice(["count_age", "oldest", "heaviest", "sorted", "tallest"])
    if k == "count_age":
        th = r.randint(4, 10)
        ans = sum(a > th for _, a, _, _ in data)
        return mc(f"{PENG_HEADER}{table}\nHow many penguins are more than {th} years old?", [str(x) for x in range(7)], ans)
    col = {"oldest": 1, "heaviest": 3, "tallest": 2}.get(k)
    if col:
        vals = [d[col] for d in data]
        if vals.count(max(vals)) > 1:
            return None
        best = data[vals.index(max(vals))][0]
        opts = names[:5]
        if best not in opts:
            return None
        return mc(f"{PENG_HEADER}{table}\nWhich is the {k} penguin?", opts, opts.index(best))
    srt = sorted(names)
    i = r.randrange(len(srt))
    opts = names[:5]
    if srt[i] not in opts:
        return None
    return mc(f"{PENG_HEADER}{table}\nWe now sort the penguins by name in alphabetical order. Which is the {ORD[i]} penguin?", opts, opts.index(srt[i]))


SHAPES = ["circle", "heptagon", "hexagon", "kite", "line", "octagon", "pentagon", "rectangle", "sector", "triangle"]


def geometric_shapes(r):
    import math

    k = r.choice(["line", "triangle", "pentagon", "hexagon", "heptagon", "octagon", "rectangle", "kite"])
    cx, cy, rad = r.uniform(10, 90), r.uniform(10, 90), r.uniform(5, 30)
    f = lambda v: f"{v:.2f}"
    if k == "line":
        pts = [(cx, cy), (cx + r.uniform(-30, 30), cy + r.uniform(-30, 30))]
    elif k == "rectangle":
        w, h = r.uniform(5, 40), r.uniform(5, 40)
        if abs(w - h) < 2:
            return None
        pts = [(cx, cy), (cx + w, cy), (cx + w, cy + h), (cx, cy + h)]
    elif k == "kite":
        a, b, c = r.uniform(5, 20), r.uniform(25, 45), r.uniform(5, 20)
        pts = [(cx, cy - c), (cx + a, cy), (cx, cy + b), (cx - a, cy)]
    else:
        n = {"triangle": 3, "pentagon": 5, "hexagon": 6, "heptagon": 7, "octagon": 8}[k]
        off = r.uniform(0, 2 * math.pi)
        pts = [(cx + rad * r.uniform(0.7, 1.0) * math.cos(off + 2 * math.pi * i / n), cy + rad * r.uniform(0.7, 1.0) * math.sin(off + 2 * math.pi * i / n)) for i in range(n)]
    d = f"M {f(pts[0][0])},{f(pts[0][1])} " + " ".join(f"L {f(x)},{f(y)}" for x, y in pts[1:]) + (f" L {f(pts[0][0])},{f(pts[0][1])}" if k != "line" else "")
    return mc(f'This SVG path element <path d="{d}"/> draws a', SHAPES, SHAPES.index(k))


TASKS = [boolean_expressions, web_of_lies, navigate, tracking_shuffled_objects, logical_deduction, date_understanding, hyperbaton, colored_objects, temporal_sequences, penguins, geometric_shapes]


def bbh(cap):
    out, seen, i = [], set(), 0
    per = cap // len(TASKS) + 1
    counts = {t.__name__: 0 for t in TASKS}
    while len(out) < cap and i < cap * 20:
        t = TASKS[i % len(TASKS)]
        i += 1
        if counts[t.__name__] >= per:
            continue
        g = t(rng("bbh", t.__name__, i))
        if not g:
            continue
        text, criteria, gold = g
        if text in seen or gold not in criteria or len(criteria) < 2:
            continue
        seen.add(text)
        counts[t.__name__] += 1
        out.append(row(58, SRC + f"#{t.__name__}", text, {"type": "choice", "instructions": CHOICE, "criteria": criteria}, gold))
    return out
