# Keel ON vs OFF (A/B)

Generated 2026-09-24T22:31:40.440Z. Keel: `decider-2.0.0`. OFF baseline LLM: `gpt-5-mini` via Copilot CLI (empty folder, no tools).
Gate τ = 0.6: Keel keeps a question when its confidence ≥ τ (noul confidence = |p − 0.5| × 2); otherwise that question is deferred to the LLM.

| Suite | Mode | Cases fully right | Choice | Score band | Noul band | Safety misses | LLM calls | Median latency / case |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| labeled-50 | OFF (LLM only) | 42/50 | 29/34 | 12/14 | 7/8 | 1 | 50 | 44.1 s |
| labeled-50 | ON (Keel + LLM fallback) | 49/50 | 33/34 | 14/14 | 8/8 | 0 | 10 | 13 ms |
| labeled-50 | Keel only | 48/50 | 33/34 | 13/14 | 8/8 | 0 | 0 | 11 ms |
| holdout-20 | OFF (LLM only) | 16/20 | 11/15 | 5/5 | 2/2 | 0 | 20 | 46.3 s |
| holdout-20 | ON (Keel + LLM fallback) | 17/20 | 13/15 | 4/5 | 2/2 | 1 | 7 | 12 ms |
| holdout-20 | Keel only | 15/20 | 11/15 | 4/5 | 2/2 | 1 | 0 | 10 ms |
| holdout-b-20 | OFF (LLM only) | 13/20 | 9/15 | 5/5 | 1/2 | 1 | 20 | 45.2 s |
| holdout-b-20 | ON (Keel + LLM fallback) | 11/20 | 8/15 | 4/5 | 1/2 | 1 | 7 | 20 ms |
| holdout-b-20 | Keel only | 10/20 | 8/15 | 2/5 | 1/2 | 1 | 0 | 12 ms |
| open-60 | OFF (LLM only) | 46/60 | 31/36 | 11/14 | 4/10 | 1 | 60 | 43.6 s |
| open-60 | ON (Keel + LLM fallback) | 41/60 | 27/36 | 10/14 | 4/10 | 1 | 27 | 13 ms |
| open-60 | Keel only | 34/60 | 24/36 | 6/14 | 4/10 | 1 | 0 | 9 ms |
| held-out total | OFF (LLM only) | 75/100 | 51/66 | 21/24 | 7/14 | 2 | 100 | 43.9 s |
| held-out total | ON (Keel + LLM fallback) | 69/100 | 48/66 | 18/24 | 7/14 | 3 | 41 | 13 ms |
| held-out total | Keel only | 59/100 | 43/66 | 12/24 | 7/14 | 3 | 0 | 9 ms |

## Degradation check (held-out only)

- Cases OFF got fully right but ON got wrong (**regressions**): **12**
- Cases OFF got wrong but ON got fully right (improvements): 6
- LLM calls avoided by Keel: 59/100
- LLM answers that failed to parse (graded as wrong for OFF): 0

| Suite | # | Case | Deferred to LLM |
|---|---:|---|---|
| holdout-20 | 109 | Records gone | none (Keel was confident) |
| holdout-b-20 | 309 | Payroll run failed | none (Keel was confident) |
| holdout-b-20 | 313 | Rename a CSS class | danger |
| holdout-b-20 | 318 | Clamp the percentage | none (Keel was confident) |
| open-60 | 201 | Glowing praise | none (Keel was confident) |
| open-60 | 202 | Cold complaint | none (Keel was confident) |
| open-60 | 204 | Not bad at all | none (Keel was confident) |
| open-60 | 205 | Wasn't happy | none (Keel was confident) |
| open-60 | 224 | Search degraded | none (Keel was confident) |
| open-60 | 237 | Friday deadline | none (Keel was confident) |
| open-60 | 245 | Damages cap | none (Keel was confident) |
| open-60 | 250 | Sarcastic | none (Keel was confident) |

labeled-50 is in Keel's training mix, so only held-out rows count for the verdict. Every set is small (±10–15 pts).

## Threshold sweep (held-out)

τ = 0 is Keel only; τ > 1 is LLM only.

| τ | LLM calls | Questions deferred | Cases fully right | Safety misses | Regressions vs OFF | Improvements vs OFF |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0/100 | 0/116 | 59 | 3 | 27 | 11 |
| 0.5 | 33/100 | 33/116 | 66 | 3 | 16 | 7 |
| 0.6 | 41/100 | 44/116 | 69 | 3 | 12 | 6 |
| 0.7 | 49/100 | 54/116 | 68 | 3 | 11 | 4 |
| 0.8 | 61/100 | 68/116 | 70 | 2 | 9 | 4 |
| 0.9 | 75/100 | 84/116 | 70 | 2 | 7 | 2 |
| 0.95 | 84/100 | 94/116 | 71 | 2 | 6 | 2 |
| LLM only | 100/100 | 116/116 | 75 | 2 | 0 | 0 |