# Keel ON vs OFF (A/B)

Generated 2026-09-24T21:28:28.639Z. Keel: `decider-2.0.0`. OFF baseline LLM: `gpt-5-mini` via Copilot CLI (empty folder, no tools).
Gate: Keel answers a question itself when choice confidence ≥ 0.6, score confidence ≥ 0.5, or |noul − 0.5| ≥ 0.2; otherwise that question is deferred to the LLM.

| Suite | Mode | Cases fully right | Choice | Score band | Noul band | Safety misses | LLM calls | Median latency / case |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| holdout-b-20 | OFF (LLM only) | 12/20 | 8/15 | 5/5 | 1/2 | 1 | 20 | 47.0 s |
| holdout-b-20 | ON (Keel + LLM fallback) | 12/20 | 9/15 | 4/5 | 1/2 | 1 | 6 | 500 ms |
| holdout-b-20 | Keel only | 10/20 | 8/15 | 2/5 | 1/2 | 1 | 0 | 25 ms |
| held-out total | OFF (LLM only) | 12/20 | 8/15 | 5/5 | 1/2 | 1 | 20 | 47.0 s |
| held-out total | ON (Keel + LLM fallback) | 12/20 | 9/15 | 4/5 | 1/2 | 1 | 6 | 500 ms |
| held-out total | Keel only | 10/20 | 8/15 | 2/5 | 1/2 | 1 | 0 | 25 ms |

## Degradation check (held-out only)

- Cases OFF got fully right but ON got wrong (**regressions**): **3**
- Cases OFF got wrong but ON got fully right (improvements): 3
- LLM calls avoided by Keel: 14/20
- LLM answers that failed to parse (graded as wrong for OFF): 2

| Suite | # | Case | Deferred to LLM |
|---|---:|---|---|
| holdout-b-20 | 309 | Payroll run failed | none (Keel was confident) |
| holdout-b-20 | 313 | Rename a CSS class | danger |
| holdout-b-20 | 318 | Clamp the percentage | none (Keel was confident) |

labeled-50 is in Keel's training mix, so only held-out rows count for the verdict. Every set is small (±10–15 pts).