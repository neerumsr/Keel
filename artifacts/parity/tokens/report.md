# Keel token-savings benchmark

Generated 2026-10-29T04:29:25.101Z by `scripts/keel-tokens.ts`. Keel: `decider-2.0.0` from `models/keel-2`.
Suites: holdout-20 (20), holdout-b-20 (20), open-60 (60), labeled-50 (50), blind-234 (234), held-out total (100), blind (234). Blind suite: loaded 234 cases from eval-blind.ts.

**Headline (held-out, τ = 0.6, dedicated decision sub-call, tokenizer-exact):** 24,830 → 9,790 LLM tokens (**60.6% fewer**), 59/100 LLM calls avoided, accuracy 75/100 → 69/100 cases fully right (**-6 pts**), safety misses 2 → 3.

## How tokens are counted

- **Tokenizer:** `gpt-tokenizer` o200k_base (devDependency added for this benchmark). Chat framing +6 tokens per LLM call.
- **OFF (no Keel):** every decision is one LLM call. Input = the exact decision prompt from `scripts/keel-ab.ts` (instructions + state + question schema). Output = the LLM's real JSON answer (gpt-5-mini answers cached by keel-ab; 0 of 100 held-out completions had no cached answer and were modeled from Keel's weights in the same JSON shape).
- **ON (with Keel):** Keel answers every question with confidence ≥ τ (noul confidence = |p − 0.5| × 2) locally for 0 LLM tokens. If any question is below τ, the agent makes one LLM call with **only the deferred questions** (same prompt template, subset of questions) and receives only those answers. Accuracy assumes the LLM gives the same per-question answer when asked fewer questions (questions are independent in the prompt); the answers used are from the full-prompt call.
- **Scenario A (visible):** prompt + completion, tokenizer-exact. **A + reasoning:** adds hidden reasoning tokens at the per-question rate measured on real claude-haiku-4.5 calls (366.7 tokens/question over 92 calls).
- **Scenario B (Copilot CLI sub-agent, measured):** what keel-ab actually did — spawn `copilot -p` per decision. Per-call cost = real mean input+output tokens from `--usage-output-file` on 92 real claude-haiku-4.5 calls; total = calls × mean. Includes the CLI's own system prompt/tool schema (the harness overhead), so it is much larger than A.
- **Scenario C (frontier agent deliberating in-context):** OFF = the agent reasons about each decision itself; deliberation tokens/question = (reasoning + output) measured on real gpt-5.6-terra calls on the same decision prompt (20.4 tokens/question over 12 calls). This is an **estimate**: OFF = rate × questions; ON = Keel tool-call body the agent must emit (output, o200k count of `{model,state,questions}` + 10) + Keel's JSON response read back (input, o200k + 4) + rate × deferred questions. The state is assumed to already be in the agent's context in both modes. The one-time Keel instruction block in the agent's system prompt (931 o200k tokens for `.github/agents/keel.agent.md`) is excluded from per-decision totals (it is prompt-cached per session).
- **Latency:** OFF = measured wall time of the gpt-5-mini Copilot CLI call cached by keel-ab (includes CLI start-up); ON = measured in-process Keel time + that LLM time only when a call is needed.

## Held-out results by τ (holdout-20 + holdout-b-20 + open-60)

| τ | LLM calls (avoided) | Questions deferred | A tokens OFF → ON | A cut | A+reasoning cut | B Copilot-subagent tokens OFF → ON | C in-context OFF → ON | C cut | Cases fully right OFF → ON (Δ) | Safety misses OFF → ON | Regr. / impr. | Latency median OFF → ON | Latency mean OFF → ON |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 33/100 (67) | 33/116 | 24,830 → 7,598 | 69.4% | 70.8% | 2,164,128 → 714,162 (67%) | 2,361 → 19,505 | -726.1% | 75/100 → 66/100 (-9) | 2 → 3 | 16 / 7 | 43.9 s → 34 ms | 48.1 s → 17.3 s |
| 0.6 | 41/100 (59) | 44/116 | 24,830 → 9,790 | 60.6% | 61.5% | 2,164,128 → 887,293 (59%) | 2,361 → 19,729 | -735.6% | 75/100 → 69/100 (-6) | 2 → 3 | 12 / 6 | 43.9 s → 38 ms | 48.1 s → 21.5 s |
| 0.7 | 49/100 (51) | 54/116 | 24,830 → 11,796 | 52.5% | 53.1% | 2,164,128 → 1,060,423 (51%) | 2,361 → 19,932 | -744.2% | 75/100 → 68/100 (-7) | 2 → 3 | 11 / 4 | 43.9 s → 68 ms | 48.1 s → 25.0 s |
| 0.8 | 61/100 (39) | 68/116 | 24,830 → 14,749 | 40.6% | 41.1% | 2,164,128 → 1,320,118 (39%) | 2,361 → 20,217 | -756.3% | 75/100 → 70/100 (-5) | 2 → 2 | 9 / 4 | 43.9 s → 37.5 s | 48.1 s → 30.4 s |
| 0.9 | 75/100 (25) | 84/116 | 24,830 → 18,170 | 26.8% | 27.3% | 2,164,128 → 1,623,096 (25%) | 2,361 → 20,543 | -770.1% | 75/100 → 70/100 (-5) | 2 → 2 | 7 / 2 | 43.9 s → 40.9 s | 48.1 s → 36.5 s |

## Blind suite by τ (data-1, 234 cases; never inspected by hand)

Token columns cover all 234 blind cases. Accuracy covers only the 71 blind cases with a real claude-haiku-4.5 answer (no gpt-5-mini cache exists for blind), so OFF accuracy here is claude-haiku-4.5, not gpt-5-mini; OFF latency uses those calls' wall time.

| τ | LLM calls (avoided) | Questions deferred | A tokens OFF → ON | A cut | A+reasoning cut | B Copilot-subagent tokens OFF → ON | C in-context OFF → ON | C cut | Cases fully right OFF → ON (Δ) | Safety misses OFF → ON | Regr. / impr. | Latency median OFF → ON | Latency mean OFF → ON |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 73/234 (161) | 73/234 | 57,934 → 19,167 | 66.9% | 68% | 5,064,060 → 1,579,814 (68.8%) | 4,764 → 44,407 | -832.1% | 64/71 → 44/71 (-28.2) | 0 → 3 | 23 / 3 | 61.9 s → 27 ms | 62.2 s → 21.4 s |
| 0.6 | 111/234 (123) | 111/234 | 57,934 → 28,516 | 50.8% | 51.8% | 5,064,060 → 2,402,182 (52.6%) | 4,764 → 45,181 | -848.4% | 64/71 → 49/71 (-21.1) | 0 → 3 | 16 / 1 | 61.9 s → 34.6 s | 62.2 s → 34.3 s |
| 0.7 | 141/234 (93) | 141/234 | 57,934 → 36,143 | 37.6% | 38.9% | 5,064,060 → 3,051,421 (39.7%) | 4,764 → 45,791 | -861.2% | 64/71 → 51/71 (-18.3) | 0 → 3 | 13 / 0 | 61.9 s → 50.1 s | 62.2 s → 43.1 s |
| 0.8 | 168/234 (66) | 168/234 | 57,934 → 42,388 | 26.8% | 27.7% | 5,064,060 → 3,635,735 (28.2%) | 4,764 → 46,341 | -872.7% | 64/71 → 57/71 (-9.9) | 0 → 2 | 7 / 0 | 61.9 s → 54.7 s | 62.2 s → 50.1 s |
| 0.9 | 207/234 (27) | 207/234 | 57,934 → 51,546 | 11% | 11.3% | 5,064,060 → 4,479,746 (11.5%) | 4,764 → 47,135 | -889.4% | 64/71 → 62/71 (-2.8) | 0 → 1 | 2 / 0 | 61.9 s → 59.8 s | 62.2 s → 58.3 s |

### Scenario C sensitivity (held-out, τ = 0.6; real per-question deliberation rates)

Keel overhead the agent pays in-context: 18,833 tokens (tool-call bodies + responses) for 72 of 116 questions answered locally. **Break-even: Keel saves tokens in C only if the agent would otherwise spend > 262 reasoning+output tokens per question.**

| Measured model (Copilot CLI) | Calls | Reasoning / q | Output / q | C OFF → ON | C cut |
|---|---:|---:|---:|---:|---:|
| claude-haiku-4.5 | 92 | 366.7 | 419.0 | 91,139 → 53,403 | 41.4% |
| claude-sonnet-5 | 1 | 0.0 | 33.0 | 3,828 → 20,285 | -429.9% |
| gpt-5.6-terra | 12 | 0.0 | 20.4 | 2,361 → 19,729 | -735.5% |
| gpt-5.6-terra@high | 12 | 0.0 | 20.4 | 2,361 → 19,729 | -735.5% |
| gpt-5.6-terra@medium | 10 | 1.5 | 24.5 | 3,027 → 19,981 | -560.2% |

Keel in-process latency on held-out: median 25 ms, p95 57 ms (CPU, ONNX int8, sequential, warmed).

## Per suite (τ = 0.6)

| Suite | Cases | LLM answers from | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---|---:|---:|---:|---:|
| holdout-20 | 20 | gpt-5-mini | 5,479 → 1,787 (67.4%) | 13/20 | 16 → 17 /20 | 0 → 1 |
| holdout-b-20 | 20 | gpt-5-mini | 5,683 → 1,854 (67.4%) | 13/20 | 13 → 11 /20 | 1 → 1 |
| open-60 | 60 | gpt-5-mini | 13,668 → 6,149 (55%) | 33/60 | 46 → 41 /60 | 1 → 1 |
| labeled-50 (in training mix) | 50 | gpt-5-mini | 13,305 → 2,401 (82%) | 40/50 | 42 → 49 /50 | 1 → 0 |
| blind-234 | 234 | claude-haiku-4.5 | 57,934 → 28,516 (50.8%) | 123/234 | 64 → 49 /71 | 0 → 3 |
| held-out total | 100 | gpt-5-mini | 24,830 → 9,790 (60.6%) | 59/100 | 75 → 69 /100 | 2 → 3 |
| blind | 234 | claude-haiku-4.5 | 57,934 → 28,516 (50.8%) | 123/234 | 64 → 49 /71 | 0 → 3 |

## Per agent workload (held-out, τ = 0.6)

Workload is inferred from the first question's shape (edit/ask/stop keys, moderation/PR/tool wording, score, noul). Small n per row — treat as indicative.

| Workload | Cases | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---:|---:|---:|---:|
| edit/ask/stop gating | 8 | 2,586 → 551 (78.7%) | 6/8 | 6 → 7 /8 | 0 → 1 |
| guardrail yes/no | 14 | 2,810 → 1,865 (33.6%) | 5/14 | 7 → 7 /14 | 0 → 0 |
| moderation | 5 | 1,167 → 702 (39.8%) | 2/5 | 3 → 4 /5 | 1 → 1 |
| routing/triage | 53 | 13,593 → 4,058 (70.1%) | 37/53 | 42 → 37 /53 | 1 → 1 |
| severity scoring | 20 | 4,674 → 2,614 (44.1%) | 9/20 | 17 → 14 /20 | 0 → 0 |

## Real LLM measurements (Copilot CLI, `--usage-output-file`)

- **claude-haiku-4.5** — 92 decision calls (3 unparseable): mean input 21,213 tokens (harness-only baseline call: 20,979; decision prompt adds 234 in the model's own tokenizer vs 229 o200k), mean output 428, of which reasoning 375; per question: reasoning 366.7, output 419.0. Median API time 6.3 s, median wall time 55.0 s (CLI start-up included). Copilot premium-request cost 0.32/call.
- **gpt-5.6-terra** — 12 decision calls: mean input 17,505 tokens (harness-only baseline call: 17,308; decision prompt adds 197 in the model's own tokenizer vs 214 o200k), mean output 24, of which reasoning 0; per question: reasoning 0.0, output 20.4. Median API time 1.8 s, median wall time 51.2 s (CLI start-up included). Copilot premium-request cost 1.00/call.
- Real calls made by this script so far: 140 / 150 budget (ledger: `artifacts/parity/tokens/calls-ledger.json`).

## Caveats

- Savings scale with how often Keel is confident; that is model- and workload-dependent. The accuracy columns are there so a cut never hides a quality loss: read Δ and safety misses next to every token number.
- Held-out sets are small (±10–15 pts on accuracy). labeled-50 is in Keel's training mix and is excluded from the held-out totals.
- OFF accuracy is gpt-5-mini via Copilot CLI (Sept 2026 cache); gpt-5-mini is no longer selectable in this CLI, so new real measurements use claude-haiku-4.5/gpt-5.6-terra. Token counts for A are model-independent (o200k); B and C rates are specific to the measured models.
- Keel itself spends 0 LLM tokens (local ONNX). Its CPU cost is in the latency column.
