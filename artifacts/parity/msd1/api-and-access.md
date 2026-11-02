# Microsoft-Decision-1 (MSD1): API, wire, access, and switching to Keel

Owner: msd1-1. Researched 2026-10-28. Every vendor number below is **vendor-reported** and cited; nothing here comes from a live MSD1 call (see §6 — no credential was available).

## 1. What MSD1 is

| Fact | Value | Source |
|---|---|---|
| Name / version | `Microsoft-Decision-1`, model version `1`, lifecycle **Preview** | [Foundry catalog][cat], [Learn how-to][learn] |
| Base model | Qwen3.5-9B, post-trained by Microsoft; to be rebased on MAI / OpenAI models later | [announcement][post], [catalog][cat], [Tech Community][tc] |
| Training data | Public datasets (Microsoft Open Data process) + team synthetic data | [catalog][cat] |
| Task | Single-pass scoring of a fixed option set → calibrated probability per option. No generated text, no rationale | [post], [learn] |
| Primitives | `noul` (yes/no), `choice` (one of N), `score` (ordered scale); rubric grading is expressed through these | [learn] |
| Modality | Text only (state may be a string or JSON). No image/audio/video | [catalog][cat], OpenRouter endpoints API (`input_modalities:["text"]`, `output_modalities:["decisions"]`) [orapi] |
| Context | 32,768 tokens | [catalog][cat], [orapi] |
| Pricing | **$0.042 per 1M input tokens, output free** (vendor-reported); OpenRouter lists `prompt: 0.000000042`, `completion: 0` | [post], [orapi] |
| Weights | **Hosted-only.** "Direct from Azure" model; no Hugging Face repo under any author for "Microsoft-Decision" / "decision-1" (HF API search, 2026-10-28). Not open-weight. | [catalog][cat], HF API |
| License | Foundry "Direct from Azure" terms (Microsoft Product Terms / acceptable-use). The catalog License tab is rendered client-side and was not retrievable as text; no weight license exists because weights are not distributed | [catalog][cat] |
| Providers | Microsoft Foundry (deploy into your own resource); OpenRouter, where the only endpoint is `Azure \| microsoft/microsoft-decision-1-20261009` | [learn], [orapi] |
| Deployment types | `GlobalStandard`; `DataZoneStandard` in selected regions | [learn] |

Vendor-reported quality/latency claims ([post]): highest accuracy in Microsoft's 36-benchmark comparison (~150,000 questions, blind from training); fastest measured, 2.5× faster than H2O-Lightning-4B v1.1 and ~35× faster than GPT-6 Sol at P50; 1.3% average decision flips across 8 perturbation types, zero flips for paraphrased option descriptions or reversed/shuffled options; safety tested on 5,250 requests across 11 benchmarks. The post states it was later updated to add Jev accuracy/calibration numbers; those are in charts we did not transcribe, so we do not quote them. No absolute millisecond figure is published in text form; OpenRouter's `latency_last_30m` was `null` when queried.

Known limitations (vendor): wording/order sensitivity, calibration strongest on familiar task types, may miss subtle harmful content, not for sole decisions about people ([learn]).

## 2. API

MSD1 uses the **System One wire** — the same request/response shape as TypeSafe Jev and Keel (`KEEL_PLAN.md` §3). The Learn page says so explicitly: "The request pattern is similar to a system-one API".

### Endpoints and auth

| Provider | URL | `model` | Auth |
|---|---|---|---|
| Foundry | `POST {resource-endpoint}/providers/microsoft/v1/systemone` | **your deployment name** (response `model` is the underlying model, e.g. `microsoft-decision-1`) | `Authorization: Bearer <Entra token for https://cognitiveservices.azure.com>` (recommended) or `api-key: <key>` |
| OpenRouter | `POST https://openrouter.ai/api/v1/systemone` (TypeSafe-SDK compatible) or `POST https://openrouter.ai/api/alpha/decisions` | `microsoft/microsoft-decision-1` | `Authorization: Bearer <OPENROUTER_API_KEY>` |

Sources: [learn] (Foundry route, auth, deployment CLI), [orsdk] (OpenRouter `/api/v1/systemone`, base-URL swap), [oralpha] (alpha decisions OpenAPI). Both OpenRouter routes exist (unauthenticated probe returned 401, not 404, on 2026-10-28). OpenRouter's published examples use Jev; routing MSD1 through `/api/v1/systemone` is inferred from the shared schema and the model's `text->decisions` modality, not verified live.

### Request

```json
{
  "model": "<deployment name | microsoft/microsoft-decision-1>",
  "state": "text or JSON",
  "questions": {
    "team":     { "type": "choice", "instructions": "Which team?", "criteria": { "billing": "Charges", "engineering": "Bugs" } },
    "severity": { "type": "score",  "instructions": "How severe?", "criteria": ["Cosmetic", "Minor", "Major", "Critical"] },
    "refund":   { "type": "noul",   "instructions": "Promises a refund?", "criteria": { "true": "Commits money", "false": "No commitment" } }
  }
}
```

- Options are passed as `criteria`: an object `{key: description}` for `choice`, an ordered array (low → high) for `score`, optional `{true,false}` for `noul` ([learn]).
- Multiple questions over one state share a request ([learn] "Combine decisions in one request").
- OpenRouter's schema also allows `provider`, `session_id`, `user`, `trace`, image `assets`, and a `box` question type — those are Jev features; MSD1 is text-only ([oralpha], [cat]).
- Published limits on number of questions/options/state length: **none found** beyond the 32K-token context.

### Response

```json
{
  "model": "microsoft-decision-1",
  "answers": {
    "team":     { "type": "choice", "choice": "engineering", "confidence": 0.9, "probabilities": { "billing": 0.1, "engineering": 0.9 } },
    "severity": { "type": "score", "score": 2.6, "confidence": 0.7, "legend": { "0": "Cosmetic", "…": "…" }, "probabilities": { "0": 0.0, "1": 0.1, "2": 0.2, "3": 0.7 } },
    "refund":   { "type": "noul", "noul": 0.97 }
  },
  "usage": { "input_tokens": 0, "output_tokens": 0 }
}
```

- Shape per [oralpha] `DecisionsResponse` (`model`, `answers`, `usage` required; OpenRouter adds `id`, `provider`, `usage.cost`) and [learn] ("returns the selected option and a probability for every option"; score = "probability-weighted average of the level indexes", may be fractional). The illustrative numbers above are ours, not MSD1 output.
- Yes/no: `noul` ∈ [0,1] = P(true). No confidence field. Caller picks the threshold.
- Errors (Foundry): 400 bad shape, 401 credential, 403 no access, 404 wrong endpoint/path, 422 unsupported deployment name or question, 429 rate limit ([learn]). OpenRouter adds 402 (credits), 413, 5xx/524/529 ([oralpha]).
- Rate limits: Foundry deployment quota (`--sku-capacity`), OpenRouter account limits. No numeric figure published.

## 3. Wire mapping MSD1 ⇄ Keel / Jev

| Element | MSD1 | Keel (`decider-*`) | Jev | Mapping |
|---|---|---|---|---|
| Path | Foundry `/providers/microsoft/v1/systemone`; OpenRouter `/api/v1/systemone` | `/api/v1/systemone` | `/v1/systemone` | OpenRouter base `…/api` → Keel base `http://host:8080/api`: identical suffix |
| `state` | string or JSON | string or JSON, ≤ 8,000 chars | string or JSON | identity |
| `choice` criteria | `{key: desc}` | `{key: desc \| null}`, 2–12 keys | same | identity |
| `score` criteria | ordered array, low first | ordered array, 2–10 | same | identity |
| `noul` criteria | optional `{true,false}` | optional `{true,false}` | same | identity |
| `choice` answer | `choice`, `confidence`, `probabilities` | same (argmax, top-p, sums to 1) | same | identity |
| `score` answer | `score` = Σ i·pᵢ, `probabilities`, `legend`, `confidence` | same | same | identity |
| `noul` answer | `noul` = P(yes) | same | same | identity |
| `model` (req) | deployment name / `microsoft/microsoft-decision-1` | **must be a Keel/Jev alias or omitted** | `jev-*` | rewrite or omit (gap ⚠ below) |
| Auth header | Entra bearer, `api-key`, or OpenRouter bearer | `Authorization: Bearer <local key>` only | bearer | switch to bearer |
| `usage` | real tokens (+`cost` on OpenRouter) | always zeros | real tokens | — |

`src/lib/decider/msd1-compare.ts` implements this: `toMsd1Body` builds the MSD1 body from the *already-parsed* Keel request (so both see identical inputs), and `normalizeMsd1Answers` validates MSD1 answers into Keel's `Answer` type. Vendor numbers are kept verbatim; a field is derived only when MSD1 omits it but returns the probabilities it is defined from (choice = argmax, confidence = top p, score = Σ i·pᵢ), and each derivation is logged in the row's `issues`. Unknown option keys, wrong types, or out-of-range values are dropped, never guessed. A `probability` field on noul answers (seen only in a third-party write-up, not in Microsoft docs) is tolerated and flagged.

## 4. Feature gaps (Keel today = `decider-2.0.0`)

| Capability | MSD1 | Keel | Notes |
|---|---|---|---|
| Same wire (state + choice/score/noul + probabilities) | ✅ | ✅ | identical shapes |
| Multiple questions per request | ✅ | ✅ (≤ 8) | MSD1 publishes no cap |
| Accepts MSD1 `model` values | ✅ | ❌ | `tryParse` returns 400 `Unknown model "microsoft/microsoft-decision-1"` and for any deployment name (verified locally). Workaround: omit `model` or send `decider-latest`. Fix belongs to the wire owner (jev-1): accept `microsoft-decision-*` / `microsoft/microsoft-decision-1` as aliases. |
| `api-key` header (Foundry key auth) | ✅ | ❌ | Keel accepts only `Authorization: Bearer` |
| Foundry path `/providers/microsoft/v1/systemone` | ✅ | ❌ | needs a route alias or reverse proxy |
| Long inputs | ✅ 32K tokens | ⚠ 8,000 chars state; encoder `maxLength` 256 tokens (truncates) | biggest functional gap for long-context / RAG judging |
| Multilingual | ✅ (vendor-claimed blind multilingual benchmarks) | ⚠ English-centric 13M encoder | not measured |
| Rubric grading of AI responses / agent actions | ✅ | ⚠ expressible via score/choice; quality unmeasured on long responses (truncation) | |
| Calibrated probabilities | ✅ (vendor-claimed) | ✅ temperature-calibrated on dev | compare on our suites once live |
| Robustness to option order/paraphrase | ✅ 1.3% flips (vendor) | ⚠ not measured | candidate addition to the parity bench |
| Determinism | ⚠ not documented | ✅ guaranteed | |
| Latency | network RTT (no absolute number published) | ✅ in-process, p95 target < 20 ms | |
| Cost | $0.042/M input | ✅ $0 | |
| Offline / air-gapped / data never leaves the machine | ❌ | ✅ | |
| Open weights, self-host, fine-tune | ❌ hosted-only | ✅ ONNX int8 ~13 MB | |
| Enterprise governance, regional data zones, SLA | ✅ Foundry | ❌ (local) | |
| `usage` token counts / cost | ✅ | ⚠ always 0 by design | |
| On/off switch semantics (409 `disabled`) | ❌ | ✅ | Keel-only extra |
| Images / `box` | ❌ (text-only) | ❌ | Jev-only on OpenRouter |

## 5. Switching from MSD1 to Keel

1. Run Keel (`npm run dev`, port 8080) or embed the judge in-process (`neuralWeights` + `projectWeights`).
2. Change the base URL: Foundry `https://<res>.services.ai.azure.com/providers/microsoft/v1/systemone` or OpenRouter `https://openrouter.ai/api/v1/systemone` → `http://127.0.0.1:8080/api/v1/systemone`. TypeSafe-SDK users set `TYPESAFE_BASE_URL=http://127.0.0.1:8080/api`.
3. Change auth: drop `api-key` / Entra token / OpenRouter key; send `Authorization: Bearer <Keel local key>` (shown in the Copilot panel; HMAC of `KEEL_SECRET`).
4. Change `model`: omit it or send `decider-latest` (until MSD1 aliases are accepted — §4).
5. Keep `state`, `questions`, thresholds, and answer parsing unchanged. Keep states under 8,000 chars and ≤ 8 questions, ≤ 12 options, ≤ 10 score levels.
6. Don't read `usage` for billing (always 0). Handle `409 disabled` (switch off) as "no decision made".
7. Re-validate thresholds on your labeled examples: the probabilities come from a different model.

## 6. Access on this machine and live comparison

Checked 2026-10-28 without printing any secret:

- `OPENROUTER_API_KEY`, `AZURE_AI_*`, `AZURE_OPENAI_*`, `AZURE_ENDPOINT`, `FOUNDRY_*`, `MSD1_*`: **not set** (process, user, and machine scope).
- `az account show`: works (signed in).
- Read-only Resource Graph listing found 14 Cognitive Services / AI Services accounts across the visible subscriptions; `az cognitiveservices account deployment list` on each found **no deployment of Microsoft-Decision-1**. Nothing was created or deployed.

Result: `artifacts/parity/msd1/live-compare.{md,json}` were written with `msd1Compared: false`, the reason, and every MSD1 field null. Keel's side of those files is real.

**To run it, provide one of:**

- OpenRouter: an API key with credits → `$env:OPENROUTER_API_KEY="…"` (optional `MSD1_OPENROUTER_MODEL`, default `microsoft/microsoft-decision-1`).
- Foundry: an existing deployment of `Microsoft-Decision-1` → `$env:MSD1_FOUNDRY_ENDPOINT="https://<resource>.services.ai.azure.com"` (or `AZURE_AI_ENDPOINT`), `$env:MSD1_FOUNDRY_DEPLOYMENT="<deployment name>"` (or `AZURE_AI_DEPLOYMENT`), and either `$env:MSD1_FOUNDRY_API_KEY="…"` (or `AZURE_AI_API_KEY`) or `$env:MSD1_USE_AZ_TOKEN="1"` to use the signed-in `az` identity (needs data-plane access to the deployment). Creating the deployment (`az cognitiveservices account deployment create … --model-name Microsoft-Decision-1 --model-format Microsoft --model-version 1 --sku-name GlobalStandard --sku-capacity 1`, [learn]) is the user's decision; this agent did not do it.
- Optional `MSD1_PROVIDER=openrouter|foundry` to force one when both are set.

Then: `npm run keel:compare-msd1` (default suites holdout-20, holdout-b-20, open-60, plus `blind` automatically once `artifacts/parity/blind/READY.json` exists; `--suites`, `--max-calls` (default 300), `--out`). The harness stops after the first 400/401/402/403/404/422 and never retries with another vendor. Estimated cost: ~100–250 short requests ≈ well under $0.01 at the listed rate.

Unit tests (no network): `node --experimental-strip-types --test src/lib/decider/msd1-compare.test.ts` — 7/7 pass.

[post]: https://commandline.microsoft.com/microsoft-decision-1-model-foundry/ "Microsoft-Decision-1: Our model for fast decision-making (Command Line). The URL given in the brief, /posts/introducing-microsoft-decision-1, returns 404."
[learn]: https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision "Deploy and use Microsoft-Decision-1 in Microsoft Foundry (ms.date 2026-10-07)"
[cat]: https://ai.azure.com/catalog/models/Microsoft-Decision-1 "Foundry model catalog"
[tc]: https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-microsoft-decision-1-in-microsoft-foundry-for-decision-and-classific/4562742 "Microsoft Foundry blog, 2026-10-09"
[orapi]: https://openrouter.ai/api/v1/models/microsoft/microsoft-decision-1/endpoints "OpenRouter endpoints API (queried 2026-10-28). Page https://openrouter.ai/microsoft/microsoft-decision-1; the brief's openrouter.ai/microsoft/decision-1 returns 404"
[orsdk]: https://openrouter.ai/docs/guides/community/typesafe-sdk "OpenRouter: TypeSafe SDK / System One API"
[oralpha]: https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request "OpenRouter: Submit a Decisions request (OpenAPI)"
