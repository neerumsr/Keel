# Architecture

How a request flows through Keel, how the MCP server and vendor aliases fit in, how models are loaded, and how a model gets from training data to `models/keel-2`.

## The big picture

<!-- diagram:request-flow -->

Keel is one Node process built with TanStack Start. It serves the bench UI, the HTTP API and the model. Agents talk to it over HTTP directly, or through a small stdio MCP server that translates tool calls into HTTP calls.

| Layer | Path | Role |
|---|---|---|
| Clients | Copilot CLI, VS Code, Claude Code, Codex, Cursor, SDKs, curl | Send System One requests |
| MCP bridge | `mcp/keel-mcp-server.mjs` | Exposes `keel_status`, `keel_decide`, `keel_switch` over stdio; holds the key in its environment |
| Routes | `src/routes/api/v1/*.ts`, `src/routes/providers/microsoft/v1/systemone.ts`, shared handler `src/lib/decider/systemone-route.server.ts` | Auth, JSON parsing, error envelope |
| Wire | `src/lib/decider/wire.ts` | Aliases, limits, request parsing, response projection |
| Judge | `src/lib/decider/judge.server.ts` | Switch check, rate limit, neural call, lexical fallback |
| Neural | `src/lib/decider/neural.server.ts` | Tokenizer, ONNX Runtime, margins, calibration, abstain |
| Lexical | `src/lib/decider/local.ts` | Keel-1 feature model, fallback |
| Auth | `src/lib/decider/auth.server.ts` | Derives the local key: HMAC of `KEEL_SECRET`, or of a random per-install secret in `~/.keel/secret` (`KEEL_SECRET_FILE`, mode 0600) |

## Request path

1. **Route.** `POST /api/v1/systemone`, or the alias `POST /providers/microsoft/v1/systemone`, reads the key from `Authorization: Bearer` or `api-key` and compares it in constant time. A missing or wrong key returns 401.
2. **Parse.** `tryParse` in `wire.ts` resolves the model alias, checks every limit (64 questions, 1,024 alternatives, 8,000-character state and so on) and normalises the question shapes: Jev `options` arrays, score objects and noul criteria. Errors return 400 with a message naming the field.
3. **Switch.** If Keel is switched off, the judge returns 409 before any model work.
4. **Rate limit.** A process-local limiter allows 120 decisions per 60 seconds and returns 429 beyond that.
5. **Engine.** The neural path runs unless the request pins `decider-1.x` or `KEEL_ENGINE=lexical` is set.
6. **Hypotheses.** `hypothesis.ts` turns each option, score level or yes/no into a hypothesis sentence. `training/keel/hypothesis.py` mirrors it exactly. `hypothesisVersion` in `keel.json` must match.
7. **Model.** Each (state, hypothesis) pair is tokenised to 256 tokens and run through the int8 ONNX graph. The output is an entailment margin per pair.
8. **Calibrate.** Margins are divided by the per-type temperature. If no option is entailed above `abstain.threshold`, the distribution is flattened toward uniform. An optional lexical blend is added.
9. **Project.** `projectWeights` builds the answer: choice, expected score, P(yes), confidence (top probability, or Jev style for `jev-*` aliases), rounded probabilities and `usage: 0`.
10. **Fallback.** Any exception in the neural path is caught, and the lexical judge answers as `decider-1.2.0`. The response `model` always names the judge that answered.

## Model aliases

`wire.ts` holds one alias table. Every alias resolves to a judge and a confidence style:

| Alias family | Judge | Confidence |
|---|---|---|
| `decider-latest`, `decider-3.0.0`, `decider-preview` | Neural (Keel-3) | Top probability |
| `decider-2.0.0` | Keel-2, pinned | Top probability |
| `decider-1.0.0`, `decider-1.1.0`, `decider-1.2.0` | Lexical | Top probability |
| `jev-latest`, `jev-1.14.0`, `jev-1.13.0`, `jev-preview` | Neural | Jev style |
| `microsoft-decision-1` and three spellings | Neural | Top probability |

The Microsoft-Decision-1 aliases and the `/providers/microsoft/v1/systemone` route share one handler with the main route, so behaviour cannot drift between them.

## The MCP server

`mcp/keel-mcp-server.mjs` is a stdio server built on `@modelcontextprotocol/sdk` and `zod`:

- **`keel_status`** calls `GET /api/v1/status`.
- **`keel_decide`** validates `{state, questions, model?}` with a zod schema (1–8 questions, 1,200-character instructions) and calls `POST /api/v1/systemone`.
- **`keel_switch`** calls `POST /api/v1/switch`.

It reads `KEEL_URL`, `KEEL_TOKEN` and `KEEL_TIMEOUT_MS` from its environment, so the key never appears in prompts. HTTP errors become MCP tool errors with the status and a one-line hint. At start-up it sends MCP `instructions`, which some clients (such as Codex) show to the model. `mcp/smoke.mjs` spawns it and calls every tool.

## Model loading

`neural.server.ts` looks for a model directory in this order:

1. `KEEL_MODEL_DIR`
2. `models/keel-3` (Keel-3, `decider-3.0.0`, the default)
3. `models/keel-2` (Keel-2, `decider-2.0.0`)
4. `models/keel-base` (the untrained base; answers as `decider-2.0.0-zeroshot`)

A directory counts only when its ONNX weights are present. Keel-2 is also loaded on demand (`KEEL2_MODEL_DIR`, default `models/keel-2`), so requests for `decider-2.0.0` keep working.

A directory is loadable when it has `tokenizer.json` and `config.json`. `keel.json` supplies the id, the ONNX path and the calibration. Release candidates live in `models/candidates/<name>/`. Promotion copies one into place.

```text
models/keel-2/
  config.json  tokenizer.json  tokenizer_config.json  special_tokens_map.json  vocab.txt
  keel.json
  onnx/model_quantized.onnx
```

### keel.json reference

| Field | Meaning |
|---|---|
| `id` | Runtime model id, such as `decider-3.0.0` |
| `base` | Base model identifier |
| `hypothesisVersion` | Must match `HYPOTHESIS_VERSION` in TypeScript and Python |
| `maxLength` | Tokens per pair, 256 |
| `threads` | ONNX intra-op threads |
| `onnx` | Relative path to the graph |
| `quantization` | `dynamic` or `mixed` |
| `temperature.choice` / `.score` / `.noul` | Per-type calibration temperatures |
| `abstain.threshold`, `abstain.floor` | When and how far to flatten toward uniform |
| `lexicalBlend.*` | Weight of the lexical log-probabilities added to neural logits (0 in Keel-3) |
| `scoreSmoothing`, `noulBias` | Optional score and noul adjustments |
| `calibration` | Fitted temperatures, dev NLL and group counts |
| `calibrationSet` | Which dev files the calibration was fitted on |
| `trainedOn`, `training` | Provenance: data, steps, minutes, best dev loss |

## Training pipeline

<!-- diagram:training-pipeline -->

| Stage | Tool | Output |
|---|---|---|
| Families | `training/keel/families.py`, `families_v3.py` | Templated decision families with soft labels |
| Data build | `training/keel/build_data.py` | `train.jsonl` and `dev.jsonl`, 6-gram decontaminated against held-out and blind states |
| Public data | `training/public/` | Converted train splits from datasets whose licenses allow training |
| Teacher | `training/keel/t2_train.py` | Keel-3-Pro (DeBERTa-v3-xsmall) and its soft labels |
| Student | `training/keel/train.py` | Checkpoints in `training/runs/<name>/best` |
| Export | `training/keel/export.py` | ONNX graph, mixed int8 quantization, calibrated `keel.json` |
| Bench | `scripts/keel-parity-bench.ts`, `scripts/keel-tokens.ts` | Scoreboard rows and token reports |
| Promote | Copy to `models/keel-2` (or `models/keel-3`) | Served by default |

See [Training guide](training-guide.md) for the commands.

## Design choices

- **A cross-encoder, not a generator.** Scoring each option against the state gives order-invariant probabilities in a single forward pass per option. There is no decoding, sampling or parsing.
- **Small on purpose.** A 6-layer, 256-wide model runs in milliseconds on any CPU and fits in a repository. Breadth is traded for latency, privacy and cost.
- **Calibration lives in config.** Temperatures and thresholds are in `keel.json`, so a model can be recalibrated without retraining.
- **A lexical fallback always answers.** If ONNX fails to load, decisions keep working, and the response `model` says so.
- **Same wire as the hosted models.** Clients can move between Keel, Jev and Microsoft-Decision-1, or use them in a cascade.
