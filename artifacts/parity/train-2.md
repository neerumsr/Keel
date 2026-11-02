# train-2 lab notebook (larger line: teacher, Keel-3-Pro, distillation)

Owner: train-2. Rules: CONTRACT.md. I never open `eval-blind*.ts` or `artifacts/parity/blind/**`.
Held-out fixtures (holdout-20, holdout-b-20, open-60 via `training/data/evals.json`) are only *reported*
(raw-margin accuracy, no temperature/blend); selection uses dev loss (v3 dev).

## Hand-off (read this first)
- **Best teacher checkpoint (final):** `training/runs/t2-dxs-b3/best` (HF format, DeBERTa-v3-xsmall 70M, no token_type_ids; train.py `--teacher` loads it with its own tokenizer). v7-dev loss 0.957 (B2 on same sample 1.034; keel-2 ~1.69 on v3.3 dev).
- **Teacher soft labels (READY):** `training/data/v3/teacher_t2dxs_v7core.jsonl` — 35,354 groups of v7 core.jsonl, 300/family × 122 families (gate/gate_yn/gate_menu/security incl.), from t2-dxs-b3 at max-len 192. One line per group:
  `{"key": <group_key>, "margins": [m_1..m_n], "family": ...}` where `margins` = entail − not_entail logits in hypothesis order and
  `group_key` = `t2_train.group_key(row)` (state_text + "\t" + sorted-key JSON of question; NLI rows: `"nli\t"+state+"\t"+pair`).
  `python training/keel/t2_train.py --teacher-labels <file> --kd 0.5 --kd-temp 2` consumes it; groups without a label are skipped for KD.

## Tools (new files)
- `training/keel/t2_train.py` — imports loss/eval from train.py; adds multi-file mix (`path::max_groups`), wall-clock budget
  (`--minutes`, `--sec-per-step` sizes the LR schedule), `--freeze-embeddings`, `--freeze-layers N`, length-bucketed batches,
  precomputed-teacher KD (`--teacher-labels`), raw-margin fixture check at every eval.
- `training/keel/t2_export.py` — generic HF→ONNX export (DeBERTa-v3 has no token_type_ids; Node loader feeds by
  session input name, so **no loader change needed**), int8 via export.py's `quantize`, dev-only calibration,
  python latency, int8-vs-fp32 argmax-flip count in keel.json.

## Environment reality (2026-10-28 ~21:00)
Machine is at 100% CPU (other users/agents). DeBERTa-v3-xsmall training: 3.7 s/step (64 pairs) when I started,
15–20 s/step under contention (~3–4 pairs/s). DeBERTa-v3-base would be ~4× slower → not trainable in a 90-min run here;
downloaded `MoritzLaurer/deberta-v3-base-zeroshot-v2.0-c` (MIT) as a zero-shot option only.

## Finding T2-1 — int8 quantization of DeBERTa-v3
Zero-shot DeBERTa-v3-xsmall, 150 dev choice groups, argmax flips vs fp32 ONNX:
| quant config | flips/150 | mean max|Δmargin| | MB |
|---|---:|---:|---:|
| dynamic per-tensor, MatMulConstBOnly | 26 | 1.47 | 87 |
| per-channel (any variant, incl. train-1 "mixed") | 96–101 | 6.1 | 87–109 |
| per-tensor, FFN-out + head + rel-pos projections fp32 | 11 | 0.77 | 108 |
**Per-channel int8 is broken for DeBERTa-v3 in ORT 1.20 — do not use `--quant mixed` on DeBERTa.** fp32 ONNX latency ≈ int8 here.

## Runs
| run | base | data | steps | min | v3-dev loss | fixtures raw acc (hold / holdB / open) | notes |
|---|---|---|---:|---:|---:|---|---|
| zero-shot | deberta-v3-xsmall-zeroshot-v1.1 | — | 0 | — | — | .45 / .36 / .45 (safety 1/3/0) | reference |
| t2-dxs-a | dxs | v2 train | ~90 | 30 | — | — | killed: v3 landed + schedule mis-sized for contention |
| keel-2 ref (xd6-v2 torch fp32) | xd6 | v1+v2 | 3292 | 30 | 1.955 (choice .48, noul .56, score MAE 1.17) | .77 / .77 / .57 (safety 1/2/1) | reference, same eval code |
| t2-dxs-b1 | dxs zero-shot | v3 40k + v2 8k + public 10×≤1.5k (62.6k groups) | 425 | 37 | 1.291 (choice .60, noul .67, MAE 1.10) | .64 / .55 / .73 (safety 3/3/0) | freeze emb + 4 layers, lr 4e-5; 5.2 s/step once load dropped. Beats keel-2 on v3 dev + open, loses on holdout (v2-like families) |

## ~22:30 — data v3 version 3 landed (`training/data/v3/v3/`, core.jsonl 80k family-balanced incl. public+MNLI). B2 (on v3 v1) killed at step 175 and restarted on core.jsonl + 10k v2, max-len 192, dev = v3/v3/dev (600 sample). Dev numbers from here on are on **v3.3 dev**, not comparable with B1's row.
| keel-2 ref on **v3.3 dev** | xd6 | — | — | — | 1.690 (choice .51, noul .61, MAE 1.05) | .77 / .77 / .57 (1/2/1) | same 600-group sample as B2 evals |
| t2-dxs-b1 on **v3.3 dev** | | | | | 1.191 (choice .66, noul .65, MAE 1.08) | .64 / .55 / .73 (3/3/0) | |
| t2-dxs-b2 | t2-dxs-b1 | v3.3 core 80k + v2 10k, max-len 192 | 960 | 76 | **1.018** (choice .77, noul .79, MAE 0.90) on v3.3 dev | .82 / .68 / .85 (1/2/0) | freeze emb + 2 layers, lr 3e-5, 4.8 s/step. Best teacher so far. |

## 2026-10-29 01:00–01:40 — B3, labels, Pro RC2
| run | init | data | steps | min | best dev loss | raw fixtures h/hb/open (safety) | notes |
|---|---|---|---:|---:|---:|---|---|
| t2-dxs-b3 | t2-dxs-b2 | v7 core 80k + v2 6k, max-len 192, lr 2.5e-5, freeze emb+2L | 980 | 70 | **0.957** (v7 dev 600; choice .80, noul .84, MAE .79) | .86 / .77 / .88 (1/2/0) | B2 on same v7 dev: 1.034. Best teacher. |

- Labels: `t2_label.py` 35,354 groups in 36 min (16 groups/s, 9 threads).
- Export `models/candidates/t2-dxs-b3` (decider-3.0.0-pro-rc2, pt-mixed, max-len 192). Calibration note: v7 dev_ood has only score/noul (no choice) → a dev_ood-only calibration fit choice T on nothing (T=0.4); re-exported on v7 dev + dev_ood concatenated: T choice 1.1 / score 1.4 / noul 1.6, abstain 0.152; 25/300 int8 argmax flips. Python p50/p95 77/150 ms at 3 threads (loaded box).
- keel-bench (`artifacts/parity/t2-dxs-b3-bench`): h20 choice 13/15 score 5/5 noul 2/2 s1; hb20 12/15 4/5 2/2 s1; open 33/36 8/14 10/10 s0; labeled-50 s2. Improves on B2 (hb 10→12, safety hb 2→1) but still not G1-clean and fails Pro latency.
- 6-layer layer-drop (`t2_prune.py`, keep 0,2,4,6,8,11) of B2 untrained: dev loss 1.59 / choice .34 → needs a KD round (~2× faster than 12L); not run (out of time). Suggested next: `t2_train --base <pruned b3> --teacher-labels training/data/v3/teacher_t2dxs_v7core.jsonl --kd 0.5`.

## Round 2 (2026-10-29 01:41 →, 8 threads)
- b3 latency re-measured in-process (keel-bench, idle box ~20–35% load), threads in keel.json 3→4: p50/p95 per case — labeled-50 74/173, h20 100/165, hb20 114/156, open-60 58/93 ms. Still ~2–3× over the 60 ms Pro gate → 12L DeBERTa-xsmall cannot be Pro on CPU; need the 6L student.
- Pro-fast: `t2_prune.py` b3 → `training/runs/t2-dxs6-init` (keep layers 0,2,4,6,8,11; fixtures@0 .27/.32/.33). KD run `t2-kd6-a`: v7 core 80k + v2 4k, teacher labels (35,109 unique keys) kd 0.6 T=2, lr 6e-5, freeze emb only, 8 threads, ~3.6 s/step, 85 min.
