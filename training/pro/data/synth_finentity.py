"""Synthetic 39 FinEntity-style rows: sentiment toward one named entity span in a short financial news text.

Framing copies the DI kit (adapters_mechanical.build_finentity): state = {document, task}, one choice question per
entity with the kit's instruction text (span offsets and value) and criteria Negative/Neutral/Positive. Companies are
fictional; each entity is mentioned once, in a sentence whose template fixes its sentiment. Several entities per
document, with mixed polarities, so the label depends on the span, not the overall tone. No FinEntity or DI row is read.
"""
from rows import rng, row

SRC = "synthetic:keel-pro/synth_finentity.py"
TASK = "FinEntity entity-given sentiment"
LABELS = ["Negative", "Neutral", "Positive"]
A = ["Arden", "Bexley", "Calloway", "Dunmore", "Elstree", "Fairhaven", "Glenrock", "Harlow", "Ivybridge", "Juniper", "Kestrel", "Larkspur", "Merrow", "Northgate", "Oakhurst", "Pemberly", "Quarry", "Redfern", "Stanmore", "Thornbury", "Upland", "Vantor", "Westbrook", "Yarrow", "Zenith", "Altmore", "Brightwater", "Coldharbour", "Driftwood", "Emberly"]
B = ["Holdings", "Group", "Energy", "Pharmaceuticals", "Bank", "Motors", "Systems", "Capital", "Foods", "Mining", "Semiconductor", "Airlines", "Retail", "Telecom", "Insurance", "Logistics", "Biotech", "Steel", "Software", "Partners"]

POS = [
    "{E} shares jumped {p}% after the company reported quarterly revenue well above analyst estimates.",
    "{E} raised its full-year profit forecast, citing strong demand across all regions.",
    "{E} won a ${b} billion government contract, its largest ever.",
    "{E} posted record quarterly earnings and announced a ${b} billion share buyback.",
    "Analysts upgraded {E} to buy, saying its new product line should drive years of growth.",
    "{E} stock hit an all-time high as investors cheered its expanding margins.",
    "{E} said orders rose {p}% from a year earlier, beating its own guidance.",
    "Regulators approved {E}'s flagship drug, clearing the way for a launch next quarter.",
    "{E} reduced its debt by ${b} billion, earning a credit rating upgrade.",
    "{E} increased its dividend for the tenth consecutive year.",
]
NEG = [
    "{E} shares tumbled {p}% after the company missed earnings expectations and cut its guidance.",
    "{E} is under federal investigation over its accounting practices.",
    "{E} announced plans to cut {p}% of its workforce as sales continue to slump.",
    "Ratings agencies downgraded {E}'s debt to junk, citing mounting losses.",
    "{E} recalled {k},000 products over a safety defect, a costly setback.",
    "{E} suspended its dividend after a ${b} billion quarterly loss.",
    "{E} warned that supply shortages would hurt profits for the rest of the year.",
    "A court ordered {E} to pay ${b} billion in damages for patent infringement.",
    "{E} lost its chief executive amid a widening scandal, sending the stock lower.",
    "Analysts cut {E} to sell, pointing to shrinking market share and weak cash flow.",
]
NEU = [
    "{E} is scheduled to report its quarterly results on {d}.",
    "{E} will hold its annual shareholder meeting in {m}.",
    "{E} declined to comment on the report.",
    "{E} is headquartered in {c} and employs about {k},000 people.",
    "A spokesperson for {E} confirmed the date of the investor call.",
    "{E} shares were little changed in early trading.",
    "{E} named a new chief financial officer effective {m}.",
    "{E} is one of several companies that supply components to the sector.",
    "{E} reports its results in euros and follows a calendar fiscal year.",
    "Trading in {E} was in line with its 30-day average volume.",
]
PAIR = [
    ("{X} overtook {Y} as the largest company in the sector after a strong quarter, while its rival struggled with falling sales.", "Positive", "Negative"),
    ("{X} lost a key customer to rival {Y}, which has been gaining market share.", "Negative", "Positive"),
    ("{X} sued {Y} for breach of contract; the defendant said the claims were without merit.", "Neutral", "Neutral"),
    ("{X} beat {Y} to a lucrative supply deal, leaving the loser without a major source of revenue.", "Positive", "Negative"),
    ("{X} cut prices aggressively, squeezing the margins of competitor {Y}.", "Neutral", "Negative"),
]
CITIES = ["Denver", "Rotterdam", "Osaka", "Toronto", "Lyon", "Austin", "Leeds", "Perth"]
DAYS = ["Tuesday", "Thursday", "Monday", "Wednesday"]
MONTHS = ["March", "May", "June", "September", "November"]
OPEN = ["Markets were mixed on {d} as investors weighed new inflation data.", "Stocks ended the week slightly higher.", "Earnings season continued with a busy slate of reports.", "Bond yields edged up ahead of the central bank meeting."]


def fill(t, g, **names):
    return t.format(p=g.randint(3, 28), b=g.randint(1, 9), k=g.randint(2, 90), d=g.choice(DAYS), m=g.choice(MONTHS), c=g.choice(CITIES), **names)


def document(g):
    names = []
    while len(names) < 8:
        n = f"{g.choice(A)} {g.choice(B)}"
        if n not in names and all(n.split()[0] != x.split()[0] for x in names):
            names.append(n)
    sents, ents = [], []  # ents: (name, label)
    if g.random() < 0.6:
        sents.append(fill(g.choice(OPEN), g))
    pool = iter(names)
    for _ in range(g.randint(2, 4)):
        r = g.random()
        if r < 0.2:
            t, lx, ly = g.choice(PAIR)
            x, y = next(pool), next(pool)
            sents.append(fill(t, g, X=x, Y=y))
            ents += [(x, lx), (y, ly)]
        else:
            lab = g.choices(LABELS, weights=[0.3, 0.35, 0.35])[0]
            e = next(pool, None)
            if e is None:
                break
            sents.append(fill(g.choice({"Negative": NEG, "Neutral": NEU, "Positive": POS}[lab]), g, E=e))
            ents.append((e, lab))
    return " ".join(sents), ents


def finentity(cap):
    out, i = [], 0
    while len(out) < cap:
        i += 1
        g = rng("finentity", i)
        doc, ents = document(g)
        if not ents:
            continue
        for name, lab in g.sample(ents, min(len(ents), 2)):
            s = doc.index(name)
            e = s + len(name)
            q = {"type": "choice", "instructions": ("Classify the sentiment toward the supplied financial entity span. " f"The entity span is given explicitly as {s}:{e} ({name}); " "do not extract or alter it. Choose exactly one of Negative, Neutral, or Positive."), "criteria": {x: x for x in LABELS}}
            out.append(row(39, SRC, {"document": doc, "task": TASK}, q, lab))
    return out[:cap]
