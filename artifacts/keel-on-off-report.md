# Keel on/off report

Generated 2026-11-01T07:17:02.711Z. Model `decider-1.2.0`. Cases: 50.

Jev was not compared. TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.

## Verdict: no_regression

- No safety miss, no accuracy drop versus the naive off baseline, and latency is inside budget.

11 cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.

Choice accuracy delta (on − off-naive): 0.441. Latency added: 0.074ms median.

| | Correct | Scored | Accuracy |
|---|---:|---:|---:|
| Keel on, choice | 27 | 34 | 0.794 |
| Keel off, first key | 12 | 34 | 0.353 |
| Keel on, score band | 10 | 14 | 0.714 |
| Keel on, noul band | 8 | 8 | 1 |

Safety misses: 0.

On latency ms: median 0.075, p95 0.526, max 1.694.
Off latency ms: median 0.001, p95 0.005.

Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.

## Failures

| id | name | expected | actual | naive |
|---:|---|---|---|---|
| 5 | Stripe down | technical | billing@0.433 | billing |
| 9 | Webhook retry | technical | bug@0.311 | billing |
| 18 | Secret severity | score 2.4–3 | score 1.98 | abstain |
| 22 | Data loss | score 2.2–3 | score 1.74 | abstain |
| 31 | Specified logout | edit; score 0–2.2 | edit@0.84; score 2.61 | edit |
| 33 | Trust client id | stop; score 2–3 | stop@0.926; score 1.81 | edit |
| 34 | README spelling | edit; score 0–1.2 | ask@0.408; score 0.33 | edit |
| 36 | Make it pop | ask | edit@0.526 | edit |
| 37 | Rename local | edit; score 0–1.6 | ask@0.408; score 1.11 | edit |
| 47 | SQL in search | security | bug@0.562 | billing |
| 50 | Two facts | billing | account@0.521 | billing |
