"""Download the TRAIN-split sources for the Keel-Pro corpus into C:\\KeelWork\\pro\\raw.

Pinned revisions are reused from the Decision Index kit (acquire.py / adapters_added.py) where the
same repository is used, so file layouts match the kit adapters. Only train-split files are read later;
some archives (CLINC data_full.json, the Humicroedit zip, the ContractNLI zip, RAGTruth response.jsonl)
also contain eval splits, and the builders read only their train members/rows.

Run: C:\\KeelWork\\decision-index\\.venv\\Scripts\\python.exe training\\pro\\data\\fetch.py [name ...]
"""
import os
import sys
import json
import hashlib
import shutil
import subprocess
import urllib.request
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

RAW = Path(os.environ.get("KEEL_PRO_RAW", r"C:\KeelWork\pro\raw"))
LOCK = RAW / "fetch-lock.json"

GIT = {
    "contractnli": ("https://github.com/stanfordnlp/contract-nli.git", "eced6528dd3c1d14d73f9a87df8f7bdbc03126f9", ["resources"]),
    "nli4ct": ("https://github.com/ai-systems/Task-2-SemEval-2024.git", "7f32fa6c7db43e577f22e9fc6c28eef1cc6d223e", ["train.json", "training_data.zip"]),
    "isarcasm": ("https://github.com/iabufarha/iSarcasmEval.git", "dfc708b53bde1bb571abfb5692f63231c2232195", ["train"]),
    "acos": ("https://github.com/NUSTM/ACOS.git", "45d179a3dcc6a3dedd848d81b16f2552454805fe", ["data/*/*_quad_train.tsv"]),
    "vast": ("https://github.com/emilyallaway/zero-shot-stance.git", "e7c4775182b184730f350995f8260579c9e066fe", ["data/VAST/vast_train.csv"]),
    "apibank": ("https://github.com/AlibabaResearch/DAMO-ConvAI.git", "188835d4f9948563a6b9c8ac50cd0f3ae4021ed6", ["api-bank"]),
    "ragtruth": ("https://github.com/ParticleMedia/RAGTruth", "c103204b9ce28d6bbad859304bf30de72b8ed8fe", ["dataset"]),
    "hover": ("https://github.com/hover-nlp/hover", "39b84697f196308f398a251a7aea9b82ae0f0562", ["data/hover/hover_train_release_v1.1.json"]),
    "habermas_machine": ("https://github.com/google-deepmind/habermas_machine.git", "7923b71966c14136077c78d7841bc9e1a182dfe0", ["LICENSE"]),
    "esci": ("https://github.com/amazon-science/esci-data.git", "7916cdf6ab75a462e77f20ab40428a10923998d5", ["LICENSE"]),
    "searchless_chess": ("https://github.com/google-deepmind/searchless_chess.git", "90ae0e6b121673fc3079aaeffa047580bb600c0a", ["LICENSE"]),
    "toolret": ("https://github.com/mangopy/tool-retrieval-benchmark.git", "c4181d914a227134705ecb6bab13fbd92ccd2938", ["LICENSE"]),
    "banking77": ("https://github.com/PolyAI-LDN/task-specific-datasets.git", None, ["banking_data/train.csv", "banking_data/categories.json"]),
    "clinc": ("https://github.com/clinc/oos-eval.git", None, ["data/data_full.json"]),
}
HTTP = {
    "downloads/humicroedit-full.zip": ("https://cs.rochester.edu/u/nhossain/semeval-2020-task-7-dataset.zip", "12a6cbf28c8b698ad80be42a65ac867b57e4c71662eedab607805e167ba791ab"),
    "downloads/hover_wiki_wo_links.db": ("https://nlp.cs.unc.edu/data/hover/wiki_wo_links.db", "c37ee397916ec0bffacfe8902db454a5cda88a7a188409217b2e15231fe5ee2f"),
    "downloads/hm_all_candidate_comparisons.parquet": ("https://storage.googleapis.com/habermas_machine/datasets/hm_all_candidate_comparisons.parquet", "7cf8d5ce3fce8853b36f0ffe1158424f7813867e422e313db4df0a5f9e03e4a4"),
    # First 80 MB (byte range) of the ChessBench TRAIN behavioral-cloning bag; records are parsed sequentially.
    "downloads/chess-train-behavioral_cloning-head80MB.bag": ("https://storage.googleapis.com/searchless_chess/data/train/behavioral_cloning_data.bag", None, (0, 79999999)),
    "downloads/esci_examples.parquet": ("https://media.githubusercontent.com/media/amazon-science/esci-data/7916cdf6ab75a462e77f20ab40428a10923998d5/shopping_queries_dataset/shopping_queries_dataset_examples.parquet", None),
    "downloads/esci_products.parquet": ("https://media.githubusercontent.com/media/amazon-science/esci-data/7916cdf6ab75a462e77f20ab40428a10923998d5/shopping_queries_dataset/shopping_queries_dataset_products.parquet", None),
}
HF = {
    "hellaswag": ("Rowan/hellaswag", "218ec52e09a7e7462a5400043bb9a69a41d06b76", ["data/train-*.parquet", "README.md"]),
    "winogrande": ("allenai/winogrande", "01e74176c63542e6b0bcb004dcdea22d94fb67b5", ["winogrande_xl/train-*.parquet", "README.md"]),
    "gsm8k": ("openai/gsm8k", "740312add88f781978c0658806c59bc2815b9866", ["main/train-*.parquet", "README.md"]),
    "arc": ("allenai/ai2_arc", "210d026faf9955653af8916fad021475a3f00453", ["ARC-Easy/train-*.parquet", "ARC-Challenge/train-*.parquet", "README.md"]),
    "multi_nli": ("nyu-mll/multi_nli", "da70db2af9d09693783c3320c4249840212ee221", ["data/train-*.parquet", "README.md"]),
    "snli": ("stanfordnlp/snli", "cdb5c3d5eed6ead6e5a341c8e56e669bb666725b", ["plain_text/train-*.parquet", "README.md"]),
    "commonsense_qa": ("tau/commonsense_qa", "94630fe30dad47192a8546eb75f094926d47e155", ["data/train-*.parquet", "README.md"]),
    "qasc": ("allenai/qasc", "a34ba204eb9a33b919c10cc08f4f1c8dae5ec070", ["data/train-*.parquet", "README.md"]),
    "medmcqa": ("openlifescienceai/medmcqa", "91c6572c454088bf71b679ad90aa8dffcd0d5868", ["data/train-*.parquet", "README.md"]),
    "when2call": ("nvidia/When2Call", "0582f7749df63a96fdc3070932e83e72396ace53", ["train/*.jsonl", "README.md"]),
    "newyorker": ("jmhessel/newyorker_caption_contest", "d81cbab7d0392708d5371d3a4960e69261824db4", ["matching/train-*.parquet", "README.md"]),
    "glaive_fc": ("glaiveai/glaive-function-calling-v2", "e7f4b6456019f5d8bcb991ef0dd67d8ff23221ac", ["glaive-function-calling-v2.json", "README.md"]),
    "toolace": ("Team-ACE/ToolACE", "6bda777c88d21e5a204703c1ee45597a8fa4f734", ["data.json", "README.md"]),
    "apibank_train": ("liminghao1630/API-Bank", "12e8158b7628c168f07e8f31fbbe3445e99f44cf", ["training-data/*", "README.md"]),
}
# Inspected but not used (no data license stated): mangopy/ToolRet-Training-20w@fdf5a317455b1e60785de7ba587496aa6cc878e4.


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(name):
    url, rev, sparse = GIT[name]
    dest = RAW / "repos" / name
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
        subprocess.run(["git", "remote", "add", "origin", url], cwd=dest, check=True)
    subprocess.run(["git", "sparse-checkout", "set", "--no-cone", *sparse, "LICENSE*", "README*", "*.md"], cwd=dest, check=True)
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", rev or "HEAD"], cwd=dest, check=True)
    subprocess.run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=dest, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dest, text=True).strip()


def http(rel):
    url, expected, *byte_range = HTTP[rel]
    dest = RAW / rel
    if dest.exists() and (expected is None or sha256(dest) == expected):
        return sha256(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url)
    if byte_range:
        req.add_header("Range", "bytes=%d-%d" % byte_range[0])
    with urllib.request.urlopen(req, timeout=3600) as r, tmp.open("wb") as f:
        shutil.copyfileobj(r, f, 1 << 22)
    actual = sha256(tmp)
    if expected and actual != expected:
        raise ValueError(f"{url}: sha256 {actual} != pinned {expected}")
    tmp.replace(dest)
    return actual


def hf(name):
    from huggingface_hub import snapshot_download

    repo, rev, patterns = HF[name]
    snapshot_download(repo, repo_type="dataset", revision=rev, allow_patterns=patterns, local_dir=str(RAW / "hf" / name))
    return rev


def main(names):
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    jobs = [("git", n) for n in GIT] + [("http", n) for n in HTTP] + [("hf", n) for n in HF]
    for kind, name in jobs:
        if names and name not in names and kind not in names:
            continue
        for attempt in (1, 2):
            try:
                rev = {"git": git, "http": http, "hf": hf}[kind](name)
                lock[f"{kind}:{name}"] = {"revision_or_sha256": rev, "status": "ok"}
                print(f"ok {kind}:{name} {rev}", flush=True)
                break
            except Exception as e:  # recorded, the builder skips missing sources
                print(f"fail {kind}:{name} attempt {attempt}: {type(e).__name__}: {e}", flush=True)
                lock[f"{kind}:{name}"] = {"status": "failed", "error": f"{type(e).__name__}: {e}"[:300]}
        LOCK.write_text(json.dumps(lock, indent=2) + "\n")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
