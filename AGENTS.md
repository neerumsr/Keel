# Contributor guide (humans and coding agents)

Keel is a local System One decision model (choice, score, yes/no) with a TanStack Start web app,
a System One-compatible HTTP API and an MCP server. No network call on the decision path.

## Layout

| Path | What |
|---|---|
| `src/lib/decider/` | Wire format, lexical judge (`local.ts`), ONNX judge (`neural.server.ts`), eval suites, switch, bearer |
| `src/routes/api/v1/` | HTTP API: `status`, `models`, `systemone`, `switch` |
| `src/routes/providers/` | Microsoft-Decision-1-compatible route |
| `src/components/keel/`, `src/routes/index.tsx` | The Keel UI |
| `src/start.ts`, `src/lib/loopback.ts` | Request middleware: UI server functions answer loopback `Host` only |
| `src/lib/db.ts`, `migrations/` | Embedded PGlite (or `DATABASE_URL` Postgres) for the on/off switch |
| `mcp/` | `keel-mcp` stdio server and `smoke.mjs` |
| `models/` | Shipped model config/tokenizer (`keel-2` ONNX is tracked; others are fetched) |
| `training/` | Python data generation, training, export |
| `scripts/` | Benches, comparisons, model fetch, audit, `start.mjs` |
| `docs/`, `artifacts/`, `hf/` | Documentation, reports, Hugging Face staging |

## Commands

```powershell
npm install
npm run model:fetch                 # only if the model you need is not on disk
npm run dev                         # http://127.0.0.1:8080 (set KEEL_HOST to bind elsewhere)
npm run build; npm start            # production server, same host/port rules
npm run --silent keel:token         # print the local bearer for /api/v1/*
```

The server binds `127.0.0.1` by default because the UI shows the bearer. Do not change that default.

## Tests (run before every pull request)

```powershell
npm run typecheck
npm run test:keel                          # wire, judges, evals, compare harnesses, loopback guard
npm test                                   # test:keel + migration-plan tests
python training/keel/test_hypothesis.py    # TS/Python hypothesis parity
node scripts/oss-audit.mjs --fail-on medium
npm run keel:bench                         # when model, data or calibration change
```

With a dev server running, `node mcp/smoke.mjs` (with `KEEL_TOKEN` set) checks the MCP server.

## Training and eval honesty rules

1. Never fabricate a Jev or Microsoft-Decision-1 output or number. Vendor numbers are cited with a
   URL and marked "vendor-reported"; live numbers come only from real calls.
2. Never delete or relabel an eval case to improve a number. If a label is wrong, say so and explain.
3. Held-out integrity: training and data-generation code must not read
   `src/lib/decider/eval-blind*.ts` or `artifacts/parity/blind/**`. Only the test suite and the final
   benchmark harness read them.
4. Keep `src/lib/decider/hypothesis.ts` and `training/keel/hypothesis.py` behaviorally identical.
5. Record the license of every downloaded dataset or weight in `docs/licenses.md`.

## Secrets

Never put secrets in files, logs, eval `state`, or commits: no API keys, no bearer values, no
connection strings with real credentials. Hosted-service keys are read from environment variables
only, and are never printed. `.env*` files are gitignored; keep it that way.
