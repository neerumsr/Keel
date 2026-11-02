# Jev wire, API and feature parity audit (jev-1)

Agent: jev-1. Date: this run. Scope: can a Jev client talk to Keel by changing only the host and bearer?

Every Jev claim below cites a public TypeSafe source. Copies of the docs were fetched from
`https://docs.typesafe.ai/llms.txt` and `https://api.typesafe.ai/openapi.json` (OpenAPI `info.version` 0.2.0). They are
kept in the session folder, not in the repo. Vendor marketing numbers are labeled as vendor-reported.

Key sources:

- [OAS] OpenAPI spec: https://api.typesafe.ai/openapi.json
- [API] https://docs.typesafe.ai/api/system-one
- [ERR] https://docs.typesafe.ai/api/errors
- [MOD] https://docs.typesafe.ai/models
- [LM] https://docs.typesafe.ai/api/list-models
- [CONF] https://docs.typesafe.ai/confidence
- [PRIM] https://docs.typesafe.ai/primitives, [CH] /primitives/choice, [SC] /primitives/score, [NO] /primitives/noul, [BOX] /primitives/box, [ADV] /primitives/advanced
- [IMG] https://docs.typesafe.ai/images
- [STATE] https://docs.typesafe.ai/concepts/state
- [SDK] https://docs.typesafe.ai/sdk
- [PY] https://docs.typesafe.ai/sdk/python and /sdk/python/usage/advanced, /sdk/python/changelog
- [JS] https://docs.typesafe.ai/sdk/javascript and /sdk/javascript/changelog
- [HOME] https://typesafe.ai
- [BLOG] the Jev 1.14 release post linked from https://typesafe.ai

## 1. Feature table

Legend: ✅ same, ⚠ partial or different, ❌ missing. "Now" means fixed in this change (`wire.ts`).

| # | Jev feature (source) | Keel before | Keel now | Notes |
|---|---|---|---|---|
| 1 | `POST /v1/systemone`, bearer auth [OAS][API] | ⚠ | ⚠ | Keel serves `/api/v1/systemone`. Both SDKs build `${baseURL}/v1/systemone`, so `baseURL = http://host:8080/api` works (proved in §4). A raw `/v1/systemone` call gets 404. Route alias: see §3 R2. |
| 2 | `GET /v1/models` returns `{models:[{name, description, release_date}]}` [OAS `ModelMetadataList`][LM] | ❌ | ❌ | Keel returns `{object:"list", data:[{id,…}]}`. JS `models.list()` throws and Python `models.list()` raises (proved in §4). Route fix: §3 R1. |
| 3 | Request `model` (required in OAS); aliases `jev-latest`, `jev-preview` → `jev-1.14.0`; `jev-1.13.0` still served [MOD] | ⚠ | ✅ | `jev-1.14.0` was rejected as an unknown model. It is now an accepted alias. `model` stays optional in Keel (a superset). |
| 4 | Response `model` is the concrete version (e.g. `jev-1.14.0`) [OAS][MOD] | ✅ | ✅ | Keel answers `decider-2.0.0`. Same semantics, its own name. |
| 5 | `state`: string, object or array [OAS][STATE] | ✅ | ✅ | Keel also JSON-parses strings that look like objects. |
| 6 | Context: 64k tokens per request, 32k per question; 400 `max_tokens_exceeded` [MOD][ERR] | ⚠ | ⚠ | Keel caps state at 8000 chars, and the cross-encoder truncates each pair at 256 tokens. **Model work**, not wire (§5). |
| 7 | Long context: header `TypeSafe-Danger-Zone-Long-Context: true` gives 262k [MOD][OAS] | ❌ | ❌ | Model work. The header is ignored, not rejected. |
| 8 | No limit on the number of questions, only the token limits [MOD] | ⚠ (8) | ⚠ (64) | Now up to 64 questions and 1024 alternatives in total. Each alternative is one cross-encoder pass, so this protects local CPU. Over the limit returns 400, like Jev's token-limit 400. |
| 9 | Question types `noul`, `choice`, `score` [PRIM][OAS] | ✅ | ✅ | |
| 10 | Question type `box` (image bounding box; `jev-preview`; header `TypeSafe-Danger-Zone-Images`) [BOX][IMG][OAS `BoxQuestion`/`BoxAnswer`] | ❌ | ❌ | Needs a vision model (§5). Keel returns 400 "type must be choice, score, or noul" (verified). |
| 11 | `instructions` may be string, object, array or null, and is optional [OAS][ADV] | ⚠ | ✅ | Instructions were required and non-empty. Now choice and score accept null or missing instructions. Noul needs instructions or criteria, which matches the JS SDK's client-side check [JS] (`noul()` d.ts: "`null` or omitted requires `criteria`"). |
| 12 | Choice `criteria`: 1–255 labels; values string, object, array or null [OAS][CH] ("accepts up to 255 options") | ⚠ (2–12, identifier keys) | ✅ | Now 1–255 options. Labels can be any string of 1–128 chars without control characters, e.g. `"Tech Support"`, `"Option 3 (EU)"`. Before, Keel returned 400 on a label with a space. Jev documents no label format; the 128-char cap is Keel's. |
| 13 | Score `criteria`: 1–10 ordered entries (docs: "should have at least two") [OAS][SC] | ⚠ | ✅ | Was 2–10 and **dropped empty or null levels, shifting indices**. Now 1–10, positions kept (null becomes ""). Keel still rejects a score whose levels are all empty (Keel-specific guard). |
| 14 | Score `legend` echoes the criteria entries, which may be structured (OAS `legend: str \| object \| array`) [OAS] | ⚠ | ✅ | Structured levels are now echoed verbatim; string levels as before. |
| 15 | Noul `criteria: {true, false}`, any JSON [OAS][NO] | ✅ | ✅ | |
| 16 | Question ids: any key of the `questions` map [OAS] | ⚠ (identifier regex, ≤ 49 chars) | ⚠ | Now 1–128 chars, no control characters. Keel still reserves `confidence`, `probabilities`, `usage`, `model`, `answers`, `state`, `questions`, `error`, `type`, `quota`. An existing test pins this. Jev does not document reserved ids. |
| 17 | Choice answer `{type, choice, confidence, probabilities}` [OAS] | ✅ | ✅ | |
| 18 | Score answer `{type, score, confidence, legend, probabilities}`; `score` is the expected value [OAS][SC] | ✅ | ✅ | |
| 19 | Noul answer `{type, noul}`; no confidence [OAS][NO][CONF] | ✅ | ✅ | |
| 20 | **Confidence semantics.** Choice: `(p_max − 1/n)/(1 − 1/n)`. Score: `max(0, 1 − Σp_i\|i−m\| / MAD_unif)` [CONF] | ❌ | ✅ for `jev-*` | Keel reported top probability, and its code comment wrongly said this "matches Jev". A Jev client gating on `confidence < 0.5` [CONF example] would mis-route: a 3-way 0.6/0.3/0.1 split is 0.4 on Jev but was 0.6 on Keel. Requests with a `jev-*` model (the SDK default, `jev-latest`) now get Jev's formula. `decider-*` keeps top probability so other agents' eval numbers and thresholds don't move. See §2 D1. |
| 21 | `usage: {input_tokens, output_tokens}`; output tokens free; billed $42 per billion input tokens [OAS][MOD] | ⚠ | ⚠ | Shape matches; Keel always reports 0 (local, free). Real token counts are a tokenizer/route change (§3 R6). |
| 22 | `assets` map and `multipart/form-data` image upload (png/jpg) [OAS][IMG] | ❌ | ❌ | Model work. JSON `assets` is ignored. Multipart gets 400. |
| 23 | Compressed bodies: `Content-Encoding: gzip`/`x-gzip`/`zstd`; unsupported encoding returns 415 [ERR] | ❌ | ❌ | **Biggest drop-in break.** Both SDKs zstd-compress bodies ≥ 1 KiB by default when zstd is available: JS on Node ≥ 22.15 [JS], Python on 3.14+ or with the `[zstd]` extra [PY advanced]. Keel returns 400 "Body must be JSON." (proved in §4). Route fix: §3 R3. Workaround: `compression: false` / `compression=False`. |
| 24 | Body ≤ 32 MiB (413); nesting ≤ 64; finite numbers (400) [ERR] | ⚠ | ⚠ | Keel rejects non-finite numbers. No explicit 413 or nesting check; the 8000-char state cap hits first. |
| 25 | 422 `{detail:[{loc,msg,type,input,ctx}]}` for validation; 400 `{detail}` for request rules [ERR][OAS `HTTPValidationError`] | ⚠ | ⚠ | Keel sends 400 `{error:{type,message,request_id}}` for both. The JS SDK reads Keel's `error.message` and maps 400 to `BadRequestError`. Code that catches `UnprocessableEntityError` won't fire. Route change: §3 R4. |
| 26 | 401 bad key; 429 rate limit with backoff; 529 overloaded [ERR][MOD] | ⚠ | ⚠ | 401 ✅. Keel's 429 (120 requests per 60 s) sends no `retry-after`. The SDKs still back off exponentially, so a `retry-after` header is only a nicety (§3 R5). Keel never sends 529. Keel adds 409 when switched off; the SDK raises a generic `APIError`. |
| 27 | Rate limits per org in tokens/s and requests/s [MOD] | ⚠ | ⚠ | Keel is per process and counts requests only. |
| 28 | Official SDKs: Python `typesafe-sdk` (0.7.5, MIT), JS `@typesafe-ai/sdk` (0.7.0, MIT) [SDK][PY][JS] | ✅ with caveats | ✅ with caveats | Proved end to end in §4: `system_one` / `systemOne` work after a base-URL override plus `compression` off; `models.list` fails (#2). |
| 29 | SDK env vars `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`, `TYPESAFE_DEFAULT_MODEL` [PY constants][JS `ENV`] | ✅ | ✅ | Point `TYPESAFE_BASE_URL` at `http://localhost:8080/api`. |
| 30 | Streaming / batching endpoints | n/a | n/a | No streaming or batch endpoint appears in the OAS or docs index. Many questions per call is Jev's batching story ("speculative fan-out", [MOD]). |
| 31 | Latency and cost (vendor-reported): "193.6x faster, 444.6x cheaper", 0.114 s vs 8.566 s, $0.000081 per workflow [HOME] | n/a | n/a | Benchmark agents own the measurement. Keel is local and free. |
| 32 | Multilingual and jaggedness notes (e.g. /model-jaggedness/jev-1.13) | n/a | n/a | Model quality, not wire. |

## 2. Decisions taken in `wire.ts`

- **D1. Confidence is gated on the alias.**
  - `jevChoiceConfidence` and `jevScoreConfidence` implement [CONF] exactly. The tests reproduce the doc's own examples: (0.6, 0.3, 0.1) → 0.4, (0, 0.5, 0.5) → 0.25, (0.5, 0, 0.5) → 0, (0, 0.57, 0.43) → 0.355 ("≈ 0.35").
  - `projectWeights` uses them when `request.model` starts with `jev-`. `decider-*` keeps `confidenceFrom` (top probability), because `eval.ts` `maxConfidence` grading, `local.test.ts` thresholds and other agents' published numbers depend on it.
  - **Recommendation for the orchestrator:** decide whether `decider-3` should switch to the Jev formula globally. It is the documented, better-behaved statistic (0 on a uniform split for any n). That would need eval thresholds re-based.
- **D2. Lenient superset parsing.** Everything Jev's OAS accepts for choice, score and noul text questions now parses. Keel still rejects these, with clear 400 messages: reserved ids, control characters in keys, keys over 128 chars, a noul with neither instructions nor criteria, all-empty score levels, more than 64 questions, more than 1024 total alternatives, and state over 8000 chars.
- **D3. Character limits.** Instructions go from 1200 to 4000 chars and descriptions from 400 to 1000, so structured JSON criteria and instructions fit. The cross-encoder still truncates each (state, hypothesis) pair at 256 tokens (`neural.ts`), so long inputs are accepted but only partly seen. This is model work (§5).

Backwards compatibility: every request that used to be valid is still valid, with the same normalized output and the same `decider-*` confidence.

## 3. Route-level gaps (not in my ownership; patches for the route owner)

These live in `src/routes/api/v1/*.ts` and `judge.server.ts`, which I don't own under CONTRACT.md. All are cheap.

- **R1. `models` shape** (`models.ts`). Add Jev's list next to the existing OpenAI-style one; both SDKs ignore unknown fields. Python's base model uses `extra="ignore"`; JS only checks `Array.isArray(body.models)`.
  ```ts
  models: MODEL_ALIASES.map((name) => ({ name, description: `Keel alias; answers as ${wantsLexical(name) ? LEXICAL_MODEL : CONCRETE_MODEL}.`, release_date: "YYYY-MM-DD" /* Keel build date */ })),
  ```
- **R2. Path alias.** Serve `/v1/systemone` and `/v1/models` as thin re-exports of the `/api/v1/*` handlers, e.g. `src/routes/v1/systemone.ts`. Then `baseURL = http://localhost:8080` works unchanged, exactly like Jev.
- **R3. Request decompression** (`systemone.ts`, before `JSON.parse`). This matches [ERR]: gzip/x-gzip/zstd, one layer, 32 MiB cap, 415 on anything else.
  ```ts
  import { gunzipSync, zstdDecompressSync } from "node:zlib"; // zstd: Node ≥ 22.15
  const enc = (request.headers.get("content-encoding") ?? "").trim().toLowerCase();
  let raw = Buffer.from(await request.arrayBuffer());
  const cap = { maxOutputLength: 32 * 1024 * 1024 };
  if (enc === "gzip" || enc === "x-gzip") raw = gunzipSync(raw, cap);
  else if (enc === "zstd") raw = zstdDecompressSync(raw, cap);
  else if (enc && enc !== "identity") return wireError(415, "unsupported_encoding", `Content-Encoding ${enc} is not supported.`);
  const body = JSON.parse(raw.toString("utf8"));
  ```
  Without R3, the SDK defaults break as soon as a body reaches 1 KiB.
- **R4. 422 for schema errors.** Optional. Return 422 with `detail:[{loc:["body","questions",id,…], msg, type}]` alongside Keel's `error` object, so `UnprocessableEntityError` handlers fire.
- **R5. `retry-after`** on Keel's 429 (`judge.server.ts`), in seconds until the window resets. Both SDKs honour it: Python `retry` option "honor `Retry-After` and `retry-after-ms`" (https://docs.typesafe.ai/sdk/python/api/retries); the JS SDK 0.7.0 does the same in its `dist/index.mjs` retry loop.
- **R6. `usage.input_tokens`.** Report the tokenizer count of the pairs actually scored, so cost dashboards built on Jev's `usage` stay meaningful.

## 4. Jev SDK drop-in: commands run and output

Keel was started with `npm run dev`; `GET /api/v1/status` returned `{"enabled":true,"model":"decider-2.0.0","engine":"neural",…}`. The bearer is the Keel Copilot key and is written as `$KEEL_KEY` here. The server was stopped afterwards.

**curl** (only the host and key change from Jev's quickstart):
```powershell
curl.exe -s -X POST http://localhost:8080/api/v1/systemone -H "Authorization: Bearer $KEEL_KEY" -H "Content-Type: application/json" --data-binary "@body.json"
# body.json: {"model":"jev-latest","state":"I was charged twice for my subscription this month.","questions":{"department":{"type":"choice","instructions":"Which team should handle this ticket?","criteria":{"Billing":"Payments, refunds, invoices","Tech Support":"Bugs and outages","Sales":"New purchases"}},"urgency":{"type":"score","instructions":"How urgent is it?","criteria":["Low","Medium","High"]},"refund":{"type":"noul","instructions":"Is the customer asking for money back?"}}}
```
```
{"model":"decider-2.0.0","answers":{"department":{"type":"choice","choice":"Billing","confidence":0.92,"probabilities":{"Billing":0.947,"Tech Support":0.0251,"Sales":0.0279}},"urgency":{"type":"score","score":0.47,"confidence":0.3,"legend":{"0":"Low","1":"Medium","2":"High"},"probabilities":{"0":0.6359,"1":0.2613,"2":0.1028}},"refund":{"type":"noul","noul":0.216}},"usage":{"input_tokens":0,"output_tokens":0}}
HTTP 200
```
Before this change, the same request returned 400 because the label `"Tech Support"` has a space. Confidence now follows [CONF]: (0.947 − 1/3)/(2/3) = 0.92.

Other probes: a wrong bearer gives HTTP 401. `POST /v1/systemone` (no `/api`) gives HTTP 404 (R2). `{"type":"box"}` gives 400 "type must be choice, score, or noul".

**TypeScript, `@typesafe-ai/sdk@0.7.0`** (npm, MIT). Installed with `npm i @typesafe-ai/sdk` in a scratch folder on Node v24.22.1:
```js
import { TypeSafeClient, choice, score, noul } from "@typesafe-ai/sdk";
const client = new TypeSafeClient({
  apiKey: process.env.TYPESAFE_API_KEY,      // the Keel key
  baseURL: "http://localhost:8080/api",      // the SDK appends /v1/systemone
  compression: false,                        // until Keel decodes zstd (R3)
});
const r = await client.systemOne({ state, questions: {
  department: choice("Which team should handle this ticket?", { Billing: "Payments, refunds, invoices", "Tech Support": "Bugs and outages", Sales: null }),
  urgency: score("How urgent is it?", ["Low", "Medium", "High"]),
  refund: noul("Is the customer asking for money back?"),
}});
```
Output of `node proof.mjs`:
```
sdk 0.7.0
1 compression:false -> {"model":"decider-2.0.0","answers":{"department":{"type":"choice","choice":"Billing","confidence":0.897,"probabilities":{"Billing":0.9313,"Tech Support":0.032,"Sales":0.0367}},"urgency":{"type":"score","score":0.3,"confidence":0.543,"legend":{"0":"Low","1":"Medium","2":"High"},"probabilities":{"0":0.7676,"1":0.1602,"2":0.0722}},"refund":{"type":"noul","noul":0.1613}},"usage":{"input_tokens":0,"output_tokens":0}}
2 default zstd, body >= 1 KiB -> BadRequestError 400 400 Body must be JSON.
3 compression:false, body >= 1 KiB -> Billing
4 models.list -> TypeSafeError Unexpected response shape from GET /v1/models; expected { models: [...] }.
```

**Python, `typesafe-sdk==0.7.5`** (PyPI, MIT). Installed with `python -m venv venv; venv\Scripts\python -m pip install typesafe-sdk==0.7.5` on Python 3.12.10:
```powershell
$env:TYPESAFE_API_KEY = $KEEL_KEY
$env:TYPESAFE_BASE_URL = "http://localhost:8080/api"
```
```python
from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
with TypeSafeClient(compression=False) as client:   # needed on Python 3.14+ or with typesafe-sdk[zstd]
    r = client.system_one(state=state, questions={
        "department": Choice(instructions="Which team should handle this ticket?", criteria={"Billing": "Payments, refunds, invoices", "Tech Support": "Bugs and outages", "Sales": None}),
        "urgency": Score(instructions="How urgent is it?", criteria=["Low", "Medium", "High"]),
        "refund": Noul(instructions="Is the customer asking for money back?"),
    })
```
Output of `venv\Scripts\python proof.py`:
```
python 3.12.10 sdk 0.7.5
1 system_one -> decider-2.0.0 input_tokens=0 output_tokens=0
   department type='choice' choice='Billing' confidence=0.897 probabilities={'Billing': 0.9313, 'Tech Support': 0.032, 'Sales': 0.0367}
   urgency type='score' score=0.3 confidence=0.543 legend={0: 'Low', 1: 'Medium', 2: 'High'} probabilities={0: 0.7676, 1: 0.1602, 2: 0.0722}
   refund type='noul' noul=0.1613
3 compression=False, body >= 1 KiB -> Billing
4 models.list -> TypeSafeAPIResponseValidationError GET http://localhost:8080/api/v1/models: 200 Invalid response data at 'models'.
```
The Python SDK parses responses with strict pydantic models (`ConfigDict(extra="ignore", frozen=True, strict=True)`), so Keel's answers validate exactly against Jev's schema. On Python 3.12 without the `[zstd]` extra, the SDK sends uncompressed bodies [PY advanced]. `compression=False` is only needed on 3.14+ or with the extra.

**Drop-in recipe today:** set the base URL to `http://<keel-host>:8080/api`, set the API key to the Keel key, and turn compression off. After R2 and R3, only the host and key change. After R1, `models.list()` works too.

## 5. Gaps ranked by user impact

1. **zstd/gzip request bodies (R3).** SDK defaults fail on any body ≥ 1 KiB, which is most real states. Route fix; cheap.
2. **Confidence semantics.** ✅ Fixed for `jev-*` requests. A global flip is pending the orchestrator's decision (D1).
3. **Choice labels, option count, null instructions, score positions.** ✅ Fixed. Previously ordinary Jev requests got a 400 (labels with spaces, more than 12 options, more than 8 questions) or wrong level indices.
4. **`/v1` path and `models` shape (R1, R2).** Needed for "host + bearer only" and for `models.list()`. Route fixes; cheap.
5. **Context length** (64k/32k tokens, 262k with the long-context header) against Keel's 8000-char state and 256-token pairs. **Model work**: a longer-context encoder, or chunking with max/mean pooling over state windows.
6. **Error contract (422 `detail`, 415, 413, 529, `retry-after`).** Affects typed error handling only (R4, R5).
7. **`box` questions and images (`assets`, multipart, danger-zone images header).** **Model work**: needs a vision model. Jev itself labels this experimental and preview-only [IMG][BOX].
8. **`usage` token counts (R6) and per-org token-rate limits.** Cosmetic for a local model.

## 6. Validation

- `node --experimental-strip-types --test src/lib/decider/wire.test.ts src/lib/decider/local.test.ts src/lib/decider/eval.test.ts src/lib/decider/jev-compare.test.ts src/lib/decider/neural.test.ts` passed: 26 tests, 26 pass, 0 fail. After §7, `npm run test:keel` (which now also runs `msd1-compare.test.ts` and `systemone-route.test.ts`) passed 38/38 on 4 of 5 runs. One run, made while the dev server was shutting down, had 1 failure that did not reproduce in 3 reruns. That includes 5 new wire tests: the doc's confidence examples, alias gating, Jev-shaped requests (255 labels with spaces, a 1-option choice, null instructions, a criteria-only noul, 23 questions), score positions with a structured legend, and the remaining rejections.
- `npx tsc --noEmit` is clean.

## 7. Microsoft-Decision-1 wire compatibility (added at the orchestrator's request)

Sources: `artifacts/parity/msd1/api-and-access.md` (msd1-1), which cites the Microsoft Learn page https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision and the OpenRouter endpoints API.

| MSD1 feature | Keel before | Keel now | Where |
|---|---|---|---|
| `model` values `microsoft-decision-1`, `Microsoft-Decision-1`, `microsoft/microsoft-decision-1`, `microsoft/microsoft-decision-1-20261009` | ❌ (400 unknown model) | ✅ Aliases that resolve to `decider-2.0.0`, with top-probability confidence. Arbitrary Foundry deployment names are still rejected: omit `model` or name the deployment `microsoft-decision-1`. | `wire.ts` `MODEL_ALIASES` |
| `api-key: <key>` header (Foundry key auth) | ❌ | ✅ On decision calls only, with the same Keel key and a constant-time compare. `/api/v1/switch` stays Bearer-only. Entra tokens are not accepted, since Keel has no identity provider. | `auth.server.ts` `authorizeDecision` |
| `POST /providers/microsoft/v1/systemone` | ❌ (404) | ✅ Same handler as `/api/v1/systemone`. | `routes/providers/microsoft/v1/systemone.ts`, `lib/decider/systemone-route.server.ts` |

Live check (`npm run dev`, then stopped; the key is written as `$KEEL_KEY`):
```
POST /providers/microsoft/v1/systemone  api-key: $KEEL_KEY  {"model":"microsoft/microsoft-decision-1",…}
{"model":"decider-2.0.0","answers":{"team":{"type":"choice","choice":"billing","confidence":0.877,"probabilities":{"billing":0.8765,"engineering":0.1235}},"refund":{"type":"noul","noul":0.1022}},"usage":{"input_tokens":0,"output_tokens":0}}
HTTP 200
POST /api/v1/systemone                  api-key: $KEEL_KEY   -> HTTP 200
POST /providers/microsoft/v1/systemone  Bearer $KEEL_KEY     -> HTTP 200
POST /providers/microsoft/v1/systemone  api-key: wrong       -> HTTP 401
POST /api/v1/switch                     api-key: $KEEL_KEY   -> HTTP 401 (switch is Bearer-only)
```
