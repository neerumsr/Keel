# Release notes

## Keel 3.0.0 (2026-11-15, first public release)

> Keel-3 (`decider-3.0.0`, training run `t1-r11`) was promoted to `models/keel-3` on 2026-10-30 and is the default. This release also adds **Keel-Pro** (`decider-pro-1.0.0`, 62.73 on the full Decision Index public 0.3 suite; see [Keel-Pro](keel-pro.md)). The full list of changes is in `CHANGELOG.md`.

### Highlights

- **Keel-3 is the default model.** `decider-latest`, the `jev-*` aliases and the Microsoft-Decision-1 aliases now resolve to `decider-3.0.0` (<!-- num:k3.size -->17.7 MB<!-- /num -->, mixed int8 ONNX, same 13M-parameter architecture). `decider-2.0.0` stays pinnable, and `GET /api/v1/models` reports what each alias `resolves_to`. Keel-3 improves on Keel-2 on every suite that decided the promotion:

  | Suite | Keel-2 | Keel-3 |
  |---|---|---|
  | holdout-20 | <!-- num:k2.h20 -->15/20<!-- /num --> | <!-- num:k3.h20 -->18/20<!-- /num --> |
  | holdout-b-20 | <!-- num:k2.hb20 -->10/20<!-- /num --> | <!-- num:k3.hb20 -->18/20<!-- /num --> |
  | open-60 | <!-- num:k2.open60 -->34/60<!-- /num --> | <!-- num:k3.open60 -->52/60<!-- /num --> |
  | Held-out 100 (the three above) | <!-- num:k2.h100 -->59/100<!-- /num --> | <!-- num:k3.h100 -->88/100<!-- /num --> |
  | Blind 234 (safety misses) | <!-- num:k2.blind -->92/234<!-- /num --> (<!-- num:k2.blind.safety -->11<!-- /num -->) | <!-- num:k3.blind -->125/234<!-- /num --> (<!-- num:k3.blind.safety -->11<!-- /num -->) |
  | All held-out 334 (safety misses) | <!-- num:k2.heldout -->151/334<!-- /num --> (<!-- num:k2.heldout.safety -->14<!-- /num -->) | <!-- num:k3.heldout -->213/334<!-- /num --> (<!-- num:k3.heldout.safety -->12<!-- /num -->) |
  | Blind calibration error (ECE, lower is better) | <!-- num:k2.ece.blind -->0.182<!-- /num --> | <!-- num:k3.ece.blind -->0.108<!-- /num --> |
  | In-process p95, idle CPU | <!-- num:k2.p95.idle -->13.3–14.5 ms<!-- /num --> | <!-- num:k3.p95.idle -->13.7–14.3 ms<!-- /num --> |
  | **blind-c 100, confirmation (safety misses)** | <!-- num:k2.blindc -->47/100<!-- /num --> (<!-- num:k2.blindc.safety -->10<!-- /num -->) | **<!-- num:k3.blindc -->40/100<!-- /num --> (<!-- num:k3.blindc.safety -->12<!-- /num -->)** |

  Counts are "cases fully right". Sources: `artifacts/parity/t1-r11-parity.md`, `artifacts/parity/scoreboard.md`, `artifacts/parity/train-r2.md`.

- **Measured token savings (release candidate).** With the earlier release candidate `t1-r2e` in front of an LLM at τ = 0.6, LLM decision tokens on the held-out suites fell by <!-- num:tok.k3.ho.cut -->75.8%<!-- /num --> and accuracy rose (<!-- num:tok.k3.ho.acc -->75 → 89 of 100 cases fully right<!-- /num -->). On the blind suite the cut was <!-- num:tok.k3.blind.cut -->44.9%<!-- /num --> at a small accuracy cost (<!-- num:tok.k3.blind.acc -->64/71 → 63/71 (−1.4 pts)<!-- /num -->). The promoted `t1-r11` has not been re-measured for tokens. See [Token savings](token-savings.md).
- **MCP server.** `mcp/keel-mcp-server.mjs` (bin `keel-mcp`) exposes `keel_status`, `keel_decide` and `keel_switch` to any MCP client. See [Integrations](integrations.md).
- **Microsoft-Decision-1 route.** `POST /providers/microsoft/v1/systemone` with `api-key` header auth; MSD1 model names resolve to Keel's neural model.
- **Broader Jev wire compatibility.** More Jev-shaped questions are accepted.
- **Benchmarks you can rerun.** A blind 234-case suite no model trained on, a 100-case blind-c confirmation suite, public-benchmark adapters, a parity harness (`scripts/keel-parity-bench.ts`), a latency tool that times each model in its own process (`scripts/keel-latency.ts`) and a token-savings benchmark (`npm run keel:tokens`).
- **Standalone server.** `npm run build` then `npm start` runs a self-contained Node server; `npm run dev` is plain `vite dev`. Both bind `127.0.0.1:8080` unless `KEEL_HOST` says otherwise.
- **Open-source release scaffolding.** Apache-2.0 `LICENSE` and `NOTICE`, contributing guide, code of conduct, security policy, CI, `CITATION.cff` and a repeatable secret/PII/size audit (`scripts/oss-audit.mjs`).
- **Keel-Pro DeBERTa (experimental, now retired; the Keel-Pro name now refers to the Qwen3.5 LoRA).** A 70M-parameter line, `t2-dxs-b3` (<!-- num:pro.size -->108 MB<!-- /num -->), scores <!-- num:pro.blind -->134/234<!-- /num --> on blind but runs at <!-- num:pro.blind.lat -->117 / 242 ms<!-- /num --> p50 / p95. It is not shipped; it served as the distillation teacher for Keel-3.

### Known regression: blind-c

blind-c is the untouched 100-case confirmation suite; it was not used to select, calibrate or promote any model. **Keel-3 is worse than Keel-2 there**: <!-- num:k3.blindc -->40/100<!-- /num --> fully right against <!-- num:k2.blindc -->47/100<!-- /num --> (<!-- num:k3.blindc.delta -->−7<!-- /num -->), and <!-- num:k3.blindc.safety -->12<!-- /num --> safety misses against <!-- num:k2.blindc.safety -->10<!-- /num --> (<!-- num:k3.blindc.safety.delta -->+2<!-- /num -->). Most of the loss is on yes/no questions, and every Keel-3 candidate this round scored below Keel-2 on blind-c.

**Recommendation:** for safety-critical gates (destructive commands, secrets, injection, moderation), use the hybrid setting, where Keel answers only above τ and an LLM handles the rest, or pin `"model": "decider-2.0.0"` for those questions. Do not let either model approve a destructive action on its own. See [Benchmarks](benchmarks.md#the-blind-c-regression).

### Release gates

Keel-3 was promoted under the round-2 rule: (a) no more safety misses than Keel-2 on blind and held-out, (b) strictly more cases fully right, (c) in-process p95 under 20 ms. It passes all three, with blind safety tied at 11. Checkpoints were chosen on dev loss and calibrated on dev data only.

Against the stricter parity gates in `artifacts/parity/CONTRACT.md`:

| Gate | Requirement | Keel-3 |
|---|---|---|
| G1 | Zero safety misses on every held-out suite | **Not met**: <!-- num:k3.blind.safety -->11<!-- /num --> on blind, <!-- num:k3.heldout.safety -->12<!-- /num --> across all held-out suites |
| G2 | At least the LLM baseline on held-out (75/100) and on blind | Held-out met (<!-- num:k3.h100 -->88/100<!-- /num -->); blind **not met** (<!-- num:k3.blind -->125/234<!-- /num --> vs <!-- num:llm.blind -->215/234<!-- /num -->) |
| G3 | Strictly better than Keel-2 on blind and held-out | Met on accuracy; blind safety ties (<!-- num:k2.blind.safety -->11<!-- /num --> vs <!-- num:k3.blind.safety -->11<!-- /num -->); **regresses on blind-c** |
| G4 | In-process p95 under 20 ms | Met (<!-- num:k3.p95.idle -->13.7–14.3 ms<!-- /num -->, idle CPU, one model per process) |
| G5 | Public benchmarks reported honestly | Done for Keel-2 ([Benchmarks](benchmarks.md)); Keel-3 not measured yet |
| G6 | Token savings measured | Done with `t1-r2e` ([Token savings](token-savings.md)); not re-measured for `t1-r11` |
### Compatibility

- No wire-breaking changes, but **answers change**: `decider-latest`, `decider-preview`, the `jev-*` aliases and the Microsoft-Decision-1 aliases now resolve to `decider-3.0.0`, and responses report `"model": "decider-3.0.0"`. Send `"model": "decider-2.0.0"` to keep Keel-2 for a request, or set `KEEL_MODEL_DIR=models/keel-2` to make it the default.
- `.gitignore` allows both shipped ONNX files (`models/keel-3`, `models/keel-2`). If the Keel-3 weights file is missing, Keel falls back to Keel-2, then to the zero-shot base; check `neural.id` in `GET /api/v1/status`.
- Node 22.6 or later is required (`--experimental-strip-types`).
- The package is renamed `keel-decider`.

### Security fixes

- **Per-install bearer secret.** The bearer token used to be derived from a public built-in constant. It is now HMAC(secret, `"keel-local-decider-v1"`), truncated to 40 base64url characters, where the secret is `KEEL_SECRET` or a random secret generated on first use in `~/.keel/secret` (path override `KEEL_SECRET_FILE`, mode 0600). Print your token with `npm run keel:token`.
- **Loopback by default.** The server (`npm run dev` or `npm start`) binds `127.0.0.1:8080`; set `KEEL_HOST` to opt in to other interfaces. The bench UI's Copilot setup panel serves the token only to loopback requests.
- **Commit-safe agent files.** `npm run keel:agents` writes `<KEEL_TOKEN>` placeholders into `.github/agents/keel.agent.md` and `.github/copilot-instructions.md`, and the real token only into `~/.copilot/agents/keel.agent.md` and the Keel block of `~/.copilot/copilot-instructions.md`. `--repo-key` restores the old behaviour of embedding the token in the repo.

### Known issues

- Safety misses remain (see G1), and Keel-3 regresses on blind-c (see above). Do not use Keel as the only check before a destructive action.
- Public benchmarks (G5) have not been rerun on Keel-3, and token savings were measured on the `t1-r2e` release candidate, not on the promoted `t1-r11`.
- Some training data is CC BY-SA, and the base model's upstream training mix included ANLI (non-commercial). Pending maintainer review; see [Licenses](licenses.md).
- Jev and MSD1 quality were **not measured** live (no credentials). Only vendor-reported figures are quoted.

### Upgrade

1. `npm install`. Run `npm run model:fetch` only if `models/` is missing. Check `GET /api/v1/status`: `model` should be `decider-3.0.0`.
2. Re-check any thresholds you tuned on Keel-2. Keel-3 is calibrated differently (blind ECE <!-- num:k3.ece.blind -->0.108<!-- /num --> vs <!-- num:k2.ece.blind -->0.182<!-- /num -->), so the same τ defers a different share of questions. For safety-critical gates see the blind-c recommendation above.
3. **Your token changes.** Unless you set `KEEL_SECRET`, the first start generates `~/.keel/secret` and a new token. Run `npm run keel:agents`, and update any MCP or client config that stores the old token (`npm run keel:token` prints the new one).
4. If another machine or container called Keel over the network, set `KEEL_HOST` deliberately and firewall port 8080.
5. Verify with `npm run test:keel`.

## Keel 2.0.0 (2026-09-24)

Keel 2.0.0 added a local neural NLI cross-encoder (`decider-2.0.0`, <!-- num:k2.size -->13 MB<!-- /num --> int8 ONNX, fine-tuned from xtremedistil-l6-h256) while keeping the System One wire contract and the Keel-1 lexical fallback. The decision path stayed offline, local and zero-token.

### What was new compared with 1.2.0

| Area | 1.2.0 | 2.0.0 |
|---|---|---|
| Judge | Lexical feature model | NLI cross-encoder with lexical fallback |
| Model artefact | Code only | ONNX int8 + tokenizer + `keel.json` |
| Semantics | Feature and overlap driven | State-hypothesis entailment margins |
| Calibration | Lexical softmax/sigmoid constants | Per-type temperature, abstain threshold, optional blend |
| Status | Basic switch and model | Engine, neural loaded/id/error, fallback |

### Compatibility

No wire-breaking changes. The concrete model id became `decider-2.0.0` when the neural model loads. Explicit `decider-1.x` requests still pin the lexical judge and answer as `decider-1.2.0`. `GET /api/v1/status` gained `engine`, `neural.loaded`, `neural.id`, `neural.error` and `fallback`; `GET /api/v1/models` lists aliases and `resolves_to`.

### Measured on today's suites

Re-measured with the parity harness: holdout-20 <!-- num:k2.h20 -->15/20<!-- /num -->, holdout-b-20 <!-- num:k2.hb20 -->10/20<!-- /num -->, open-60 <!-- num:k2.open60 -->34/60<!-- /num -->, blind <!-- num:k2.blind -->92/234<!-- /num --> with <!-- num:k2.blind.safety -->11<!-- /num --> blind safety misses. Typical warm latency on short prompts is <!-- num:k2.p50.clean -->6–12 ms<!-- /num -->. The original 2.0.0 notes reported per-type results on smaller, partly in-sample suites; those are superseded by [Benchmarks](benchmarks.md).

## Keel 1.2.0

The lexical decider (`decider-1.2.0`), the System One wire (`POST /api/v1/systemone`), the on/off switch and the Copilot agent files.
