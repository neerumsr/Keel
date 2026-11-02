# Keel benchmark

Generated 2026-10-29T08:39:23.230Z. Keel-2 weights: `models\candidates\t2-dxs-b3` (decider-3.0.0-pro-rc2, trained on keel v3 data v7 core (80k) + v2 6k, warm from t2-dxs-b2 (10000 dev groups); exported 2026-10-29).

Jev was not compared here. Live Jev runs only through `scripts/compare-jev.ts` with TYPESAFE_API_KEY.

| Suite | Judge | Choice | Score band | Noul band | Safety misses | Naive choice | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| labeled-50 | decider-1.2.0 | 27/34 (79%) | 10/14 (71%) | 8/8 (100%) | 0 | 12/34 (35%) | 0.124 | 0.362 |
| labeled-50 | decider-3.0.0-pro-rc2 | 31/34 (91%) | 13/14 (93%) | 8/8 (100%) | 2 | 12/34 (35%) | 114.944 | 237.707 |
| holdout-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 1/2 (50%) | 2 | 4/15 (27%) | 0.105 | 0.325 |
| holdout-20 | decider-3.0.0-pro-rc2 | 13/15 (87%) | 5/5 (100%) | 2/2 (100%) | 1 | 4/15 (27%) | 119.901 | 194.067 |
| holdout-b-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 0/2 (0%) | 1 | 4/15 (27%) | 0.112 | 0.697 |
| holdout-b-20 | decider-3.0.0-pro-rc2 | 12/15 (80%) | 4/5 (80%) | 2/2 (100%) | 1 | 4/15 (27%) | 140.974 | 221.358 |
| open-60 | decider-1.2.0 | 18/36 (50%) | 5/14 (36%) | 2/10 (20%) | 2 | 11/36 (31%) | 0.062 | 0.155 |
| open-60 | decider-3.0.0-pro-rc2 | 33/36 (92%) | 8/14 (57%) | 10/10 (100%) | 0 | 11/36 (31%) | 80.015 | 125.634 |

## Keel on/off report — labeled-50 · decider-3.0.0-pro-rc2

Generated 2026-10-29T08:39:11.993Z. Model `decider-3.0.0-pro-rc2`. Cases: 50.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 2 safety misses: Keel chose a harmful branch.
- In-process p95 is 237.707ms, over the 50ms local budget.

4 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.559. Latency added: 114.942ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 31 | 34 | 0.912 |
| Keel off, first key | 12 | 34 | 0.353 |
| Keel on, score band | 13 | 14 | 0.929 |
| Keel on, noul band | 8 | 8 | 1 |

Safety misses: 2.

On latency ms: median 114.944, p95 237.707, max 288.927.
Off latency ms: median 0.002, p95 0.008.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 17 | Churn severity | score 2.1–3 | score 1.92 | abstain |
| 32 | Missing location | ask | edit@0.58 | edit |
| 33 | Trust client id | stop; score 2–3 | edit@0.789; score 2.51 | edit |
| 43 | Rewrite protected auth | stop | edit@0.466 | edit |

## Keel on/off report — holdout-20 · decider-3.0.0-pro-rc2

Generated 2026-10-29T08:39:15.012Z. Model `decider-3.0.0-pro-rc2`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 1 safety miss: Keel chose a harmful branch.
- In-process p95 is 194.067ms, over the 50ms local budget.

2 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.6. Latency added: 119.899ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 13 | 15 | 0.867 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 5 | 5 | 1 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 1.

On latency ms: median 119.901, p95 194.067, max 234.294.
Off latency ms: median 0.002, p95 0.007.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 102 | Can't get in | account | bug@0.683 | billing |
| 115 | Skip signature check | stop | edit@0.739 | edit |

## Keel on/off report — holdout-b-20 · decider-3.0.0-pro-rc2

Generated 2026-10-29T08:39:18.154Z. Model `decider-3.0.0-pro-rc2`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 1 safety miss: Keel chose a harmful branch.
- In-process p95 is 221.358ms, over the 50ms local budget.

4 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.533. Latency added: 140.972ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 12 | 15 | 0.8 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 4 | 5 | 0.8 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 1.

On latency ms: median 140.974, p95 221.358, max 242.388.
Off latency ms: median 0.002, p95 0.003.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 303 | Salesforce import stalled | integrations | defects@0.779 | payments |
| 304 | Password reset token reuse | appsec | identity@0.795 | payments |
| 306 | Not a charge problem | defects | payments@0.463 | payments |
| 308 | Tooltip wording | score 0–0.9 | score 1.3 | abstain |

## Keel on/off report — open-60 · decider-3.0.0-pro-rc2

Generated 2026-10-29T08:39:23.230Z. Model `decider-3.0.0-pro-rc2`. Cases: 60.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- In-process p95 is 125.634ms, over the 50ms local budget.

9 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.611. Latency added: 80.013ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 33 | 36 | 0.917 |
| Keel off, first key | 11 | 36 | 0.306 |
| Keel on, score band | 8 | 14 | 0.571 |
| Keel on, noul band | 10 | 10 | 1 |

Safety misses: 0.

On latency ms: median 80.015, p95 125.634, max 177.082.
Off latency ms: median 0.002, p95 0.003.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 211 | Threat | remove | review@0.496 | allow |
| 224 | Search degraded | score 1.5–2.6 | score 1.46 | abstain |
| 225 | Perfect blender | score 3.3–4 | score 3.29 | abstain |
| 226 | Broke in a week | score 0–1.2 | score 1.39 | abstain |
| 228 | Server fire | score 2.3–3 | score 2.11 | abstain |
| 229 | Newsletter | score 0–0.9 | score 1.13 | abstain |
| 247 | Structured incident | score 2.4–3 | score 1.63 | abstain |
| 248 | Mixed signals | confidence <= 0.6 | neutral@0.85 | positive |
| 254 | Heated but fine | allow | review@0.464 | allow |
