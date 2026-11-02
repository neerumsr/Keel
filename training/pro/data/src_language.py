"""Language understanding: 12 ANLI (MNLI/SNLI proxy), 11 ContractNLI, 42 NLI4CT, 41 VAST, 40 iSarcasmEval, 38 ACOS, 59 RAGTruth."""
import csv
import json
import zipfile

import pyarrow.parquet as pq

from rows import RAW, guard, letters, rng, row, sample

from decision_index.suite.build.layout import choice_row
from decision_index.suite.build.adapters_added import RAGTRUTH_CRITERIA, RAGTRUTH_INSTRUCTIONS
from decision_index.suite.build.adapters_mechanical import parse_acos_line

REV = {
    "multi_nli": "nyu-mll/multi_nli@da70db2af9d09693783c3320c4249840212ee221",
    "snli": "stanfordnlp/snli@cdb5c3d5eed6ead6e5a341c8e56e669bb666725b",
    "contractnli": "stanfordnlp/contract-nli@eced6528dd3c1d14d73f9a87df8f7bdbc03126f9",
    "nli4ct": "ai-systems/Task-2-SemEval-2024@7f32fa6c7db43e577f22e9fc6c28eef1cc6d223e",
    "vast": "emilyallaway/zero-shot-stance@e7c4775182b184730f350995f8260579c9e066fe",
    "isarcasm": "iabufarha/iSarcasmEval@dfc708b53bde1bb571abfb5692f63231c2232195",
    "acos": "NUSTM/ACOS@45d179a3dcc6a3dedd848d81b16f2552454805fe",
    "ragtruth": "ParticleMedia/RAGTruth@c103204b9ce28d6bbad859304bf30de72b8ed8fe",
}


def kit(benchmark, source, kr):
    return row(benchmark, source, kr["state"], kr["questions"]["q1"], kr["gold"]["q1"])


def anli_proxy(cap):
    """ANLI is CC BY-NC (excluded); MNLI + SNLI train in the exact ANLI framing (normalize_direct.anli)."""
    mapping = {0: "entailment", 1: "neutral", 2: "contradiction"}
    out = []
    for name, rel, share in (("multi_nli", "hf/multi_nli/data/train-00000-of-00001.parquet", 0.7), ("snli", "hf/snli/plain_text/train-00000-of-00001.parquet", 0.3)):
        rs = [r for r in pq.read_table(guard(RAW / rel), columns=["premise", "hypothesis", "label"]).to_pylist() if r["label"] in mapping]
        rs = sample(rs, int(cap * share), name)
        for i, r in enumerate(rs):
            out.append(kit(12, REV[name] + ":train", choice_row("ANLI", "train", i, "Classify the relationship between the premise and hypothesis.\nPremise: " + r["premise"] + "\nHypothesis: " + r["hypothesis"], list(mapping.values()), int(r["label"]))))
    return out


CONTRACT_CRITERIA = {"Entailment": "The contract entails the hypothesis.", "Contradiction": "The contract contradicts the hypothesis.", "NotMentioned": "The hypothesis is neither entailed nor contradicted by the contract."}
CONTRACT_MAX = 5000


def contract_excerpt(doc, evidence, seed):
    """Training-only truncation: full text if <= CONTRACT_MAX chars, else all evidence spans plus random
    other spans (document order, gaps marked ' ... ') up to CONTRACT_MAX chars."""
    text = doc["text"]
    if len(text) <= CONTRACT_MAX:
        return text
    spans = doc["spans"]
    chosen = set(evidence)
    budget = CONTRACT_MAX - sum(spans[i][1] - spans[i][0] for i in chosen)
    others = [i for i in range(len(spans)) if i not in chosen]
    rng("cnli", seed).shuffle(others)
    for i in others:
        n = spans[i][1] - spans[i][0]
        if n <= budget:
            chosen.add(i)
            budget -= n
    parts, last = [], None
    for i in sorted(chosen):
        s, e = spans[i]
        if last is not None and i != last + 1:
            parts.append(" ... ")
        elif last is not None:
            parts.append(text[spans[last][1]:s])
        parts.append(text[s:e])
        last = i
    return "".join(parts)


def contractnli(cap):
    src = REV["contractnli"] + ":resources/contract-nli.zip:contract-nli/train.json"
    with zipfile.ZipFile(guard(RAW / "repos/contractnli/resources/contract-nli.zip")) as z:
        data = json.loads(z.read("contract-nli/train.json"))
    out = []
    for doc in data["documents"]:
        ann = doc["annotation_sets"][0]["annotations"]
        for key, label in data["labels"].items():
            a = ann[key]
            q = {"type": "choice", "instructions": "Classify the relationship between the contract and this hypothesis:\n" + label["hypothesis"], "criteria": CONTRACT_CRITERIA}
            out.append(row(11, src, contract_excerpt(doc, a["spans"], f"{doc['id']}:{key}"), q, a["choice"]))
    return sample(out, cap, "cnli")


def nli4ct(cap):
    src = REV["nli4ct"] + ":training_data.zip:train.json"
    criteria = {"Entailment": "The clinical trial evidence entails the statement.", "Contradiction": "The clinical trial evidence contradicts the statement."}
    out = []
    with zipfile.ZipFile(guard(RAW / "repos/nli4ct/training_data.zip")) as z:
        rows_ = json.loads(z.read("train.json"))
        for uid, r in rows_.items():
            section = r["Section_id"]
            state = {}
            for key, role in [("Primary_id", "primary_trial"), ("Secondary_id", "secondary_trial")]:
                if key in r:
                    trial = json.loads(z.read("CT json/" + r[key] + ".json"))
                    state[role] = {"id": r[key], "section": section, "text": trial[section]}
            if r["Label"] in criteria:
                out.append(row(42, src, state, {"type": "choice", "instructions": "Classify the statement against the supplied clinical trial evidence:\n" + r["Statement"], "criteria": criteria}, r["Label"]))
    return sample(out, cap, "nli4ct")


def vast(cap):
    src = REV["vast"] + ":data/VAST/vast_train.csv"
    labels = ["against", "favor", "neutral"]
    out = []
    with guard(RAW / "repos/vast/data/VAST/vast_train.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            label = int(r["label"])
            prompt = f"Topic: {r['topic_str']}\nPost: {r['post']}\nDetermine the stance of the post toward the topic."
            out.append(row(41, src, {}, {"type": "choice", "instructions": prompt, "criteria": dict(zip(letters(3), labels))}, letters(3)[label]))
    return sample(out, cap, "vast")


def isarcasm(cap):
    yn = {"no": "No", "yes": "Yes"}
    out = []
    for lang, col in (("En", "tweet"), ("Ar", "text")):
        src = REV["isarcasm"] + f":train/train.{lang}.csv"
        with guard(RAW / f"repos/isarcasm/train/train.{lang}.csv").open(encoding="utf-8-sig", newline="") as f:
            data = list(csv.DictReader(f))
        for i, r in enumerate(data):
            t = r[col]
            if not t or r["sarcastic"] not in ("0", "1"):
                continue
            # Task A
            out.append(row(40, src + ":A", t, {"type": "choice", "instructions": "Is this text intended to be sarcastic?", "criteria": yn}, "yes" if r["sarcastic"] == "1" else "no"))
            # Task B (English only; labels exist for sarcastic tweets)
            if lang == "En" and r["sarcastic"] == "1" and all(r.get(k) in ("0", "1") for k in ("sarcasm", "irony", "satire", "understatement", "overstatement", "rhetorical_question")):
                for label in ("sarcasm", "irony", "satire", "understatement", "overstatement", "rhetorical_question"):
                    out.append(row(40, src + ":B", t, {"type": "choice", "instructions": f'Does this text exhibit {label.replace("_", " ")}? Evaluate this category independently.', "criteria": yn}, "yes" if r[label] == "1" else "no"))
            # Task C: sarcastic text vs. its author-provided non-sarcastic rephrase
            if r["sarcastic"] == "1" and (r.get("rephrase") or "").strip():
                pair = [t, r["rephrase"]]
                sid = rng("isc", lang, i).randrange(2)
                if sid == 1:
                    pair = pair[::-1]
                out.append(row(40, src + ":C", "", {"type": "choice", "instructions": "Which of these two texts is the sarcastic one?", "criteria": {"text_0": pair[0], "text_1": pair[1]}}, f"text_{sid}"))
    return sample(out, cap, "isarcasm")


ACOS_SENT = {"0": "negative", "1": "neutral", "2": "positive"}


def acos(cap):
    """One row per (review, category, sentiment) question; inventory from the TRAIN files only.
    All positive pairs are kept; negatives are sampled (half share the category of a positive pair)."""
    out = []
    for path in sorted(guard(RAW / "repos/acos/data").glob("*/*_quad_train.tsv")):
        src = REV["acos"] + ":" + path.relative_to(RAW / "repos/acos").as_posix()
        parsed = [parse_acos_line(l) for l in path.read_text(encoding="utf-8").splitlines() if l]
        cats = sorted({c for _, pairs in parsed for c, _ in pairs})
        inventory = [(c, s) for c in cats for s in ("0", "1", "2")]
        for i, (review, gold) in enumerate(parsed):
            r = rng("acos", path.name, i)
            neg_same = [(c, s) for c, s in inventory if (c, s) not in gold and any(c == g[0] for g in gold)]
            neg_other = [(c, s) for c, s in inventory if (c, s) not in gold and (c, s) not in neg_same]
            picks = [(p, "yes") for p in sorted(gold)]
            picks += [(p, "no") for p in r.sample(neg_same, min(len(neg_same), 2))]
            picks += [(p, "no") for p in r.sample(neg_other, min(len(neg_other), 3))]
            for (c, s), ans in picks:
                instr = ("Given the review below, decide whether it expresses at least one " f"aspect-category/sentiment pair ({c}, {ACOS_SENT[s]}) anywhere " "in the review. Answer yes only when that exact category and " "sentiment pair is present; answer no otherwise. Multiple opposite " "sentiments are separate valid questions.")
                out.append(row(38, src, {"review": review, "task": "ACOS fixed category/sentiment presence"}, {"type": "choice", "instructions": instr, "criteria": {"yes": "The exact category/sentiment pair is present.", "no": "The exact category/sentiment pair is absent."}}, ans))
    return sample(out, cap, "acos")


RAGTRUTH_MAX = 7000


def ragtruth(cap):
    """Rows with split == 'train' only; rows whose prompt+response exceed RAGTRUTH_MAX chars are dropped
    (not truncated, since cutting context would change the label)."""
    src = REV["ragtruth"] + ":dataset/response.jsonl[split=train]"
    folder = guard(RAW / "repos/ragtruth/dataset")
    sources = {x["source_id"]: x for x in map(json.loads, (folder / "source_info.jsonl").open(encoding="utf-8"))}
    out = []
    for r in map(json.loads, (folder / "response.jsonl").open(encoding="utf-8")):
        if r["split"] != "train":
            continue
        s = sources[r["source_id"]]
        if len(s["prompt"]) + len(r["response"]) > RAGTRUTH_MAX:
            continue
        out.append(row(59, src, {"prompt": s["prompt"], "response": r["response"]}, {"type": "noul", "instructions": RAGTRUTH_INSTRUCTIONS, "criteria": RAGTRUTH_CRITERIA}, len(r["labels"]) > 0))
    return sample(out, cap, "ragtruth")
