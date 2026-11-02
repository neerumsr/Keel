# API reference

Every endpoint, field, alias, limit and error in Keel's System One-compatible HTTP API.

The base URL is `http://localhost:8080`, the port `npm run dev` serves. All bodies are UTF-8 JSON. Compressed request bodies (`Content-Encoding: zstd` or `gzip`) are not supported yet and return 400.

## Endpoints

| Method and path | Auth | Purpose |
|---|---|---|
| `POST /api/v1/systemone` | Key | Score one state against 1–64 typed questions |
| `POST /providers/microsoft/v1/systemone` | Key | Same handler, on the Microsoft Foundry path |
| `GET /api/v1/status` | None | Switch state, loaded model, engine, fallback |
| `POST /api/v1/switch` | Bearer only | Turn Keel on or off |
| `GET /api/v1/models` | None | List of accepted model aliases |

There is no `/v1/systemone` route without the `/api` prefix. Jev SDKs reach the right path when their base URL is `http://localhost:8080/api`.

## Authentication

Decision calls accept either header:

```http
Authorization: Bearer <key>
api-key: <key>
```

The switch accepts only `Authorization: Bearer`. Status and models are public.

The key is a local password for this Keel process, not a vendor API key. It is the first 40 characters of base64url(HMAC-SHA256(secret, `"keel-local-decider-v1"`)). The secret is `KEEL_SECRET` if set; otherwise it is a random 32-byte secret that Keel generates on first use and stores in `~/.keel/secret` (override the path with `KEEL_SECRET_FILE`; file mode 0600). Every install therefore has its own key. Print yours with `npm run keel:token`. To rotate it, delete the secret file or change `KEEL_SECRET`, restart, and rerun `npm run keel:agents`. Keys are compared in constant time.

Entra ID and OAuth tokens are not accepted, because Keel has no identity provider.

## POST /api/v1/systemone

### Request

```json
{
  "model": "decider-latest",
  "state": "git push --force origin main",
  "questions": {
    "cmd": {
      "type": "choice",
      "instructions": "The agent wants to run this command. What should happen?",
      "criteria": {
        "run": "Read-only or workspace-scoped",
        "confirm": "Has side effects; ask the user",
        "block": "Destructive or exfiltrates data"
      }
    }
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `model` | string | No | An alias from the table below. Defaults to `decider-latest`. Unknown names return 400. |
| `state` | string, object or array | Yes | The text being judged. Objects and arrays are serialised to JSON text. Up to 8,000 characters. |
| `questions` | object | Yes | 1–64 entries. The key is your question id and is echoed in `answers`. |
| `questions.<id>.type` | `choice`, `score` or `noul` | Yes | Jev's `box` type returns 400. |
| `questions.<id>.instructions` | string or null | Noul: yes, unless `criteria` is set | Up to 4,000 characters. |
| `questions.<id>.criteria` | object, array or null | Choice and score: yes | See below. |
| `questions.<id>.options` | array | No | Jev's alternative to choice `criteria`: a list of option descriptions. Keys are derived from each description. |

Criteria by type:

- **choice**: an object `{ "<option>": "<description>" | null }` with 1–255 options. Option keys must be unique.
- **score**: an ordered array such as `["Low", "Medium", "High"]`, or an object with numeric keys such as `{ "0": "Low", "1": "Medium", "2": "High" }`, with 1–10 levels. Structured level values are echoed in `legend`.
- **noul**: optional `{ "true": "<what yes means>", "false": "<what no means>" }`.

Keel is text-only. Image inputs are not supported, and Jev's long-context header is ignored.

### Response

```json
{
  "model": "decider-3.0.0",
  "answers": {
    "cmd": { "type": "choice", "choice": "block", "confidence": 0.882,
             "probabilities": { "run": 0.0762, "confirm": 0.0422, "block": 0.8816 } }
  },
  "usage": { "input_tokens": 0, "output_tokens": 0 }
}
```

This is real Keel-3 (`decider-3.0.0`) output for the request above.

| Answer field | Types | Meaning |
|---|---|---|
| `type` | all | Echo of the question type |
| `choice` | choice | The most likely option key |
| `score` | score | Expected level Σ i·pᵢ, to 2 decimals |
| `noul` | noul | P(yes), to 4 decimals |
| `confidence` | choice, score | The top probability (`decider-*` and MSD1 aliases), or Jev-style confidence (`jev-*`), to 3 decimals. See [Concepts](concepts.md#confidence). |
| `probabilities` | choice, score | The full distribution, to 4 decimals. Keys are option names for choice and level indexes for score. |
| `legend` | score | Level index → level name |

`model` is the id of the judge that actually answered. `usage` is always zero. Responses carry `Cache-Control: no-store`.

## POST /providers/microsoft/v1/systemone

This is the same handler as `/api/v1/systemone`, mounted on the path Microsoft Foundry uses for Microsoft-Decision-1. Send the `api-key` header and `"model": "microsoft-decision-1"`, or omit `model`. Custom Foundry deployment names return 400, because Keel has no deployments.

## Model aliases

| Alias | Answered by | Confidence style |
|---|---|---|
| `decider-latest`, `decider-3.0.0`, `decider-preview` | Neural model (Keel-3) | Top probability |
| `decider-2.0.0` | Keel-2, pinned (`models/keel-2`) | Top probability |
| `decider-1.2.0`, `decider-1.1.0`, `decider-1.0.0` | Lexical judge `decider-1.2.0` | Top probability |
| `jev-latest`, `jev-1.14.0`, `jev-1.13.0`, `jev-preview` | Neural model | Jev style |
| `microsoft-decision-1`, `Microsoft-Decision-1`, `microsoft/microsoft-decision-1`, `microsoft/microsoft-decision-1-20261009` | Neural model | Top probability |

"Neural model" means the first loadable directory among `KEEL_MODEL_DIR`, `models/keel-3`, `models/keel-2` and `models/keel-base`. Its id is `decider-3.0.0` with the shipped weights, `decider-2.0.0` if Keel-3's weights are missing, or `decider-2.0.0-zeroshot` when only the base is installed. `GET /api/v1/models` reports what each alias `resolves_to`. If it cannot load, or `KEEL_ENGINE=lexical` is set, the lexical judge answers as `decider-1.2.0`. Vendor aliases exist for drop-in compatibility and never mean that a hosted service answered.

## Limits

| Limit | Value |
|---|---:|
| Questions per request | 64 |
| Total alternatives across all questions | 1,024 |
| Options per choice | 1–255 |
| Levels per score | 1–10 |
| Question id and option key | 128 characters, no control characters |
| `state` | 8,000 characters |
| `instructions` | 4,000 characters |
| Option or level description | 1,000 characters |
| Encoder window | about 256 tokens per (state, option) pair |
| Rate | 120 decision requests per 60 seconds per server process (`KEEL_RATE_PER_MINUTE`) |

The `decider-pro-1.0.0` pin (the optional Keel-Pro sidecar, `artifacts/parity/pro/SERVE.md`) reads long contexts, so
it accepts an empty `state` (everything in the question), states up to 200,000 characters, instructions up to 100,000
and descriptions up to 8,000. The counts above are the same for every model.

Reserved question ids are `confidence`, `probabilities`, `usage`, `model`, `answers`, `state`, `questions`, `error`, `type` and `quota`.

The MCP tool `keel_decide` is stricter than the wire. It allows 1–8 questions and 1,200-character instructions per call.

## Errors

Every error uses one envelope:

```json
{ "error": { "type": "invalid_request", "message": "state is 9120 characters. The limit is 8000.", "request_id": "req_3f9c0a1b2d4e5f60" } }
```

| Status | `type` | When | What to do |
|---:|---|---|---|
| 400 | `invalid_request` | The body is not JSON or is compressed, or a field is missing, too long or the wrong shape | Fix the request. The message names the field. |
| 401 | `unauthorized` | The key is missing or wrong | Send `Authorization: Bearer <key>` or `api-key: <key>`. |
| 409 | `disabled` | The switch is off. No model ran. | Fall back to your own logic, or turn Keel on. |
| 429 | `rate_limited` | More than 120 requests in 60 seconds (`KEEL_RATE_PER_MINUTE` changes it) | Back off and retry. There is no `Retry-After` header. |

## GET /api/v1/status

```json
{"enabled":true,"model":"decider-3.0.0","engine":"neural","neural":{"loaded":true,"id":"decider-3.0.0","error":null},"fallback":"decider-1.2.0"}
```

| Field | Meaning |
|---|---|
| `enabled` | Switch state. When false, decisions return 409. |
| `model` | The judge that would answer `decider-latest` now |
| `engine` | `neural` or `lexical` |
| `neural.loaded`, `neural.id`, `neural.error` | Whether the ONNX model loaded, its id, and the load error if any |
| `fallback` | The lexical judge id |

## POST /api/v1/switch

```bash
curl -s -X POST http://localhost:8080/api/v1/switch \
  -H "Authorization: Bearer $KEEL_TOKEN" -H "Content-Type: application/json" -d '{"enabled":false}'
# {"enabled":false}
```

The switch lives in memory and resets to on when the server restarts.

## GET /api/v1/models

```json
{"object":"list","data":[{"id":"decider-latest","object":"model","owned_by":"keel","resolves_to":"decider-3.0.0"}, ...]}
```

The real list has one entry per alias. It is an OpenAI-style list, which the Jev SDK's `models.list()` does not parse yet.

## Differences from Jev and Microsoft-Decision-1

| Area | Keel | Jev and Microsoft-Decision-1 |
|---|---|---|
| Where it runs | Your machine | Hosted API |
| Auth | Local derived key, as Bearer or `api-key` | Vendor key. Foundry also supports Entra ID. |
| Question types | `choice`, `score`, `noul` | Jev also has `box` and image inputs |
| Context | About 256 tokens per pair | Jev 64k tokens, Microsoft-Decision-1 32k tokens (vendor-documented) |
| Compressed bodies | Not supported | Jev SDKs compress bodies of 1 KiB or more |
| `usage` | Always 0 | Billed input tokens |
| Rate limit | 120 per minute per process | Per-account quotas |
| `models.list()` | OpenAI-style list | SDK-specific shape |

## Code samples

### curl

```bash
curl -s http://localhost:8080/api/v1/systemone \
  -H "Authorization: Bearer $KEEL_TOKEN" -H "Content-Type: application/json" \
  -d '{"state":"Invoice charged twice","questions":{"route":{"type":"choice","instructions":"Which queue?","criteria":{"billing":"Money or invoices","bug":"Product broken"}}}}'
```

### PowerShell

```powershell
$body = @{ state = "Invoice charged twice"; questions = @{ route = @{ type = "choice"; instructions = "Which queue?"
  criteria = @{ billing = "Money or invoices"; bug = "Product broken" } } } } | ConvertTo-Json -Depth 8
Invoke-RestMethod http://localhost:8080/api/v1/systemone -Method Post -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $env:KEEL_TOKEN" } -Body $body
```

### Python

```python
import os, requests
r = requests.post("http://localhost:8080/api/v1/systemone",
    headers={"api-key": os.environ["KEEL_TOKEN"]},
    json={"state": "Invoice charged twice",
          "questions": {"route": {"type": "choice", "instructions": "Which queue?",
                                  "criteria": {"billing": "Money or invoices", "bug": "Product broken"}}}},
    timeout=5)
print(r.json()["answers"]["route"]["choice"])
```

### TypeScript

```ts
const res = await fetch("http://localhost:8080/api/v1/systemone", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.KEEL_TOKEN}`, "Content-Type": "application/json" },
  body: JSON.stringify({ state: "Invoice charged twice", questions: { route: { type: "choice", instructions: "Which queue?", criteria: { billing: "Money or invoices", bug: "Product broken" } } } }),
});
const { answers } = await res.json();
```

## Migrating from a hosted service

| From | Change |
|---|---|
| Jev REST | Replace `https://api.typesafe.ai/v1/systemone` with `http://localhost:8080/api/v1/systemone`, and use the Keel key |
| Jev SDK | Set `TYPESAFE_BASE_URL=http://localhost:8080/api` and `TYPESAFE_API_KEY=<Keel key>`, and pass `compression=False` |
| Microsoft-Decision-1 on Foundry | Replace `{endpoint}/providers/microsoft/v1/systemone` with `http://localhost:8080/providers/microsoft/v1/systemone`, and send `api-key: <Keel key>` |
| OpenRouter | Set the base URL to `http://localhost:8080/api` and keep `model: "microsoft/microsoft-decision-1"` |
