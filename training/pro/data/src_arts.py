"""Arts: 21 Humicroedit (subtask-2 train; no explicit license -> opt-in only), 64 New Yorker caption matching (train),
50 Habermas consensus (question.split TRAIN cohorts)."""
import collections
import csv
import hashlib
import io
import re
import zipfile

from rows import RAW, guard, letters, row, sample

from decision_index.suite.build.adapters_added import NEWYORKER_INSTRUCTIONS

REV = {
    "humicroedit": "cs.rochester.edu/u/nhossain/semeval-2020-task-7-dataset.zip@sha256:12a6cbf28c8b698ad80be42a65ac867b57e4c71662eedab607805e167ba791ab",
    "newyorker": "jmhessel/newyorker_caption_contest@d81cbab7d0392708d5371d3a4960e69261824db4",
    "habermas": "storage.googleapis.com/habermas_machine/datasets/hm_all_candidate_comparisons.parquet@sha256:7cf8d5ce3fce8853b36f0ffe1158424f7813867e422e313db4df0a5f9e03e4a4",
}


def humicroedit(cap):
    out = []
    with zipfile.ZipFile(guard(RAW / "downloads/humicroedit-full.zip")) as z:
        for member in ("semeval-2020-task-7-dataset/subtask-2/train.csv", "semeval-2020-task-7-dataset/subtask-2/train_funlines.csv"):
            src = REV["humicroedit"] + ":" + member.split("/", 1)[1]
            for r in csv.DictReader(io.StringIO(z.read(member).decode("utf-8-sig"))):
                if r["label"] not in {"1", "2"}:
                    continue
                criteria = {}
                for n in (1, 2):
                    rendered, count = re.subn(r"<[^<>]+/>", lambda _: r[f"edit{n}"], r[f"original{n}"])
                    if count != 1:
                        break
                    criteria[f"headline_{n}"] = rendered
                if len(criteria) == 2 and criteria["headline_1"] != criteria["headline_2"]:
                    out.append(row(21, src, "", {"type": "choice", "instructions": "Which edited news headline is funnier?", "criteria": criteria}, "headline_" + r["label"]))
    return sample(out, cap, "humicroedit")


def newyorker(cap):
    import pyarrow.parquet as pq

    out = []
    for p in sorted(guard(RAW / "hf/newyorker/matching").glob("train-*.parquet")):
        src = REV["newyorker"] + f":matching/{p.name}"
        for r in pq.read_table(guard(p), columns=["image_location", "image_description", "image_uncanny_description", "entities", "caption_choices", "label"]).to_pylist():
            keys = letters(len(r["caption_choices"]))
            out.append(row(64, src, {"scene": r["image_location"], "description": r["image_description"], "uncanny_description": r["image_uncanny_description"], "entities": r["entities"]}, {"type": "choice", "instructions": NEWYORKER_INSTRUCTIONS, "criteria": dict(zip(keys, r["caption_choices"]))}, r["label"]))
    return sample(out, cap, "newyorker")


HABERMAS_INSTRUCTIONS = "Choose the consensus statement you predict this group would rank highest on average, given their expressed opinions. Each participant has equal weight. Assess the group's preferences, rather than your own policy preference."


def habermas(cap):
    """Kit adapters_scored.habermas logic applied to the TRAINING_DATA_* cohorts (question.split TRAIN) instead of
    EVAL_*; both iterations are used (each iteration has its own candidate pool). Panels with tied best are skipped."""
    import pyarrow.parquet as pq

    src = REV["habermas"] + "[question.split=TRAIN]"
    columns = ["metadata.version", "metadata.status", "round_id", "iteration_index", "question.split", "question.text", "rankings.metadata.status", "rankings.candidate_ids", "rankings.numerical_ranks", "candidates.metadata.id", "candidates.text", "own_opinion.metadata.id", "own_opinion.text", "other_opinions.metadata.id"]
    raw = pq.read_table(guard(RAW / "downloads/hm_all_candidate_comparisons.parquet"), columns=columns).to_pylist()
    groups = collections.defaultdict(list)
    for r in raw:
        if not r["metadata.version"].startswith("TRAINING_DATA") or r["question.split"] != "TRAIN":
            continue
        if r["metadata.status"] != "COMPLETED" or r["rankings.metadata.status"] != "COMPLETED":
            continue
        groups[(r["round_id"], r["iteration_index"], tuple(sorted(r["rankings.candidate_ids"] or [])))].append(r)
    out = []
    for (round_id, it, candidates), panel in sorted(groups.items()):
        ref = panel[0]
        expected = set(ref["other_opinions.metadata.id"]) | {ref["own_opinion.metadata.id"]}
        actual = [r["own_opinion.metadata.id"] for r in panel]
        if set(actual) != expected or len(actual) != len(set(actual)) or not 2 <= len(candidates) <= 255:
            continue
        text_map = dict(zip(ref["candidates.metadata.id"], ref["candidates.text"]))
        if not all(isinstance(text_map.get(c), str) and text_map[c].strip() for c in candidates):
            continue
        if len({" ".join(text_map[c].split()) for c in candidates}) != len(candidates):
            continue
        sums = dict.fromkeys(candidates, 0)
        ok = True
        for r in panel:
            ranks = dict(zip(r["rankings.candidate_ids"], r["rankings.numerical_ranks"]))
            if set(ranks) != set(candidates) or not all(type(v) is int for v in ranks.values()):
                ok = False
                break
            for c, v in ranks.items():
                sums[c] += v
        best = [c for c in candidates if sums[c] == min(sums.values())]
        if not ok or len(best) != 1:
            continue
        order = sorted(candidates, key=lambda c: hashlib.sha256((round_id + c).encode()).digest())
        keys = {c: f"option_{i}" for i, c in enumerate(order)}
        opinions = {r["own_opinion.metadata.id"]: r["own_opinion.text"] for r in panel}
        state = {"policy_question": ref["question.text"], "participant_opinions": [opinions[k] for k in sorted(opinions)]}
        out.append(row(50, src, state, {"type": "choice", "instructions": HABERMAS_INSTRUCTIONS, "criteria": {keys[c]: text_map[c] for c in order}}, keys[best[0]]))
    return sample(out, cap, "habermas")
