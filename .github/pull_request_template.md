## What and why

<!-- One paragraph: what changed and the problem it solves. Link issues with "Fixes #123". -->

## Kind of change

- [ ] Server / wire / MCP bridge
- [ ] Model, training data, calibration or export
- [ ] Benchmarks or eval harness
- [ ] Docs only
- [ ] CI / tooling

## Checks

- [ ] `npm run typecheck` passes
- [ ] `npm run test:keel` passes
- [ ] `python training/keel/test_hypothesis.py` passes (if `hypothesis.ts` or `hypothesis.py` changed)
- [ ] `node scripts/oss-audit.mjs` reports no new findings (no secrets, local paths or private data)
- [ ] I did not edit held-out or blind eval cases to improve a score
- [ ] New datasets or weights are licensed for redistribution and listed in `docs/licenses.md`
- [ ] `CHANGELOG.md` updated under "Unreleased"

## Bench table (required if model, data, calibration, hypothesis or wire behavior changed)

<!--
Paste the summary table from `npm run keel:bench` and, for model changes,
`node --experimental-strip-types scripts/keel-parity-bench.ts --model <dir> --out <prefix>`.
Show before (current main) and after. A PR that adds a safety miss on any held-out suite will not be merged.
-->

| Suite | Model | Cases fully right | Choice acc | Score MAE | Noul acc | Safety misses | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|
| holdout-20 | before |  |  |  |  |  |  |  |
| holdout-20 | after |  |  |  |  |  |  |  |
| holdout-b-20 | before |  |  |  |  |  |  |  |
| holdout-b-20 | after |  |  |  |  |  |  |  |
| open-60 | before |  |  |  |  |  |  |  |
| open-60 | after |  |  |  |  |  |  |  |
| blind | before |  |  |  |  |  |  |  |
| blind | after |  |  |  |  |  |  |  |
