"""Retrieval & classification: 4 BANKING77, 5 CLINC150+OOS, 37 Amazon-ESCI, 61 HoVer, 2 ToolRet (glaive-based)."""
import csv
import json
import re
import sqlite3
import unicodedata

from rows import RAW, clip, guard, rng, row, sample

from decision_index.suite.build.layout import choice_row
from decision_index.suite.build.adapters_added import HOVER_CRITERIA, HOVER_INSTRUCTIONS
from decision_index.suite.build.adapters_retrieval import retrieve

REV = {
    "banking77": "PolyAI-LDN/task-specific-datasets@57ec275d8078af65b7731c2a98be812d844a6d6b",
    "clinc": "clinc/oos-eval@828f8093932c8fe6ca7936c3d2e52903b1c523de",
    "esci": "amazon-science/esci-data@7916cdf6ab75a462e77f20ab40428a10923998d5",
    "hover": "hover-nlp/hover@39b84697f196308f398a251a7aea9b82ae0f0562",
    "hover_db": "nlp.cs.unc.edu/data/hover/wiki_wo_links.db@sha256:c37ee397916ec0bffacfe8902db454a5cda88a7a188409217b2e15231fe5ee2f",
    "glaive": "glaiveai/glaive-function-calling-v2@e7f4b6456019f5d8bcb991ef0dd67d8ff23221ac",
}


def kit(benchmark, source, kr):
    return row(benchmark, source, kr["state"], kr["questions"]["q1"], kr["gold"]["q1"])


def banking77(cap):
    src = REV["banking77"] + ":banking_data/train.csv"
    labels = json.loads(guard(RAW / "repos/banking77/banking_data/categories.json").read_text())
    assert len(labels) == 77
    with guard(RAW / "repos/banking77/banking_data/train.csv").open(newline="", encoding="utf-8") as f:
        data = list(csv.DictReader(f))
    out = [kit(4, src, choice_row("BANKING77", "train", i, "Classify the banking intent of this user request:\n" + r["text"], labels, labels.index(r["category"]))) for i, r in enumerate(data)]
    return sample(out, cap, "banking")


def clinc(cap):
    """Keys 'train' and 'oos_train' only; oos_train (100 rows) is repeated 5x to keep the OOS rate near the eval mix."""
    obj = json.loads(guard(RAW / "repos/clinc/data/data_full.json").read_text())
    labels = sorted({p[1] for p in obj["train"]} | {"oos"})
    assert len(labels) == 151
    desc = ["out of scope: none of the listed intents" if l == "oos" else l.replace("_", " ") for l in labels]
    out = []
    for split, reps in (("train", 1), ("oos_train", 5)):
        for i, (t, label) in enumerate(obj[split]):
            for _ in range(reps):
                out.append(kit(5, REV["clinc"] + f":data/data_full.json[{split}]", choice_row("CLINC150+OOS", split, i, "Classify the intent of this user request, or choose out of scope if none applies:\n" + t, desc, labels.index(label))))
    return sample(out, cap, "clinc")


ESCI_CRITERIA = {"E": "Exact: the product satisfies the search query.", "S": "Substitute: a product that could substitute for the requested product.", "C": "Complement: a product that complements the requested product.", "I": "Irrelevant: the product does not address the requested product need."}
ESCI_FIELD_MAX = {"product_title": 300, "product_description": 600, "product_bullet_point": 600, "product_brand": 100, "product_color": 100}


def esci(cap):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    src = REV["esci"] + ":shopping_queries_dataset_examples.parquet[split=train]"
    ex = pq.read_table(guard(RAW / "downloads/esci_examples.parquet"), filters=[("split", "=", "train")], columns=["example_id", "query", "product_id", "product_locale", "esci_label"])
    idx = sorted(rng("esci").sample(range(ex.num_rows), min(cap, ex.num_rows)))
    ex = ex.take(pa.array(idx))
    keys = ["product_locale", "product_id"]
    prod = pq.read_table(guard(RAW / "downloads/esci_products.parquet"), filters=[("product_id", "in", list(set(ex["product_id"].to_pylist())))])
    joined = ex.join(prod, keys=keys, join_type="left outer").sort_by([("example_id", "ascending")])
    out = []
    for r in joined.to_pylist():
        if r.get("product_title") is None or r["esci_label"] not in ESCI_CRITERIA:
            continue
        product = {k.removeprefix("product_"): clip(r[k], ESCI_FIELD_MAX[k]) for k in ["product_title", "product_description", "product_bullet_point", "product_brand", "product_color"] if r.get(k) is not None}
        out.append(row(37, src, {"search_query": r["query"], "product": product}, {"type": "choice", "instructions": "Classify the relevance of this product to the search query using the ESCI categories.", "criteria": ESCI_CRITERIA}, r["esci_label"]))
    return out


HOVER_DOC_MAX = 1500


def hover(cap):
    src = REV["hover"] + ":data/hover/hover_train_release_v1.1.json (+ " + REV["hover_db"] + ")"
    data = json.loads(guard(RAW / "repos/hover/data/hover/hover_train_release_v1.1.json").read_text(encoding="utf-8"))
    data = sample(data, cap, "hover")
    db = sqlite3.connect(f"file:{guard(RAW / 'downloads/hover_wiki_wo_links.db')}?mode=ro", uri=True)
    out = []
    for r in data:
        evidence = []
        ok = True
        for t in dict.fromkeys(t for t, _ in r["supporting_facts"]):
            found = db.execute("SELECT id, text FROM documents WHERE id=?", (unicodedata.normalize("NFD", t),)).fetchall()
            if len(found) != 1:
                ok = False
                break
            evidence.append({"title": t, "text": clip(found[0][1], HOVER_DOC_MAX)})
        if ok:
            out.append(row(61, src, {"claim": r["claim"], "evidence": evidence}, {"type": "choice", "instructions": HOVER_INSTRUCTIONS, "criteria": HOVER_CRITERIA}, r["label"]))
    db.close()
    return out


def json_objects(s):
    dec = json.JSONDecoder()
    i, out = 0, []
    while True:
        j = s.find("{", i)
        if j < 0:
            return out
        try:
            obj, end = dec.raw_decode(s, j)
        except json.JSONDecodeError:
            i = j + 1
            continue
        out.append(obj)
        i = end


def glaive_samples():
    data = json.loads(guard(RAW / "hf/glaive_fc/glaive-function-calling-v2.json").read_text(encoding="utf-8"))
    for i, x in enumerate(data):
        tools = [t for t in json_objects(x["system"].split("Use them if required -", 1)[-1]) if isinstance(t, dict) and t.get("name")]
        m = re.match(r"\s*USER: (.*?)\n\n\nASSISTANT: (.*?)(?:<\|endoftext\|>|\n\n\n|$)", x["chat"], re.S)
        if not tools or not m:
            continue
        user, reply = m.group(1).strip(), m.group(2).strip()
        called = None
        if reply.startswith("<functioncall>"):
            mm = re.search(r'"name"\s*:\s*"([^"]+)"', reply)
            called = mm.group(1) if mm else None
        yield i, tools, user, called


TOOLRET_TASK = "Rank candidate documents/tools by relevance to this query."
TOOLRET_Q = "Assess whether this candidate is relevant/useful to the query. Use the full text below; return the probability of relevance."
TOOLRET_CRITERIA = {"yes": "Relevant/useful to the query.", "no": "Not relevant/useful to the query."}


def toolret(cap, negatives=3):
    """ToolRet framing from glaive-function-calling-v2: query = first user turn, positive = the called tool's
    JSON documentation, negatives = kit BM25 (adapters_retrieval.retrieve) over all glaive tool docs,
    excluding docs with the same tool name."""
    src = REV["glaive"] + ":train"
    docs, names, items = {}, {}, []
    for i, tools, user, called in glaive_samples():
        for t in tools:
            d = json.dumps(t, ensure_ascii=False)
            if d not in docs:
                docs[d] = str(len(docs))
                names[docs[d]] = t["name"]
        if called:
            pos = [json.dumps(t, ensure_ascii=False) for t in tools if t["name"] == called]
            if pos:
                items.append((user, pos[0]))
    conn = sqlite3.connect(":memory:")
    conn.execute('CREATE VIRTUAL TABLE docs USING fts5(docid UNINDEXED,content,tokenize="porter unicode61")')
    conn.executemany("INSERT INTO docs(docid,content) VALUES (?,?)", [(v, k) for k, v in docs.items()])
    by_id = {v: k for k, v in docs.items()}
    seen_q = set()
    items = [x for x in items if not (x[0] in seen_q or seen_q.add(x[0]))]
    items = sample(items, cap // (1 + negatives) + 1, "toolret")
    by_name = {}
    for did, n in names.items():
        by_name.setdefault(n, []).append(did)
    out = []
    state_of = lambda q: {"query": q, "task": TOOLRET_TASK}
    for qi, (query, pos) in enumerate(items):
        pname = json.loads(pos)["name"]
        hits = retrieve(conn, query, excluded=by_name.get(pname, []), k=16)
        r = rng("toolret", qi)
        negs = [c for _, c in hits[:16]]
        negs = r.sample(negs, min(negatives, len(negs)))
        cands = [(pos, "yes")] + [(c, "no") for c in negs]
        for content, ans in cands:
            out.append(row(2, src, state_of(query), {"type": "choice", "instructions": {"task": TOOLRET_Q, "candidate": content}, "criteria": TOOLRET_CRITERIA}, ans))
    conn.close()
    return sample(out, cap, "toolret-out")
