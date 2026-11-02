# Keel token-savings benchmark

Generated 2026-10-29T06:59:03.442Z by `scripts/keel-tokens.ts`. Keel: `decider-3.0.0-rc.t1-r2e` from `models/candidates/t1-r2e`.
Suites: holdout-20 (20), holdout-b-20 (20), open-60 (60), labeled-50 (50), blind-234 (234), held-out total (100), blind (234). Blind suite: loaded 234 cases from eval-blind.ts.

**Headline (held-out, τ = 0.6, dedicated decision sub-call, tokenizer-exact):** 24,830 → 6,019 LLM tokens (**75.8% fewer**), 75/100 LLM calls avoided, accuracy 75/100 → 89/100 cases fully right (**+14 pts**), safety misses 2 → 2.

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
| 0.5 | 15/100 (85) | 15/116 | 24,830 → 3,600 | 85.5% | 86.5% | 2,164,128 → 324,619 (85%) | 2,361 → 19,839 | -740.3% | 75/100 → 89/100 (+14) | 2 → 1 | 5 / 19 | 43.9 s → 22 ms | 48.1 s → 6.5 s |
| 0.6 | 25/100 (75) | 25/116 | 24,830 → 6,019 | 75.8% | 77.5% | 2,164,128 → 541,032 (75%) | 2,361 → 20,043 | -748.9% | 75/100 → 89/100 (+14) | 2 → 2 | 3 / 17 | 43.9 s → 22 ms | 48.1 s → 11.7 s |
| 0.7 | 37/100 (63) | 37/116 | 24,830 → 8,772 | 64.7% | 66.8% | 2,164,128 → 800,727 (63%) | 2,361 → 20,287 | -759.3% | 75/100 → 90/100 (+15) | 2 → 2 | 1 / 16 | 43.9 s → 24 ms | 48.1 s → 17.2 s |
| 0.8 | 43/100 (57) | 44/116 | 24,830 → 10,296 | 58.5% | 60.8% | 2,164,128 → 930,575 (57%) | 2,361 → 20,430 | -765.3% | 75/100 → 88/100 (+13) | 2 → 2 | 0 / 13 | 43.9 s → 30 ms | 48.1 s → 19.7 s |
| 0.9 | 52/100 (48) | 53/116 | 24,830 → 12,264 | 50.6% | 52.9% | 2,164,128 → 1,125,347 (48%) | 2,361 → 20,613 | -773.1% | 75/100 → 86/100 (+11) | 2 → 2 | 0 / 11 | 43.9 s → 34.7 s | 48.1 s → 23.7 s |

## Blind suite by τ (data-1, 234 cases; never inspected by hand)

Token columns cover all 234 blind cases. Accuracy covers only the 71 blind cases with a real claude-haiku-4.5 answer (no gpt-5-mini cache exists for blind), so OFF accuracy here is claude-haiku-4.5, not gpt-5-mini; OFF latency uses those calls' wall time.

| τ | LLM calls (avoided) | Questions deferred | A tokens OFF → ON | A cut | A+reasoning cut | B Copilot-subagent tokens OFF → ON | C in-context OFF → ON | C cut | Cases fully right OFF → ON (Δ) | Safety misses OFF → ON | Regr. / impr. | Latency median OFF → ON | Latency mean OFF → ON |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 85/234 (149) | 85/234 | 57,934 → 22,725 | 60.8% | 62.5% | 5,064,060 → 1,839,509 (63.7%) | 4,764 → 46,255 | -870.9% | 64/71 → 59/71 (-7) | 0 → 3 | 9 / 4 | 61.9 s → 26 ms | 62.2 s → 23.5 s |
| 0.6 | 124/234 (110) | 124/234 | 57,934 → 31,919 | 44.9% | 46.2% | 5,064,060 → 2,683,519 (47%) | 4,764 → 47,049 | -887.6% | 64/71 → 63/71 (-1.4) | 0 → 1 | 3 / 2 | 61.9 s → 35.8 s | 62.2 s → 35.8 s |
| 0.7 | 160/234 (74) | 160/234 | 57,934 → 40,443 | 30.2% | 31% | 5,064,060 → 3,462,605 (31.6%) | 4,764 → 47,782 | -903% | 64/71 → 63/71 (-1.4) | 0 → 1 | 2 / 1 | 61.9 s → 48.3 s | 62.2 s → 42.9 s |
| 0.8 | 179/234 (55) | 179/234 | 57,934 → 44,636 | 23% | 23.3% | 5,064,060 → 3,873,790 (23.5%) | 4,764 → 48,169 | -911.1% | 64/71 → 63/71 (-1.4) | 0 → 1 | 2 / 1 | 61.9 s → 52.1 s | 62.2 s → 47.6 s |
| 0.9 | 209/234 (25) | 209/234 | 57,934 → 51,757 | 10.7% | 10.7% | 5,064,060 → 4,523,028 (10.7%) | 4,764 → 48,780 | -923.9% | 64/71 → 65/71 (+1.4) | 0 → 0 | 0 / 1 | 61.9 s → 59.0 s | 62.2 s → 53.3 s |

### Scenario C sensitivity (held-out, τ = 0.6; real per-question deliberation rates)

Keel overhead the agent pays in-context: 19,534 tokens (tool-call bodies + responses) for 91 of 116 questions answered locally. **Break-even: Keel saves tokens in C only if the agent would otherwise spend > 215 reasoning+output tokens per question.**

| Measured model (Copilot CLI) | Calls | Reasoning / q | Output / q | C OFF → ON | C cut |
|---|---:|---:|---:|---:|---:|
| claude-haiku-4.5 | 92 | 366.7 | 419.0 | 91,139 → 39,176 | 57% |
| claude-sonnet-5 | 1 | 0.0 | 33.0 | 3,828 → 20,359 | -431.8% |
| gpt-5.6-terra | 12 | 0.0 | 20.4 | 2,361 → 20,043 | -748.8% |
| gpt-5.6-terra@high | 12 | 0.0 | 20.4 | 2,361 → 20,043 | -748.8% |
| gpt-5.6-terra@medium | 10 | 1.5 | 24.5 | 3,027 → 20,186 | -567% |

Keel in-process latency on held-out: median 19 ms, p95 36 ms (CPU, ONNX int8, sequential, warmed).

## Per suite (τ = 0.6)

| Suite | Cases | LLM answers from | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---|---:|---:|---:|---:|
| holdout-20 | 20 | gpt-5-mini | 5,479 → 536 (90.2%) | 18/20 | 16 → 18 /20 | 0 → 0 |
| holdout-b-20 | 20 | gpt-5-mini | 5,683 → 1,961 (65.5%) | 12/20 | 13 → 18 /20 | 1 → 1 |
| open-60 | 60 | gpt-5-mini | 13,668 → 3,522 (74.2%) | 45/60 | 46 → 53 /60 | 1 → 1 |
| labeled-50 (in training mix) | 50 | gpt-5-mini | 13,305 → 692 (94.8%) | 47/50 | 42 → 50 /50 | 1 → 0 |
| blind-234 | 234 | claude-haiku-4.5 | 57,934 → 31,919 (44.9%) | 110/234 | 64 → 63 /71 | 0 → 1 |
| held-out total | 100 | gpt-5-mini | 24,830 → 6,019 (75.8%) | 75/100 | 75 → 89 /100 | 2 → 2 |
| blind | 234 | claude-haiku-4.5 | 57,934 → 31,919 (44.9%) | 110/234 | 64 → 63 /71 | 0 → 1 |

## Per agent workload (held-out, τ = 0.6)

Workload is inferred from the first question's shape (edit/ask/stop keys, moderation/PR/tool wording, score, noul). Small n per row — treat as indicative.

| Workload | Cases | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---:|---:|---:|---:|
| edit/ask/stop gating | 8 | 2,586 → 0 (100%) | 8/8 | 6 → 7 /8 | 0 → 0 |
| guardrail yes/no | 14 | 2,810 → 0 (100%) | 14/14 | 7 → 14 /14 | 0 → 0 |
| moderation | 5 | 1,167 → 465 (60.2%) | 3/5 | 3 → 2 /5 | 1 → 1 |
| routing/triage | 53 | 13,593 → 2,704 (80.1%) | 42/53 | 42 → 49 /53 | 1 → 1 |
| severity scoring | 20 | 4,674 → 2,850 (39%) | 8/20 | 17 → 17 /20 | 0 → 0 |

## Real LLM measurements (Copilot CLI, `--usage-output-file`)

- **claude-haiku-4.5** — 92 decision calls (3 unparseable): mean input 21,213 tokens (harness-only baseline call: 20,979; decision prompt adds 234 in the model's own tokenizer vs 229 o200k), mean output 428, of which reasoning 375; per question: reasoning 366.7, output 419.0. Median API time 6.3 s, median wall time 55.0 s (CLI start-up included). Copilot premium-request cost 0.32/call.
- **gpt-5.6-terra** — 12 decision calls: mean input 17,505 tokens (harness-only baseline call: 17,308; decision prompt adds 197 in the model's own tokenizer vs 214 o200k), mean output 24, of which reasoning 0; per question: reasoning 0.0, output 20.4. Median API time 1.8 s, median wall time 51.2 s (CLI start-up included). Copilot premium-request cost 1.00/call.
- Real calls made by this script so far: 140 / 150 budget (ledger: `artifacts/parity/tokens/calls-ledger.json`).

## Caveats

- Savings scale with how often Keel is confident; that is model- and workload-dependent. The accuracy columns are there so a cut never hides a quality loss: read Δ and safety misses next to every token number.
- Held-out sets are small (±10–15 pts on accuracy). labeled-50 is in Keel's training mix and is excluded from the held-out totals.
- OFF accuracy is gpt-5-mini via Copilot CLI (Sept 2026 cache); gpt-5-mini is no longer selectable in this CLI, so new real measurements use claude-haiku-4.5/gpt-5.6-terra. Token counts for A are model-independent (o200k); B and C rates are specific to the measured models.
- Keel itself spends 0 LLM tokens (local ONNX). Its CPU cost is in the latency column.
