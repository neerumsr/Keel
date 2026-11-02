# Contributing to Keel

Thanks for helping. Keel is small on purpose: one wire, one local model, honest numbers.

## Ground rules

1. **No network on the decision path.** `local.ts`, `neural.server.ts` and `judge.server.ts` must never call a hosted model.
2. **Never fabricate a competitor number.** Jev and Microsoft-Decision-1 figures are either vendor-reported (with a link) or measured by a script in this repo.
3. **Do not edit held-out or blind eval cases to improve a score.** If a label is wrong, open an issue with your reasoning.
4. **Keep `hypothesis.py` and `hypothesis.ts` byte-identical** in behavior (`python training/keel/test_hypothesis.py`).

## Setup

```powershell
npm install
npm run model:fetch        # only if models/keel-3 is not present
npm run dev                # http://127.0.0.1:8080 (loopback only)
```

The dev server (and `npm start` after `npm run build`) binds `127.0.0.1` because the UI hands the local
bearer to the browser. Set `KEEL_HOST=0.0.0.0` only on a trusted network; even then the UI's server
functions answer only requests addressed to `localhost` / `127.0.0.1`.

## Before you open a pull request

```powershell
npm run test:keel          # wire, judge, eval, compare harness tests
npm run typecheck
npm run keel:bench         # if you touched the model, data, or calibration
```

Paste the bench summary table into the pull request when model behavior changes. A pull request that adds a safety miss on any held-out suite will not be merged.

`serve/requirements.txt` pins the exact versions the Keel-Pro numbers were measured with. A bump there can change
model outputs, so include a before/after DI dev-sample score (`scripts/di/score_sample.py`) in the pull request. If
you change a `Dockerfile`, the Containers workflow builds it and asks the image one question.

## Adding training data

New families go in `training/keel/` and must pass the contamination filter in the data builder (6-gram overlap against held-out and blind states). Only use datasets whose license allows redistribution of derived weights under Apache-2.0, and add a row to `docs/licenses.md`.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
