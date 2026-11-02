# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). Model ids (`decider-X.Y.Z`) track the
package major version.

## [Unreleased]

### Added
- Press kit (`docs/press.md`) and a social preview card (`docs/media/keel-social-card.png`, shown as the README banner).
- Keel-Pro full public Decision Index 0.3 run: 139,677/139,677 requests answered, public index **62.73**
  (HLE gated, counted 0), latency median 245 / p80 438 / mean 528 ms on an RTX 5090
  (`artifacts/parity/pro/di-results.md`).
- Deployment: `Dockerfile` (Keel server, non-root, health check), `serve/Dockerfile` and pinned
  `serve/requirements.txt` (Keel-Pro sidecar, CUDA 12.8), `compose.yaml`, `compose.pro.yaml`,
  `deploy/kubernetes/` (Keel-Lite, and Keel + Keel-Pro in one GPU pod), and `docs/deployment.md` with
  Azure, Google Cloud and AWS recipes.
- CI: container build and decision smoke test on pull requests, GHCR publishing with SBOM and
  provenance on tags, CodeQL, Dependabot.
- `SUPPORT.md`, `GOVERNANCE.md`, `.github/CODEOWNERS`.

## [3.0.0-rc.1] — unreleased

Release candidate for the first public, open-source release. Final numbers are filled in
from `docs/benchmarks` when Keel-3 is promoted; until then the default model is Keel-2.

### Added
- Keel-3 (`decider-3.0.0`) training line and candidate pipeline (`models/candidates/`,
  `artifacts/parity/candidates.md`); promotion target `models/keel-3`. *(pending promotion)*
- MCP server (`mcp/keel-mcp-server.mjs`, `keel-mcp` bin) bridging any MCP client to the
  local HTTP API.
- Microsoft Foundry-style provider route (`/providers/microsoft/v1/systemone`) and
  `api-key` header auth for decision calls.
- Parity benchmark harness (`scripts/keel-parity-bench.ts`), blind held-out suite, public
  benchmark adapters and token-savings benchmark.
- Open-source scaffolding: Apache-2.0 `LICENSE` and `NOTICE`, contributing guide, code of
  conduct, security policy, issue and PR templates, CI, `CITATION.cff`, and a repeatable
  secret/PII/size audit (`scripts/oss-audit.mjs`).

### Changed
- Wire: accepts more Jev-shaped questions; Microsoft-Decision-1 model names resolve to
  Keel's neural model.
- Package renamed to `keel-decider`; Node `>=22.6` required (`--experimental-strip-types`).
- `package-lock.json` resolves from the public npm registry.

### Removed
- Hosting-platform sandbox leftovers: `startup.sh` and the `artifacts/keel-local.tar.gz`
  source snapshot.

## [2.0.0] — 2026-09-24

### Added
- Keel-2 (`decider-2.0.0`): 13M-parameter NLI cross-encoder fine-tuned from
  xtremedistil-l6-h256, int8 ONNX (~13 MB), in-process with ONNX Runtime; temperature
  calibration, abstain threshold and lexical blend in `keel.json`.
- Training pipeline (`training/keel/`), Python/TypeScript hypothesis parity fixtures,
  held-out and open eval suites, on/off and A/B reports.

## [1.2.0]

### Added
- Lexical decider (`decider-1.2.0`), the System One wire (`POST /api/v1/systemone`),
  the on/off switch and Copilot agent files.

[Unreleased]: https://github.com/neerumsr/Keel/compare/v3.0.0-rc.1...HEAD
[3.0.0-rc.1]: https://github.com/neerumsr/Keel/releases/tag/v3.0.0-rc.1
[2.0.0]: https://github.com/neerumsr/Keel/releases/tag/v2.0.0
