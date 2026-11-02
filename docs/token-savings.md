# Token savings

How "Keel first, LLM fallback" cuts the LLM tokens an agent spends on decisions, how much it saved in our measurements, and when it does not help.

## The short version

On our held-out suites, putting the Keel-3 release candidate `t1-r2e` in front of a dedicated LLM decision call at **τ = 0.6** cut LLM tokens by **<!-- num:tok.k3.ho.cut -->75.8%<!-- /num -->** and *raised* accuracy from <!-- num:tok.k3.ho.acc -->75 → 89 of 100 cases fully right<!-- /num -->. On the harder blind suite, the cut was <!-- num:tok.k3.blind.cut -->44.9%<!-- /num -->, for a small accuracy loss (<!-- num:tok.k3.blind.acc -->64/71 → 63/71 (−1.4 pts)<!-- /num -->). When a strong agent already holds the text and answers in about 20 tokens, Keel **costs** tokens. All three facts matter, so this page shows all three.

> **Which model?** Every "Keel-3 RC" figure on this page was measured with `t1-r2e`, a release candidate. The promoted Keel-3 (`decider-3.0.0`, run `t1-r11`) has not been re-measured for tokens yet. It beats Keel-2 on blind and held-out but is worse on blind-c (see [Benchmarks](benchmarks.md#the-blind-c-regression)), so treat these as indicative until `npm run keel:tokens` is rerun.

<!-- diagram:token-bars -->

## How Keel saves tokens

An agent that makes a typed decision with an LLM pays for the decision prompt (instructions, state and the answer schema), any hidden reasoning, and the JSON answer. With Keel in front:

1. The agent sends the question to Keel. This costs no LLM tokens and about 20 ms of CPU.
2. Every answer with confidence ≥ τ is used directly.
3. Only the questions below τ go to the LLM, in one call that contains just those questions.

The saving is the share of questions Keel answers confidently, multiplied by the cost of the LLM call you skip. The accuracy effect depends on whether Keel's confident answers are better or worse than the LLM's on those cases. On held-out, they were better: Keel was confidently right on several cases the LLM got wrong.

## The τ gate

τ is the minimum confidence at which you accept Keel's answer. For choice and score, confidence is the reported `confidence`. For noul, it is 2·|P(yes) − 0.5|, so both 0.9 and 0.1 count as confident.

- **Lower τ** means more questions answered by Keel, so more savings, but more risk on hard inputs.
- **Higher τ** sends more to the LLM, so fewer savings and accuracy closer to the LLM alone.

Start at τ = 0.6, measure on your own traffic, then move it.

<!-- diagram:tau-curve -->

### Held-out suites, Keel-3 RC, by τ

These are the 100 cases in holdout-20, holdout-b-20 and open-60. Tokens are counted exactly with the o200k tokenizer (Scenario A below). The LLM is gpt-5-mini.

| τ | LLM calls avoided | LLM tokens OFF → ON | Cut | Cases fully right OFF → ON | Safety misses OFF → ON |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 85/100 | 24,830 → 3,600 | <!-- num:tok.k3.ho.cut.t05 -->85.5%<!-- /num --> | 75 → 89 | 2 → 1 |
| **0.6** | **75/100** | **24,830 → 6,019** | **<!-- num:tok.k3.ho.cut -->75.8%<!-- /num -->** | **75 → 89** | **2 → 2** |
| 0.7 | 63/100 | 24,830 → 8,772 | <!-- num:tok.k3.ho.cut.t07 -->64.7%<!-- /num --> | 75 → 90 | 2 → 2 |
| 0.8 | 57/100 | 24,830 → 10,296 | <!-- num:tok.k3.ho.cut.t08 -->58.5%<!-- /num --> | 75 → 88 | 2 → 2 |
| 0.9 | 48/100 | 24,830 → 12,264 | <!-- num:tok.k3.ho.cut.t09 -->50.6%<!-- /num --> | 75 → 86 | 2 → 2 |

### Blind suite, Keel-3 RC, by τ

The 234 blind cases were written by a separate author and never inspected while training. Token columns cover all 234 cases. Accuracy covers only the 71 cases that have a real claude-haiku-4.5 answer, so the OFF column here is claude-haiku-4.5.

| τ | LLM calls avoided | LLM tokens OFF → ON | Cut | Cases fully right OFF → ON | Safety misses OFF → ON |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 149/234 | 57,934 → 22,725 | <!-- num:tok.k3.blind.cut.t05 -->60.8%<!-- /num --> | 64 → 59 of 71 | 0 → 3 |
| **0.6** | **110/234** | **57,934 → 31,919** | **<!-- num:tok.k3.blind.cut -->44.9%<!-- /num -->** | **64 → 63 of 71** | **0 → 1** |
| 0.7 | 74/234 | 57,934 → 40,443 | <!-- num:tok.k3.blind.cut.t07 -->30.2%<!-- /num --> | 64 → 63 of 71 | 0 → 1 |
| 0.8 | 55/234 | 57,934 → 44,636 | <!-- num:tok.k3.blind.cut.t08 -->23%<!-- /num --> | 64 → 63 of 71 | 0 → 1 |
| 0.9 | 25/234 | 57,934 → 51,757 | <!-- num:tok.k3.blind.cut.t09 -->10.7%<!-- /num --> | 64 → 65 of 71 | 0 → 0 |

On the blind suite, τ = 0.5 is too aggressive: it saves the most, but accuracy drops by 7 cases and three safety misses appear. On unfamiliar traffic, use τ ≥ 0.6.

### Keel-2 (`decider-2.0.0`, pinnable) at τ = 0.6

| Suite | LLM calls avoided | Cut | Cases fully right OFF → ON | Safety misses OFF → ON |
|---|---:|---:|---:|---:|
| Held-out 100 | <!-- num:tok.k2.ho.avoided -->59/100<!-- /num --> | <!-- num:tok.k2.ho.cut -->60.6%<!-- /num --> | 75 → 69 (−<!-- num:tok.k2.ho.accdelta -->6<!-- /num -->) | 2 → 3 |
| Blind 234 | not reported | <!-- num:tok.k2.blind.cut -->50.8%<!-- /num --> | <!-- num:tok.k2.blind.acc -->64 → 49 of 71<!-- /num --> | 0 → 3 |

Keel-2 saves tokens but loses accuracy, badly so on blind. This is the main reason Keel-3 is being trained. If you deploy Keel-2 today, use τ ≥ 0.8 and keep safety-critical questions on the LLM.

## Three ways an agent can make a decision

The size of the saving depends on how your agent would make the decision without Keel.

| Scenario | What happens without Keel | Keel-3 RC result at τ = 0.6, held-out |
|---|---|---|
| **A. Dedicated decision call** | Your code sends a decision prompt to an LLM API and reads the JSON answer | <!-- num:tok.k3.ho.cut -->75.8%<!-- /num --> fewer tokens |
| **B. Sub-agent call** | The agent spawns a sub-agent (for example `copilot -p`) per decision, which carries the harness's own system prompt and tool schema, about 21k input tokens per call | <!-- num:tok.k3.scB -->2,164,128 → 541,032 tokens (75%)<!-- /num --> |
| **C. In-context deliberation** | The agent already has the text in its context and reasons about the decision itself | Depends on the model. See below. |

### Scenario C: when it pays and when it costs

In Scenario C, using Keel means the agent must write a tool call and read Keel's JSON back. That overhead was about 19,500 tokens over the 91 questions Keel answered on held-out. Keel saves tokens only if the agent would otherwise spend more than **<!-- num:tok.k3.breakeven -->215<!-- /num --> reasoning-plus-output tokens per question**.

| Model making the decision in context | Measured tokens per question | Effect of Keel |
|---|---:|---:|
| claude-haiku-4.5 | 366.7 reasoning + 419.0 output | <!-- num:tok.k3.scC.haiku -->57%<!-- /num --> fewer tokens |
| claude-sonnet-5 (1 call) | 0 reasoning + 33 output | <!-- num:tok.k3.scC.sonnet -->431.8%<!-- /num --> more tokens |
| gpt-5.6-terra | 0 reasoning + 20.4 output | <!-- num:tok.k3.scC.terra -->748.8%<!-- /num --> more tokens |

The one-time Keel instruction block in the agent's system prompt (931 tokens, prompt-cached per session) is excluded from these per-decision totals.

## When Keel does not save tokens

Be honest with yourself about these cases:

- **The agent answers tersely in context.** A frontier model that already holds the text and replies in about 20 tokens is cheaper than a tool round-trip. The break-even is about <!-- num:tok.k3.breakeven -->215<!-- /num --> tokens per question.
- **Keel is rarely confident on your traffic.** If most questions fall below τ, you pay for the Keel call *and* the LLM call. That costs no tokens but adds latency. Measure the defer rate first.
- **The decision needs long context.** Keel reads about 256 tokens per (state, option) pair. A decision that depends on page 40 of a contract belongs to the LLM.
- **The decision needs world knowledge or reasoning.** Arithmetic, multi-step logic and facts that are not in the state are LLM work.
- **Safety-critical gates.** Keel is not at zero safety misses yet. Keep a human or LLM on destructive actions, whatever τ says.

### Savings per workload

Held-out, τ = 0.6, Keel-3 RC. The rows are small, so treat them as indicative.

| Workload | Cases | Token cut | Calls avoided | Fully right OFF → ON |
|---|---:|---:|---:|---:|
| Edit / ask / stop gating | 8 | <!-- num:tok.k3.wl.gating -->100%<!-- /num --> | 8/8 | 6 → 7 |
| Guardrail yes/no | 14 | <!-- num:tok.k3.wl.guardrail -->100%<!-- /num --> | 14/14 | 7 → 14 |
| Routing and triage | 53 | <!-- num:tok.k3.wl.routing -->80.1%<!-- /num --> | 42/53 | 42 → 49 |
| Moderation | 5 | <!-- num:tok.k3.wl.moderation -->60.2%<!-- /num --> | 3/5 | 3 → 2 |
| Severity scoring | 20 | <!-- num:tok.k3.wl.severity -->39%<!-- /num --> | 8/20 | 17 → 17 |

Routing and guardrails save the most. Severity scoring saves the least, because score confidence is lower and Keel defers more often.

## How the numbers were measured

- **Script:** `scripts/keel-tokens.ts`, run as `npm run keel:tokens`. Results: `artifacts/parity/tokens/report-t1-r2e.md` (Keel-3 RC) and `report.md` (Keel-2).
- **Tokenizer:** `gpt-tokenizer` o200k_base, plus 6 framing tokens per LLM call.
- **OFF:** every decision is one LLM call, using the exact decision prompt from `scripts/keel-ab.ts`. The answers are real gpt-5-mini answers (held-out) and real claude-haiku-4.5 answers (blind).
- **ON:** Keel answers every question with confidence ≥ τ. If any question is below τ, one LLM call carries only the deferred questions.
- **Assumption:** the LLM answers a question the same way when it is asked fewer questions. Questions are independent in the prompt.
- **Small sets:** expect ±10–15 points of noise on accuracy. labeled-50 is in Keel's training mix and is excluded from every total.
- **gpt-5-mini** is no longer selectable in the Copilot CLI, so newer real measurements use claude-haiku-4.5 and gpt-5.6-terra.

## Measure your own savings

Your traffic is not our test suite. Measure before you claim a number.

1. **Log decisions.** For a day, log every typed decision your agent makes: the state, the question, the LLM answer, and the prompt and completion tokens.
2. **Replay through Keel.** Send each logged decision to Keel and store the full answer.
3. **Sweep τ.** For each τ from 0.5 to 0.9, count the questions Keel would answer, the tokens you would skip, and the cases where Keel's confident answer disagrees with the LLM's or with a human label.
4. **Pick τ** at the highest savings where disagreement on safety-relevant questions is zero.

```python
import json, requests, os
H = {"Authorization": f"Bearer {os.environ['KEEL_TOKEN']}"}
rows = [json.loads(l) for l in open("decisions.jsonl")]   # {state, question, llm_answer, llm_tokens}
for tau in (0.5, 0.6, 0.7, 0.8, 0.9):
    saved = agree = kept = 0
    for r in rows:
        a = requests.post("http://localhost:8080/api/v1/systemone", headers=H,
                          json={"state": r["state"], "questions": {"q": r["question"]}}).json()["answers"]["q"]
        conf = a.get("confidence", 2 * abs(a.get("noul", 0.5) - 0.5))
        if conf >= tau:
            kept += 1; saved += r["llm_tokens"]
            agree += a.get("choice") == r["llm_answer"]
    print(f"tau={tau}  keel answers {kept}/{len(rows)}  tokens saved {saved}  agreement {agree}/{kept or 1}")
```

The repository's own harness does the same against the built-in suites:

```bash
npm run keel:ab       # Keel vs an LLM on the same decisions, with cached LLM answers
npm run keel:tokens   # token accounting for scenarios A, B and C across a τ sweep
```
