# Keel parity bench

Generated 2026-10-29T04:46:19.502Z. Columns: `models/keel-2` (decider-2.0.0), `models/candidates/t1-q0k` (decider-3.0.0-rc.t1-q0k), `gpt-5-mini (LLM only)` (gpt-5-mini).

- Blind suite: 234 cases (half A 150, half B 84), never trained on.
- labeled-50 is **in-sample** for every Keel model (training mix). It is shown for reference and excluded from "held-out total".
- LLM baseline: cache only (run with --llm-run to fill missing blind answers). Older suites use the keel-ab cache (`artifacts/ab-cache`). Unanswered LLM cases count as wrong. LLM latency is wall-clock per Copilot CLI call, not comparable to in-process Keel latency.
- Live MSD1: not measured — No MSD1 credential: OPENROUTER_API_KEY is not set and no Foundry deployment of Microsoft-Decision-1 is configured (MSD1_FOUNDRY_ENDPOINT + MSD1_FOUNDRY_DEPLOYMENT + key or Entra token). No request was sent.
- Live Jev: not measured — TYPESAFE_API_KEY is not set. No request was sent to TypeSafe.
- "Fully right" = every graded question right and no safety miss. ECE = expected calibration error of choice confidence on unambiguous choice questions (10 bins; lower is better). Latency = in-process ms (tokenize + ONNX + projection), sequential, warmed.

| Suite | Column | Fully right | Choice | Score band | Noul band | Safety misses | ECE (n) | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| holdout-20 | models/keel-2 | 15/20 | 11/15 | 4/5 | 2/2 | 1 | 0.122 (14) | 25.83 | 38.81 |
| holdout-20 | models/candidates/t1-q0k | 16/20 | 11/15 | 5/5 | 2/2 | 1 | 0.235 (14) | 21.76 | 29.7 |
| holdout-20 | gpt-5-mini (LLM only) | 16/20 | 11/15 | 5/5 | 2/2 | 0 | 0.266 (14) | 46.3 s | 58.2 s |
| holdout-b-20 | models/keel-2 | 10/20 | 8/15 | 2/5 | 1/2 | 1 | 0.451 (14) | 28.63 | 40.44 |
| holdout-b-20 | models/candidates/t1-q0k | 16/20 | 11/15 | 5/5 | 2/2 | 2 | 0.137 (14) | 24.93 | 55.33 |
| holdout-b-20 | gpt-5-mini (LLM only) | 13/20 | 9/15 | 5/5 | 1/2 | 1 | 0.251 (14) | 45.2 s | 111.6 s |
| open-60 | models/keel-2 | 34/60 | 24/36 | 6/14 | 4/10 | 1 | 0.237 (34) | 14.41 | 22.64 |
| open-60 | models/candidates/t1-q0k | 36/60 | 27/36 | 5/14 | 4/10 | 1 | 0.279 (34) | 14.61 | 20.26 |
| open-60 | gpt-5-mini (LLM only) | 46/60 | 31/36 | 11/14 | 4/10 | 1 | 0.065 (34) | 43.6 s | 60.7 s |
| blind | models/keel-2 | 92/234 | 59/135 | 13/39 | 20/60 | 11 | 0.182 (127) | 17.9 | 33.74 |
| blind | models/candidates/t1-q0k | 101/234 | 61/135 | 15/39 | 25/60 | 17 | 0.27 (127) | 17.77 | 42.38 |
| blind | gpt-5-mini (LLM only) | 0/234 (0 answered) | 0/135 | 0/39 | 0/60 | 0 | — (0) | — | — |
| held-out total | models/keel-2 | 151/334 | 102/201 | 25/63 | 27/74 | 14 | 0.174 (189) | 17.74 | 36.22 |
| held-out total | models/candidates/t1-q0k | 169/334 | 110/201 | 30/63 | 33/74 | 21 | 0.221 (189) | 17.56 | 38.87 |
| held-out total | gpt-5-mini (LLM only) | 75/334 (100 answered) | 51/201 | 21/63 | 7/74 | 2 | 0.141 (62) | 43.9 s | 60.7 s |
| labeled-50 (in-sample) | models/keel-2 | 48/50 | 33/34 | 13/14 | 8/8 | 0 | 0.092 (33) | 22.79 | 36.64 |
| labeled-50 (in-sample) | models/candidates/t1-q0k | 50/50 | 34/34 | 14/14 | 8/8 | 0 | 0.005 (33) | 18.77 | 34.14 |
| labeled-50 (in-sample) | gpt-5-mini (LLM only) | 42/50 | 29/34 | 12/14 | 7/8 | 1 | 0.089 (33) | 44.1 s | 55.6 s |

Blind per-case details are omitted because --out is outside artifacts/parity/blind/ (held-out integrity).
