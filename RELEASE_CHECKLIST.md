# Release checklist — Keel 3.0.0 (Apache-2.0, GitHub + Hugging Face)

Owner: maintainer. Prepared by oss-prep on 2026-10-29. Nothing in this list has been pushed,
created, uploaded or published. Tick items in order; each step says how to verify it.

Related: `artifacts/parity/oss-audit.md` (audit findings and size decisions), `hf/FILES.md`,
`hf/upload.ps1`, `docs/press.md` (press kit and social card).

## 0. Status at preparation time

- [x] `.gitignore` covers training data/runs (GBs), candidates, teachers, fetched weights, ONNX
      binaries (except the grandfathered `models/keel-2` ONNX), restricted public-benchmark
      subsets and bulky parity caches. `.gitattributes` added (LF, binary weights, linguist).
- [x] `package-lock.json` resolves from `registry.npmjs.org` (was an internal feed).
- [x] `package.json`: `keel-decider@3.0.0`, `Apache-2.0`, keywords, `engines.node >=22.6.0`,
      `bin.keel-mcp`, `files`, repository `sivamatic/Keel`.
- [x] **`"private": true` is kept on purpose** so `npm publish` cannot run by accident. Remove it
      only in step 12 (MCP registry), and only if publishing to npm is decided.
- [x] CI (`.github/workflows/ci.yml`), issue templates, PR template, `CITATION.cff`, `CHANGELOG.md`,
      HF staging (`hf/`), repeatable audit (`scripts/oss-audit.mjs`).
- [x] Removed: `startup.sh` (sandbox revive script, `cd /workspace`), `artifacts/keel-local.tar.gz`
      (unused source snapshot). Verified after removal: `npm run typecheck` ✔, `npm run test:keel` ✔ (38/38).

## 1. Platform cleanup plan (reviewed list)

The repo began as a "Grok App Builder" workspace. Goal: a standalone project where
`npm install && npm run dev` and `npm run test:keel` work with no platform services. Keel's own
code depends on the platform in only two places: `src/routes/__root.tsx` (`AuthProvider`,
`PreviewHostBridge`, `/__grok/` manifest links) and `src/lib/decider/switch.server.ts` (`@/lib/db`
for the on/off switch, PGlite + `migrations/0002_keel_switch.sql`).

Several batches touch `package.json` scripts/dependencies, `vite.config.ts`, and `src/`. They are
outside oss-prep's ownership and would restart the shared dev server other agents use, so they
were **pending the maintainer's approval**; P1–P7 and P9–P11 were done by oss-cleanup on 2026-10-29 (verification: typecheck, `test:keel` 41/41, build, `oss-audit --fail-on medium`, dev-server API + UI + MCP smoke). After each batch run:
`npm run typecheck; npm run test:keel; npm run build` and check that the HTML at
`http://127.0.0.1:8080/` has no `grok` string.

| # | Files | What it is | Decision | Status |
|---|---|---|---|---|
| P0 | `startup.sh`, `artifacts/keel-local.tar.gz` | Sandbox revive script; stale source tarball | Remove | **Done** |
| P1 | Root `AGENTS.md` | The platform's agent contract (Linux sandbox, `/workspace`, Grok banner rules) — wrong for contributors | **Do not edit (orchestrator rule).** Replace with a contributor-focused `AGENTS.md`: setup, `npm run test:keel`/`typecheck`, file ownership, honesty rules (no fabricated vendor numbers, never touch blind evals), hypothesis TS/Python parity, "no network on the decision path" | **Done** (oss-cleanup): contributor guide — layout, commands, tests, honesty rules, no-secrets rule |
| P2 | `scripts/grok-pwa-plugin.mjs`, `grok-pwa-shared.mjs`, `grok-pwa-shared.d.mts`, `grok-pwa-plugin.test.mjs`, `scripts/install-page.html`, `server/middleware/grok-pwa.ts`, `server/virtual-grok-og-identity.d.ts`, `public/__grok/**`; `grokPwaPlugin()` and `nitro({ serverDir })` in `vite.config.ts`; the two `/__grok/` links in `__root.tsx` | Injects `https://grok.com/.../extensions.js` ("Created with Grok" pill), PWA manifest, OG tags from `og.grok.me` into every page | Remove. Keel branding (`<title>Keel`, `public/favicon.svg`, `public/og.jpg`) is app-owned and does not depend on it; add a plain `<meta property="og:image" content="/og.jpg">` in `__root.tsx` instead | **Done** (oss-cleanup): files, plugin and links removed; `og:title`/`og:image` meta added; nitro `serverDir` dropped |
| P3 | `src/components/preview-host-bridge.tsx`, `src/lib/preview-host-bridge.ts`, `src/lib/preview-embedder-origin.ts` | postMessage bridge for the Grok preview iframe | Remove (and its `<PreviewHostBridge />` in `__root.tsx`) | **Done** |
| P4 | `.grok/references/**`, `.grok/skills/**` (88 files) | Platform agent docs/skills | Remove together with P5 (`brand-check` tests read `.grok/skills/og/SKILL.md`) | **Done** |
| P5 | `scripts/brand-check*.mjs`, `browser-smoke*.mjs`, `browser-guard.mjs`, `preview.mjs`, `preview.test.mjs`, `preview-thumbnail.mjs`, `write-atomic*.mjs`, `sign-out-plan*.mjs`, `check-auth-invariant*.mjs`; `package.json` scripts `test`, `check:auth`, `preview:restart`, `preview:stop` | Platform QA tooling | Remove; make `npm test` = `npm run test:keel` (+ Python parity) | **Done**: `npm test` = `migration-plan.test.mjs` + `test:keel` |
| P6 | `src/lib/auth/**`, `src/lib/app-data/**`, `migrations/auth/`, `AuthProvider` in `__root.tsx`; deps `better-auth`, `jose` | Platform sign-in (disabled: `VITE_AUTH_ENABLED=false`) and connector data | Remove | **Done**: also removed `src/lib/env.server.ts`, `src/lib/multiplayer/`, `src/lib/og/`, `kysely`, and `getPglite()` in `db.ts` |
| P7 | `scripts/with-app-env.mjs`, `with-app-env.test.mjs`, `app-env-plugin.mjs`, `.grok/app-env.json` | Env wrapper for platform flags | Remove; `dev` becomes `vite dev --host 127.0.0.1 --port 8080` | **Done**: `dev` = `vite dev` (host/port in `vite.config.ts`); `build` = `vite build` (no `db:migrate`) |
| P8 | `src/lib/db.ts`, `migrate.mjs`, `migration-plan*.mjs`, `migrations/0002_keel_switch.sql`; deps `@electric-sql/pglite`, `pg`, `kysely`, `@types/pg` | Database for one boolean (the Keel switch) | Keep for 3.0.0 (works locally with PGlite). Later: store the switch in a small JSON file and drop the DB stack | Keep |
| P9 | `nitro` preset `"vercel"` in `vite.config.ts`; `.vercel/` | Vercel deploy target | Switch to `node-server` so `npm run build && node .output/server/index.mjs` runs anywhere | **Done**: `node-server` preset (PGlite traced, not bundled); `npm start` runs `scripts/start.mjs` on `127.0.0.1:8080` |
| P10 | `vite.config.ts` `server.host: "0.0.0.0"` | Sandbox preview contract | Bind `127.0.0.1` by default (security H2 in the audit) | **Done**: dev, preview and `npm start` bind `127.0.0.1`; opt-in `KEEL_HOST`. `src/start.ts` returns 403 for server-function calls (incl. `getCopilotSetup`) whose `Host` is not loopback (also blocks DNS rebinding). Random per-install secret in `~/.keel/secret` (mode 0600, `KEEL_SECRET` overrides) also done |
| P11 | Unused UI dependencies (most `@radix-ui/*`, `cmdk`, `vaul`, `recharts`, `react-day-picker`, `react-hook-form`, …; there is no `src/components/ui/`) | Template leftovers | Run `npx depcheck`, remove what is unused | **Done**: 44 unused packages uninstalled (depcheck); `@types/react-dom`, `tailwindcss` kept |
| P12 | `.github/agents/keel.agent.md`, `.github/copilot-instructions.md` | Dogfooding agent files with the literal default bearer (audit H1) | Regenerate with a `<KEEL_TOKEN>` placeholder or untrack + gitignore | Pending — owner of `write-agent-files.ts` |
| P13 | `KEEL_PLAN.md`, `artifacts/parity/CONTRACT.md` | Internal build plans | Keep `KEEL_PLAN.md` as design history (or move to `docs/history/`); drop or sanitize `CONTRACT.md` (local path) | Pending |
| P14 | `.tanstack/`, `screenshots/`, `.vercel/` | Local caches | Already gitignored | Done |

## 2. Launch plan (ordered)

1. **Final numbers refresh.**
   - [ ] Keel-3 promotion decided (`models/keel-3` exists, or ship Keel-2 and say so).
   - [ ] Re-run `scripts/keel-parity-bench.ts`, `npm run keel:bench`, public and token benches on
         the promoted model; docs-writer refreshes `README.md`, `docs/benchmarks`,
         `docs/model-card.md`; fill every `TBD` in `hf/README.md`; update `CHANGELOG.md`.
   - [ ] Every competitor number is either measured by a script here or marked vendor-reported
         with a URL. No blind/held-out case edited.
   - [ ] `scripts/fetch-model.mjs` learns `--model keel-3` (HF revision + SHA-256, release-asset
         fallback) and `neural.server.ts` looks in `models/keel-3` first (audit, "Size").
2. **Audit pass.**
   - [ ] Fix or accept every open item in `artifacts/parity/oss-audit.md` (H1, H2, M3, M4, M5).
   - [ ] Ask data-1 to change the AWS-shaped fixture in `eval-blind.ts` to an `…EXAMPLE` value
         (GitHub push protection).
   - [ ] `node scripts/oss-audit.mjs --history --fail-on medium` exits 0 on the tree to be published.
   - [ ] Platform cleanup batches approved in section 1 are done; `npm ci && npm run typecheck &&
         npm run test:keel && npm run build` pass on a clean clone; the served HTML has no third-party script.
   - [x] License review: `docs/licenses.md` lists base weights (MIT) and every training dataset;
         decided 2026-11-02 ("Licence decisions"): CC BY-SA train groups kept, attributed, not
         redistributed; weights Apache-2.0. The xtremedistil "all-33" base (ANLI in its mix) is
         MIT per its card, cited, lineage disclosed.
3. **History decision.** Recommended: publish a single squashed root commit (orphan branch) to a
   new public repo; keep the private history private. Alternative: `git filter-repo`
   (see audit). Re-run the audit with `--history` on whatever will be pushed.
4. **Repo create.** Public repo `sivamatic/Keel` (replace `OWNER` in `package.json`, `CITATION.cff`,
   `CHANGELOG.md`, `.github/ISSUE_TEMPLATE/config.yml`, `hf/README.md`). Settings: enable private
   vulnerability reporting, Discussions, Dependabot alerts + security updates, secret scanning +
   push protection; branch protection on `main` requiring the three CI jobs; squash merges only.
5. **Topics.** `decision-model`, `local-first`, `onnx`, `onnxruntime`, `cross-encoder`,
   `zero-shot-classification`, `nli`, `mcp`, `mcp-server`, `model-context-protocol`,
   `github-copilot`, `coding-agents`, `ai-agents`, `llm-tools`, `guardrails`, `typescript`.
   Description: "Open-weight local decision model for coding agents — choice/score/yes-no in ~10 ms on CPU, System One-compatible API and MCP server."
6. **Social preview image.** 1280×640 PNG (< 1 MB): Keel wordmark, one-line pitch, one honest
   headline number from `docs/benchmarks`. Start from `public/og.jpg`. Upload in Settings → Social preview.
7. **Release v3.0.0 with assets.**
   - [ ] Bump `package.json` to `3.0.0`, finalize `CHANGELOG.md`, add `date-released` to `CITATION.cff`.
   - [ ] Tag `v3.0.0`; release notes from `docs/release-notes.md` + bench table.
   - [ ] Assets: `keel-3-onnx-int8.zip` (contents of `models/keel-3`), `SHA256SUMS`, optional
         `parity-raw-results.zip` (the gitignored per-candidate JSON).
   - [ ] The tag push publishes `ghcr.io/sivamatic/keel` and `ghcr.io/sivamatic/keel-pro-sidecar`
         (`.github/workflows/containers.yml`, with SBOM and provenance). Make both packages public, then run
         `docs/deployment.md` sections 2 and 3 against the published images and tick its "What we tested" table.
8. **Hugging Face upload.** Follow `hf/FILES.md`, then run `hf/upload.ps1` by hand (commented out
   on purpose). Tag the HF revision `v3.0.0` and pin that revision in `fetch-model.mjs`.
   Verify `npm run model:fetch` on a clean clone.
9. **Launch posts.** Drafts are kept outside the repo (HN, Reddit, X, LinkedIn); facts come from `docs/press.md`. Fill
   numbers from step 1 only. Post HN on a weekday morning US Pacific; be in the thread for 3 hours.
10. **"awesome-*" lists** (check each list is active and read its CONTRIBUTING first):
    - `punkpeye/awesome-mcp-servers` (and the glama.ai directory it feeds)
    - `wong2/awesome-mcp-servers`, `appcypher/awesome-mcp-servers`
    - `github/awesome-copilot` (submit the Keel agent file as an agent/instructions example)
    - `e2b-dev/awesome-ai-agents`
    - `janhq/awesome-local-ai`
    - `EthicalML/awesome-production-machine-learning`
11. **MCP registry listing.**
    - Official MCP Registry (`registry.modelcontextprotocol.io`) via `mcp-publisher` with a
      `server.json` (name `io.github.sivamatic/keel`, stdio transport, package `keel-decider`,
      bin `keel-mcp`, env `KEEL_URL`, `KEEL_TOKEN`). npm-based entries need the package on npm
      with a matching `mcpName` field — so this step requires removing `"private": true`
      (or publishing a small separate `keel-mcp` package that depends only on
      `@modelcontextprotocol/sdk` and `zod`, which is preferable given this package's
      app dependencies). Verify `npm view keel-decider` on the public registry first.
    - Also list on Smithery, mcp.so and PulseMCP once the registry entry is live.
12. **After launch.** Watch issues for model-quality reports (template `model_quality.yml`);
    triage safety misses first. Open a `v3.0.1` milestone.

## 3. Keel-Pro (Qwen3.5 LoRA) release

Keel-Pro is the optional GPU sidecar behind the `decider-pro-1.0.0` pin. Its weights are a LoRA on
an Apache-2.0 Qwen3.5 base. Results, data and serving: `artifacts/parity/pro/` (`MODEL_CARD.md`,
`di-results.md`, `train-notes.md`, `DATA.md`, `SERVE.md`, `status.json`). Upload kit: `hf/keel-pro/`.
Nothing here has been pushed, created, uploaded or published.

Blockers (all must be resolved by the maintainer before anything is public):

- [x] **Git history.** Squashed to a single root commit on 2026-11-02 (old history backed up outside the repo; audit H1/P12).
      Publish a single squashed root commit (section 2, step 3); run
      `node scripts/oss-audit.mjs --history --fail-on medium` on the squashed tree.
- [x] **Training-data licenses.** Decided 2026-11-02 (`docs/licenses.md`, "Licence decisions"):
      CC BY-SA sources are kept, attributed and never redistributed; NC data (ANLI, RACE) was
      never trained on; the `jev-phishing-bench` prompts are kept with attribution under its
      README's MIT statement. The adapter is Apache-2.0.
- [ ] **Base license.** Confirm the exact Qwen3.5 base (repo id + revision in `MODEL_CARD.md`) is
      Apache-2.0 and keep its notice (`hf/keel-pro/NOTICE`).
- [ ] **npm.** Decide the package name and whether to drop `"private": true` (section 2, step 11).
      Keel-Pro itself needs no npm package; the sidecar is Python (`serve/keel_pro_server.py`).

Release steps:

1. [ ] Numbers in `MODEL_CARD.md`, `docs/benchmarks*`, `README.md` match `di-results.md`
       (dev and the single report-sample run). Vendor numbers (Jev, MSD1, StartLux) are cited
       with URLs and marked vendor-reported or estimated.
2. [ ] `npm run typecheck; npm test; python training/keel/test_hypothesis.py;
       node scripts/oss-audit.mjs --fail-on medium` pass; MCP smoke passes.
3. [ ] GGUF fidelity (`scripts/di/gguf_check.py`) agreement recorded in `MODEL_CARD.md`.
4. [x] Follow `hf/keel-pro/FILES.md`, then run `hf/keel-pro/upload.ps1`. Done 2026-11-15: `neerumsr/keel-pro` and
       `neerumsr/keel-pro-GGUF` uploaded **private**, tagged `v1.0.0`; Quick start tested from the Hub download.
       At launch: flip both repos to public.
5. [ ] Release notes entry and launch-post line for Keel-Pro (honest: dev-sample index with CI).

### Decision Index board submission

Rules are in the DI kit README, "Submitting a model to the leaderboard"
([apolinario/decision-index](https://github.com/apolinario/decision-index)).

1. [x] **Latency gate.** The maintainers measure on one RTX PRO 6000; median, mean **and** p80 must each be
       ≤ 1,000 ms per request. Before: median 329 ms, mean 2,082 ms, p80 2,232 ms. After shared-prefix scoring
       (`hybrid_engine.py prefix_share=1`): median 316 ms, mean 844 ms, p80 847 ms (report sample, RTX 5090).
2. [ ] **Full public 0.3 run** (not our samples) with the kit (`pipeline` or `hf-job --flavor rtx-pro-6000`),
       `scores.json` with `"complete": true`, uploaded to a Hub dataset `neerumsr/decision-index-results`.
       Status: **done except HLE** (2026-11-13): 139,677/139,677 answered, public index **62.73**, latency
       median 245 / p80 438 / mean 528 ms (RTX 5090); see `artifacts/parity/pro/di-results.md`. The local
       suite was rebuilt without HLE (gated; needs an HF account with access), so it runs with `--no-verify`. After HLE
       access: rebuild with HLE, re-import, then resume the same run directory so only HLE's 513 requests run.
3. [ ] **Weights and code on the Hub.** The adapter (and GGUF) public, or access granted to the maintainers, plus the
       inference code (`scripts/di/hybrid_engine.py` + letters read-out, or the `/v1/systemone` sidecar) and exact settings.
4. [ ] **Pull request** to `apolinario/decision-index` adding a line to `submissions/README.md`: model name, Hub
       model repo, results dataset link, engine/commit, hardware, inference settings, declared capacity limits
       (HLE gated: unanswered; requests over the context cap: unsupported).
5. [ ] Expect the maintainers to run the private Full-score parts (60% same-skill, 40% new-domain) themselves.
