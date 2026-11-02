# Open-source release audit (oss-prep)

Date: 2026-10-29. Scope: working tree (tracked + untracked-not-ignored files, i.e. what would ship)
and full git history (`git log -p --all`: 2 commits on `main`, no tags, no stashes, one author
identity — a GitHub noreply address). Scanner: `scripts/oss-audit.mjs` (repeatable; exits non-zero
on findings). Raw JSON: `artifacts/parity/oss-audit.json` (gitignored; regenerate with
`node scripts/oss-audit.mjs --history --json artifacts/parity/oss-audit.json`).

Secret values are never printed here or by the scanner: file:line and type only.

## Summary

| Severity | Open (tree) | Open (history only) | Fixed during this audit |
|---|---:|---:|---:|
| High | 4 scanner + 1 manual | 4 (same lines as tree) | 0 |
| Medium | 6 scanner + 1 manual | 75 | 153 + 2 manual |
| Low | 29 (18 are reviewed synthetic fixtures) | 4 | 2 |

Bottom line: **no real third-party credential (API key, cloud key, PAT, private key, password)
was found in the tree or in history.** The high findings are Keel's own *default* local bearer,
which is derived from a constant in public source code. That is a design problem rather than a
leak (see H1/H2). The rest are local paths, an internal package-feed hostname that is now only in
history, and license/hygiene items.

## High

| ID | Location | Type | Status / action |
|---|---|---|---|
| H1 | `.github/agents/keel.agent.md:11`, `:21`; `.github/copilot-instructions.md:7`, `:15` (tree **and** history, commit 98237bc) | Literal Keel bearer = HMAC-SHA256 of the built-in default secret (`src/lib/decider/auth.server.ts`). | **Fixed.** Both files now carry `<KEEL_TOKEN>`; `npm run keel:agents` writes placeholders to the repo (real token only with `--repo-key`) and the real token to `~/.copilot`. The old value remains in git history, so publish from a squashed single commit. |
| H2 | `src/lib/decider/auth.server.ts:4-10`, `src/lib/decider/decide.functions.ts:26-35`, `vite.config.ts` (`server.host: "0.0.0.0"`) | Manual review: weak default auth. The default secret is public; `getCopilotSetup` returns the bearer to any caller without auth; and the dev server listens on all interfaces (confirmed: port 8080 listening on `0.0.0.0`). Anyone on the same network can read the bearer and flip `/api/v1/switch`. | **Fixed.** Random per-install secret in `~/.keel/secret` (mode 0600; `KEEL_SECRET` / `KEEL_SECRET_FILE` override; `npm run keel:token` prints the bearer). Dev, preview and start bind `127.0.0.1` (opt-in `KEEL_HOST`). `src/start.ts` returns 403 for server functions, including `getCopilotSetup`, on non-loopback Host. |

The `copilot-panel` source (`src/components/keel/copilot-panel.tsx`) does **not** contain the
token: it fetches it at runtime from `getCopilotSetup`. No other file embeds it.

## Medium

| ID | Location | Type | Status / action |
|---|---|---|---|
| M1 | `package-lock.json`, 153 `resolved` URLs (tree) | Internal Microsoft package-feed host (Azure Artifacts upstream proxy). Also breaks `npm ci` for anyone outside the corporate network. | **Fixed:** rewritten to `https://registry.npmjs.org/` (same tarballs, same `integrity` hashes; `npm ls` clean). npm's default `replace-registry-host=npmjs` still lets corporate machines use their configured feed. Re-check after every `npm install` on a corporate machine (`node scripts/oss-audit.mjs` catches it). |
| M2 | `package-lock.json`, 72 lines (history only, commit 98237bc) | Same internal feed host. | Open: history decision (below). |
| M3 | `artifacts/keel-2-report.json:4`, `artifacts/cand-xd6-report.json:4`, `artifacts/keel-base-report.json:4` (tree + history); `artifacts/parity/jev/keel2-baseline.json:4`, `artifacts/parity/jev/keel2-fp32.json:4` (tree) | Local user path (absolute model directory, includes the Windows username). | Open. Root cause: the bench scripts write `path.resolve(modelDir)`. Fix the writer to store a repo-relative path (owners of `scripts/keel-bench.ts` / `keel-parity-bench.ts`), then regenerate or hand-edit the `model` field. |
| M4 | `artifacts/parity/CONTRACT.md:3` | Local user path (repo location). | Open. Internal working document of the parity program; recommend not shipping it (or replacing the path with "the repo root"). Orchestrator decision. |
| M5 | Every HTML page served by `npm run dev` / preview / build | Manual review: the Grok platform injector (`scripts/grok-pwa-plugin.mjs`, `server/middleware/grok-pwa.ts`) adds `<script src="https://grok.com/…/extensions.js">` and a manifest under `/__grok/`. A "no network" local product should not load a third-party script. | Open, part of the platform cleanup (RELEASE_CHECKLIST.md, P2). The app's own branding (title "Keel", `public/favicon.svg`, `public/og.jpg`) does **not** depend on the injector; offline the deferred script just fails to load and the UI works. |
| M6 | `training/public/eval/*.jsonl`, `training/data/public/*.jsonl` (untracked) | License: eval subsets include sources that forbid redistribution (AG News non-commercial, dair-ai/emotion research-only, ANLI CC BY-NC 4.0, MRPC/RTE/SST-2 unclear) — see `artifacts/parity/licenses.md`. | **Fixed:** gitignored; rebuild with `training/public/build_eval.py` (keeps `MANIFEST.json` and code in git). |
| M7 | `artifacts/parity/msd1/source/widget1-6.html`, `di-*.json` (untracked) | Copies of a vendor announcement's chart widgets (third-party copyrighted content) and a 3.3 MB cache. | **Fixed:** `artifacts/parity/msd1/source/` gitignored. Docs cite the URLs instead. `di-*.json` (MIT, apolinario/decision-index) can be re-downloaded. |

## Low

| Location | Type | Note |
|---|---|---|
| `src/lib/decider/eval-blind.ts:649` | AWS access-key-id shape | Synthetic safety case. It does **not** use AWS's documented example value, so **GitHub push protection may block the push.** Ask data-1 to switch it to `AKIAIOSFODNN7EXAMPLE` (same shape, recognized as fake) — label-neutral, so it does not change the case. |
| `training/keel/gen_prog.py:317` | PEM private-key header | Synthetic template in a data generator (no key body). Low push-protection risk; trainers may add `oss-audit:allow` on the line. |
| `src/lib/decider/eval-blind-b.ts:88` (bearer), `:96` (connection string), `src/lib/decider/eval-blind-c-2.ts:56` (connection string) | Credential-shaped strings | Synthetic eval states (reserved/invalid hosts). Keep. |
| 13 emails in `src/lib/decider/eval-blind*.ts`, `training/keel/gen_seeds_d.py:156`, `gen_safety2.py:171` | Email address | Phishing/PII scenarios. One uses a public webmail domain; confirm it is invented (owners). |
| `artifacts/*-report.json:4` ×3 (+history), `artifacts/parity/CONTRACT.md:3`, `artifacts/parity/jev/*.json:4` ×2 | Local username | Same lines as M3/M4. |
| `scripts/grok-pwa-plugin.test.mjs:453` (+history) | Private IP | Test fixture of a platform file slated for removal. |
| `artifacts/keel-local.tar.gz` (history; contained platform test fixtures with a private IP and a `.invalid` email) | Archive | **Fixed:** unused source snapshot deleted from the tree. |

## Not found

No AWS/GCP/Azure keys, GitHub/HF/OpenAI/Anthropic/Slack tokens, JWTs, private key bodies, real
connection strings, `.env` files, internal Microsoft hosts other than the package feed (no
SharePoint, corp-domain, Azure DevOps org or Teams links), or personal emails in
committed files. Git identities are a GitHub noreply address. Hosted-service keys
(`TYPESAFE_API_KEY`, OpenRouter, Foundry) are referenced only by environment-variable name.

## Size audit (files over 5 MB)

Tracked: `models/keel-2/onnx/model_quantized.onnx` (12.4 MB) only.

Would have been added before this audit (now gitignored): ~2.1 GB of `training/data/v3/**`
(largest 182 MB), 360 MB of `models/candidates/*` (7 × 17.7 MB t1, 2 × 108 MB t2 ONNX + 8 MB
tokenizers), 380 MB `models/teacher-deberta-base-c`, 42 MB `training/data/public` +
`training/public/eval`, 3.3 MB `artifacts/parity/msd1/source/di-index.json`, and ~6 MB of
per-candidate raw JSON in `artifacts/parity/**`. After the new `.gitignore`, the scanner finds no
file over 5 MB that would ship except the grandfathered Keel-2 ONNX.

Where things ship:

| What | Git | GitHub Release asset | Hugging Face |
|---|---|---|---|
| Code, docs, eval suites, small reports (`*.md`, final JSON) | yes | — | — |
| `models/keel-*/` config, `keel.json`, tokenizer (≤ 1 MB) | yes | — | yes |
| Shipped ONNX (`models/keel-3/onnx/model_quantized.onnx`, 13–18 MB) | **no** | yes (+ `SHA256SUMS`) | yes (canonical) |
| Keel-2 ONNX (12.4 MB) | already in history; keep tracked until v3.0.0, then optionally untrack | yes (v2.0.0) | optional `keel-2` repo |
| Candidates, teachers, PyTorch checkpoints, `training/runs/` | no | no | no (optionally a `keel-3-pro` repo later) |
| Training data v3 (GBs), public-benchmark subsets | no | no | optional HF *dataset* repo for the synthetic data only (our own Apache-2.0 content), after a license review |
| Per-candidate raw bench/margin/token JSON | no (gitignored) | optional zip | no |

**ONNX recommendation: GitHub Release asset + Hugging Face, fetched by `npm run model:fetch`
with a pinned revision and SHA-256 check — not Git LFS.** Reasons: (1) LFS objects are not in
GitHub's "Download ZIP" by default and clones without `git-lfs` get a 130-byte pointer that
ONNX Runtime rejects with an opaque protobuf error; (2) LFS bandwidth/storage quotas are billed
to the repo owner and consumed by every clone, fork and CI run; (3) the weights' canonical home
should be HF anyway (model card, versioning, downloads stats), so a fetch script is needed
regardless; (4) the ONNX is a build artifact versioned by `keel.json` `id`, not source;
(5) it keeps history small when Keel-3.x weights are retrained. Cost: `scripts/fetch-model.mjs`
must learn `--model keel-3` (download from `https://huggingface.co/neerumsr/keel-3/resolve/<rev>/…`,
verify SHA-256, fall back to the release asset) and `neural.server.ts` `modelDir()` must look in
`models/keel-3` first. Until then the app and tests fall back to the tracked Keel-2 / lexical
judge, and `neural.test.ts` skips cleanly when no model is present, so nothing breaks.

## History decision (recommendation; NOT executed)

History contains no real secret. It does contain the default bearer (H1), 72 internal feed URLs
(M2) and 3 local paths (M3). The repo has only 2 commits, and an `origin` remote on GitHub
already exists (visibility unknown). Recommended plan, in order of preference:

1. **Fresh public history (recommended).** After all fixes are in the tree, create the public
   repo from a single squashed root commit: `git checkout --orphan public-main`, `git add -A`,
   commit "Keel 3.0.0", push that branch only to the new public repo. The current private
   history stays in the private repo. Simple, no tooling, nothing old leaks.
2. **Rewrite in place** (if the 2-commit history must be kept): `git filter-repo
   --replace-text <expressions file>` with literal rules for the feed URL prefix, the user path
   prefix and the default bearer (value read from a local file, never committed), then
   `git filter-repo --invert-paths --path artifacts/keel-local.tar.gz`. Requires a fresh
   clone, a force-push, and every collaborator re-cloning. Re-run
   `node scripts/oss-audit.mjs --history` afterwards; it must report no high/medium.

## Repeat the audit

```powershell
node scripts/oss-audit.mjs                     # tree only; exit 1 on any finding
node scripts/oss-audit.mjs --history           # + every added line in history
node scripts/oss-audit.mjs --fail-on medium    # what CI runs (with --history)
```

Reviewed false positives can be suppressed with `oss-audit:allow` on the same line. Synthetic
secrets in `src/lib/decider/eval*.ts`, `training/keel/gen_*.py`, `families*.py` and
`artifacts/parity/blind/` are reported as low, never dropped.

## Notes for other owners

- **MCP bin / shebang:** `package.json` now has `"bin": { "keel-mcp": "mcp/keel-mcp-server.mjs" }`.
  `mcp/keel-mcp-server.mjs` already starts with `#!/usr/bin/env node`, so no edit was made to it.
  (Appended by oss-prep; msd1-3 / msd1-1 own the MCP file.)
- **docs-writer:** `docs/model-card.md` has two paths where `\t` became a tab character
  (`training\keel<TAB>rain.py`). The CI and the PR template reference `docs/benchmarks`; the HF
  card points there too.
- **data-1:** see the AWS-key fixture note above (push protection).
- **Bench script owners:** write repo-relative model paths (M3).
- `npm view keel-decider` could not reach the public registry from this network (the configured
  corporate proxy returned "not found in feed", npms.io search returned 0 results). Treat the
  name as *probably free*; re-check from an unrestricted network before publishing.
