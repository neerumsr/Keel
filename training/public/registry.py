"""Public benchmark registry: how each dataset becomes Keel wire requests.

Microsoft did not publish the per-benchmark list or prompts behind MSD1's
"36 benchmarks" (see artifacts/parity/msd1/benchmarks.md), so the framing here
is ours: state = the raw text, instructions = the task question, criteria = the
dataset's own labels with short neutral descriptions (Foundry-docs style). The
framing is fixed per dataset and was not tuned on Keel's results.

Every adapter returns (wire_request, gold):
  choice -> index into criteria keys
  noul   -> True / False
  score  -> {"level": int, "target": float}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

Row = dict[str, Any]


@dataclass
class Spec:
    name: str
    hf: str
    config: str | None
    eval_split: str
    train_split: str | None
    kind: str  # choice | noul | score
    license: str
    license_url: str
    train_ok: bool
    train_note: str
    adapt: Callable[[Row], tuple[dict, Any]]
    label: Callable[[Row], Any]  # stratification key
    text: Callable[[Row], str]  # dedup key
    stream: bool = False
    stream_take: int = 0
    balanced: bool = False
    keep: Callable[[Row], bool] = lambda r: True
    notes: str = ""
    extra_eval_splits: list[str] = field(default_factory=list)


def req(state: Any, qtype: str, instructions: str, criteria: Any) -> dict:
    return {"state": state, "questions": {"answer": {"type": qtype, "instructions": instructions, "criteria": criteria}}}


# ---------------------------------------------------------------- choice tasks

SST2 = {"negative": "The writer feels negatively about the subject", "positive": "The writer feels positively about the subject"}


def sst2(r: Row):
    return req(r["sentence"].strip(), "choice", "What is the sentiment of this movie review?", SST2), int(r["label"])


AG = {
    "world": "World news, politics, international affairs",
    "sports": "Sports",
    "business": "Business, economy, companies, markets",
    "sci_tech": "Science and technology",
}


def ag_news(r: Row):
    return req(r["text"].strip(), "choice", "Which news section does this article belong in?", AG), int(r["label"])


EMOTION_KEYS = ["sadness", "joy", "love", "anger", "fear", "surprise"]


def emotion(r: Row):
    return req(r["text"].strip(), "choice", "Which emotion does the writer express?", {k: None for k in EMOTION_KEYS}), int(r["label"])


NLI3 = {
    "entailment": "The text implies the statement is true",
    "neutral": "The text neither implies nor contradicts the statement",
    "contradiction": "The text contradicts the statement",
}


def nli_choice(r: Row):
    instr = f'How does the text relate to this statement: "{r["hypothesis"].strip()}"?'
    return req(r["premise"].strip(), "choice", instr, NLI3), int(r["label"])


BANKING77_LABELS: list[str] = []
CLINC_LABELS: list[str] = []


def banking77(r: Row):
    crit = {k: None for k in BANKING77_LABELS}
    return req(r["text"].strip(), "choice", "Which banking intent does this customer message express?", crit), int(r["label"])


def clinc(r: Row):
    crit = {k: ("None of the supported intents; out of scope" if k == "oos" else None) for k in CLINC_LABELS}
    return req(r["text"].strip(), "choice", "Which intent does this user request express?", crit), int(r["intent"])


def winogrande(r: Row):
    crit = {"option_a": r["option1"].strip(), "option_b": r["option2"].strip()}
    return req(r["sentence"].strip(), "choice", "Which option correctly fills the blank (_) in the sentence?", crit), int(r["answer"]) - 1


def hellaswag(r: Row):
    crit = {f"ending_{chr(97 + i)}": e.strip()[:400] for i, e in enumerate(r["endings"])}
    return req(r["ctx"].strip(), "choice", "Which ending most plausibly continues the text?", crit), int(r["label"])


def arc(r: Row):
    labels = r["choices"]["label"]
    keys = [lab if lab[0].isalpha() else "option_" + lab for lab in labels]
    crit = {k: t.strip()[:400] for k, t in zip(keys, r["choices"]["text"])}
    return req(r["question"].strip(), "choice", "Which answer to the question is correct?", crit), labels.index(r["answerKey"])


def mmlu(r: Row):
    crit = {k: str(t).strip()[:400] for k, t in zip("ABCD", r["choices"])}
    subject = r["subject"].replace("_", " ")
    return req(r["question"].strip(), "choice", f"Which answer to this {subject} question is correct?", crit), int(r["answer"])


# ---------------------------------------------------------------- noul tasks

def boolq(r: Row):
    q = r["question"].strip()
    q = q[0].upper() + q[1:] + ("" if q.endswith("?") else "?")
    crit = {"true": "The passage indicates the answer is yes", "false": "The passage indicates the answer is no"}
    return req(r["passage"].strip(), "noul", q, crit), bool(r["answer"])


def rte(r: Row):
    instr = f'Does the text imply this statement: "{r["sentence2"].strip()}"?'
    crit = {"true": "The text implies the statement is true", "false": "The text does not imply the statement"}
    return req(r["sentence1"].strip(), "noul", instr, crit), int(r["label"]) == 0  # GLUE RTE: 0 = entailment


def mrpc(r: Row):
    state = {"sentence_1": r["sentence1"].strip(), "sentence_2": r["sentence2"].strip()}
    crit = {"true": "Both sentences say the same thing", "false": "The sentences differ in meaning"}
    return req(state, "noul", "Do the two sentences mean the same thing?", crit), int(r["label"]) == 1


def civil(r: Row):
    crit = {"true": "Rude, disrespectful, hateful, or unreasonable", "false": "Civil, even if critical"}
    return req(r["text"].strip()[:4000], "noul", "Is this comment toxic?", crit), float(r["toxicity"]) >= 0.5


# ---------------------------------------------------------------- score tasks

STSB_LEVELS = [
    "0 - completely different topics",
    "1 - not equivalent, same topic",
    "2 - not equivalent, share some details",
    "3 - roughly equivalent, some important details differ",
    "4 - mostly equivalent, minor details differ",
    "5 - completely equivalent",
]


def stsb(r: Row):
    state = {"sentence_1": r["sentence1"].strip(), "sentence_2": r["sentence2"].strip()}
    lab = float(r["label"])
    return req(state, "score", "How similar in meaning are the two sentences?", STSB_LEVELS), {"level": int(round(lab)), "target": lab}


ESCI_LEVELS = ["Irrelevant", "Complement: useful alongside what was asked for", "Substitute: close but not exactly what was asked for", "Exact match"]
ESCI_MAP = {"I": 0, "C": 1, "S": 2, "E": 3, "Irrelevant": 0, "Complement": 1, "Substitute": 2, "Exact": 3}


def esci(r: Row):
    state = {"query": r["query"].strip(), "product": (r.get("product_title") or "").strip()[:600]}
    lvl = ESCI_MAP[r["esci_label"]]
    return req(state, "score", "How relevant is this product to the shopping query?", ESCI_LEVELS), {"level": lvl, "target": float(lvl)}


def _lab(key: str):
    return lambda r: r[key]


SPECS: list[Spec] = [
    Spec("sst2", "nyu-mll/glue", "sst2", "validation", "train", "choice",
         "unspecified (SST, Stanford; via GLUE)", "https://nlp.stanford.edu/sentiment/", False,
         "No explicit license; excluded from training by default.",
         sst2, _lab("label"), lambda r: r["sentence"], notes="GLUE test labels hidden; validation used."),
    Spec("ag_news", "fancyzhx/ag_news", None, "test", "train", "choice",
         "unspecified; AG corpus offered for academic/non-commercial use", "http://groups.di.unipi.it/~gulli/AG_corpus_of_news_articles.html", False,
         "Non-commercial terms; excluded from training.",
         ag_news, _lab("label"), lambda r: r["text"]),
    Spec("emotion", "dair-ai/emotion", "split", "test", "train", "choice",
         "educational/research use only (dataset card)", "https://huggingface.co/datasets/dair-ai/emotion", False,
         "Research/educational only; excluded from training.",
         emotion, _lab("label"), lambda r: r["text"]),
    Spec("mnli_m", "nyu-mll/glue", "mnli", "validation_matched", "train", "choice",
         "OANC (permissive) + CC BY-SA 3.0 portions", "https://cims.nyu.edu/~sbowman/multinli/", True,
         "Share-alike portions: attribute. Keel-2 already replays ~6k MNLI train pairs.",
         nli_choice, _lab("label"), lambda r: r["premise"] + " || " + r["hypothesis"],
         notes="Keel-2 training replayed MNLI train pairs (NLI form); matched validation not used in training."),
    Spec("anli", "facebook/anli", None, "test_r1", None, "choice",
         "CC BY-NC 4.0", "https://github.com/facebookresearch/anli", False,
         "Non-commercial: evaluation only.",
         nli_choice, _lab("label"), lambda r: r["premise"] + " || " + r["hypothesis"],
         extra_eval_splits=["test_r2", "test_r3"], notes="R1+R2+R3 test pooled (3,200), stratified sample."),
    Spec("banking77", "PolyAI/banking77", None, "test", "train", "choice",
         "CC BY 4.0", "https://huggingface.co/datasets/PolyAI/banking77", True,
         "Permissive. 77 labels: training groups sample 12 options (gold + 11 negatives) to bound cost; --max-options changes it.",
         banking77, _lab("label"), lambda r: r["text"], notes="77 options in one choice question."),
    Spec("clinc150", "clinc/clinc_oos", "plus", "test", "train", "choice",
         "CC BY 3.0", "https://github.com/clinc/oos-eval", True,
         "Permissive. 151 labels: training groups sample 12 options (gold + 11 negatives).",
         clinc, _lab("intent"), lambda r: r["text"], notes="151 options (incl. oos) in one choice question."),
    Spec("winogrande", "allenai/winogrande", "winogrande_xl", "validation", "train", "choice",
         "CC BY 4.0", "https://github.com/allenai/winogrande", True, "Permissive.",
         winogrande, _lab("answer"), lambda r: r["sentence"], notes="Test labels hidden; validation used."),
    Spec("hellaswag", "Rowan/hellaswag", None, "validation", "train", "choice",
         "MIT", "https://github.com/rowanz/hellaswag", True, "Permissive.",
         hellaswag, _lab("label"), lambda r: r["ctx"], notes="Test labels hidden; validation used."),
    Spec("arc_easy", "allenai/ai2_arc", "ARC-Easy", "test", "train", "choice",
         "CC BY-SA 4.0", "https://allenai.org/data/arc", True, "Share-alike: attribute.",
         arc, _lab("answerKey"), lambda r: r["question"]),
    Spec("arc_challenge", "allenai/ai2_arc", "ARC-Challenge", "test", "train", "choice",
         "CC BY-SA 4.0", "https://allenai.org/data/arc", True, "Share-alike: attribute.",
         arc, _lab("answerKey"), lambda r: r["question"]),
    Spec("mmlu", "cais/mmlu", "all", "test", None, "choice",
         "MIT", "https://github.com/hendrycks/test", False,
         "No in-domain train split; not converted.",
         mmlu, _lab("subject"), lambda r: r["question"], notes="Stratified by subject."),
    Spec("boolq", "google/boolq", None, "validation", "train", "noul",
         "CC BY-SA 3.0", "https://github.com/google-research-datasets/boolean-questions", True, "Share-alike: attribute.",
         boolq, _lab("answer"), lambda r: r["question"] + " || " + r["passage"],
         notes="Test labels hidden; validation used. Long passages truncated by Keel's token window."),
    Spec("rte", "nyu-mll/glue", "rte", "validation", "train", "noul",
         "unspecified (PASCAL RTE; via GLUE)", "https://aclweb.org/aclwiki/Recognizing_Textual_Entailment", False,
         "No clear license; excluded from training.",
         rte, _lab("label"), lambda r: r["sentence1"] + " || " + r["sentence2"], notes="All 277 validation items."),
    Spec("mrpc", "nyu-mll/glue", "mrpc", "test", "train", "noul",
         "Microsoft Research Paraphrase Corpus license", "https://www.microsoft.com/en-us/download/details.aspx?id=52398", False,
         "Research license; excluded from training.",
         mrpc, _lab("label"), lambda r: r["sentence1"] + " || " + r["sentence2"]),
    Spec("civil_comments", "google/civil_comments", None, "test", "train", "noul",
         "CC0 1.0", "https://huggingface.co/datasets/google/civil_comments", True, "Public domain.",
         civil, lambda r: float(r["toxicity"]) >= 0.5, lambda r: r["text"], stream=True, stream_take=60000, balanced=True,
         notes="Toxic = toxicity >= 0.5. Class-balanced 50/50 sample (natural rate ~8%) from first 60k test rows."),
    Spec("stsb", "nyu-mll/glue", "stsb", "validation", "train", "score",
         "STS Benchmark: mixed sources (CC BY-SA 3.0 annotations)", "https://ixa2.si.ehu.eus/stswiki/index.php/STSbenchmark", True,
         "Share-alike: attribute.",
         stsb, lambda r: int(round(float(r["label"]))), lambda r: r["sentence1"] + " || " + r["sentence2"],
         notes="GLUE test labels hidden; validation used. Gold level = round(similarity)."),
    Spec("esci", "tasksource/esci", None, "test", "train", "score",
         "Apache 2.0", "https://github.com/amazon-science/esci-data", True, "Permissive; US locale only.",
         esci, _lab("esci_label"), lambda r: r["query"] + " || " + (r.get("product_title") or ""),
         stream=True, stream_take=80000, keep=lambda r: r.get("product_locale") == "us",
         notes="US locale; stream prefix of the test split; ordinal levels I<C<S<E."),
]

BY_NAME = {s.name: s for s in SPECS}


def init_labels(spec: Spec, features: Any) -> None:
    if spec.name == "banking77" and not BANKING77_LABELS:
        BANKING77_LABELS.extend(features["label"].names)
    if spec.name == "clinc150" and not CLINC_LABELS:
        CLINC_LABELS.extend(features["intent"].names)


def norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)
