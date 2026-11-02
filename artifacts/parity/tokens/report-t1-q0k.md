# Keel token-savings benchmark

Generated 2026-10-29T04:52:24.513Z by `scripts/keel-tokens.ts`. Keel: `decider-3.0.0-rc.t1-q0k` from `models/candidates/t1-q0k`.
Suites: holdout-20 (20), holdout-b-20 (20), open-60 (60), labeled-50 (50), blind-234 (234), held-out total (100), blind (234). Blind suite: loaded 234 cases from eval-blind.ts.

**Headline (held-out, τ = 0.6, dedicated decision sub-call, tokenizer-exact):** 24,830 → 6,372 LLM tokens (**74.3% fewer**), 73/100 LLM calls avoided, accuracy 75/100 → 73/100 cases fully right (**-2 pts**), safety misses 2 → 3.

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
| 0.5 | 15/100 (85) | 15/116 | 24,830 → 3,458 | 86.1% | 86.7% | 2,164,128 → 324,619 (85%) | 2,361 → 19,848 | -740.7% | 75/100 → 73/100 (-2) | 2 → 3 | 12 / 10 | 43.9 s → 19 ms | 48.1 s → 6.8 s |
| 0.6 | 27/100 (73) | 27/116 | 24,830 → 6,372 | 74.3% | 75.8% | 2,164,128 → 584,315 (73%) | 2,361 → 20,093 | -751% | 75/100 → 73/100 (-2) | 2 → 3 | 11 / 9 | 43.9 s → 22 ms | 48.1 s → 11.9 s |
| 0.7 | 39/100 (61) | 39/116 | 24,830 → 9,081 | 63.4% | 65.3% | 2,164,128 → 844,010 (61%) | 2,361 → 20,337 | -761.4% | 75/100 → 72/100 (-3) | 2 → 2 | 10 / 7 | 43.9 s → 26 ms | 48.1 s → 17.3 s |
| 0.8 | 48/100 (52) | 49/116 | 24,830 → 11,253 | 54.7% | 56.6% | 2,164,128 → 1,038,782 (52%) | 2,361 → 20,541 | -770% | 75/100 → 73/100 (-2) | 2 → 2 | 8 / 6 | 43.9 s → 34 ms | 48.1 s → 21.9 s |
| 0.9 | 59/100 (41) | 60/116 | 24,830 → 13,740 | 44.7% | 46.9% | 2,164,128 → 1,276,836 (41%) | 2,361 → 20,764 | -779.5% | 75/100 → 75/100 (+0) | 2 → 2 | 5 / 5 | 43.9 s → 37.1 s | 48.1 s → 26.9 s |

## Blind suite by τ (data-1, 234 cases; never inspected by hand)

Token columns cover all 234 blind cases. Accuracy covers only the 71 blind cases with a real claude-haiku-4.5 answer (no gpt-5-mini cache exists for blind), so OFF accuracy here is claude-haiku-4.5, not gpt-5-mini; OFF latency uses those calls' wall time.

| τ | LLM calls (avoided) | Questions deferred | A tokens OFF → ON | A cut | A+reasoning cut | B Copilot-subagent tokens OFF → ON | C in-context OFF → ON | C cut | Cases fully right OFF → ON (Δ) | Safety misses OFF → ON | Regr. / impr. | Latency median OFF → ON | Latency mean OFF → ON |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 64/234 (170) | 64/234 | 57,934 → 16,895 | 70.8% | 71.9% | 5,064,060 → 1,385,042 (72.6%) | 4,764 → 45,841 | -862.2% | 64/71 → 45/71 (-26.8) | 0 → 2 | 21 / 2 | 61.9 s → 24 ms | 62.2 s → 19.9 s |
| 0.6 | 98/234 (136) | 98/234 | 57,934 → 25,055 | 56.8% | 57.6% | 5,064,060 → 2,120,846 (58.1%) | 4,764 → 46,533 | -876.8% | 64/71 → 49/71 (-21.1) | 0 → 2 | 16 / 1 | 61.9 s → 86 ms | 62.2 s → 31.5 s |
| 0.7 | 125/234 (109) | 125/234 | 57,934 → 32,061 | 44.7% | 45.8% | 5,064,060 → 2,705,160 (46.6%) | 4,764 → 47,083 | -888.3% | 64/71 → 54/71 (-14.1) | 0 → 2 | 11 / 1 | 61.9 s → 43.8 s | 62.2 s → 37.0 s |
| 0.8 | 146/234 (88) | 146/234 | 57,934 → 36,745 | 36.6% | 37.2% | 5,064,060 → 3,159,627 (37.6%) | 4,764 → 47,510 | -897.3% | 64/71 → 56/71 (-11.3) | 0 → 2 | 9 / 1 | 61.9 s → 51.6 s | 62.2 s → 40.9 s |
| 0.9 | 174/234 (60) | 174/234 | 57,934 → 43,132 | 25.5% | 25.6% | 5,064,060 → 3,765,583 (25.6%) | 4,764 → 48,080 | -909.2% | 64/71 → 59/71 (-7) | 0 → 2 | 6 / 1 | 61.9 s → 55.0 s | 62.2 s → 46.7 s |

### Scenario C sensitivity (held-out, τ = 0.6; real per-question deliberation rates)

Keel overhead the agent pays in-context: 19,543 tokens (tool-call bodies + responses) for 89 of 116 questions answered locally. **Break-even: Keel saves tokens in C only if the agent would otherwise spend > 220 reasoning+output tokens per question.**

| Measured model (Copilot CLI) | Calls | Reasoning / q | Output / q | C OFF → ON | C cut |
|---|---:|---:|---:|---:|---:|
| claude-haiku-4.5 | 92 | 366.7 | 419.0 | 91,139 → 40,756 | 55.3% |
| claude-sonnet-5 | 1 | 0.0 | 33.0 | 3,828 → 20,434 | -433.8% |
| gpt-5.6-terra | 12 | 0.0 | 20.4 | 2,361 → 20,093 | -750.9% |
| gpt-5.6-terra@high | 12 | 0.0 | 20.4 | 2,361 → 20,093 | -750.9% |
| gpt-5.6-terra@medium | 10 | 1.5 | 24.5 | 3,027 → 20,247 | -569% |

Keel in-process latency on held-out: median 18 ms, p95 34 ms (CPU, ONNX int8, sequential, warmed).

## Per suite (τ = 0.6)

| Suite | Cases | LLM answers from | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---|---:|---:|---:|---:|
| holdout-20 | 20 | gpt-5-mini | 5,479 → 766 (86%) | 17/20 | 16 → 16 /20 | 0 → 1 |
| holdout-b-20 | 20 | gpt-5-mini | 5,683 → 1,246 (78.1%) | 15/20 | 13 → 15 /20 | 1 → 2 |
| open-60 | 60 | gpt-5-mini | 13,668 → 4,360 (68.1%) | 41/60 | 46 → 42 /60 | 1 → 0 |
| labeled-50 (in training mix) | 50 | gpt-5-mini | 13,305 → 718 (94.6%) | 47/50 | 42 → 50 /50 | 1 → 0 |
| blind-234 | 234 | claude-haiku-4.5 | 57,934 → 25,055 (56.8%) | 136/234 | 64 → 49 /71 | 0 → 2 |
| held-out total | 100 | gpt-5-mini | 24,830 → 6,372 (74.3%) | 73/100 | 75 → 73 /100 | 2 → 3 |
| blind | 234 | claude-haiku-4.5 | 57,934 → 25,055 (56.8%) | 136/234 | 64 → 49 /71 | 0 → 2 |

## Per agent workload (held-out, τ = 0.6)

Workload is inferred from the first question's shape (edit/ask/stop keys, moderation/PR/tool wording, score, noul). Small n per row — treat as indicative.

| Workload | Cases | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |
|---|---:|---:|---:|---:|---:|
| edit/ask/stop gating | 8 | 2,586 → 230 (91.1%) | 7/8 | 6 → 6 /8 | 0 → 1 |
| guardrail yes/no | 14 | 2,810 → 612 (78.2%) | 11/14 | 7 → 9 /14 | 0 → 0 |
| moderation | 5 | 1,167 → 924 (20.8%) | 1/5 | 3 → 4 /5 | 1 → 0 |
| routing/triage | 53 | 13,593 → 2,465 (81.9%) | 43/53 | 42 → 39 /53 | 1 → 2 |
| severity scoring | 20 | 4,674 → 2,141 (54.2%) | 11/20 | 17 → 15 /20 | 0 → 0 |

## Real LLM measurements (Copilot CLI, `--usage-output-file`)

- **claude-haiku-4.5** — 92 decision calls (3 unparseable): mean input 21,213 tokens (harness-only baseline call: 20,979; decision prompt adds 234 in the model's own tokenizer vs 229 o200k), mean output 428, of which reasoning 375; per question: reasoning 366.7, output 419.0. Median API time 6.3 s, median wall time 55.0 s (CLI start-up included). Copilot premium-request cost 0.32/call.
- **gpt-5.6-terra** — 12 decision calls: mean input 17,505 tokens (harness-only baseline call: 17,308; decision prompt adds 197 in the model's own tokenizer vs 214 o200k), mean output 24, of which reasoning 0; per question: reasoning 0.0, output 20.4. Median API time 1.8 s, median wall time 51.2 s (CLI start-up included). Copilot premium-request cost 1.00/call.
- Real calls made by this script so far: 140 / 150 budget (ledger: `artifacts/parity/tokens/calls-ledger.json`).

## Caveats

- Savings scale with how often Keel is confident; that is model- and workload-dependent. The accuracy columns are there so a cut never hides a quality loss: read Δ and safety misses next to every token number.
- Held-out sets are small (±10–15 pts on accuracy). labeled-50 is in Keel's training mix and is excluded from the held-out totals.
- OFF accuracy is gpt-5-mini via Copilot CLI (Sept 2026 cache); gpt-5-mini is no longer selectable in this CLI, so new real measurements use claude-haiku-4.5/gpt-5.6-terra. Token counts for A are model-independent (o200k); B and C rates are specific to the measured models.
- Keel itself spends 0 LLM tokens (local ONNX). Its CPU cost is in the latency column.
