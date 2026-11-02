# Keel public benchmarks — `keel-2`

Generated 2026-10-29T05:05:22.657Z (wire LIMITS.choiceOptions = 255) by `scripts/keel-public-bench.ts` (production path: tryParse → neuralWeights → projectWeights). Model: `models\keel-2` (decider-2.0.0).

**MSD1 per-benchmark numbers do not exist publicly.** Microsoft reports only an aggregate: 83.5% average accuracy over 36 undisclosed benchmarks / 147,137 questions (vendor-reported; see `artifacts/parity/msd1/benchmarks.md`). The "MSD1" column therefore shows "n/p" (not published) and no delta can be computed per dataset. The Jev column is third-party: Decision Index board, Jev 1.14, different sample, prompts and sometimes metric (shown) — indicative only.

Accuracy: choice = argmax option; noul = P(yes) ≥ 0.5; score = round(expected level) == round(gold). CI = Wilson 95%. Samples are stratified, ≤1000 per dataset (civil_comments class-balanced). Prompt framing is ours (MSD1's is unpublished); see `training/public/registry.py`.

| Dataset | Type | n | Keel acc % (95% CI) | Majority % | Keel macro-F1 % | ECE | MSD1 (vendor) | Δ vs MSD1 | Jev 1.14 (DI, 3rd-party) | p50 ms | Notes |
|---|---|---:|---|---:|---:|---:|---|---|---|---:|---|
| ag_news | choice | 1000 | 79.8 (77.2–82.2) | 25.0 | 79.5 | 0.070 | n/p | n/a | — | 25.3 |  |
| emotion | choice | 1000 | 47.3 (44.2–50.4) | 34.8 | 36.5 | 0.107 | n/p | n/a | — | 20.4 |  |
| mnli_m | choice | 1000 | 35.4 (32.5–38.4) | 35.5 | 34.0 | 0.297 | n/p | n/a | — | 19.3 | Keel-2 training replayed MNLI train pairs (NLI form); matched validation not used in training. |
| anli | choice | 1000 | 34.7 (31.8–37.7) | 33.4 | 32.1 | 0.300 | n/p | n/a | 74.3 (macro-F1) | 27.9 | R1+R2+R3 test pooled (3,200), stratified sample. |
| banking77 | choice | 1000 | 42.6 (39.6–45.7) | 1.3 | 42.5 | 0.126 | n/p | n/a | 79.9 (macro-F1) | 161.2 | 77 options in one choice question (wire limit is now 255). |
| clinc150 | choice | 1000 | 38.3 (35.3–41.4) | 18.2 | 44.2 | 0.022 | n/p | n/a | 90.3 (macro-F1) | 320.5 | 151 options (incl. oos) in one choice question (wire limit is now 255). |
| winogrande | choice | 1000 | 48.6 (45.5–51.7) | 50.4 | 47.0 | 0.252 | n/p | n/a | 91.1 (accuracy) | 10.7 | Test labels hidden; validation used. |
| mmlu | choice | 1000 | 26.1 (23.5–28.9) | 27.4 | 26.0 | 0.260 | n/p | n/a | 91.7 (accuracy) | 22.0 | Stratified by subject. |
| boolq | noul | 1000 | 62.9 (59.9–65.8) | 62.2 | 46.2 | 0.190 | n/p | n/a | — | 24.9 | Test labels hidden; validation used. Long passages truncated by Keel's token window. Brier 0.263, predicted-yes 93.5% |
| rte | noul | 277 | 59.2 (53.3–64.8) | 52.7 | 53.4 | 0.150 | n/p | n/a | — | 16.6 | All 277 validation items. Brier 0.265, predicted-yes 82.7% |
| mrpc | noul | 1000 | 49.5 (46.4–52.6) | 66.5 | 48.4 | 0.171 | n/p | n/a | — | 18.1 | Brier 0.293, predicted-yes 48.2% |
| sst2 | choice | 872 | 74.3 (71.3–77.1) | 50.9 | 73.5 | 0.148 | n/p | n/a | — | 10.8 | GLUE test labels hidden; validation used. |
| hellaswag | choice | 1000 | 29.5 (26.8–32.4) | 25.7 | 29.4 | 0.312 | n/p | n/a | 94.3 (accuracy) | 37.2 | Test labels hidden; validation used. |
| arc_easy | choice | 1000 | 32.9 (30.1–35.9) | 26.7 | 32.9 | 0.195 | n/p | n/a | 99.3 (accuracy) | 17.0 |  |
| arc_challenge | choice | 1000 | 23.5 (21.0–26.2) | 26.6 | 23.3 | 0.302 | n/p | n/a | 97.6 (accuracy) | 19.0 |  |
| stsb | score | 1000 | 21.6 (19.2–24.3) | 23.1 | 10.2 | 0.308 | n/p | n/a | — | 31.4 | GLUE test labels hidden; validation used. Gold level = round(similarity). argmax acc 18.3, within-1 40.8, Spearman 0.098, argmax macro-F1 9.4 |
| civil_comments | noul | 1000 | 58.1 (55.0–61.1) | 50.0 | 56.6 | 0.181 | n/p | n/a | — | 15.7 | Toxic = toxicity >= 0.5. Class-balanced 50/50 sample (natural rate ~8%) from first 60k test rows. Brier 0.265, predicted-yes 68.7% |
| esci | score | 1000 | 6.8 (5.4–8.5) | 55.4 | 6.8 | 0.654 | n/p | n/a | 57.2 (macro-F1) | 25.7 | US locale; stream prefix of the test split; ordinal levels I<C<S<E. argmax acc 6.8, within-1 28.9, Spearman -0.118, argmax macro-F1 7.0 |

Unweighted mean accuracy over the 18 production-supported datasets: **42.8%**. This is NOT comparable to MSD1's 83.5% (different, undisclosed benchmark set and prompts).

Split by exposure to `training/data/public` train groups: the 11 datasets that have public train groups (in-distribution for any model trained on them) have a mean of **36.4%**. The 7 eval-only datasets (ag_news, emotion, anli, mmlu, rte, mrpc, sst2) have a mean of **53.0%**. keel-2 itself was not trained on these groups.

## Findings (msd1-2, written by hand after the 2026-10-28 run)

- **Clearly above the majority baseline:**
  - AG News: 79.8 (majority 25)
  - SST-2: 74.3 (majority 51)
  - BANKING77, 77-way: 42.6 (majority 1.3)
  - CLINC150, 151-way: 38.3 (majority 18)
  - emotion: 47.3 (majority 35)
  - civil_comments: 58.1 (balanced, majority 50)
  - RTE: 59.2 (majority 53)
- **At or below chance:**
  - MNLI and ANLI (about 35 on 3-way)
  - WinoGrande
  - MMLU
  - HellaSwag
  - ARC-Challenge and ARC-Easy
  - MRPC
  - BoolQ: answers "yes" 93.5% of the time.
  - STS-B: Spearman 0.10.
  - ESCI: almost never predicts "Exact"; Spearman −0.12, below the majority baseline.
  - These are reasoning and knowledge tasks where a 13M cross-encoder is expected to lose badly to 4B–30B decision models.
- **Comparison with Jev 1.14.** On the 9 overlapping datasets, using Decision Index numbers (third-party, with different samples and prompts), Keel-2 trails by 35–75 points.
- **Comparison with MSD1.** No per-dataset comparison is possible. Keel-2's unweighted mean here is 42.8% against MSD1's vendor-reported 83.5% on its own undisclosed 36-benchmark suite. The two numbers are not comparable, but the gap is clearly large.
- **MNLI is at chance even though keel-2 replayed MNLI train pairs.** Those pairs were in raw NLI form (premise, hypothesis). Through the wire, the statement sits inside the instruction ("How does the text relate to this statement: …? Answer: entailment. …"), and the NLI skill does not transfer to that framing. `training/data/public/mnli_m.jsonl` holds 5k groups in exactly this framing.
- **Latency.** p50 is 10–40 ms for questions with up to 12 options, and 160 ms (77 options) to 320 ms (151 options) for the intent sets, which scale linearly with option count. Measured on a box shared with trainers.
- **Contamination note.** Candidates trained on `training/data/public/*` see the same framing and the same datasets' train splits, deduplicated against these eval pools. Their gains on those 11 datasets are in-distribution: report them separately from the eval-only datasets (SST-2, AG News, emotion, ANLI, RTE, MRPC, MMLU).
