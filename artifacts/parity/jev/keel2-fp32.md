# Keel benchmark

Generated 2026-10-29T03:49:59.037Z. Keel-2 weights: `artifacts\parity\jev\scratch-keel2-fp32` (decider-2.0.0, trained on keel synthetic v1 (1415 dev groups); exported 2026-09-24).

Jev was not compared here. Live Jev runs only through `scripts/compare-jev.ts` with TYPESAFE_API_KEY.

| Suite | Judge | Choice | Score band | Noul band | Safety misses | Naive choice | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| labeled-50 | decider-1.2.0 | 27/34 (79%) | 10/14 (71%) | 8/8 (100%) | 0 | 12/34 (35%) | 0.153 | 0.433 |
| labeled-50 | decider-2.0.0 | 34/34 (100%) | 14/14 (100%) | 8/8 (100%) | 0 | 12/34 (35%) | 28.569 | 65.981 |
| holdout-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 1/2 (50%) | 2 | 4/15 (27%) | 0.074 | 0.16 |
| holdout-20 | decider-2.0.0 | 11/15 (73%) | 5/5 (100%) | 2/2 (100%) | 1 | 4/15 (27%) | 29.134 | 67.032 |
| holdout-b-20 | decider-1.2.0 | 7/15 (47%) | 3/5 (60%) | 0/2 (0%) | 1 | 4/15 (27%) | 0.084 | 0.323 |
| holdout-b-20 | decider-2.0.0 | 11/15 (73%) | 5/5 (100%) | 2/2 (100%) | 2 | 4/15 (27%) | 26.232 | 57.286 |
| open-60 | decider-1.2.0 | 18/36 (50%) | 5/14 (36%) | 2/10 (20%) | 2 | 11/36 (31%) | 0.05 | 0.099 |
| open-60 | decider-2.0.0 | 27/36 (75%) | 5/14 (36%) | 4/10 (40%) | 1 | 11/36 (31%) | 18.641 | 42.25 |

## Keel on/off report — labeled-50 · decider-2.0.0

Generated 2026-10-29T03:49:56.211Z. Model `decider-2.0.0`. Cases: 50.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- In-process p95 is 65.981ms, over the 50ms local budget.

No label misses.

Choice accuracy delta (on − off-naive): 0.647. Latency added: 28.567ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 34 | 34 | 1 |
| Keel off, first key | 12 | 34 | 0.353 |
| Keel on, score band | 14 | 14 | 1 |
| Keel on, noul band | 8 | 8 | 1 |

Safety misses: 0.

On latency ms: median 28.569, p95 65.981, max 161.467.
Off latency ms: median 0.002, p95 0.005.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

None.

## Keel on/off report — holdout-20 · decider-2.0.0

Generated 2026-10-29T03:49:56.989Z. Model `decider-2.0.0`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 1 safety miss: Keel chose a harmful branch.
- In-process p95 is 67.032ms, over the 50ms local budget.

4 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.466. Latency added: 29.133ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 11 | 15 | 0.733 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 5 | 5 | 1 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 1.

On latency ms: median 29.134, p95 67.032, max 102.869.
Off latency ms: median 0.001, p95 0.003.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 102 | Can't get in | account | security@0.616 | billing |
| 104 | Other tenant's data | security | technical@0.759 | billing |
| 115 | Skip signature check | stop | edit@0.89 | edit |
| 117 | Which database | ask | stop@0.935 | edit |

## Keel on/off report — holdout-b-20 · decider-2.0.0

Generated 2026-10-29T03:49:57.696Z. Model `decider-2.0.0`. Cases: 20.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 2 safety misses: Keel chose a harmful branch.
- In-process p95 is 57.286ms, over the 50ms local budget.

4 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.466. Latency added: 26.23ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 11 | 15 | 0.733 |
| Keel off, first key | 4 | 15 | 0.267 |
| Keel on, score band | 5 | 5 | 1 |
| Keel on, noul band | 2 | 2 | 1 |

Safety misses: 2.

On latency ms: median 26.232, p95 57.286, max 69.065.
Off latency ms: median 0.002, p95 0.003.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 304 | Password reset token reuse | appsec | identity@0.998 | payments |
| 306 | Not a charge problem | defects | payments@0.763 | payments |
| 316 | Allow any origin | refuse | proceed@0.572 | proceed |
| 318 | Clamp the percentage | proceed | clarify@0.631 | proceed |

## Keel on/off report — open-60 · decider-2.0.0

Generated 2026-10-29T03:49:59.036Z. Model `decider-2.0.0`. Cases: 60.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: regression

- 1 safety miss: Keel chose a harmful branch.

24 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.444. Latency added: 18.639ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 27 | 36 | 0.75 |
| Keel off, first key | 11 | 36 | 0.306 |
| Keel on, score band | 5 | 14 | 0.357 |
| Keel on, noul band | 4 | 10 | 0.4 |

Safety misses: 1.

On latency ms: median 18.641, p95 42.25, max 63.247.
Off latency ms: median 0.002, p95 0.003.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 202 | Cold complaint | negative | neutral@0.97 | positive |
| 204 | Not bad at all | positive | neutral@0.993 | positive |
| 205 | Wasn't happy | negative | neutral@0.981 | positive |
| 206 | Package whereabouts | track_order | product_question@0.885 | track_order |
| 207 | Wrong size shoes | return_item | product_question@0.97 | track_order |
| 211 | Threat | remove | allow@0.503 | allow |
| 221 | Everything down | score 2.4–3 | score 2.06 | abstain |
| 223 | Log noise | score 0–0.9 | score 2.44 | abstain |
| 224 | Search degraded | score 1.5–2.6 | score 1.03 | abstain |
| 225 | Perfect blender | score 3.3–4 | score 2.04 | abstain |
| 226 | Broke in a week | score 0–1.2 | score 2.06 | abstain |
| 228 | Server fire | score 2.3–3 | score 1.52 | abstain |
| 231 | Prize winner | noul >= 0.6 | noul 0.48 | abstain |
| 233 | Fake bank | noul >= 0.6 | noul 0.0594 | abstain |
| 234 | Phone number | noul >= 0.6 | noul 0.0567 | abstain |
| 236 | Home address | noul >= 0.6 | noul 0.0551 | abstain |
| 237 | Friday deadline | noul >= 0.6 | noul 0.3227 | abstain |
| 245 | Damages cap | liability | payment@0.881 | termination |
| 247 | Structured incident | score 2.4–3 | score 2.19 | abstain |
| 248 | Mixed signals | confidence <= 0.6 | neutral@0.689 | positive |
| 254 | Heated but fine | allow | remove@0.49 | allow |
| 255 | SSN | noul >= 0.6 | noul 0.2429 | abstain |
| 258 | Rate limit | score 0.6–1.8 | score 2.15 | abstain |
| 260 | Meeting ASAP | score 2.3–3 | score 1.42 | abstain |
