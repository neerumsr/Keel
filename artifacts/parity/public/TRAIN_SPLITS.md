# Public TRAIN splits for Keel training

Owner: msd1-2. Converter: `training/public/to_groups.py`. Output: `training/data/public/<name>.jsonl`. Index: `training/data/public/READY.json`.

## How to use

```
python training/keel/train.py ... --extra-train training/data/public/boolq.jsonl@0.5 training/data/public/banking77.jsonl ...
```

- **Schema.** Rows use the same schema as `training/data/train.jsonl`: `family`, `state`, `question{type, instructions, criteria}`, `target`, `gold`. The family is `public_<name>`. `train.py` handles them through `to_pairs`, unchanged.
- **Targets.**
  - choice: label-smoothed one-hot (0.95 on gold, 0.05 spread over the other options).
  - noul: `[0.95, 0.05]` for yes and `[0.05, 0.95]` for no; gold 0 means yes.
  - score: a Gaussian centred on the continuous gold level, σ = 0.35.
- **Wire framing.** Rows use the same wire framing as the eval adapters in `training/public/registry.py`. Training on them therefore teaches the exact framing the public bench uses, so treat public-bench gains on these datasets as in-distribution. Report them that way.
- **Dedup.** For every dataset, train rows whose normalized text (lower-cased, whitespace-collapsed) matches any row in that dataset's full eval split or splits were dropped. This uses the full split, not only our 1,000-item sample. For the streamed datasets (civil_comments, esci), the check covers the streamed eval prefix that the bench samples from.
- **Caps.** At most 5,000 groups per dataset, stratified by label with a fixed seed. The flag `--max-per-dataset` changes the cap.
- **More than 12 labels.** For BANKING77 (77 labels) and CLINC150 (151), each group keeps the gold label plus 11 random negatives, to keep training cost bounded. The wire now accepts up to 255 options, so full-label groups are possible with `--max-options 255`, at about 6x to 13x the pairs per group.
- **Blind suite.** Nothing here was checked against the blind suite, which I may not open. The data sources are public academic datasets, not the blind suite's sources, but the parity owner should run the usual contamination check before a release model trains on them.

## Datasets

| Dataset | Source (train split) | License | Groups | Dropped (eval overlap) | Train OK? | Notes |
|---|---|---|---:|---:|---|---|
| boolq | google/boolq train | CC BY-SA 3.0 | 5,000 | 0 | Yes (share-alike) | noul; passage = state, question = instructions |
| winogrande | allenai/winogrande winogrande_xl train | CC BY 4.0 | 5,000 | 0 | Yes | choice option_a / option_b |
| mnli_m | nyu-mll/glue mnli train | OANC + CC BY-SA 3.0 parts | 5,000 | 0 | Yes (attribute) | 3-way choice. keel-2 already saw about 6k MNLI train pairs in NLI form. |
| banking77 | PolyAI/banking77 train | CC BY 4.0 | 5,000 | 7 | Yes | 12-option subsets |
| clinc150 | clinc/clinc_oos plus train | CC BY 3.0 | 5,000 | 2 | Yes | 12-option subsets, includes `oos` |
| hellaswag | Rowan/hellaswag train | MIT | 5,000 | 25 | Yes | 4 endings |
| arc_easy | allenai/ai2_arc ARC-Easy train | CC BY-SA 4.0 | 2,243 | 8 | Yes (share-alike) | whole split |
| arc_challenge | allenai/ai2_arc ARC-Challenge train | CC BY-SA 4.0 | 1,113 | 6 | Yes (share-alike) | whole split |
| stsb | nyu-mll/glue stsb train | mixed sources, CC BY-SA annotations | 5,000 | 6 | Yes (share-alike; check sources before release) | 6-level score |
| civil_comments | google/civil_comments train (stream prefix) | CC0 | 5,000 | 1,319 (short duplicate comments) | Yes | noul toxic ≥ 0.5, class-balanced |
| esci | tasksource/esci train (stream prefix, US) | Apache 2.0 | 5,000 | 0 (ESCI splits by query) | Yes | 4-level score I < C < S < E |

**Evaluation only. Never train on these:**
- ANLI: CC BY-NC.
- emotion: research and educational use only.
- AG News: non-commercial terms.
- SST-2, RTE, MRPC: unclear or research-only licenses.
- MMLU: no in-domain train split.

Total: **48,356 groups in 11 files** (READY.json `"complete": true`, written 2026-10-28 ~21:55). READY.json carries the authoritative counts.
