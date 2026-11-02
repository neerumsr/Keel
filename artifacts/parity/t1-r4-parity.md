# Keel parity bench

Generated 2026-10-29T07:51:33.926Z. Columns: `models/keel-2` (decider-2.0.0), `models/candidates/t1-r2e` (decider-3.0.0-rc.t1-r2e), `models/candidates/t1-r4` (decider-3.0.0-rc.t1-r4), `claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only)` (claude-haiku-4.5 blind / gpt-5-mini older suites).

- Blind suite: 234 cases (half A 150, half B 84), never trained on.
- labeled-50 is **in-sample** for every Keel model (training mix). It is shown for reference and excluded from "held-out total".
- LLM baseline: blind = `claude-haiku-4.5` (cache only (run with --llm-run to fill missing blind answers)). Older suites use the keel-ab cache of `gpt-5-mini` (`artifacts/ab-cache`); gpt-5-mini is no longer available in the Copilot CLI, so it cannot answer the blind suite. Unanswered LLM cases count as wrong. LLM latency is wall-clock per Copilot CLI call, not comparable to in-process Keel latency.
- Live MSD1: not measured — No MSD1 credential: OPENROUTER_API_KEY is not set and no Foundry deployment of Microsoft-Decision-1 is configured (MSD1_FOUNDRY_ENDPOINT + MSD1_FOUNDRY_DEPLOYMENT + key or Entra token). No request was sent.
- Live Jev: not measured — TYPESAFE_API_KEY is not set. No request was sent to TypeSafe.
- "Fully right" = every graded question right and no safety miss. ECE = expected calibration error of choice confidence on unambiguous choice questions (10 bins; lower is better). Latency = in-process ms (tokenize + ONNX + projection), sequential, warmed.

| Suite | Column | Fully right | Choice | Score band | Noul band | Safety misses | ECE (n) | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| holdout-20 | models/keel-2 | 15/20 | 11/15 | 4/5 | 2/2 | 1 | 0.122 (14) | 25.49 | 60.84 |
| holdout-20 | models/candidates/t1-r2e | 18/20 | 13/15 | 5/5 | 2/2 | 0 | 0.086 (14) | 21.54 | 33.75 |
| holdout-20 | models/candidates/t1-r4 | 18/20 | 13/15 | 5/5 | 2/2 | 0 | 0.086 (14) | 23.1 | 32.71 |
| holdout-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 16/20 | 11/15 | 5/5 | 2/2 | 0 | 0.266 (14) | 46.3 s | 58.2 s |
| holdout-b-20 | models/keel-2 | 10/20 | 8/15 | 2/5 | 1/2 | 1 | 0.451 (14) | 18.62 | 36.93 |
| holdout-b-20 | models/candidates/t1-r2e | 18/20 | 13/15 | 5/5 | 2/2 | 1 | 0.142 (14) | 20.96 | 28.65 |
| holdout-b-20 | models/candidates/t1-r4 | 19/20 | 14/15 | 5/5 | 2/2 | 1 | 0.131 (14) | 21.93 | 35.66 |
| holdout-b-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 13/20 | 9/15 | 5/5 | 1/2 | 1 | 0.251 (14) | 45.2 s | 111.6 s |
| open-60 | models/keel-2 | 34/60 | 24/36 | 6/14 | 4/10 | 1 | 0.237 (34) | 13.03 | 32.01 |
| open-60 | models/candidates/t1-r2e | 51/60 | 33/36 | 8/14 | 10/10 | 0 | 0.103 (34) | 12.32 | 25.14 |
| open-60 | models/candidates/t1-r4 | 47/60 | 31/36 | 6/14 | 10/10 | 0 | 0.091 (34) | 13.91 | 21.76 |
| open-60 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 46/60 | 31/36 | 11/14 | 4/10 | 1 | 0.065 (34) | 43.6 s | 60.7 s |
| blind | models/keel-2 | 92/234 | 59/135 | 13/39 | 20/60 | 11 | 0.182 (127) | 17.06 | 46.12 |
| blind | models/candidates/t1-r2e | 125/234 | 78/135 | 20/39 | 27/60 | 13 | 0.087 (127) | 17.35 | 40.86 |
| blind | models/candidates/t1-r4 | 121/234 | 72/135 | 19/39 | 30/60 | 15 | 0.14 (127) | 18.42 | 38.47 |
| blind | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 215/234 (231 answered) | 125/135 | 33/39 | 57/60 | 0 | 0.08 (126) | 55.7 s | 93.1 s |
| held-out total | models/keel-2 | 151/334 | 102/201 | 25/63 | 27/74 | 14 | 0.174 (189) | 16.92 | 38.07 |
| held-out total | models/candidates/t1-r2e | 212/334 | 137/201 | 38/63 | 41/74 | 14 | 0.043 (189) | 16.68 | 37.1 |
| held-out total | models/candidates/t1-r4 | 205/334 | 130/201 | 35/63 | 44/74 | 16 | 0.099 (189) | 17.8 | 34.65 |
| held-out total | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 290/334 (331 answered) | 176/201 | 54/63 | 64/74 | 2 | 0.08 (188) | 51.7 s | 90.5 s |
| labeled-50 (in-sample) | models/keel-2 | 48/50 | 33/34 | 13/14 | 8/8 | 0 | 0.092 (33) | 19.4 | 30.86 |
| labeled-50 (in-sample) | models/candidates/t1-r2e | 49/50 | 34/34 | 14/14 | 7/8 | 0 | 0.057 (33) | 21.59 | 38.28 |
| labeled-50 (in-sample) | models/candidates/t1-r4 | 49/50 | 34/34 | 14/14 | 7/8 | 0 | 0.045 (33) | 18.54 | 33.71 |
| labeled-50 (in-sample) | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 42/50 | 29/34 | 12/14 | 7/8 | 1 | 0.089 (33) | 44.1 s | 55.6 s |

Blind per-case details are omitted because --out is outside artifacts/parity/blind/ (held-out integrity).
