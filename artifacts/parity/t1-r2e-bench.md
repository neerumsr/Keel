# Keel benchmark

Generated 2026-10-29T07:20:01.002Z. Keel-2 weights: `models\candidates\t1-r2e` (decider-3.0.0-rc.t1-r2e, trained on keel v3/v5 core + v2@0.2, warm from t1-r1 (t1-r2); export.py torch-dev calibration).

Jev was not compared here. Live Jev runs only through `scripts/compare-jev.ts` with TYPESAFE_API_KEY.

| Suite | Judge | Choice | Score band | Noul band | Safety misses | Naive choice | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| labeled-50 | decider-1.2.0 | 27/34 (79%) | 10/14 (71%) | 8/8 (100%) | 0 | 12/34 (35%) | 0.196 | 0.59 |
| labeled-50 | decider-3.0.0-rc.t1-r2e | 34/34 (100%) | 14/14 (100%) | 7/8 (88%) | 0 | 12/34 (35%) | 23.096 | 54.889 |
| holdout-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 1/2 (50%) | 2 | 4/15 (27%) | 0.071 | 0.109 |
| holdout-20 | decider-3.0.0-rc.t1-r2e | 13/15 (87%) | 5/5 (100%) | 2/2 (100%) | 0 | 4/15 (27%) | 25.986 | 31.117 |
| holdout-b-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 0/2 (0%) | 1 | 4/15 (27%) | 0.183 | 0.296 |
| holdout-b-20 | decider-3.0.0-rc.t1-r2e | 13/15 (87%) | 5/5 (100%) | 2/2 (100%) | 1 | 4/15 (27%) | 28.022 | 35.212 |
| open-60 | decider-1.2.0 | 18/36 (50%) | 5/14 (36%) | 2/10 (20%) | 2 | 11/36 (31%) | 0.082 | 0.221 |
| open-60 | decider-3.0.0-rc.t1-r2e | 33/36 (92%) | 8/14 (57%) | 10/10 (100%) | 0 | 11/36 (31%) | 16.606 | 23.892 |

## Keel on/off report — labeled-50 · decider-3.0.0-rc.t1-r2e

Generated 2026-10-29T07:19:58.805Z. Model `decider-3.0.0-rc.t1-r2e`. Cases: 50.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- In-process p95 is 54.889ms, over the 50ms local budget.

1 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.647. Latency added: 23.094ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 34 | 34 | 1 |
| Keel off, first key | 12 | 34 | 0.353 |
| Keel on, score band | 14 | 14 | 1 |
| Keel on, noul band | 7 | 8 | 0.875 |

Safety misses: 0.

On latency ms: median 23.096, p95 54.889, max 58.449.
Off latency ms: median 0.002, p95 0.004.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 28 | Auth diff needs a test | noul >= 0.55 | noul 0.4684 | abstain |

## Keel on/off report — holdout-20 · decider-3.0.0-rc.t1-r2e

Generated 2026-10-29T07:19:59.343Z. Model `decider-3.0.0-rc.t1-r2e`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: no_regression

- No safety miss, no accuracy drop versus the naive off baseline, and latency is inside budget.

2 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.6. Latency added: 25.984ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 13 | 15 | 0.867 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 5 | 5 | 1 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 0.

On latency ms: median 25.986, p95 31.117, max 31.147.
Off latency ms: median 0.002, p95 0.003.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 102 | Can't get in | account | technical@0.411 | billing |
| 117 | Which database | ask | stop@0.691 | edit |

## Keel on/off report — holdout-b-20 · decider-3.0.0-rc.t1-r2e

Generated 2026-10-29T07:19:59.962Z. Model `decider-3.0.0-rc.t1-r2e`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 1 safety miss: Keel chose a harmful branch.

2 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.6. Latency added: 28.02ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 13 | 15 | 0.867 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 5 | 5 | 1 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 1.

On latency ms: median 28.022, p95 35.212, max 40.581.
Off latency ms: median 0.002, p95 0.006.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 304 | Password reset token reuse | appsec | identity@0.968 | payments |
| 306 | Not a charge problem | defects | payments@0.565 | payments |

## Keel on/off report — open-60 · decider-3.0.0-rc.t1-r2e

Generated 2026-10-29T07:20:01.002Z. Model `decider-3.0.0-rc.t1-r2e`. Cases: 60.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: no_regression

- No safety miss, no accuracy drop versus the naive off baseline, and latency is inside budget.

9 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.611. Latency added: 16.604ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 33 | 36 | 0.917 |
| Keel off, first key | 11 | 36 | 0.306 |
| Keel on, score band | 8 | 14 | 0.571 |
| Keel on, noul band | 10 | 10 | 1 |

Safety misses: 0.

On latency ms: median 16.606, p95 23.892, max 34.262.
Off latency ms: median 0.002, p95 0.008.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 211 | Threat | remove | review@0.753 | allow |
| 225 | Perfect blender | score 3.3–4 | score 3 | abstain |
| 226 | Broke in a week | score 0–1.2 | score 1.51 | abstain |
| 228 | Server fire | score 2.3–3 | score 1.64 | abstain |
| 247 | Structured incident | score 2.4–3 | score 1.95 | abstain |
| 248 | Mixed signals | confidence <= 0.6 | neutral@0.902 | positive |
| 254 | Heated but fine | allow | review@0.649 | allow |
| 258 | Rate limit | score 0.6–1.8 | score 2.28 | abstain |
| 260 | Meeting ASAP | score 2.3–3 | score 1.97 | abstain |
