# Concepts

What Keel computes, how to read its numbers, and how to build a "Keel first, LLM fallback" decision.

## The idea in one paragraph

Agents and apps are full of small, typed branches: which queue gets this ticket, how severe is this incident, is this command safe to run, does this answer stick to its sources. Asking a general LLM each of these costs hundreds of tokens and a second or more. Keel answers them with a small cross-encoder that runs on your CPU. You describe the situation in `state`, ask typed `questions` about it, and get back a probability distribution over the allowed answers. You then decide what to do. Keel never takes the action itself.

<!-- diagram:question-types -->

## State and questions

A request has one `state` and one or more `questions`:

```json
{
  "model": "decider-latest",
  "state": "Deploy failed: migration 0042 timed out on the orders table. Rollback succeeded.",
  "questions": {
    "owner":    { "type": "choice", "instructions": "Which team owns the fix?",
                  "criteria": { "platform": "CI, deploy tooling", "data": "Schemas and migrations", "app": "Product code" } },
    "severity": { "type": "score",  "instructions": "How severe is this?",
                  "criteria": ["SEV4 minor", "SEV3 limited", "SEV2 major", "SEV1 critical"] },
    "page":     { "type": "noul",   "instructions": "Should someone be paged right now?" }
  }
}
```

- **`state`** is the text being judged: a ticket, a diff summary, a shell command, a retrieved page. It can be up to 8,000 characters, but the encoder reads about 256 tokens per (state, option) pair, so put the decisive facts first.
- **Each question is scored independently** against the same state. One request with three questions costs the same as three requests, minus HTTP overhead.
- **`instructions`** tells Keel what is being decided. Write it as a short question.
- **`criteria`** lists the allowed answers. Describe each option in a few concrete words: Keel compares the state against each description, so "Schemas and migrations" works much better than "data".

## The three question types

| Type | You give | You get | Use it for |
|---|---|---|---|
| `choice` | 1–255 named options | `choice`, `confidence`, `probabilities` | Routing, classification, picking a tool or a sub-agent |
| `score` | 1–10 ordered levels | `score` (expected level), `confidence`, `legend`, `probabilities` | Severity, priority, risk, quality ratings |
| `noul` | A yes/no question | `noul` = P(yes) | Gates: is this PII, is this an injection, should this ship with tests |

### choice

Options are the keys of `criteria`. A value can be a description string or `null`. Keel also accepts the Jev `options` array form. The answer is the most likely key:

```json
{ "type": "choice", "choice": "data", "confidence": 0.81,
  "probabilities": { "platform": 0.12, "data": 0.81, "app": 0.07 } }
```

### score

Levels are ordered from 0. `criteria` can be a list, or an object with numeric keys. The answer is the **expected level**, Σ i·pᵢ, rounded to 2 decimals, so it can be fractional. A score of 1.6 on a 0–3 scale means "between level 1 and 2, leaning 2". `legend` echoes the level names so you can print them.

```json
{ "type": "score", "score": 1.62, "confidence": 0.55,
  "legend": { "0": "SEV4 minor", "1": "SEV3 limited", "2": "SEV2 major", "3": "SEV1 critical" },
  "probabilities": { "0": 0.05, "1": 0.31, "2": 0.55, "3": 0.09 } }
```

To get a single level, round `score` or take the arg-max of `probabilities`. They usually agree. When they do not, the distribution is spread and you should look at `confidence`.

### noul

A noul is a yes/no question. The answer is a single number, `noul` = P(yes), between 0 and 1. A noul has **no confidence field**. Its distance from 0.5 is the confidence. You pick the threshold per use: a PII gate might fire at 0.3, a "ship it" gate might need 0.8.

```json
{ "type": "noul", "noul": 0.87 }
```

You can make the meaning of yes and no explicit with `criteria: { "true": "...", "false": "..." }`. A noul needs either `instructions` or `criteria`.

## Probabilities

Every choice and score answer carries the full distribution, rounded to 4 decimals and summing to 1. Use it:

- **Margins.** If the top two options are close, treat the decision as unsure even if the top one is above your threshold.
- **Asymmetric costs.** For a run / confirm / block command gate, you can act on `P(block) > 0.2` even when `run` wins, because a wrong "run" costs far more than a wrong "confirm".
- **Logging.** Store the distribution, not just the winner. It makes later threshold tuning possible without re-running.

## Confidence

Keel reports confidence in two styles, picked by the model alias you send:

| Alias family | `confidence` for choice | `confidence` for score |
|---|---|---|
| `decider-*`, `microsoft-decision-1` and its aliases | Top probability, p_max | Probability of the most likely level |
| `jev-*` | (p_max − 1/n) / (1 − 1/n), so 0 means uniform and 1 means certain | 1 − (spread around the mode ÷ spread of a uniform distribution) |

The Jev style exists so that clients ported from Jev keep the meaning of their existing thresholds. For example, a three-way choice split of 0.6 / 0.3 / 0.1 reports 0.6 under `decider-latest` and 0.4 under `jev-latest`. Pick one alias family and calibrate your thresholds against it.

Keel's calibration is measured with expected calibration error (ECE, lower is better). On the blind suite, choice ECE is <!-- num:k2.ece.blind -->0.182<!-- /num --> for Keel-2 and <!-- num:k3.ece.blind -->0.108<!-- /num --> for the Keel-3 RC, against <!-- num:llm.ece.blind -->0.080<!-- /num --> for claude-haiku-4.5. A Keel-3 RC confidence of 0.8 is therefore right roughly 80% of the time on unseen data; for Keel-2 it is noticeably over-confident.

## Abstain: when Keel thinks no option fits

Keel scores each option by asking "does the state entail this description?". If **no** option is entailed above a small threshold (`abstain.threshold` in `keel.json`), Keel flattens the distribution toward uniform. You see this as low confidence on every option, not as an error.

Keel never refuses and never invents an option. "None of the above" is your decision to make: add an explicit `other` option, or treat low confidence as "ask someone else".

## The τ gate: Keel first, LLM fallback

This is the pattern that saves tokens. Pick a confidence threshold **τ**. If Keel's confidence is at least τ, use Keel's answer. Otherwise ask your LLM, a human, or a stricter policy.

<!-- diagram:tau-gate -->

```python
def decide(state, question, tau=0.6):
    a = keel(state, question)            # ~20 ms, free
    conf = a.get("confidence", 2 * abs(a.get("noul", 0.5) - 0.5))
    if conf >= tau:
        return a, "keel"
    return llm(state, question), "llm"   # ~1 s, costs tokens
```

For a noul, the snippet maps P(yes) to a confidence of 2·|p − 0.5|, so 0.9 and 0.1 are both confident, and 0.5 is not.

Measured on our held-out suites at τ = 0.6, the Keel-3 release candidate `t1-r2e` answered <!-- num:tok.k3.ho.avoided -->75/100<!-- /num --> calls itself and the hybrid was **more** accurate than the LLM alone (<!-- num:tok.k3.ho.acc -->75 → 89 of 100 cases fully right<!-- /num -->). Raising τ sends more to the LLM: fewer savings, higher accuracy on hard suites. See [Token savings](token-savings.md) for the full τ table.

Always gate safety-critical answers separately. Do not let a confident `run` or `approve` from Keel skip a human on destructive or irreversible actions.

## The on/off switch

Keel has a process-wide switch, shared by the bench UI, the API and the MCP server.

- `GET /api/v1/status` returns `{"enabled": true|false, ...}`. It needs no key.
- `POST /api/v1/switch` with `{"enabled": false}` turns Keel off. It needs the bearer key.
- When Keel is off, `POST /api/v1/systemone` returns **409 `disabled`** and runs no model.

Agents check the status before their first decision. If Keel is off, they fall back to their own judgement and do not call the decision endpoint. This gives a user a single kill switch: "Keel off" in chat stops every agent from consulting it. The switch is in memory, so restarting the server turns Keel back on.

## Determinism

The same request to the same model gives the same answer, every time. There is no sampling and no temperature at inference. The calibration temperatures in `keel.json` are fixed constants. This makes Keel decisions easy to test: snapshot a response in your unit tests and it will not drift until you change the model.

Two things can change an answer: a different model version (check the response `model` field), and a fallback to the lexical judge when the neural model fails to load (check `GET /api/v1/status`).

## Which judge answered

The response `model` is always the judge that actually answered, not the alias you requested:

| `model` in the response | Meaning |
|---|---|
| `decider-3.0.0` | Keel-3, the default neural model |
| `decider-2.0.0` | Keel-2, when you pin `decider-2.0.0` or Keel-3's weights are missing |
| `decider-2.0.0-zeroshot` | Only the untrained base model is installed (`models/keel-base`) |
| `decider-1.2.0` | Lexical judge, because you pinned `decider-1.x`, set `KEEL_ENGINE=lexical`, or the neural model failed to load |

Jev and Microsoft-Decision-1 aliases are accepted for drop-in compatibility. They never mean that a hosted service answered.

## Next

- [API reference](api-reference.md) for every field, limit and error.
- [Use cases](use-cases.md) for 50 ready-made request bodies.
- [Token savings](token-savings.md) for when the τ gate pays off, and when it does not.
