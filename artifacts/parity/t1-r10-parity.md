# Keel parity bench

Generated 2026-10-30T02:53:17.889Z. Columns: `models/keel-2` (decider-2.0.0), `models/candidates/t1-r10` (decider-3.0.0-rc-t1-r10), `lexical` (decider-1.2.0), `claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only)` (claude-haiku-4.5 blind / gpt-5-mini older suites).

- Blind suite: 234 cases (half A 150, half B 84), never trained on.
- blind-c: 100 cases, final-confirmation suite (data-1 + a different-model sub-agent); excluded from "held-out total".
- labeled-50 is **in-sample** for every Keel model (training mix). It is shown for reference and excluded from "held-out total".
- LLM baseline: blind / blind-c = `claude-haiku-4.5` (blind: cache only (run with --llm-run to fill missing answers); blind-c: cache only (run with --llm-run to fill missing answers)). Older suites use the keel-ab cache of `gpt-5-mini` (`artifacts/ab-cache`); gpt-5-mini is no longer available in the Copilot CLI, so it cannot answer the blind suite. Unanswered LLM cases count as wrong. LLM latency is wall-clock per Copilot CLI call, not comparable to in-process Keel latency.
- Live MSD1: not measured — No MSD1 credential: OPENROUTER_API_KEY is not set and no Foundry deployment of Microsoft-Decision-1 is configured (MSD1_FOUNDRY_ENDPOINT + MSD1_FOUNDRY_DEPLOYMENT + key or Entra token). No request was sent.
- Live Jev: not measured — TYPESAFE_API_KEY is not set. No request was sent to TypeSafe.
- "Fully right" = every graded question right and no safety miss. ECE = expected calibration error of choice confidence on unambiguous choice questions (10 bins; lower is better). Latency = in-process ms (tokenize + ONNX + projection), sequential, warmed.

| Suite | Column | Fully right | Choice | Score band | Noul band | Safety misses | ECE (n) | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| holdout-20 | models/keel-2 | 15/20 | 11/15 | 4/5 | 2/2 | 1 | 0.122 (14) | 10.84 | 15.95 |
| holdout-20 | models/candidates/t1-r10 | 18/20 | 13/15 | 5/5 | 2/2 | 0 | 0.149 (14) | 19.57 | 30.98 |
| holdout-20 | lexical | 9/20 | 7/15 | 3/5 | 1/2 | 2 | 0.138 (14) | 0.05 | 0.09 |
| holdout-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 16/20 | 11/15 | 5/5 | 2/2 | 0 | 0.266 (14) | 46.3 s | 58.2 s |
| holdout-b-20 | models/keel-2 | 10/20 | 8/15 | 2/5 | 1/2 | 1 | 0.451 (14) | 20.91 | 27.44 |
| holdout-b-20 | models/candidates/t1-r10 | 18/20 | 13/15 | 5/5 | 2/2 | 1 | 0.155 (14) | 22.23 | 33.99 |
| holdout-b-20 | lexical | 8/20 | 7/15 | 3/5 | 0/2 | 1 | 0.118 (14) | 0.05 | 0.08 |
| holdout-b-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 13/20 | 9/15 | 5/5 | 1/2 | 1 | 0.251 (14) | 45.2 s | 111.6 s |
| open-60 | models/keel-2 | 34/60 | 24/36 | 6/14 | 4/10 | 1 | 0.237 (34) | 11.76 | 17.06 |
| open-60 | models/candidates/t1-r10 | 50/60 | 33/36 | 7/14 | 10/10 | 0 | 0.049 (34) | 11.11 | 18.2 |
| open-60 | lexical | 25/60 | 18/36 | 5/14 | 2/10 | 2 | 0.178 (34) | 0.03 | 0.05 |
| open-60 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 46/60 | 31/36 | 11/14 | 4/10 | 1 | 0.065 (34) | 43.6 s | 60.7 s |
| blind | models/keel-2 | 92/234 | 59/135 | 13/39 | 20/60 | 11 | 0.182 (127) | 16.04 | 25.78 |
| blind | models/candidates/t1-r10 | 119/234 | 77/135 | 17/39 | 25/60 | 12 | 0.106 (127) | 15.54 | 29.39 |
| blind | lexical | 87/234 | 62/135 | 6/39 | 19/60 | 22 | 0.112 (127) | 0.04 | 0.14 |
| blind | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 215/234 (231 answered) | 125/135 | 33/39 | 57/60 | 0 | 0.08 (126) | 55.7 s | 93.1 s |
| held-out total | models/keel-2 | 151/334 | 102/201 | 25/63 | 27/74 | 14 | 0.174 (189) | 14.97 | 24.95 |
| held-out total | models/candidates/t1-r10 | 205/334 | 136/201 | 34/63 | 39/74 | 13 | 0.068 (189) | 15.22 | 27.69 |
| held-out total | lexical | 129/334 | 94/201 | 17/63 | 22/74 | 27 | 0.107 (189) | 0.04 | 0.11 |
| held-out total | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 290/334 (331 answered) | 176/201 | 54/63 | 64/74 | 2 | 0.08 (188) | 51.7 s | 90.5 s |
| blind-c (confirmation) | models/keel-2 | 47/100 | 32/56 | 4/19 | 11/25 | 10 | 0.178 (52) | 23.88 | 67.94 |
| blind-c (confirmation) | models/candidates/t1-r10 | 38/100 | 31/56 | 3/19 | 4/25 | 13 | 0.124 (52) | 21.6 | 67.58 |
| blind-c (confirmation) | lexical | 43/100 | 34/56 | 2/19 | 7/25 | 10 | 0.136 (52) | 0.05 | 0.16 |
| blind-c (confirmation) | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 37/100 (39 answered) | 23/56 | 5/19 | 9/25 | 0 | 0.138 (24) | 90.8 s | 176.0 s |
| labeled-50 (in-sample) | models/keel-2 | 48/50 | 33/34 | 13/14 | 8/8 | 0 | 0.092 (33) | 18.21 | 34.24 |
| labeled-50 (in-sample) | models/candidates/t1-r10 | 50/50 | 34/34 | 14/14 | 8/8 | 0 | 0.055 (33) | 16.33 | 25.69 |
| labeled-50 (in-sample) | lexical | 39/50 | 27/34 | 10/14 | 8/8 | 0 | 0.194 (33) | 0.03 | 0.04 |
| labeled-50 (in-sample) | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 42/50 | 29/34 | 12/14 | 7/8 | 1 | 0.089 (33) | 44.1 s | 55.6 s |

blind per-case details are omitted because --out is outside artifacts/parity/blind/ (held-out integrity).

blind-c per-case details are omitted because --out is outside artifacts/parity/blind-c/ (held-out integrity).
