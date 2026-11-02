# Keel parity bench

Generated 2026-10-30T01:08:03.930Z. Columns: `models/keel-2` (decider-2.0.0), `models/candidates/t1-r2e` (decider-3.0.0-rc.t1-r2e), `models/candidates/t1-r5` (decider-3.0.0-rc-t1-r5), `models/candidates/t1-r6s` (decider-3.0.0-rc-t1-r6s), `lexical` (decider-1.2.0), `claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only)` (claude-haiku-4.5 blind / gpt-5-mini older suites).

- Blind suite: 234 cases (half A 150, half B 84), never trained on.
- blind-c: 100 cases, final-confirmation suite (data-1 + a different-model sub-agent); excluded from "held-out total".
- labeled-50 is **in-sample** for every Keel model (training mix). It is shown for reference and excluded from "held-out total".
- LLM baseline: blind / blind-c = `claude-haiku-4.5` (blind: cache only (run with --llm-run to fill missing answers); blind-c: cache only (run with --llm-run to fill missing answers)). Older suites use the keel-ab cache of `gpt-5-mini` (`artifacts/ab-cache`); gpt-5-mini is no longer available in the Copilot CLI, so it cannot answer the blind suite. Unanswered LLM cases count as wrong. LLM latency is wall-clock per Copilot CLI call, not comparable to in-process Keel latency.
- Live MSD1: not measured — No MSD1 credential: OPENROUTER_API_KEY is not set and no Foundry deployment of Microsoft-Decision-1 is configured (MSD1_FOUNDRY_ENDPOINT + MSD1_FOUNDRY_DEPLOYMENT + key or Entra token). No request was sent.
- Live Jev: not measured — TYPESAFE_API_KEY is not set. No request was sent to TypeSafe.
- "Fully right" = every graded question right and no safety miss. ECE = expected calibration error of choice confidence on unambiguous choice questions (10 bins; lower is better). Latency = in-process ms (tokenize + ONNX + projection), sequential, warmed.

| Suite | Column | Fully right | Choice | Score band | Noul band | Safety misses | ECE (n) | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| holdout-20 | models/keel-2 | 15/20 | 11/15 | 4/5 | 2/2 | 1 | 0.122 (14) | 17.57 | 25.64 |
| holdout-20 | models/candidates/t1-r2e | 18/20 | 13/15 | 5/5 | 2/2 | 0 | 0.086 (14) | 16.11 | 22.93 |
| holdout-20 | models/candidates/t1-r5 | 18/20 | 13/15 | 5/5 | 2/2 | 0 | 0.138 (14) | 15.4 | 19.42 |
| holdout-20 | models/candidates/t1-r6s | 18/20 | 13/15 | 5/5 | 2/2 | 0 | 0.164 (14) | 16.1 | 23.32 |
| holdout-20 | lexical | 9/20 | 7/15 | 3/5 | 1/2 | 2 | 0.138 (14) | 0.03 | 0.04 |
| holdout-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 16/20 | 11/15 | 5/5 | 2/2 | 0 | 0.266 (14) | 46.3 s | 58.2 s |
| holdout-b-20 | models/keel-2 | 10/20 | 8/15 | 2/5 | 1/2 | 1 | 0.451 (14) | 19.57 | 33.08 |
| holdout-b-20 | models/candidates/t1-r2e | 18/20 | 13/15 | 5/5 | 2/2 | 1 | 0.142 (14) | 17.06 | 22.34 |
| holdout-b-20 | models/candidates/t1-r5 | 18/20 | 13/15 | 5/5 | 2/2 | 1 | 0.146 (14) | 16.68 | 22.25 |
| holdout-b-20 | models/candidates/t1-r6s | 18/20 | 13/15 | 5/5 | 2/2 | 1 | 0.148 (14) | 17.35 | 26.41 |
| holdout-b-20 | lexical | 8/20 | 7/15 | 3/5 | 0/2 | 1 | 0.118 (14) | 0.03 | 0.05 |
| holdout-b-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 13/20 | 9/15 | 5/5 | 1/2 | 1 | 0.251 (14) | 45.2 s | 111.6 s |
| open-60 | models/keel-2 | 34/60 | 24/36 | 6/14 | 4/10 | 1 | 0.237 (34) | 12.78 | 18.03 |
| open-60 | models/candidates/t1-r2e | 51/60 | 33/36 | 8/14 | 10/10 | 0 | 0.103 (34) | 9.91 | 15.18 |
| open-60 | models/candidates/t1-r5 | 49/60 | 31/36 | 8/14 | 10/10 | 0 | 0.072 (34) | 10.65 | 16.64 |
| open-60 | models/candidates/t1-r6s | 50/60 | 33/36 | 7/14 | 10/10 | 0 | 0.087 (34) | 9.89 | 16.1 |
| open-60 | lexical | 25/60 | 18/36 | 5/14 | 2/10 | 2 | 0.178 (34) | 0.02 | 0.03 |
| open-60 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 46/60 | 31/36 | 11/14 | 4/10 | 1 | 0.065 (34) | 43.6 s | 60.7 s |
| blind | models/keel-2 | 92/234 | 59/135 | 13/39 | 20/60 | 11 | 0.182 (127) | 13.13 | 24.74 |
| blind | models/candidates/t1-r2e | 125/234 | 78/135 | 20/39 | 27/60 | 13 | 0.087 (127) | 14.14 | 23.55 |
| blind | models/candidates/t1-r5 | 119/234 | 74/135 | 18/39 | 27/60 | 15 | 0.133 (127) | 13.47 | 21.66 |
| blind | models/candidates/t1-r6s | 116/234 | 70/135 | 19/39 | 27/60 | 10 | 0.166 (127) | 12.83 | 23.66 |
| blind | lexical | 87/234 | 62/135 | 6/39 | 19/60 | 22 | 0.112 (127) | 0.03 | 0.05 |
| blind | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 215/234 (231 answered) | 125/135 | 33/39 | 57/60 | 0 | 0.08 (126) | 55.7 s | 93.1 s |
| held-out total | models/keel-2 | 151/334 | 102/201 | 25/63 | 27/74 | 14 | 0.174 (189) | 13.5 | 25.64 |
| held-out total | models/candidates/t1-r2e | 212/334 | 137/201 | 38/63 | 41/74 | 14 | 0.043 (189) | 13.39 | 22.34 |
| held-out total | models/candidates/t1-r5 | 204/334 | 131/201 | 36/63 | 41/74 | 16 | 0.098 (189) | 12.51 | 21 |
| held-out total | models/candidates/t1-r6s | 202/334 | 129/201 | 36/63 | 41/74 | 11 | 0.108 (189) | 12.71 | 21.77 |
| held-out total | lexical | 129/334 | 94/201 | 17/63 | 22/74 | 27 | 0.107 (189) | 0.03 | 0.05 |
| held-out total | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 290/334 (331 answered) | 176/201 | 54/63 | 64/74 | 2 | 0.08 (188) | 51.7 s | 90.5 s |
| blind-c (confirmation) | models/keel-2 | 47/100 | 32/56 | 4/19 | 11/25 | 10 | 0.178 (52) | 19.52 | 52.91 |
| blind-c (confirmation) | models/candidates/t1-r2e | 37/100 | 29/56 | 3/19 | 5/25 | 14 | 0.206 (52) | 17.74 | 48.59 |
| blind-c (confirmation) | models/candidates/t1-r5 | 38/100 | 31/56 | 3/19 | 4/25 | 14 | 0.147 (52) | 17.47 | 47.55 |
| blind-c (confirmation) | models/candidates/t1-r6s | 39/100 | 32/56 | 2/19 | 5/25 | 12 | 0.113 (52) | 17.72 | 47.52 |
| blind-c (confirmation) | lexical | 43/100 | 34/56 | 2/19 | 7/25 | 10 | 0.136 (52) | 0.05 | 0.18 |
| blind-c (confirmation) | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 37/100 (39 answered) | 23/56 | 5/19 | 9/25 | 0 | 0.138 (24) | 90.8 s | 176.0 s |
| labeled-50 (in-sample) | models/keel-2 | 48/50 | 33/34 | 13/14 | 8/8 | 0 | 0.092 (33) | 16.29 | 24.37 |
| labeled-50 (in-sample) | models/candidates/t1-r2e | 49/50 | 34/34 | 14/14 | 7/8 | 0 | 0.057 (33) | 12.31 | 22.15 |
| labeled-50 (in-sample) | models/candidates/t1-r5 | 50/50 | 34/34 | 14/14 | 8/8 | 0 | 0.037 (33) | 15.15 | 23.01 |
| labeled-50 (in-sample) | models/candidates/t1-r6s | 50/50 | 34/34 | 14/14 | 8/8 | 0 | 0.05 (33) | 14.96 | 24.59 |
| labeled-50 (in-sample) | lexical | 39/50 | 27/34 | 10/14 | 8/8 | 0 | 0.194 (33) | 0.03 | 0.05 |
| labeled-50 (in-sample) | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 42/50 | 29/34 | 12/14 | 7/8 | 1 | 0.089 (33) | 44.1 s | 55.6 s |

blind per-case details are omitted because --out is outside artifacts/parity/blind/ (held-out integrity).

blind-c per-case details are omitted because --out is outside artifacts/parity/blind-c/ (held-out integrity).
