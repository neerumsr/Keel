# Keel parity bench

Generated 2026-10-29T07:19:40.786Z. Columns: `models/candidates/t1-r3` (decider-3.0.0-rc.t1-r3), `claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only)` (claude-haiku-4.5 blind / gpt-5-mini older suites).

- Blind suite: 234 cases (half A 150, half B 84), never trained on.
- labeled-50 is **in-sample** for every Keel model (training mix). It is shown for reference and excluded from "held-out total".
- LLM baseline: blind = `claude-haiku-4.5` (cache only (run with --llm-run to fill missing blind answers)). Older suites use the keel-ab cache of `gpt-5-mini` (`artifacts/ab-cache`); gpt-5-mini is no longer available in the Copilot CLI, so it cannot answer the blind suite. Unanswered LLM cases count as wrong. LLM latency is wall-clock per Copilot CLI call, not comparable to in-process Keel latency.
- Live MSD1: not measured — No MSD1 credential: OPENROUTER_API_KEY is not set and no Foundry deployment of Microsoft-Decision-1 is configured (MSD1_FOUNDRY_ENDPOINT + MSD1_FOUNDRY_DEPLOYMENT + key or Entra token). No request was sent.
- Live Jev: not measured — TYPESAFE_API_KEY is not set. No request was sent to TypeSafe.
- "Fully right" = every graded question right and no safety miss. ECE = expected calibration error of choice confidence on unambiguous choice questions (10 bins; lower is better). Latency = in-process ms (tokenize + ONNX + projection), sequential, warmed.

| Suite | Column | Fully right | Choice | Score band | Noul band | Safety misses | ECE (n) | p50 ms | p95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| holdout-20 | models/candidates/t1-r3 | 18/20 | 13/15 | 5/5 | 2/2 | 0 | 0.157 (14) | 24.54 | 34.51 |
| holdout-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 16/20 | 11/15 | 5/5 | 2/2 | 0 | 0.266 (14) | 46.3 s | 58.2 s |
| holdout-b-20 | models/candidates/t1-r3 | 18/20 | 13/15 | 5/5 | 2/2 | 1 | 0.133 (14) | 26.8 | 32.78 |
| holdout-b-20 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 13/20 | 9/15 | 5/5 | 1/2 | 1 | 0.251 (14) | 45.2 s | 111.6 s |
| open-60 | models/candidates/t1-r3 | 49/60 | 32/36 | 7/14 | 10/10 | 0 | 0.088 (34) | 14.28 | 20.97 |
| open-60 | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 46/60 | 31/36 | 11/14 | 4/10 | 1 | 0.065 (34) | 43.6 s | 60.7 s |
| blind | models/candidates/t1-r3 | 122/234 | 74/135 | 19/39 | 29/60 | 15 | 0.124 (127) | 19.07 | 38.67 |
| blind | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 215/234 (231 answered) | 125/135 | 33/39 | 57/60 | 0 | 0.08 (126) | 55.7 s | 93.1 s |
| held-out total | models/candidates/t1-r3 | 207/334 | 132/201 | 36/63 | 43/74 | 16 | 0.079 (189) | 18.44 | 34.14 |
| held-out total | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 290/334 (331 answered) | 176/201 | 54/63 | 64/74 | 2 | 0.08 (188) | 51.7 s | 90.5 s |
| labeled-50 (in-sample) | models/candidates/t1-r3 | 50/50 | 34/34 | 14/14 | 8/8 | 0 | 0.047 (33) | 21.6 | 34.8 |
| labeled-50 (in-sample) | claude-haiku-4.5 blind / gpt-5-mini older suites (LLM only) | 42/50 | 29/34 | 12/14 | 7/8 | 1 | 0.089 (33) | 44.1 s | 55.6 s |

Blind per-case details are omitted because --out is outside artifacts/parity/blind/ (held-out integrity).
