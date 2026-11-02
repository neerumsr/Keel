# Microsoft Decision 1 (MSD1): published benchmark claims

Compiled by msd1-2 on 2026-10-28. Every MSD1 number below is **vendor-reported** by Microsoft unless it says otherwise. Keel's own results are in `artifacts/parity/public/<model>.md`.

## TL;DR

- Microsoft reports an **83.5% average accuracy over 36 benchmarks / 147,137 questions** ("blind from training"). It has **not published the list of the 36 benchmarks, per-benchmark scores, prompts, or sampling**. As of 2026-10-28 I found no model card, tech report, paper, Hugging Face page or OpenRouter page with that breakdown.
- So MSD1 can only be compared with Keel **in aggregate**. No per-dataset delta against MSD1 is possible, and our public-suite average does not measure the same thing as 83.5% (different datasets and prompts).
- A third-party measurement exists: JevBench measured MSD1 at intelligence 57.2 and calibration 84.4 on its own 1,500-item suite.
- Jev 1.14 per-benchmark numbers on public datasets come from the third-party Decision Index (DI) board. Our runner uses them as the comparison column where the datasets overlap.

## 1. Vendor-reported (Microsoft)

Source: the announcement, https://commandline.microsoft.com/microsoft-decision-1-model-foundry/. The URL given in the task brief (`/posts/introducing-microsoft-decision-1`) returns 404. I decoded the chart widgets embedded in the page and saved them to `artifacts/parity/msd1/source/widget1.html` … `widget6.html`. Marktechpost cites the same chart via a Satya Nadella post (x.com/satyanadella/status/2108627923888754862).

| Model | Avg accuracy, 36 benchmarks | Calibration | p50 latency |
|---|---:|---:|---:|
| **Microsoft Decision 1** | **83.5** | 92.2 | 85 ms (p95 125 ms) |
| Jev 1.13.0 | 82.3 | 93.7 | 240 ms |
| Quyet-1.0-Large | 81.9 | 93.1 | 380 ms |
| Surogate Rune 26B-A4B | 79.7 | 91.8 | 380 ms |
| GPT-6 Luna Decisions | 79.4 | 89.9 | 300 ms |
| deck-31B | 77.8 | 83.5 | 400 ms |
| H2O-Lightning-4B v1.1 | 77.2 | 91.8 | 210 ms |
| Strands-Decider 2B | 54.8 (only 23 of 36 benchmarks) | — | — |
| GPT-6 Sol (latency reference) | — | — | 3,010 ms |

Microsoft's numbers for the other models are also vendor-reported, meaning Microsoft measured them. Microsoft's text notes that MSD1 is third on calibration: 1.5 points behind Jev and 0.9 behind Quyet.

Other claims from the same page, none with a per-item breakdown:
- 147,137 questions across 36 benchmarks, "blind from training".
- 1.3% decision flips across 8 kinds of perturbation (robustness).
- A safety evaluation of 5,250 requests across 11 safety benchmarks. No aggregate score is shown.
- Xbox case studies: Racing Title, 753 reviews; FPS, 341; Studio Livestream, 1,030 chat messages. Only speed and cost charts are given; these are private data with no accuracy.

Secondary write-ups repeat the aggregates without a benchmark list: Microsoft Learn (Foundry "Decision models" docs), Marktechpost and AIModelReport.

**Missing (searched 2026-10-28):** the per-benchmark list, per-benchmark accuracy, prompt templates, a model card with evaluation details, and a tech report or paper. If Microsoft publishes these, add them here and wire them into `scripts/keel-public-bench.ts` (column "MSD1 (vendor)").

## 2. Third-party measurement of MSD1 (JevBench)

Source: https://benchmarkheaven.com/jev-models/microsoft-decision-1 (JevBench v1.7.15, measured 2026-10-10, 1,500 items). JevBench is published by TypeSafe (Jev's vendor), so it is third-party for MSD1 but not neutral.

| Metric | MSD1 |
|---|---:|
| Intelligence | 57.2 |
| Calibration | 84.4 |
| Speed | 81.4 |
| Cost | 61.5 |
| Capability | 70.8 |
| Composite | 69.1 |
| p50 / p95 latency | 0.479 s / 1.518 s |
| Cost | $0.019 per 1,000 decisions |

## 3. Closest public analogue: Decision Index (third-party, MIT)

https://github.com/apolinario/decision-index rebuilds a suite of about 37 public text benchmarks (about 110k scoreable requests in board version `decision-index-0.3`, generated 2026-10-28T19:32Z) from public sources. MSD1 is **not** on the board. Jev 1.14 is (lab run, 2026-10-14). The board data is saved at `artifacts/parity/msd1/source/di-index.json`.

Jev 1.14 raw scores on datasets that overlap our public suite. These are DI's numbers, with DI's sampling, prompts and metric, so they are not directly comparable to our 1,000-item samples:

| DI benchmark (id) | Metric | Jev 1.14 raw |
|---|---|---:|
| BANKING77 (4) | macro-F1 | 79.9 |
| CLINC150+OOS (5) | macro-F1 | 90.3 |
| ANLI (12) | macro-F1 | 74.3 |
| MMLU (24) | accuracy | 91.7 |
| ARC-Easy (26) | accuracy | 99.3 |
| ARC-Challenge (27) | accuracy | 97.6 |
| WinoGrande (28) | accuracy | 91.1 |
| HellaSwag (29) | accuracy | 94.3 |
| Amazon ESCI (37) | macro-F1 | 57.2 |

If jev-2 finds vendor-reported Jev numbers on these datasets, they take precedence for the "Jev" column. As of 21:51, `artifacts/parity/jev/benchmarks.md` (jev-2) confirms that TypeSafe publishes **no** standard public-benchmark table. Their stated reason is https://typesafe.ai/blog/antibenchmaxxing. The DI numbers above are therefore the only per-dataset Jev numbers available, and they are third-party.

## 4. What we run instead

`training/public/registry.py` defines 18 public datasets that MSD1's undisclosed suite plausibly contains:
- sentiment, topic and emotion classification;
- NLI (MNLI, ANLI, RTE);
- intent (BANKING77, CLINC150);
- commonsense and knowledge multiple choice (WinoGrande, HellaSwag, ARC, MMLU);
- BoolQ, paraphrase (MRPC), toxicity (Civil Comments);
- graded similarity and relevance (STS-B, ESCI).

The prompt framing is ours, because Microsoft's is unpublished: state is the text, instructions are the task question, and criteria are the labels. `scripts/keel-public-bench.ts` scores up to 1,000 stratified test items per dataset through Keel's production path.

## Verified third-party measurement: JevBench (fetched 2026-10-29)

Source: https://benchmarkheaven.com/jev-models/microsoft-decision-1-r2. Note that JevBench is published by TypeSafe, Jev's vendor.

- **Run:** Microsoft-Decision-1, updated weights (Oct 2026). JevBench v1.7.23, method v1.7 (10 s rule), measured 2026-10-28.
- **Scores:** intelligence 67.1, calibration 92.5, speed 89.3, cost 66.4, composite 77.0. **Unranked**: the 27 Oct draw is not yet equated to the reference scale.
- **Latency:** p50 0.319 s, p95 0.364 s, on Azure Foundry (Sweden Central).
- **Errors:** 4 of 1,493 requests were refused for exceeding the 32,768-token context.
- **Cost:** about USD 0.013 per 1,000 decisions.
- **Comparability:** this scale is NOT comparable to the Decision Index public_skill scale. MSD1 is not on the Decision Index; our DI target of ~62 for MSD1 is an estimate (MSD1 chart delta +1.2 over Jev 1.13, applied to Jev 1.14's DI 60.70).
