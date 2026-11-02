"""SATA-Bench-style rows (33) from QASC train: does this candidate correctly answer the question?

Framing copies the DI kit (normalize_text.sata): state = {paragraph, question, options}, one choice question per
candidate with the kit's instruction text and criteria {"no": "No", "yes": "Yes"}. QASC (CC BY 4.0) supplies the
paragraph (its two supporting facts), the question and eight candidates with one correct answer. Candidate order is
shuffled with our own seed. No SATA-Bench or DI row is read.
"""
import pyarrow.parquet as pq

from rows import RAW, guard, rng, row

REV = "allenai/qasc@a34ba204eb9a33b919c10cc08f4f1c8dae5ec070:train"


def sata(cap):
    out = []
    data = pq.read_table(guard(RAW / "hf/qasc/data/train-00000-of-00001.parquet")).to_pylist()
    for i, r in enumerate(data):
        labels, texts = list(r["choices"]["label"]), list(r["choices"]["text"])
        if r["answerKey"] not in labels or not r.get("fact1"):
            continue
        g = rng("sata", i)
        gold = texts[labels.index(r["answerKey"])]
        opts = texts[:]
        g.shuffle(opts)
        paragraph = " ".join(f.strip().rstrip(".") + "." for f in (r["fact1"], r["fact2"]) if f)
        state = {"paragraph": paragraph, "question": r["question"], "options": opts}
        picks = [gold] + g.sample([o for o in opts if o != gold], 1)
        for c in picks:
            q = {"type": "choice", "instructions": f'Question: {r["question"]}\nDoes this candidate correctly answer the question?\nCandidate: {c}', "criteria": {"no": "No", "yes": "Yes"}}
            out.append(row(33, REV, state, q, "yes" if c == gold else "no"))
        if len(out) >= cap:
            break
    return out[:cap]
