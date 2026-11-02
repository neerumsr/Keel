# Help guide

Day-to-day use of Keel: running it, switching it on and off, connecting agents, writing good questions, reading answers and fixing common problems. New here? Start with [Quickstart](quickstart.md). Short answers to common questions are in the [FAQ](faq.md).

## Install and run

```powershell
npm install
npm run dev          # vite dev: bench UI and API on http://127.0.0.1:8080
```

For a long-running service, build once and start the standalone Node server. It needs no Vite at runtime and binds the same `127.0.0.1:8080` (`KEEL_HOST` and `PORT` override):

```powershell
npm run build
npm start            # node scripts/start.mjs, serves .output/server
```

There is no sign-in and no hosted backend: the only credential is your local bearer token.

You need Node 22.6 or later. The trained weights ship in `models/keel-3` (Keel-3, the default) and `models/keel-2` (Keel-2, pinnable as `decider-2.0.0`). If both are missing, `npm run model:fetch` downloads the MIT zero-shot base into `models/keel-base`, and Keel answers as `decider-2.0.0-zeroshot` until you train or restore a model.

| Environment variable | Default | Effect |
|---|---|---|
| `KEEL_SECRET` | Unset: use the per-install secret file | Secret the bearer token is derived from. Set it to share one key across machines or CI. |
| `KEEL_SECRET_FILE` | `~/.keel/secret` | Where the random per-install secret is generated (mode 0600) and read. |
| `KEEL_HOST` | `127.0.0.1` | Interface `npm run dev` and `npm start` bind. Change it only if you deliberately want other machines to reach Keel. |
| `KEEL_MODEL_DIR` | `models/keel-3`, then `models/keel-2`, then `models/keel-base` | Load a different default model folder, for example `models/keel-2` or a candidate. |
| `PORT` | `8080` | Port for `npm start` (the dev server always uses 8080). |
| `KEEL_ENGINE` | Unset (neural) | Set to `lexical` to force the Keel-1 fallback judge. |
| `KEEL_RATE_PER_MINUTE` | `120` | Decisions allowed per 60 s per process. `0` turns the limit off (benchmark runs). |
| `KEEL_PRO_URL` | `http://127.0.0.1:8090` | Keel-Pro sidecar for the `decider-pro-1.0.0` pin (loopback only, see `artifacts/parity/pro/SERVE.md`). |

## Get your token

Decision calls need a bearer token: an HMAC of `KEEL_SECRET`, or, when that is unset, of a random secret Keel generates on first use in `~/.keel/secret`. Each install has its own token. These docs write it as `<KEEL_TOKEN>`; never paste the real value into shared files. Three ways to get yours:

- Run `npm run keel:token`, which prints it (`npm run -s keel:token` prints only the token, for use in scripts).
- Open the bench UI at `http://localhost:8080` from the same machine; the Copilot tab shows it to loopback requests only.
- Run `npm run keel:agents`. It writes the real token only to your user-level files, `~/.copilot/agents/keel.agent.md` and the Keel block of `~/.copilot/copilot-instructions.md`. The repo copies (`.github/agents/keel.agent.md`, `.github/copilot-instructions.md`) get a `<KEEL_TOKEN>` placeholder and are safe to commit; `--repo-key` embeds the real token there too, for private use only.

To rotate the token: delete `~/.keel/secret` (or change `KEEL_SECRET`), restart the server, then rerun `npm run keel:agents` and update any client that stores the token.

## Turn Keel on or off

The switch is shared by every agent and the bench UI. Say "Keel on" or "Keel off" to an agent that has the integration, flip it in the UI, or call the API:

```bash
curl -s -X POST http://localhost:8080/api/v1/switch \
  -H "Authorization: Bearer $KEEL_TOKEN" -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

While it is off, `POST /api/v1/systemone` returns `409` and no model runs; agents fall back to their own judgement. `GET /api/v1/status` needs no token and reports `enabled`.

## Connect an agent

The bundled MCP server, `mcp/keel-mcp-server.mjs` (bin `keel-mcp`), gives any MCP client three tools: `keel_status`, `keel_decide` and `keel_switch`. It reads `KEEL_URL` (default `http://localhost:8080`), `KEEL_TOKEN` and `KEEL_TIMEOUT_MS` (default 15000). Copy-paste configs for GitHub Copilot CLI, VS Code Copilot, Claude Code, OpenAI Codex CLI and Cursor are in [Integrations](integrations.md). Check the bridge with `node mcp/smoke.mjs`.

## Use the bench UI

The bench UI at `http://localhost:8080` is for people. Paste a state and questions, and it shows the answer, probabilities, model id and latency. Use it to try a rubric before wiring it into an agent.

## Writing good questions

- Put the facts in `state` and the rubric in `instructions` and `criteria`. Never put secrets in `state`.
- Keep the deciding fact early. The encoder reads about 256 tokens per (state, option) pair.
- Make choice options mutually exclusive and describe each in a few concrete words; the descriptions become the hypotheses the model reads.
- Order score levels from low to high.
- For `noul`, say what "yes" means when the threshold matters.
- Ask related questions in one request; Keel judges them in parallel.

More patterns: [Concepts](concepts.md) and [50 use cases](use-cases.md).

## Reading answers

| Type | Field | Meaning |
|---|---|---|
| choice | `choice`, `confidence`, `probabilities` | Winning key, its probability, all keys' probabilities |
| score | `score`, `probabilities` | Expected level index (can be fractional), per-level probabilities |
| noul | `noul` | P(yes). There is no confidence field; pick your own threshold |

Act on Keel's answer when confidence (or the distance of `noul` from 0.5) clears your τ threshold, and send the rest to an LLM or a person. τ = 0.6 is a good starting point. Values of `noul` between 0.4 and 0.6 mean "unsure".

The response's `model` is the judge that actually answered: `decider-3.0.0` for Keel-3 (the default), `decider-2.0.0` for Keel-2 (pinned, or when Keel-3's weights are missing), `decider-2.0.0-zeroshot` for the base model only, or `decider-1.2.0` for the lexical fallback or any `decider-1.x` pin.

## Troubleshooting

| Symptom | Meaning | Fix |
|---|---|---|
| `409` from `/systemone` | The switch is off; no model ran | Turn Keel on |
| `401` | Missing or wrong token | Run `npm run keel:token` again; if the secret changed (new `~/.keel/secret`, `KEEL_SECRET`, or a different user account), rerun `npm run keel:agents` and update stored client configs |
| Connection refused from another machine or container | The server binds `127.0.0.1` by default | Call it from the same machine, or set `KEEL_HOST` deliberately and firewall the port |
| `400` | Malformed request | Check the request against the [API reference](api-reference.md) |
| `429` | More than 120 decisions in 60 seconds | Wait, then retry once |
| MCP tool says "unreachable" | The server is not running or `KEEL_URL` is wrong | Run `npm run dev`; check `KEEL_URL` |
| `status.neural.error` is set | The model did not load | Check `KEEL_MODEL_DIR` and `models/keel-2`, or run `npm run model:fetch` |
| `engine: "lexical"` | Neural is unavailable or forced off | Unset `KEEL_ENGINE`; check the model folder |
| Slow first call | The model loads on first use | Warm it with one request at startup |

## Benchmarks and tests

```powershell
npm run test:keel        # unit and wire tests
npm run keel:token       # print your bearer token (-s for the bare value)
npm run keel:bench       # labelled and held-out suites for models/keel-2
npm run keel:tokens      # token-savings benchmark (calls an LLM; costs tokens)
```

Results and their caveats are in [Benchmarks](benchmarks.md) and [Token savings](token-savings.md).
