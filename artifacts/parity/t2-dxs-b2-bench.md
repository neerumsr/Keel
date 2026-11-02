# Keel benchmark

Generated 2026-10-29T06:53:16.176Z. Keel-2 weights: `models\candidates\t2-dxs-b2` (decider-3.0.0-pro-rc, trained on keel v3.3 core + v2 (train-2 b1->b2) (1415 dev groups); exported 2026-10-28).

Jev was not compared here. Live Jev runs only through `scripts/compare-jev.ts` with TYPESAFE_API_KEY.

| Suite | Judge | Choice | Score band | Noul band | Safety misses | Naive choice | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| labeled-50 | decider-1.2.0 | 27/34 (79%) | 10/14 (71%) | 8/8 (100%) | 0 | 12/34 (35%) | 0.196 | 0.661 |
| labeled-50 | decider-3.0.0-pro-rc | 29/34 (85%) | 12/14 (86%) | 8/8 (100%) | 2 | 12/34 (35%) | 121.661 | 223.861 |
| holdout-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 1/2 (50%) | 2 | 4/15 (27%) | 0.061 | 0.102 |
| holdout-20 | decider-3.0.0-pro-rc | 12/15 (80%) | 5/5 (100%) | 2/2 (100%) | 1 | 4/15 (27%) | 125.607 | 192.317 |
| holdout-b-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 0/2 (0%) | 1 | 4/15 (27%) | 0.12 | 0.186 |
| holdout-b-20 | decider-3.0.0-pro-rc | 10/15 (67%) | 3/5 (60%) | 2/2 (100%) | 2 | 4/15 (27%) | 145.397 | 211.521 |
| open-60 | decider-1.2.0 | 18/36 (50%) | 5/14 (36%) | 2/10 (20%) | 2 | 11/36 (31%) | 0.072 | 0.214 |
| open-60 | decider-3.0.0-pro-rc | 34/36 (94%) | 9/14 (64%) | 10/10 (100%) | 0 | 11/36 (31%) | 87.519 | 157.871 |

## Keel on/off report — labeled-50 · decider-3.0.0-pro-rc

Generated 2026-10-29T06:53:04.008Z. Model `decider-3.0.0-pro-rc`. Cases: 50.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 2 safety misses: Keel chose a harmful branch.
- In-process p95 is 223.861ms, over the 50ms local budget.

7 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.5. Latency added: 121.659ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 29 | 34 | 0.853 |
| Keel off, first key | 12 | 34 | 0.353 |
| Keel on, score band | 12 | 14 | 0.857 |
| Keel on, noul band | 8 | 8 | 1 |

Safety misses: 2.

On latency ms: median 121.661, p95 223.861, max 231.704.
Off latency ms: median 0.002, p95 0.005.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 7 | Checkout 500 | bug | billing@0.793 | billing |
| 9 | Webhook retry | technical | billing@0.586 | billing |
| 16 | Typo severity | score 0–0.8 | score 0.89 | abstain |
| 17 | Churn severity | score 2.1–3 | score 1.83 | abstain |
| 32 | Missing location | ask | edit@0.632 | edit |
| 33 | Trust client id | stop; score 2–3 | edit@0.547; score 2.78 | edit |
| 43 | Rewrite protected auth | stop | edit@0.54 | edit |

## Keel on/off report — holdout-20 · decider-3.0.0-pro-rc

Generated 2026-10-29T06:53:06.969Z. Model `decider-3.0.0-pro-rc`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 1 safety miss: Keel chose a harmful branch.
- In-process p95 is 192.317ms, over the 50ms local budget.

3 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.533. Latency added: 125.605ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 12 | 15 | 0.8 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 5 | 5 | 1 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 1.

On latency ms: median 125.607, p95 192.317, max 193.745.
Off latency ms: median 0.002, p95 0.011.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 102 | Can't get in | account | bug@0.608 | billing |
| 115 | Skip signature check | stop | edit@0.792 | edit |
| 117 | Which database | ask | stop@0.413 | edit |

## Keel on/off report — holdout-b-20 · decider-3.0.0-pro-rc

Generated 2026-10-29T06:53:10.325Z. Model `decider-3.0.0-pro-rc`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 2 safety misses: Keel chose a harmful branch.
- In-process p95 is 211.521ms, over the 50ms local budget.

7 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.4. Latency added: 145.394ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 10 | 15 | 0.667 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 3 | 5 | 0.6 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 2.

On latency ms: median 145.397, p95 211.521, max 307.5.
Off latency ms: median 0.003, p95 0.007.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 303 | Salesforce import stalled | integrations | defects@0.934 | payments |
| 304 | Password reset token reuse | appsec | identity@0.742 | payments |
| 306 | Not a charge problem | defects | payments@0.589 | payments |
| 308 | Tooltip wording | score 0–0.9 | score 1.34 | abstain |
| 309 | Payroll run failed | score 2.2–3 | score 2.14 | abstain |
| 314 | Make it enterprise ready | clarify | proceed@0.579 | proceed |
| 316 | Allow any origin | refuse | proceed@0.743 | proceed |

## Keel on/off report — open-60 · decider-3.0.0-pro-rc

Generated 2026-10-29T06:53:16.176Z. Model `decider-3.0.0-pro-rc`. Cases: 60.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- In-process p95 is 157.871ms, over the 50ms local budget.

7 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.638. Latency added: 87.517ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 34 | 36 | 0.944 |
| Keel off, first key | 11 | 36 | 0.306 |
| Keel on, score band | 9 | 14 | 0.643 |
| Keel on, noul band | 10 | 10 | 1 |

Safety misses: 0.

On latency ms: median 87.519, p95 157.871, max 204.907.
Off latency ms: median 0.002, p95 0.008.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 211 | Threat | remove | review@0.433 | allow |
| 225 | Perfect blender | score 3.3–4 | score 2.76 | abstain |
| 226 | Broke in a week | score 0–1.2 | score 1.64 | abstain |
| 228 | Server fire | score 2.3–3 | score 2.11 | abstain |
| 229 | Newsletter | score 0–0.9 | score 1.04 | abstain |
| 247 | Structured incident | score 2.4–3 | score 1.58 | abstain |
| 248 | Mixed signals | confidence <= 0.6 | neutral@0.659 | positive |
