# Keel — implementation plan

This document is the spec. An agent that has only this file, plus the repo if it is present, should be able to implement, test, and wire Keel into GitHub Copilot CLI and the Copilot agent in VS Code.

Jev means TypeSafe AI’s System One model (`jev-latest`, `jev-1.13.0`, `jev-preview`) at `POST https://api.typesafe.ai/v1/systemone`. “Arjev” in the source request is the same product. Keel is our model. It is not a wrapper around Grok, OpenAI, or Jev.

## 1. What we are building

A local decision service that speaks Jev’s wire and runs in-process.

Copilot (CLI and VS Code) calls it when a task needs a typed branch: where to route, how severe, whether to edit, ask, or stop. Keel returns probabilities. The agent branches on those numbers. Keel does not edit code and does not write prose.

The service must:

- Run on the user’s machine with `npm install` and `npm run dev`. No `XAI_API_KEY`, no `TYPESAFE_API_KEY`, no outbound call on the decision path.
- Accept the same request Jev accepts: `model`, `state`, `questions` of type `choice`, `score`, and `noul`.
- Return the same answer shapes: probabilities that sum to 1, a winning key, a confidence, a score that may sit between levels, a noul in `[0, 1]`.
- Expose an on/off switch that Copilot obeys. Off does not run the model.
- Ship a labeled eval of at least 50 cases, a Keel-on vs Keel-off report, and a Jev comparison that runs only when `TYPESAFE_API_KEY` is set.
- Stay fast enough that turning it on does not stall Copilot. Budget: under 20ms in-process p95, under 50ms HTTP p95 once the process is warm.

Match or beat Jev on the axes we control: latency, cost (zero marginal), offline use, wire compatibility, and decision quality on our labeled set. Do not claim equal quality to Jev’s trained weights until the optional live comparison says so.

## 2. Current baseline (do not throw this away)

The repo already has this shape. Extend it. Do not reintroduce an LLM call.

| Path | Role |
|---|---|
| `src/lib/decider/wire.ts` | Parse and project. Client-safe. |
| `src/lib/decider/local.ts` | The judge. Pure function. No I/O. |
| `src/lib/decider/judge.server.ts` | HTTP/server entry. Switch, rate limit, then `localWeights`. |
| `src/lib/decider/auth.server.ts` | Local bearer from `KEEL_SECRET` or a built-in secret. Not an API key. |
| `src/lib/decider/switch.server.ts` | `keel_switch` row. On by default. |
| `src/routes/api/v1/systemone.ts` | `POST` the wire. |
| `src/routes/api/v1/status.ts` | `GET { enabled, model }`. |
| `src/routes/api/v1/switch.ts` | `POST { enabled }` with the bearer. |
| `src/routes/api/v1/models.ts` | Alias list. `jev-latest` maps to the concrete Keel model id. |
| `src/lib/decider/eval-set.ts` | 50 labeled cases. |
| `src/lib/decider/eval.ts` | On/off scorer and markdown report. |
| `src/components/keel/*` | Bench, compare, Copilot copy panels, header switch. |
| `migrations/0002_keel_switch.sql` | The switch table. |

Concrete model id today: `decider-1.2.0`.

The judge in `local.ts` is a linear system-one, not a neural net:

1. Tokenize, stem, mark a token negated if `not` / `no` / `never` / `without` / `none` is within three tokens before it.
2. Activate a fixed feature lexicon from non-negated state tokens (money, defect, access, security, unsafe, integration, leave, blocked, mild, anger, extreme).
3. Score each option by dot(activation, affinity of the option text) plus lexical overlap with the state.
4. Softmax at temperature 0.42. If every score is noise (`max < 0.12` or spread `< 0.06`), return equal weights so confidence stays low.
5. Scores use a severity index plus the same dot product so “cancel Friday” can land on a “churn” level without sharing that word.
6. Noul is a sigmoid of yes-evidence minus no-evidence. Negated overlap with the yes text counts as no. A security question with no security activation is pushed toward no.

`projectWeights` in `wire.ts` turns those weights into the wire answer. Choice confidence is the top probability, not entropy.

## 3. Wire contract

Implement this exactly. Clients written for Jev must not need a fork beyond the host and the bearer.

### Request

`POST /api/v1/systemone`

Headers: `Authorization: Bearer <local bearer>`, `Content-Type: application/json`.

```json
{
  "model": "decider-latest",
  "state": "string or JSON value",
  "questions": {
    "<id>": {
      "type": "choice" | "score" | "noul",
      "instructions": "string",
      "criteria": {}
    }
  }
}
```

Rules already enforced in `tryParse`:

- `model` optional. Allowed aliases: `decider-latest`, `decider-1.2.0`, `decider-1.1.0`, `decider-1.0.0`, `decider-preview`, `jev-latest`, `jev-1.13.0`, `jev-preview`. Unknown model → 400. Every alias returns `model: decider-1.2.0` (or the next concrete id). Never return `jev-*` as the model name. This host is not TypeSafe.
- `state` required, non-empty, max 8000 characters after stringifying objects.
- 1–8 questions. Ids match `^[A-Za-z][A-Za-z0-9_:-]{0,48}$` and are not reserved (`confidence`, `probabilities`, `usage`, `model`, `answers`, `state`, `questions`, `error`, `type`, `quota`).
- `choice`: `criteria` is an object of 2–12 `{ key: description | null }`. Keys are identifiers.
- `score`: `criteria` is an array of 2–10 level strings, ordered, index 0 is the low end.
- `noul`: `criteria` optional `{ true, false }` descriptions.
- Instructions max 1200 characters. Descriptions max 400.

### Response 200

```json
{
  "model": "decider-1.2.0",
  "answers": {
    "kind": {
      "type": "choice",
      "choice": "billing",
      "confidence": 0.91,
      "probabilities": { "billing": 0.91, "bug": 0.045, "account": 0.045 }
    },
    "severity": {
      "type": "score",
      "score": 2.64,
      "confidence": 0.7,
      "legend": { "0": "Cosmetic", "1": "Workaround exists", "2": "Blocks the task", "3": "Data loss or about to churn" },
      "probabilities": { "0": 0.02, "1": 0.08, "2": 0.2, "3": 0.7 }
    },
    "security": { "type": "noul", "noul": 0.05 }
  },
  "usage": { "input_tokens": 0, "output_tokens": 0 }
}
```

Invariants:

- Choice and score probabilities sum to 1 within 1e-6. Round to 4 decimal places, put the drift on the largest mass.
- `choice` is the argmax. Ties take the earlier key.
- `confidence` is the top probability, rounded to 3 decimal places. A noul has no confidence.
- `score` is the expected level index `sum(i * p_i)`, rounded to 2 decimal places. It may be fractional.
- Noul is `yesWeight / 100` if the judge emits 0–100, clamped to `[0, 1]`, 4 decimal places. 0.5 means the judge cannot tell.
- `usage` stays `{ input_tokens: 0, output_tokens: 0 }` while the judge is local. Do not invent token counts.

### Errors

| Status | type | When |
|---|---|---|
| 400 | `invalid_request` | Parse failure. Message says which field. |
| 401 | `unauthorized` | Missing or wrong bearer on `/systemone` and `/switch`. |
| 409 | `disabled` | Switch is off. Body must say no model call was made. Do not score. |
| 429 | `rate_limited` | Over 120 requests / 60s in this process. |
| 200 | — | Success. |

Error body: `{ "error": { "type", "message", "request_id" } }`. `request_id` is `req_` plus 16 hex chars.

`GET /api/v1/status` is public: `{ "enabled": true, "model": "decider-1.2.0" }`. No store cache.

`POST /api/v1/switch` requires the bearer and `{ "enabled": boolean }`.

`GET /api/v1/models` lists aliases and states that the concrete model is Keel.

## 4. Local runtime

- Dev: `npm run dev` → Vite on `0.0.0.0:8080` via `scripts/with-app-env.mjs`.
- The decision function must not `fetch`. Grep the judge for `api.x.ai`, `api.typesafe.ai`, and `api.openai.com`. Those strings must not appear in `local.ts` or `judge.server.ts`.
- Bearer: HMAC-SHA256 of `KEEL_SECRET` or the built-in `keel-local-decider`, purpose string `keel-local-decider-v1`, base64url, first 40 chars. Compare with `timingSafeEqual`. Document the bearer in the Copilot panel. It is a local password, not a vendor key.
- Switch: Postgres when `DATABASE_URL` is set, embedded PGLite otherwise. Table `keel_switch (id int primary key, enabled boolean not null default true)`. Single row id `1`.
- Determinism: same state and questions → same answers. No temperature, no clock, no random in the judge.
- Do not log state bodies. They may contain customer text. Log only status, latency, and question ids if you log at all.

## 5. Quality bar against Jev

Jev, from its public contract (not from a call we made):

- One endpoint, three primitives, probabilities, parallel questions, no chain of thought in the response.
- Published latency band about 70–500ms end to end.
- Hosted, billed per input token, needs `TYPESAFE_API_KEY`.
- Text only.

Keel must beat that on:

| Axis | Gate |
|---|---|
| Latency | In-process p95 < 20ms on the 50-case set. Warm HTTP p95 < 50ms. |
| Cost | Zero calls. `usage` tokens are 0. |
| Offline | Airplane mode still decides. |
| Wire | The fixtures in `wire.test.ts` and the examples in section 3 pass. |
| Stability | Two runs of `runEval()` deep-equal on `rows[].actual`. |
| On vs off | Defined in section 7. Safety misses must be 0 before calling the result a pass. |
| Vs live Jev | Only with `TYPESAFE_API_KEY`. Report agreement, latency, and disagreements. Never fabricate Jev outputs. |

Keel does not yet beat Jev on open-domain calibration. The linear lexicon misses paraphrases that share no feature and no word with the option text. Closing that gap is the model work in section 6, measured by section 7. Do not paper over misses by deleting cases.

## 6. Model work, in order

Do these only after the eval harness is green as a harness (it runs, writes a report, latency holds). Improve the model until the gates in section 7 pass. Re-run the report after every change.

1. **Keep the pure function.** `localWeights(request) -> WeightBag`. Unit-test it without the server.
2. **Error analysis.** Read `artifacts/keel-on-off-report.md` failures. Group them: negation, missing paraphrase, score scale, noul threshold, copilot edit/ask/stop. Fix the group, not one fixture.
3. **Negation scope.** A negated topic (“this is not a billing issue”) must not vote for that topic. Window is three tokens today; extend to the clause if failures remain, not the whole document.
4. **Paraphrase features.** Add a feature only when a failure class needs it. Stem the lexicon the same way as the text. Do not add the answer key as a special case (`if state includes "stripe" return technical`).
5. **Copilot policy features.** Concrete path (`/file.ext`) plus an imperative (`add`, `fix`, `update`, `remove`, `rename`) supports `edit`. `where` / `which` / “did not say” supports `ask`. Trust-boundary and secret-exfiltration language supports `stop`. “Must not be rewritten” is a constraint, not a task, when the task is a different file.
6. **Calibration.** On the labeled set, choice confidence should be ≥ 0.6 when the label is unambiguous and ≤ 0.5 when the case is marked ambiguous. Do not force confidence to 1.0.
7. **Optional trained head.** If the lexicon plateaus, fit a small logistic model offline: features are the current activation vector plus lexical overlap. Export coefficients as JSON checked into `src/lib/decider/weights.json`. Load that file in `local.ts`. Training data is `eval-set.ts` plus a held-out file `eval-holdout.ts` that the trainer must not see. No network at inference. No Python required at runtime.
8. **Do not call an LLM to judge.** Not Grok, not Jev, not a local llama, unless a later revision of this plan says so. The product requirement is a local system-one that returns in milliseconds.

## 7. Eval and the on/off report

### Sets

- `EVAL_CASES` in `eval-set.ts`: exactly 50, unique states, tags among `route`, `score`, `noul`, `copilot`, `safety`, `negation`, `ambiguous`.
- Held-out later: 20 more cases in `eval-holdout.ts`, same shape, never used to add a feature by hand while looking at the result. Write them before tuning, or have a second person write them.

### What “Keel off” means

Off is not a second model. The status endpoint says `enabled: false`, and `/systemone` returns 409 without scoring.

For the quality report, the off baseline is **naive**: pick the first criteria key of each choice and do not look at the state. That is the decision you get from a client that ignores the model. Latency of off is the time to read that key, which is ~0ms.

A case with `maxConfidence` is ambiguous. Naive counts as wrong, because guessing the first key is a confident mistake. Keel passes only if its confidence is at or below the cap.

### What a regression is

`runEval()` sets `verdict` to `regression` if any of these are true:

- One or more **safety misses**. A safety miss is a choice in `expect.safetyMiss.keys`. Examples: the case is “commit the production secret” and Keel says `edit`; the case is “markup injection” and Keel says `billing`.
- Choice accuracy of Keel on is **lower** than naive off.
- In-process p95 over **20ms**.

Score-band and noul-band misses are listed in the report. They are quality gaps. They become a regression only when you are gating a release; the current `verdict` does not fail the process solely for a score miss. Raise them into the verdict once choice accuracy is stable, by adding:

- score in-band accuracy < 0.8 → regression
- noul in-band accuracy < 0.8 → regression

### Report files

`node --experimental-strip-types --test src/lib/decider/eval.test.ts` writes:

- `artifacts/keel-on-off-report.json` — full rows
- `artifacts/keel-on-off-report.md` — verdict, accuracy table, latency, failure table

JSON shape:

```json
{
  "model": "decider-1.2.0",
  "cases": 50,
  "jevCompared": false,
  "jevReason": "TYPESAFE_API_KEY is not set...",
  "keelOn": { "choice": { "correct": 0, "scored": 0, "accuracy": 0 }, "score": {}, "noul": {}, "safetyMisses": 0, "latencyMs": {} },
  "keelOffNaive": { "choice": {}, "latencyMs": {}, "note": "" },
  "regression": { "verdict": "no_regression", "reasons": [], "choiceAccuracyDelta": 0, "safetyMisses": 0, "latencyAddedMs": 0 },
  "failures": [],
  "rows": []
}
```

Each row: `id`, `name`, `tags`, `onMs`, `choiceOk`, `scoreOk`, `noulOk`, `safetyMiss`, `naiveOk`, `expected`, `actual`, `naive`.

Show this markdown to a human before claiming the model is ready for Copilot. Do not summarize away the failure table.

### Live Jev comparison

Add `src/lib/decider/jev-compare.ts`. Do not run it from the default test.

```
TYPESAFE_API_KEY=... node --experimental-strip-types scripts/compare-jev.ts
```

For each of the 50 bodies:

1. Time `localWeights` + `projectWeights`.
2. `POST https://api.typesafe.ai/v1/systemone` with `model: jev-1.13.0`, the same `state` and `questions`, bearer `TYPESAFE_API_KEY`, timeout 10s.
3. Record both answers, both latencies, HTTP status.

Write `artifacts/keel-vs-jev.json` and `.md`:

- Agreement: fraction of choice keys that match, fraction of noul on the same side of 0.5, mean absolute error of score.
- Latency: median and p95 for both.
- Disagreements: the state, both answers, nothing else.
- If the key is missing or the host returns 401, write `jevCompared: false` and the status. Leave every Jev field null. Do not retry with another vendor.

Cost note: 50 short states is a few hundred tokens. At Jev’s published input price that is well under one cent. Still do not loop the script.

### Gates an agent must hit before saying “done”

1. `node --experimental-strip-types --test src/lib/decider/wire.test.ts src/lib/decider/local.test.ts src/lib/decider/eval.test.ts` exits 0.
2. The on/off report exists and `cases` is 50.
3. `safetyMisses` is 0. If it is not, the task is not done; fix the model or correct a bad label and say which.
4. Choice accuracy delta ≥ 0.
5. p95 < 20ms in-process.
6. `curl` of a triage body to `http://127.0.0.1:8080/api/v1/systemone` returns 200 with `usage` zeros and latency under 50ms on the second call.
7. Switch off, same curl, 409, no change in process network connections.
8. Jev section of the report is explicit: compared, or not compared, with the reason. Never a guessed Jev answer.

## 8. Copilot CLI and VS Code

Keel is not an extension. Copilot already has an HTTP tool. The “skill” is an agent markdown file plus a short instructions file.

### Files to generate from the running origin

VS Code and GitHub, in the repo under work:

- `.github/agents/keel.agent.md`
- `.github/copilot-instructions.md`

CLI, user scope (same body):

- `~/.copilot/agents/keel.agent.md`

The in-app Copilot tab (`src/components/keel/copilot-panel.tsx`) is the generator. The origin must be `http://localhost:8080` when the files are copied for local use. Do not hardcode a public host.

### Agent contract

Frontmatter:

```yaml
---
name: keel
description: Routes ambiguous judgments through Keel, a local System One decision model. Use before editing when the next step, risk, or policy is not obvious.
tools: ["web/fetch", "read", "search", "edit"]
---
```

Body, in this order:

1. **Switch.** If the user says “Keel on”, “Keel off”, “Hey Keel, turn on”, or “Hey Keel, turn off”, POST `/api/v1/switch` with the bearer and `{"enabled": true|false}`. Do not edit. Confirm in one sentence.
2. **Status.** Before the first decision in a conversation, GET `/api/v1/status`. If `enabled` is false, do not call `/api/v1/systemone`. Behave as a normal coding agent. Remember that until the user flips it.
3. **Call.** POST `/api/v1/systemone` only to this origin. One question group per step, at most 8 questions, judged in parallel. State is the facts already in the task. No secrets, tokens, or `.env` values in `state`.
4. **Default questions** for a coding step:
   - `action` choice: `edit` | `ask` | `stop` with the descriptions in section 2’s Copilot preset.
   - `risk` score: Cosmetic, Local and reversible, Behavior change, Data auth or secrets.
   - `tests` noul: whether this step needs a test.
5. **Branch.**
   - `stop`, or `risk.score >= 2.5`: do not edit. One paragraph why.
   - `ask`, or action confidence `< 0.6`: ask one question. Do not edit.
   - else: smallest edit that satisfies the task. If `tests.noul >= 0.5`, add or update a test in the same change.
6. **Read the wire** exactly as section 3. Do not treat a noul’s missing confidence as zero. Do not threshold a noul at 0 unless the user said so.
7. **Failure.** 409 means off. 401 means the bearer in the file does not match the server (`KEEL_SECRET` drift). 400 means the agent built a bad body; fix the body, do not guess the branch.

CLI: `/agent` then Keel, or start with the agent name if the CLI supports it. The HTTP call uses the same curl the file shows. VS Code uses the `web/fetch` tool.

### Adapt to another client

Any client that can POST JSON can use Keel. Keep the wire in `wire.ts` as the only schema. A new client is a new markdown file with the same branch rules, not a new server.

## 9. UI

The bench is for humans checking a decision. It is not required for Copilot.

- Header switch calls `setKeelEnabled` and must match what `/status` returns.
- Bench runs `runDecision` and shows model id, latency, and `local` when usage is zero.
- Compare tab runs the 50 suite for latency. The labeled report in section 7 is the quality report; do not pretend the latency suite measures correctness.
- No xAI copy, no quota copy, no “publish to get a key”.

## 10. Implementation order for a fresh agent

1. Read `wire.ts`, `local.ts`, `judge.server.ts`, `eval.ts`. Run the three test files. Read the report.
2. If safety misses or a negative accuracy delta exist, do section 6. Re-run. Diff the failure table. Stop when section 7 gates 1–5 pass.
3. Start the dev server. Run gates 6 and 7 with curl.
4. Open `/`, copy the agent files, point them at `http://localhost:8080`.
5. Only if the user provides `TYPESAFE_API_KEY`, run the Jev script once and attach that report. Otherwise write the reason and stop.

## 11. Out of scope

- Training or hosting TypeSafe’s weights. We cannot. Do not scrape Jev to build a dataset beyond the optional 50-call comparison the user asked for.
- An xAI or other LLM fallback “for quality”. That was the previous design and it was rejected.
- Accounts, billing, multi-tenant isolation. One local switch.
- Image or audio state. Text only, same as Jev at launch.

## 12. Definition of done

A stranger clones the repo, runs `npm install` and `npm run dev`, copies two markdown files into a repo, selects the Keel agent in Copilot CLI or VS Code, and gets typed branches from a process on their machine. The on/off report shows no safety regression and no accuracy regression versus ignoring the model. Latency stays inside the budget. The report states, in one sentence, whether live Jev was measured.

## 13. Revision 2 — Keel-2 neural judge (decider-2.0.0)

This revision supersedes §6.7 ("optional trained head") and clarifies §6.8. Everything else stands: same wire, same switch, same gates, no network on the decision path, `usage` tokens 0.

**What changed.** The lexicon plateaued on paraphrases (open-domain choice ≈ 50%, held-out safety misses > 0). Keel-2 adds a small **NLI cross-encoder** (13M parameters, `xtremedistil-l6-h256`, MIT) that we fine-tune ourselves and serve in-process through ONNX int8 (~13 MB). It is **not an LLM**: it does not generate text, it scores `(state, hypothesis)` pairs in one forward pass (~10–20 ms on CPU). §6.8 still forbids calling Grok, Jev, or any generative model to judge.

**How a question is scored.** `hypothesis.ts` turns each option/level into a sentence (`"<instructions> Answer: <option>. <description>"`). The model returns an entailment margin per sentence; choice and score are a calibrated softmax over the margins; noul is a sigmoid of the yes-hypothesis minus the no-hypothesis margin. When no hypothesis is entailed, the distribution is blended toward uniform (abstain), which keeps confidence low on ambiguous states (§6.6).

**Training.** `training/keel/` builds ~31k synthetic decision groups across 21 task families with soft labels (plus 6k MNLI replay), trains with listwise CE + pointwise BCE (optional distillation from a larger teacher on a GPU machine), exports to ONNX int8, and fits per-type temperature and the abstain threshold on dev. `hypothesis.py` must stay byte-identical to `hypothesis.ts` (`test_hypothesis.py`).

**Evaluation sets.** `eval-set.ts` (50) is now *in-sample* (it is in the training mix). The honest numbers are `eval-holdout.ts` (20, never trained on) and `eval-open.ts` (60, domains excluded from training). `npm run keel:bench` reports all three for Keel-2, Keel-1, and naive-off. Recommend a blind held-out set written by someone else.

**Model ids.** `decider-latest`, `decider-2.0.0`, `jev-*` → **decider-2.0.0** (neural). `decider-1.x` pins **decider-1.2.0** (lexical). If no model is on disk or it fails to load, the response says `decider-1.2.0` — the id always names the judge that actually answered. `KEEL_ENGINE=lexical` forces the lexical judge.

**Model directory.** `KEEL_MODEL_DIR` → `models/keel-2` (trained) → `models/keel-base` (zero-shot base, `npm run model:fetch`). Config lives in `keel.json`.

**Jev.** `scripts/compare-jev.ts` compares Keel-2 with live Jev only when `TYPESAFE_API_KEY` is set; otherwise it writes `jevCompared: false` and the reason. We do not claim accuracy parity with Jev until that report exists.
