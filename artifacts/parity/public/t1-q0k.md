# Keel public benchmarks — `t1-q0k`

Generated 2026-10-29T05:36:20.302Z (wire LIMITS.choiceOptions = 255) by `scripts/keel-public-bench.ts` (production path: tryParse → neuralWeights → projectWeights). Model: `models\candidates\t1-q0k` (decider-3.0.0-rc.t1-q0k).

**MSD1 per-benchmark numbers do not exist publicly.** Microsoft reports only an aggregate: 83.5% average accuracy over 36 undisclosed benchmarks / 147,137 questions (vendor-reported; see `artifacts/parity/msd1/benchmarks.md`). The "MSD1" column therefore shows "n/p" (not published) and no delta can be computed per dataset. The Jev column is third-party: Decision Index board, Jev 1.14, different sample, prompts and sometimes metric (shown) — indicative only.

Accuracy: choice = argmax option; noul = P(yes) ≥ 0.5; score = round(expected level) == round(gold). CI = Wilson 95%. Samples are stratified, ≤1000 per dataset (civil_comments class-balanced). Prompt framing is ours (MSD1's is unpublished); see `training/public/registry.py`.

| Dataset | Type | n | Keel acc % (95% CI) | Majority % | Keel macro-F1 % | ECE | MSD1 (vendor) | Δ vs MSD1 | Jev 1.14 (DI, 3rd-party) | p50 ms | Notes |
|---|---|---:|---|---:|---:|---:|---|---|---|---:|---|
| ag_news | choice | 1000 | 76.8 (74.1–79.3) | 25.0 | 75.9 | 0.081 | n/p | n/a | — | 28.3 |  |
| emotion | choice | 1000 | 56.6 (53.5–59.6) | 34.8 | 47.5 | 0.169 | n/p | n/a | — | 21.9 |  |
| mnli_m | choice | 1000 | 37.7 (34.7–40.7) | 35.5 | 37.2 | 0.226 | n/p | n/a | — | 20.5 | Keel-2 training replayed MNLI train pairs (NLI form); matched validation not used in training. |
| anli | choice | 1000 | 36.7 (33.8–39.7) | 33.4 | 33.2 | 0.211 | n/p | n/a | 74.3 (macro-F1) | 30.8 | R1+R2+R3 test pooled (3,200), stratified sample. |
| banking77 | choice | 1000 | 46.0 (42.9–49.1) | 1.3 | 46.1 | 0.090 | n/p | n/a | 79.9 (macro-F1) | 175.0 | 77 options in one choice question (wire limit is now 255). |
| clinc150 | choice | 1000 | 41.7 (38.7–44.8) | 18.2 | 45.0 | 0.043 | n/p | n/a | 90.3 (macro-F1) | 353.9 | 151 options (incl. oos) in one choice question (wire limit is now 255). |
| winogrande | choice | 1000 | 50.4 (47.3–53.5) | 50.4 | 48.9 | 0.242 | n/p | n/a | 91.1 (accuracy) | 11.8 | Test labels hidden; validation used. |
| mmlu | choice | 1000 | 26.5 (23.9–29.3) | 27.4 | 26.5 | 0.294 | n/p | n/a | 91.7 (accuracy) | 25.7 | Stratified by subject. |
| boolq | noul | 1000 | 67.2 (64.2–70.0) | 62.2 | 58.7 | 0.114 | n/p | n/a | — | 27.4 | Test labels hidden; validation used. Long passages truncated by Keel's token window. Brier 0.226, predicted-yes 83.2% |
| rte | noul | 277 | 63.9 (58.1–69.3) | 52.7 | 58.4 | 0.188 | n/p | n/a | — | 16.1 | All 277 validation items. Brier 0.265, predicted-yes 83.8% |
| mrpc | noul | 1000 | 51.0 (47.9–54.1) | 66.5 | 51.0 | 0.170 | n/p | n/a | — | 20.2 | Brier 0.294, predicted-yes 35.7% |
| sst2 | choice | 872 | 79.5 (76.7–82.0) | 50.9 | 79.4 | 0.140 | n/p | n/a | — | 11.4 | GLUE test labels hidden; validation used. |
| hellaswag | choice | 1000 | 29.2 (26.5–32.1) | 25.7 | 29.2 | 0.360 | n/p | n/a | 94.3 (accuracy) | 37.7 | Test labels hidden; validation used. |
| arc_easy | choice | 1000 | 33.1 (30.3–36.1) | 26.7 | 33.0 | 0.231 | n/p | n/a | 99.3 (accuracy) | 18.0 |  |
| arc_challenge | choice | 1000 | 24.4 (21.8–27.2) | 26.6 | 24.0 | 0.311 | n/p | n/a | 97.6 (accuracy) | 20.0 |  |
| stsb | score | 1000 | 17.9 (15.6–20.4) | 23.1 | 8.9 | 0.339 | n/p | n/a | — | 33.1 | GLUE test labels hidden; validation used. Gold level = round(similarity). argmax acc 18.3, within-1 38.9, Spearman 0.111, argmax macro-F1 12.6 |
| civil_comments | noul | 1000 | 61.5 (58.4–64.5) | 50.0 | 60.3 | 0.197 | n/p | n/a | — | 16.4 | Toxic = toxicity >= 0.5. Class-balanced 50/50 sample (natural rate ~8%) from first 60k test rows. Brier 0.261, predicted-yes 67.1% |
| esci | score | 1000 | 15.1 (13.0–17.5) | 55.4 | 13.5 | 0.403 | n/p | n/a | 57.2 (macro-F1) | 27.5 | US locale; stream prefix of the test split; ordinal levels I<C<S<E. argmax acc 13.8, within-1 33.3, Spearman -0.009, argmax macro-F1 13.7 |

Unweighted mean accuracy over the 18 production-supported datasets: **45.3%**. This is NOT comparable to MSD1's 83.5% (different, undisclosed benchmark set and prompts).

Split by exposure to `training/data/public` train groups: datasets with public train groups (11; in-distribution for any model trained on them) mean **38.6%**; eval-only datasets (7: ag_news, emotion, anli, mmlu, rte, mrpc, sst2) mean **55.9%**.

Note (msd1-2): t1-q0k uses the t1-q0 graph with keel-2's calibration, as an ablation (candidates.md); it is not a trained candidate. Mean 45.3 vs keel-2 42.8.
