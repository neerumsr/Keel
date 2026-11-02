# Keel-Pro training corpus: data provenance and licences

This corpus trains the Keel-Pro LoRA (Qwen3.5 2B/4B/9B). It is framed exactly as the Decision Index (DI) kit edition 0.3 frames each benchmark. Read this together with `CONTRACT.md` Phase 3.

## Outputs and code

- **Builder code:** `training/pro/data/`
  - `fetch.py`: downloads into `C:\KeelWork\pro\raw` and pins every revision in `fetch-lock.json`.
  - `build_train.py`: orchestrates the build.
  - Per-source builders: `src_*.py` and `synth_*.py`.
  - `validate.py`: checks the framing.
  - Run everything with the DI kit venv: `python -X utf8 build_train.py`.
- **Outputs:**
  - `C:\KeelWork\pro\data\train.jsonl.gz`: 330,232 rows.
  - `train-holdout.jsonl.gz`: 3,367 rows, for loss sanity only.
  - `train-stats.json`
- **Determinism:**
  - All sampling uses `random.Random` seeded from `"keel-pro-2026"`, and the final shuffle uses `"keel-pro-2026:shuffle"`.
  - Holdout rule: the first 8 hex characters of `sha256(row content)`, mod 100, is < 1.
  - Rows are de-duplicated on a content hash. Benchmark 5 is exempt.
- **Framing:**
  - Rows are built with the kit's own helpers where practical: `layout.choice_row`, the `normalize_direct` ANLI recipe, `adapters_selection.apibank_catalog`, the BBH and MMLU-Pro framing from `adapters_added`, and the `home_appliance` resolver.
  - Otherwise they copy the kit's instruction text, criteria keys, option order and state shape literally.
  - `validate.py` checks every row's state keys, criteria-key style, gold-in-criteria and instruction text against the kit source. On the full build it reports `PROBLEMS: none` for all 24 benchmarks.

## Data used (train splits or own synthetic data only)

"Rows" are rows in `train.jsonl.gz`, copied from `train-stats.json`. Holdout rows are counted per benchmark in `train-stats.json`.

| DI # | DI benchmark | Dataset | Source / revision | Split used | Licence | Rows |
|---|---|---|---|---|---|---|
| 1 | BFCL (tool-name selection) | ToolACE | [Team-ACE/ToolACE](https://huggingface.co/datasets/Team-ACE/ToolACE) @ `6bda777c88d21e5a204703c1ee45597a8fa4f734` | `data.json` (the only release; BFCL is a separate benchmark) | Apache-2.0 (dataset card) | 14,827 |
| 2 | ToolRet (proxy) | glaive-function-calling-v2 | [glaiveai/glaive-function-calling-v2](https://huggingface.co/datasets/glaiveai/glaive-function-calling-v2) @ `e7f4b6456019f5d8bcb991ef0dd67d8ff23221ac` | train | Apache-2.0 (dataset card) | 14,843 |
| 3 | API-Bank | API-Bank training data | [liminghao1630/API-Bank](https://huggingface.co/datasets/liminghao1630/API-Bank) @ `12e8158b7628c168f07e8f31fbbe3445e99f44cf` | `training-data/lv1-api-train.json` (3,138) + `lv2-api-train.json` (3,179) | MIT (dataset card) | 6,317 |
| 3 | (tool catalog in state) | API-Bank `apis/*.py` | [AlibabaResearch/DAMO-ConvAI](https://github.com/AlibabaResearch/DAMO-ConvAI) @ `188835d4f9948563a6b9c8ac50cd0f3ae4021ed6`, `api-bank/` | tool schemas only | Apache-2.0 (`api-bank/LICENSE`); repo MIT | (state) |
| 4 | BANKING77 | BANKING77 | [PolyAI-LDN/task-specific-datasets](https://github.com/PolyAI-LDN/task-specific-datasets) @ `57ec275d8078af65b7731c2a98be812d844a6d6b` | `banking_data/train.csv` | CC BY 4.0 (`LICENSE`) | 9,913 |
| 5 | CLINC150+OOS | CLINC oos-eval | [clinc/oos-eval](https://github.com/clinc/oos-eval) @ `828f8093932c8fe6ca7936c3d2e52903b1c523de` | `data_full.json` `train` (14,860) + `oos_train` (485) | CC BY 3.0 (`LICENSE`) | 15,345 |
| 9 | Home appliance simulator | synthetic | `training/pro/data/synth_home.py` | own generator | Apache-2.0 (this repo) | 11,877 |
| 11 | ContractNLI | ContractNLI | [stanfordnlp/contract-nli](https://github.com/stanfordnlp/contract-nli) @ `eced6528dd3c1d14d73f9a87df8f7bdbc03126f9`, `resources/contract-nli.zip` | `train.json` | CC BY 4.0 (`LICENSE`) | 7,099 |
| 12 | ANLI (proxy) | MultiNLI | [nyu-mll/multi_nli](https://huggingface.co/datasets/nyu-mll/multi_nli) @ `da70db2af9d09693783c3320c4249840212ee221` | train | Mixed: OANC / CC BY 3.0 / **CC BY-SA 3.0** / MIT / "other" (card) | 24,262 |
| 12 | ANLI (proxy) | SNLI | [stanfordnlp/snli](https://huggingface.co/datasets/stanfordnlp/snli) @ `cdb5c3d5eed6ead6e5a341c8e56e669bb666725b` | train | **CC BY-SA 4.0** (card) | 10,401 |
| 25 | GPQA Diamond (proxy) | MedMCQA | [openlifescienceai/medmcqa](https://huggingface.co/datasets/openlifescienceai/medmcqa) @ `91c6572c454088bf71b679ad90aa8dffcd0d5868` | train | Apache-2.0 (card) | 8,323 |
| 25 | GPQA Diamond (proxy) | ARC-Challenge | [allenai/ai2_arc](https://huggingface.co/datasets/allenai/ai2_arc) @ `210d026faf9955653af8916fad021475a3f00453` | ARC-Challenge train | **CC BY-SA 4.0** (card) | 1,103 |
| 28 | WinoGrande | WinoGrande | [allenai/winogrande](https://huggingface.co/datasets/allenai/winogrande) @ `01e74176c63542e6b0bcb004dcdea22d94fb67b5` | `winogrande_xl` train | CC BY 4.0 ([AI2](https://winogrande.allenai.org/)) | 14,849 |
| 29 | HellaSwag | HellaSwag | [Rowan/hellaswag](https://huggingface.co/datasets/Rowan/hellaswag) @ `218ec52e09a7e7462a5400043bb9a69a41d06b76` | train | MIT ([rowanz/hellaswag](https://github.com/rowanz/hellaswag/blob/master/LICENSE)) | 19,809 |
| 30 | GSM8K | GSM8K | [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) @ `740312add88f781978c0658806c59bc2815b9866` | `main` train | MIT (card) | 13,865 |
| 31 | ChessBench | searchless_chess behavioural-cloning data | [google-deepmind/searchless_chess](https://github.com/google-deepmind/searchless_chess) @ `90ae0e6b121673fc3079aaeffa047580bb600c0a`; `storage.googleapis.com/searchless_chess/data/train/behavioral_cloning_data.bag` | **train**, first 80 MB byte range | Data CC BY 4.0, code Apache-2.0 (README); games CC0 (lichess) | 11,857 |
| 37 | Amazon ESCI | Shopping Queries Dataset | [amazon-science/esci-data](https://github.com/amazon-science/esci-data) @ `7916cdf6ab75a462e77f20ab40428a10923998d5` | `split == "train"` | Apache-2.0 (`LICENSE`) | 19,783 |
| 40 | iSarcasmEval | iSarcasmEval | [iabufarha/iSarcasmEval](https://github.com/iabufarha/iSarcasmEval) @ `dfc708b53bde1bb571abfb5692f63231c2232195` | `train/train.En.csv` (A 3,426 / B 5,163 / C 860) + `train/train.Ar.csv` (A 3,071 / C 740); DI has the same five tracks | MIT (`LICENSE`) | 13,260 |
| 43 | CRUXEval | synthetic | `synth_crux.py` (own Python functions, executed for gold) | own generator | Apache-2.0 (this repo) | 11,871 |
| 44 | CLadder | synthetic | `synth_cladder.py` (own causal graphs, computed answers) | own generator | Apache-2.0 (this repo) | 9,911 |
| 50 | Habermas Machine | Habermas Machine candidate comparisons | [google-deepmind/habermas_machine](https://github.com/google-deepmind/habermas_machine) @ `7923b71966c14136077c78d7841bc9e1a182dfe0`; `hm_all_candidate_comparisons.parquet` sha256 `7cf8d5ce…e4a4` | `question.split == TRAIN` (cohorts TRAINING_DATA_V1–V5) | CC BY 4.0 for materials (README) | 1,898 |
| 57 | MMLU-Pro (proxy) | MedMCQA | as above | train | Apache-2.0 | 14,824 |
| 57 | MMLU-Pro (proxy) | CommonsenseQA | [tau/commonsense_qa](https://huggingface.co/datasets/tau/commonsense_qa) @ `94630fe30dad47192a8546eb75f094926d47e155` | train | MIT (card) | 7,210 |
| 57 | MMLU-Pro (proxy) | QASC | [allenai/qasc](https://huggingface.co/datasets/allenai/qasc) @ `a34ba204eb9a33b919c10cc08f4f1c8dae5ec070` | train | CC BY 4.0 (card) | 5,983 |
| 57 | MMLU-Pro (proxy) | ARC-Easy / ARC-Challenge | `allenai/ai2_arc` as above | train | **CC BY-SA 4.0** | 1,644 / 2 |
| 58 | BBH fixed-option tasks | synthetic | `synth_bbh.py` (11 task families; all text generated, no BBH files read) | own generator | Apache-2.0 (this repo) | 14,846 |
| 59 | RAGTruth | RAGTruth | [ParticleMedia/RAGTruth](https://github.com/ParticleMedia/RAGTruth) @ `c103204b9ce28d6bbad859304bf30de72b8ed8fe` | `response.jsonl`, `split == "train"` | MIT (`LICENSE`) | 14,295 |
| 61 | HoVer | HoVer + its Wikipedia DB | [hover-nlp/hover](https://github.com/hover-nlp/hover) @ `39b84697f196308f398a251a7aea9b82ae0f0562`, `hover_train_release_v1.1.json`; `nlp.cs.unc.edu/data/hover/wiki_wo_links.db` sha256 `c37ee397…5ee2f` | train | Data **CC BY-SA 4.0** ([hover-nlp.github.io](https://hover-nlp.github.io/)); code MIT; Wikipedia text CC BY-SA | 17,730 |
| 62 | When2Call MCQ | When2Call | [nvidia/When2Call](https://huggingface.co/datasets/nvidia/When2Call) @ `0582f7749df63a96fdc3070932e83e72396ace53` | `train/when2call_train_pref.jsonl` + `train/when2call_train_sft.jsonl` | CC BY 4.0 (card) | 2,668 |
| 64 | New Yorker caption matching | newyorker_caption_contest | [jmhessel/newyorker_caption_contest](https://huggingface.co/datasets/jmhessel/newyorker_caption_contest) @ `d81cbab7d0392708d5371d3a4960e69261824db4` | `matching/train-0000{0,1}-of-00002.parquet` (DI uses `matching/test-*`) | CC BY 4.0 (card) | 9,617 |

Total: **330,232** train rows and **3,367** holdout rows.

Per-benchmark gold balance and rendered-length percentiles are in `train-stats.json`.

## Truncation and length rules (training only)

- **11 ContractNLI:** the contract is cut to ≤ 5,000 chars. Every evidence span is kept, plus random other spans in document order, joined with ` ... `.
- **37 ESCI:**
  - Product title ≤ 300 chars.
  - Description and bullets ≤ 600 chars.
  - Brand and colour ≤ 100 chars.
  - The cut keeps the first 70% and the end, joined with ` ... `.
- **61 HoVer:** each evidence document ≤ 1,500 chars (same head/tail cut).
- **59 RAGTruth:** rows with prompt + response > 7,000 chars are dropped, not truncated.
- **3 API-Bank:** no truncation. The state carries the full published tool catalog, as DI does: 53 kit tools plus the sample's own APIs, about 26–31k rendered chars. Every API-Bank row is over 6,000 chars, so a trainer with a short `max_len` will drop them. Decide this at training time.
- **Other rows over 6,000 rendered chars:**
  - BFCL: 88.
  - Habermas: 117.
  - RAGTruth: 513.
  - When2Call: 5.

## Skipped or excluded sources

| Source | DI # | Why |
|---|---|---|
| ANLI | 12 | CC BY-NC 4.0. Replaced by MNLI + SNLI train in the exact ANLI framing. |
| MMLU `auxiliary_train` | 57/25 | Contains RACE, which is research/non-commercial. Replaced by MedMCQA, CommonsenseQA, QASC and ARC train. |
| OpenBookQA | 57 | Licence could not be confirmed. |
| ToolRet-Training (`mangopy/ToolRet-Training-20w`) | 2 | No data licence stated. Replaced by glaive-function-calling-v2. |
| ACOS (`NUSTM/ACOS`) train TSVs | 38 | No explicit licence. Builder exists; opt-in only with `--include-unlicensed`. |
| VAST `vast_train.csv` | 41 | No explicit licence. Opt-in only. |
| NLI4CT `training_data.zip` | 42 | No licence (confirmed by a web search). Train and test also share trial documents. Opt-in only. |
| Humicroedit subtask-2 train | 21 | No explicit licence. Opt-in only. DI uses the test file. |
| FinEntity | 39 | DI samples the whole dataset, which has no official split, so disjointness cannot be proven. |
| PhishNChips | 56 | Licence "other"; no separate train split proven disjoint from the DI rows. |
| MuSR, SATA-Bench, HLE, BRIGHT | 32, 33, 45, 36 | No train split. |
| BPoMP, POP909-CL, cfcolor | 20, 22, 23 | No train split provably disjoint from the DI rows. |

The opt-in sources were smoke-tested at their full available size: ACOS 27,952, VAST 13,477, NLI4CT 1,700 and Humicroedit 10,141 rows. They are **not** in the default corpus.

## DI benchmarks with no training data in this corpus

- 20 BPoMP
- 21 Humicroedit (unless opted in)
- 22 POP909-CL (synthetic `synth_chords.py` rows in `data2` only; no POP909 data)
- 23 cfcolor (synthetic `synth_color.py` rows in `data2` only; no CFColor data)
- 32 MuSR (synthetic `synth_musr.py` rows in `data2` only; no MuSR data)
- 33 SATA-Bench (QASC-derived `synth_sata.py` rows in `data2` only)
- 36 BRIGHT (shares the ToolRet/BRIGHT yes/no relevance framing, so it is covered only indirectly)
- 38 ACOS, 41 VAST and 42 NLI4CT (unless opted in)
- 39 FinEntity (synthetic `synth_finentity.py` rows in `data2` only; no FinEntity data)
- 45 HLE
- 56 PhishNChips (synthetic `synth_phish.py` rows in `data2` only; no PhishNChips data)

## Synthetic generators

All generators are deterministic and seeded. None reads a DI file.

- **`synth_phish.py` (56), `synth_chords.py` (22), `synth_sata.py` (33), `synth_musr.py` (32), `synth_finentity.py`
  (39) and `synth_color.py` (23)** were added for it6 and are built into `C:\KeelWork\pro\data2` (372,803 train rows,
  3,796 holdout; every row of the original 330,232-row corpus plus the new ones). `validate.py` reports
  `PROBLEMS: none` on it.
  - `synth_finentity.py`: 6,000 rows. Short financial news texts about fictional companies; each company is mentioned
    once, in a sentence whose template fixes its sentiment (results, guidance, downgrades, lawsuits, neutral
    scheduling). Pair sentences ("X lost a customer to rival Y") give two entities opposite labels, so the label
    depends on the span. Framing and instruction text follow the kit's FinEntity builder, with real character offsets.
  - `synth_color.py`: 5,000 rows. CFColor's ratings have no stated licence and are not used. Each synthetic user has
    hidden taste weights over palette features (lightness, saturation, warmth, contrast, hue spread). The history is
    4–8 rated palettes (1–5, with noise); the two target palettes differ by at least 2 noiseless rating points.
  - `synth_musr.py`: 9,000 short narratives in MuSR's three task types, written and solved by the generator. Murder
    mysteries: each innocent suspect lacks exactly one of means, motive or opportunity (the killer has all three).
    Object placement: an object moves while people leave and return; the question is where a given person would look
    (their last sighting). Team allocation: skill and teamwork clues; the allocation with the unique best total
    wins. Framing follows the kit's MuSR normalizer (empty state, story plus question as instructions, keys A, B, C).
  - `synth_phish.py`: 3,000 template emails from fictional organizations. Each email produces three rows: `verdict`
    plus two of the other eight questions. The nine question texts are copied from `jev-phishing-bench/run_jev.py`,
    which the kit loads. Labels follow from how each email was built. Phishing emails link to a URL shortener, a
    free host, an IPFS gateway or a lookalike domain. Legitimate emails link to the organization's own site. About
    20% of legitimate emails are hard cases: a colleague's shared document on a public platform, the
    organization's CDN or marketing domain, or a private sender on webmail. About a quarter of phishing emails use
    a lookalike domain rather than free hosting.
  - `synth_chords.py`: a random key and a mostly diatonic progression drawn from the kit's chord templates, with
    about 10% chromatic chords and 4% rests. The progression is rendered as humanized bass, accompaniment (block,
    arpeggio, Alberti or pad) and melody notes, including non-chord tones and omitted fifths. The label is the
    generated chord at a grid beat (the kit's 2 + 4k grid), with notes within ±4 beats as context. The vocabulary
    and the 129-option criteria are imported from the kit (`adapters_creative.VOCAB`). Rendered prompts run
    4–6k tokens, so training needs `--max-len` ≥ 6144.
  - `synth_sata.py`: QASC train (CC BY 4.0, already a corpus source). The two supporting facts form the paragraph
    and the eight answer candidates are shuffled with our own seed. Each question yields one row for the correct
    candidate (`yes`) and one for a random distractor (`no`), using the kit's SATA instruction text. QASC has one
    correct answer per question, so unlike SATA-Bench these rows never have several correct candidates.

- **`synth_home.py` (9):**
  - Reuses only the kit's `home_appliance` resolver, its summary/choice helpers, its scenario list and its question texts.
  - The household names and room sets are new; an assertion checks they are disjoint from the kit's.
  - Each generated home is projected to about 3 single-question rows.
- **`synth_bbh.py` (58):** 11 BBH-style fixed-option task families:
  - boolean expressions, web of lies, navigate, shuffled objects, logical deduction, date understanding, hyperbaton, coloured objects, temporal sequences, penguins and geometric shapes.
  - Puzzles are generated and solved programmatically, with the kit's BBH option-key conventions.
- **`synth_crux.py` (43):**
  - 15 templates of small Python functions, executed for the gold output.
  - Distractors come from executing mutated variants, with 2–10 options.
- **`synth_cladder.py` (44):**
  - Chain, confounding, mediation, fork and direct graphs with nonsense variable names.
  - Marginal, correlation, ATE and ETT queries.
  - The answer is computed exactly, with a 0.02 margin threshold.

## Compliance notes and open questions

1. **Share-alike:** MNLI (part), SNLI, ARC and HoVer, including its Wikipedia text, are CC BY-SA. Decision (see `docs/licenses.md`, "Licence decisions"): keep, attribute, never redistribute the rows; the adapter stays Apache-2.0.
2. **Mixed licences:** MNLI's card lists "other" alongside the CC licences, for its OANC/fiction genres.
3. **Proxies:**
   - 12 ANLI uses MNLI/SNLI.
   - 25 GPQA and 57 MMLU-Pro use MedMCQA, CommonsenseQA, QASC and ARC.
   - 2 ToolRet uses glaive.
   - 1 BFCL uses ToolACE.

   None of these is the benchmark's own source.

   ARC train is the official train split. DI's ARC benchmarks (26/27, not in the 0.3 index) use the test split.
4. **When2Call:** only questions with a natural direct answer are kept. The missing request-for-info, cannot-answer and tool-call options are templated, so the gold is A only 34 times.
5. **New Yorker:** train and test contest disjointness relies on the dataset's own split design and was not independently verified.
6. **ChessBench:** only the TRAIN bag is used (a byte-range head). Opening positions with fullmove ≤ 10 are skipped.
7. **`synth_home.py`:** it is structurally close to the kit's test generator, but its homes, names and rooms are new.
8. **No forbidden inputs:** no DI rows, test/validation/dev splits or forbidden paths were read. `rows.guard()` refuses `di-work` request/release/normalized/selected/added/gsm8k paths, `di-samples` and `decision-index\suite-*`.
