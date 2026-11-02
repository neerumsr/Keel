# Keel token-savings benchmark

Generated 2026-10-29T07:01:56.037Z by `scripts/keel-tokens.ts`. Keel: `decider-3.0.0-pro-rc` from `models/candidates/t2-dxs-b2`.
Suites: holdout-20 (20), holdout-b-20 (20), open-60 (60), labeled-50 (50), blind-234 (234), held-out total (100), blind (234). Blind suite: loaded 234 cases from eval-blind.ts.

**Headline (held-out, τ = 0.6, dedicated decision sub-call, tokenizer-exact):** 24,830 → 9,676 LLM tokens (**61% fewer**), 60/100 LLM calls avoided, accuracy 75/100 → 88/100 cases fully right (**+13 pts**), safety misses 2 → 3.

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
| 0.5 | 30/100 (70) | 31/116 | 24,830 → 7,088 | 71.5% | 72.6% | 2,164,128 → 649,238 (70%) | 2,361 → 19,764 | -737.1% | 75/100 → 87/100 (+12) | 2 → 3 | 3 / 15 | 43.9 s → 108 ms | 48.1 s → 15.8 s |
| 0.6 | 40/100 (60) | 43/116 | 24,830 → 9,676 | 61% | 62.2% | 2,164,128 → 865,651 (60%) | 2,361 → 20,008 | -747.4% | 75/100 → 88/100 (+13) | 2 → 3 | 0 / 13 | 43.9 s → 124 ms | 48.1 s → 21.1 s |
| 0.7 | 51/100 (49) | 56/116 | 24,830 → 12,399 | 50.1% | 51.1% | 2,164,128 → 1,103,705 (49%) | 2,361 → 20,273 | -758.7% | 75/100 → 83/100 (+8) | 2 → 3 | 0 / 8 | 43.9 s → 34.8 s | 48.1 s → 25.7 s |
| 0.8 | 60/100 (40) | 67/116 | 24,830 → 14,726 | 40.7% | 41.7% | 2,164,128 → 1,298,477 (40%) | 2,361 → 20,497 | -768.1% | 75/100 → 80/100 (+5) | 2 → 2 | 0 / 5 | 43.9 s → 37.9 s | 48.1 s → 30.2 s |
| 0.9 | 69/100 (31) | 79/116 | 24,830 → 17,006 | 31.5% | 31.8% | 2,164,128 → 1,493,249 (31%) | 2,361 → 20,741 | -778.5% | 75/100 → 79/100 (+4) | 2 → 2 | 0 / 4 | 43.9 s → 40.9 s | 48.1 s → 34.4 s |

## Blind suite by τ (data-1, 234 cases; never inspected by hand)

Token columns cover all 234 blind cases. Accuracy covers only the 71 blind cases with a real claude-haiku-4.5 answer (no gpt-5-mini cache exists for blind), so OFF accuracy here is claude-haiku-4.5, not gpt-5-mini; OFF latency uses those calls' wall time.

| τ | LLM calls (avoided) | Questions deferred | A tokens OFF → ON | A cut | A+reasoning cut | B Copilot-subagent tokens OFF → ON | C in-context OFF → ON | C cut | Cases fully right OFF → ON (Δ) | Safety misses OFF → ON | Regr. / impr. | Latency median OFF → ON | Latency mean OFF → ON |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 100/234 (134) | 100/234 | 57,934 → 26,097 | 55% | 56.3% | 5,064,060 → 2,164,128 (57.3%) | 4,764 → 45,601 | -857.2% | 64/71 → 63/71 (-1.4) | 0 → 2 | 6 / 5 | 61.9 s → 134 ms | 62.2 s → 29.7 s |
| 0.6 | 136/234 (98) | 136/234 | 57,934 → 34,753 | 40% | 41.1% | 5,064,060 → 2,943,214 (41.9%) | 4,764 → 46,334 | -872.6% | 64/71 → 64/71 (+0) | 0 → 1 | 3 / 3 | 61.9 s → 42.5 s | 62.2 s → 37.7 s |
| 0.7 | 158/234 (76) | 158/234 | 57,934 → 39,967 | 31% | 31.9% | 5,064,060 → 3,419,323 (32.5%) | 4,764 → 46,781 | -882% | 64/71 → 63/71 (-1.4) | 0 → 1 | 3 / 2 | 61.9 s → 53.5 s | 62.2 s → 44.2 s |
| 0.8 | 181/234 (53) | 181/234 | 57,934 → 45,264 | 21.9% | 22.3% | 5,064,060 → 3,917,072 (22.6%) | 4,764 → 47,250 | -891.8% | 64/71 → 64/71 (+0) | 0 → 1 | 1 / 1 | 61.9 s → 58.4 s | 62.2 s → 50.3 s |
| 0.9 | 214/234 (20) | 214/234 | 57,934 → 53,137 | 8.3% | 8.4% | 5,064,060 → 4,631,234 (8.5%) | 4,764 → 47,921 | -905.9% | 64/71 → 63/71 (-1.4) | 0 → 1 | 1 / 0 | 61.9 s → 61.9 s | 62.2 s → 57.8 s |

### Scenario C sensitivity (held-out, τ = 0.6; real per-question deliberation rates)

Keel overhead the agent pays in-context: 19,133 tokens (tool-call bodies + responses) for 73 of 116 questions answered locally. **Break-even: Keel saves tokens in C only if the agent would otherwise spend > 262 reasoning+output tokens per question.**

| Measured model (Copilot CLI) | Calls | Reasoning / q | Output / q | C OFF → ON | C cut |
|---|---:|---:|---:|---:|---:|
| claude-haiku-4.5 | 92 | 366.7 | 419.0 | 91,139 → 52,917 | 41.9% |
| claude-sonnet-5 | 1 | 0.0 | 33.0 | 3,828 → 20,552 | -436.9% |
| gpt-5.6-terra | 12 | 0.0 | 20.4 | 2,361 → 20,008 | -747.3% |
| gpt-5.6-terra@high | 12 | 0.0 | 20.4 | 2,361 → 20,008 | -747.3% |
| gpt-5.6-terra@medium | 10 | 1.5 | 24.5 | 3,027 → 20,255 | -569.2% |

Keel in-process latency on held-out: median 105 ms, p95 212 ms (CPU, ONNX int8, sequential, warmed).

## Per suite (τ = 0.6)

| Suite | Cases | LLM answers from | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---|---:|---:|---:|---:|
| holdout-20 | 20 | gpt-5-mini | 5,479 → 2,301 (58%) | 11/20 | 16 → 18 /20 | 0 → 1 |
| holdout-b-20 | 20 | gpt-5-mini | 5,683 → 3,185 (44%) | 7/20 | 13 → 15 /20 | 1 → 2 |
| open-60 | 60 | gpt-5-mini | 13,668 → 4,190 (69.3%) | 42/60 | 46 → 55 /60 | 1 → 0 |
| labeled-50 (in training mix) | 50 | gpt-5-mini | 13,305 → 4,919 (63%) | 30/50 | 42 → 45 /50 | 1 → 0 |
| blind-234 | 234 | claude-haiku-4.5 | 57,934 → 34,753 (40%) | 98/234 | 64 → 64 /71 | 0 → 1 |
| held-out total | 100 | gpt-5-mini | 24,830 → 9,676 (61%) | 60/100 | 75 → 88 /100 | 2 → 3 |
| blind | 234 | claude-haiku-4.5 | 57,934 → 34,753 (40%) | 98/234 | 64 → 64 /71 | 0 → 1 |

## Per agent workload (held-out, τ = 0.6)

Workload is inferred from the first question's shape (edit/ask/stop keys, moderation/PR/tool wording, score, noul). Small n per row — treat as indicative.

| Workload | Cases | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---:|---:|---:|---:|
| edit/ask/stop gating | 8 | 2,586 → 1,791 (30.7%) | 1/8 | 6 → 7 /8 | 0 → 1 |
| guardrail yes/no | 14 | 2,810 → 615 (78.1%) | 11/14 | 7 → 12 /14 | 0 → 0 |
| moderation | 5 | 1,167 → 681 (41.6%) | 2/5 | 3 → 5 /5 | 1 → 0 |
| routing/triage | 53 | 13,593 → 3,269 (76%) | 40/53 | 42 → 46 /53 | 1 → 2 |
| severity scoring | 20 | 4,674 → 3,320 (29%) | 6/20 | 17 → 18 /20 | 0 → 0 |

## Real LLM measurements (Copilot CLI, `--usage-output-file`)

- **claude-haiku-4.5** — 92 decision calls (3 unparseable): mean input 21,213 tokens (harness-only baseline call: 20,979; decision prompt adds 234 in the model's own tokenizer vs 229 o200k), mean output 428, of which reasoning 375; per question: reasoning 366.7, output 419.0. Median API time 6.3 s, median wall time 55.0 s (CLI start-up included). Copilot premium-request cost 0.32/call.
- **gpt-5.6-terra** — 12 decision calls: mean input 17,505 tokens (harness-only baseline call: 17,308; decision prompt adds 197 in the model's own tokenizer vs 214 o200k), mean output 24, of which reasoning 0; per question: reasoning 0.0, output 20.4. Median API time 1.8 s, median wall time 51.2 s (CLI start-up included). Copilot premium-request cost 1.00/call.
- Real calls made by this script so far: 140 / 150 budget (ledger: `artifacts/parity/tokens/calls-ledger.json`).

## Caveats

- Savings scale with how often Keel is confident; that is model- and workload-dependent. The accuracy columns are there so a cut never hides a quality loss: read Δ and safety misses next to every token number.
- Held-out sets are small (±10–15 pts on accuracy). labeled-50 is in Keel's training mix and is excluded from the held-out totals.
- OFF accuracy is gpt-5-mini via Copilot CLI (Sept 2026 cache); gpt-5-mini is no longer selectable in this CLI, so new real measurements use claude-haiku-4.5/gpt-5.6-terra. Token counts for A are model-independent (o200k); B and C rates are specific to the measured models.
- Keel itself spends 0 LLM tokens (local ONNX). Its CPU cost is in the latency column.
