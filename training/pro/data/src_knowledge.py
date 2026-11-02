"""Knowledge & reasoning benchmarks: 28 WinoGrande, 25 GPQA (proxy), 57 MMLU-Pro (proxy), 30 GSM8K, 31 ChessBench."""
import hashlib
import re

import pyarrow.parquet as pq

from rows import RAW, guard, letters, rng, row, sample

from decision_index.suite.build.layout import choice_row
from decision_index.suite.build import gsm8k_v3

REV = {
    "winogrande": "allenai/winogrande@01e74176c63542e6b0bcb004dcdea22d94fb67b5",
    "hellaswag": "Rowan/hellaswag@218ec52e09a7e7462a5400043bb9a69a41d06b76",
    "gsm8k": "openai/gsm8k@740312add88f781978c0658806c59bc2815b9866",
    "arc": "allenai/ai2_arc@210d026faf9955653af8916fad021475a3f00453",
    "commonsense_qa": "tau/commonsense_qa@94630fe30dad47192a8546eb75f094926d47e155",
    "qasc": "allenai/qasc@a34ba204eb9a33b919c10cc08f4f1c8dae5ec070",
    "medmcqa": "openlifescienceai/medmcqa@91c6572c454088bf71b679ad90aa8dffcd0d5868",
    "chess": "google-deepmind/searchless_chess@90ae0e6b121673fc3079aaeffa047580bb600c0a",
}
CHOICE = "Which option is the correct answer?"  # adapters_added.CHOICE (MMLU-Pro / BBH)


def pq_rows(rel):
    return pq.read_table(guard(RAW / rel)).to_pylist()


def kit(benchmark, source, kr):
    q = kr["questions"]["q1"]
    return row(benchmark, source, kr["state"], q, kr["gold"]["q1"])


def winogrande(cap):
    src = REV["winogrande"] + ":winogrande_xl/train"
    rs = pq_rows("hf/winogrande/winogrande_xl/train-00000-of-00001.parquet")
    out = [kit(28, src, choice_row("WinoGrande", "train", i, "Which option correctly fills the blank?\n" + r["sentence"], [r["option1"], r["option2"]], int(r["answer"]) - 1)) for i, r in enumerate(rs) if r["answer"] in ("1", "2")]
    return sample(out, cap, "wino")


def hellaswag(cap):
    src = REV["hellaswag"] + ":train"
    rs = pq_rows("hf/hellaswag/data/train-00000-of-00001.parquet")
    clean = lambda s: " ".join(str(s).split())
    out = [kit(29, src, choice_row("HellaSwag", "train", i, "Which continuation is most plausible?\n" + clean(r["ctx"]), [clean(x) for x in r["endings"]], int(r["label"]))) for i, r in enumerate(rs) if str(r["label"]).isdigit()]
    return sample(out, cap, "hella")


def gsm8k(cap):
    """v0.3 framing: options drawn from answer groups of OTHER train problems (kit gsm8k_v3 functions)."""
    src = REV["gsm8k"] + ":main/train"
    rs = pq_rows("hf/gsm8k/main/train-00000-of-00001.parquet")
    golds = {i: gsm8k_v3.gold_of(r["answer"]) for i, r in enumerate(rs)}
    sets = gsm8k_v3.option_sets(golds)
    out = []
    for i, r in enumerate(rs):
        for count in (4, 10):
            ordered, correct = gsm8k_v3.options(golds[i], sets[i][count], count, f"train:{i}")
            q = {"type": "choice", "instructions": "Choose the numeric answer to the problem in state. Do not provide reasoning. This is a named multiple-choice adaptation of GSM8K.", "criteria": {f"option_{j}": v for j, v in enumerate(ordered)}}
            out.append(row(30, src, {"question": r["question"], "task": f"GSM8K deterministic {count}-choice numeric selection"}, q, f"option_{correct}"))
    return sample(out, cap, "gsm8k")


BAD_OPT = re.compile(r"\b(all|none|both|neither) of (the )?(above|these)\b|\ball the above\b|^both\b|^none\b|^all\b|^[a-e](\s*[,&and]+\s*[a-e])*\.?$|^[a-e]{2,5}$", re.I)
ENUM_Q = re.compile(r"(^|\s)[a-e1-5]\)\s*\S", re.I)


def mcq_pool():
    """(source, question, options, gold_index, subject) from train splits only."""
    pool = []
    for sub in ("ARC-Easy", "ARC-Challenge"):
        for r in pq_rows(f"hf/arc/{sub}/train-00000-of-00001.parquet"):
            labels = list(r["choices"]["label"])
            if r["answerKey"] in labels:
                pool.append((REV["arc"] + f":{sub}/train", r["question"], list(r["choices"]["text"]), labels.index(r["answerKey"]), sub))
    for r in pq_rows("hf/commonsense_qa/data/train-00000-of-00001.parquet"):
        labels = list(r["choices"]["label"])
        if r["answerKey"] in labels:
            pool.append((REV["commonsense_qa"] + ":train", r["question"], list(r["choices"]["text"]), labels.index(r["answerKey"]), "csqa"))
    for r in pq_rows("hf/qasc/data/train-00000-of-00001.parquet"):
        labels = list(r["choices"]["label"])
        if r["answerKey"] in labels:
            pool.append((REV["qasc"] + ":train", r["question"], list(r["choices"]["text"]), labels.index(r["answerKey"]), "qasc"))
    med = []
    for r in pq_rows("hf/medmcqa/data/train-00000-of-00001.parquet"):
        if r.get("choice_type") != "single" or r.get("cop") not in (0, 1, 2, 3):
            continue
        opts = [r["opa"], r["opb"], r["opc"], r["opd"]]
        if any(not isinstance(o, str) or not o.strip() for o in opts) or len(set(o.strip().lower() for o in opts)) < 4:
            continue
        med.append((REV["medmcqa"] + ":train", r["question"], opts, int(r["cop"]), r.get("subject_name") or "medicine"))
    return pool, med


def augment(item, by_subject, n_total, seed):
    """Extend options with distractors taken from other train questions of the same subject."""
    src, q, opts, gi, subj = item
    if any(BAD_OPT.search(o.strip()) for o in opts) or ENUM_Q.search(q):
        return item
    r = rng("aug", seed)
    cand = by_subject.get(subj, [])
    have = {o.strip().lower() for o in opts}
    extra = []
    for _ in range(60):
        if len(opts) + len(extra) >= n_total or not cand:
            break
        o = r.choice(cand)
        k = o.strip().lower()
        if k not in have and not BAD_OPT.search(o.strip()) and 3 <= len(o) <= 200:
            have.add(k)
            extra.append(o)
    return (src, q, opts + extra, gi, subj)


def shuffled(item, seed):
    src, q, opts, gi, subj = item
    order = list(range(len(opts)))
    rng("shuf", seed).shuffle(order)
    return [opts[j] for j in order], order.index(gi)


def mmlu_pro_and_gpqa(cap57, cap25):
    pool, med = mcq_pool()
    r = rng("mcq-split")
    r.shuffle(pool)
    r.shuffle(med)
    by_subject = {}
    for _, _, opts, gi, subj in med + pool:
        by_subject.setdefault(subj, []).extend(o for j, o in enumerate(opts) if j != gi)
    # GPQA framing (state "", instructions=question, 4 options A-D): MedMCQA + ARC-Challenge 4-option items.
    n25_med = int(cap25 * 0.7)
    g25 = [x for x in med[:n25_med]] + [x for x in pool if x[4] == "ARC-Challenge" and len(x[2]) == 4][: cap25 - n25_med]
    used = {id(x) for x in g25}
    out25 = []
    for i, it in enumerate(g25):
        opts, gi = shuffled(it, f"25:{i}")
        out25.append(row(25, it[0], "", {"type": "choice", "instructions": it[1], "criteria": dict(zip(letters(4), opts))}, letters(4)[gi]))
    # MMLU-Pro framing (state=question string, CHOICE instructions, A.. up to 10 options).
    # Source quotas keep MedMCQA from dominating: all remaining ARC/CSQA/QASC, MedMCQA fills the rest.
    rest = [x for x in pool if id(x) not in used]
    rest = sample(rest, cap57 // 2, "57pool") + sample(med[n25_med:], cap57 - min(cap57 // 2, len(rest)), "57med")
    out57 = []
    for i, it in enumerate(rest):
        rr = rng("57n", i)
        if rr.random() < 0.6:
            it = augment(it, by_subject, rr.choice([6, 8, 10, 10, 10]), f"57:{i}")
        opts, gi = shuffled(it, f"57:{i}")
        keys = letters(len(opts))
        out57.append(row(57, it[0], it[1], {"type": "choice", "instructions": CHOICE, "criteria": dict(zip(keys, opts))}, keys[gi]))
    return out57, out25


def chess_records(path, limit):
    """Sequentially parse a byte-range prefix of the behavioral_cloning bag: varint len + FEN, then the move (unprefixed)."""
    import chess

    data = guard(path).read_bytes()
    off = 0
    out = []
    while off < len(data) - 100 and len(out) < limit:
        n = data[off]
        if n >= 128:
            raise ValueError("unexpected multi-byte FEN length")
        fen = data[off + 1: off + 1 + n].decode("ascii")
        off += 1 + n
        move = data[off: off + 4].decode("ascii")
        off += 4
        if data[off: off + 1] in (b"q", b"r", b"b", b"n") and (move[1] in "27" and move[3] in "18"):
            move += data[off: off + 1].decode()
            off += 1
        board = chess.Board(fen)
        assert chess.Move.from_uci(move) in board.legal_moves, (fen, move)
        out.append((fen, move))
    return out


def chessbench(cap):
    import chess

    src = REV["chess"] + ":train/behavioral_cloning_data.bag[bytes 0-79999999]"
    seen = set()
    out = []
    for fen, best in chess_records(RAW / "downloads/chess-train-behavioral_cloning-head80MB.bag", cap * 4):
        board = chess.Board(fen)
        # Openings dominate train/test position overlap in ChessBench; train only on positions after move 10.
        if fen in seen or board.fullmove_number <= 10:
            continue
        seen.add(fen)
        moves = {m.uci(): m for m in board.legal_moves}
        if not 2 <= len(moves) <= 255:
            continue
        order = sorted(moves, key=lambda m: hashlib.sha256((fen + ":" + m).encode()).digest())
        criteria = {m: {"uci": m, "san": board.san(moves[m])} for m in order}
        q = {"type": "choice", "instructions": "Choose the strongest legal move for the side to move. Board rows run from rank 8 to rank 1; columns a to h. Uppercase pieces are white. All legal moves are supplied.", "criteria": criteria}
        out.append(row(31, src, {"fen": fen, "board": str(board), "side_to_move": "white" if board.turn else "black"}, q, best))
        if len(out) >= cap:
            break
    return out
