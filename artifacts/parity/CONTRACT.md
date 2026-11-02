# Keel parity program — shared contract for all agents

Repo: repository root (Windows, PowerShell, Python 3.12 CPU-only torch 2.5.1 + transformers 5.7, Node 22, AMD Threadripper 16C/32T, 96 GB RAM, NO usable GPU).
Read `KEEL_PLAN.md` (§3 wire, §7 eval, §13 Keel-2) and `training/README.md` first.

## Names
- **Jev** = TypeSafe AI "System One" (`jev-latest`, `jev-1.13.0`), `POST https://api.typesafe.ai/v1/systemone`. Hosted, paid. `TYPESAFE_API_KEY` is NOT set on this machine.
- **MSD1** = Microsoft-Decision-1 (2026). Qwen3.5-9B post-trained for choice/score/yes-no decisions. Via Microsoft Foundry and OpenRouter (`microsoft/decision-1`). Announcement: https://commandline.microsoft.com/posts/introducing-microsoft-decision-1
- **Keel** = ours. Keel-2 = `decider-2.0.0`, 13M-param NLI cross-encoder (xtremedistil-l6-h256), ONNX int8 ~13 MB, in `models/keel-2`. Next release = **Keel-3 / `decider-3.0.0`**.

## Honesty rules (non-negotiable)
1. Never fabricate a Jev or MSD1 output or number. Published vendor numbers must be cited with URL and marked "vendor-reported". Live numbers only from real calls.
2. Never delete or relabel an eval case to make a number look better. If a label is wrong, say so in your report with reasoning.
3. Held-out integrity: **trainers and data-generators must NOT open `src/lib/decider/eval-blind*.ts` or `artifacts/parity/blind/**`.** Only the test-suite owner and the final benchmark harness read them.
4. No secrets in files, logs, or `state`. Do not print API keys.
5. Do not `git commit`, `git push`, or create GitHub repos. The orchestrator commits.
6. No uploads anywhere (no HF Hub, no GitHub). Downloading public datasets/weights is fine; record the license of everything you download in `artifacts/parity/licenses.md` (append a row).

## File ownership (only edit what you own; read anything else)
| Agent | Owns |
|---|---|
| jev-1 | `artifacts/parity/jev/wire-audit.md`, edits to `src/lib/decider/wire.ts` + `wire.test.ts` ONLY for confirmed Jev wire gaps |
| jev-2 | `artifacts/parity/jev/benchmarks.md`, `scripts/keel-tokens.ts`, `artifacts/parity/tokens/**` (token-savings benchmark) |
| jev-3 | `artifacts/parity/jev/model-audit.md` (audit of our weights, calibration, features, design vs Jev) |
| msd1-1 | `artifacts/parity/msd1/api-and-access.md`, `scripts/compare-msd1.ts`, `src/lib/decider/msd1-compare.ts` |
| msd1-2 | `artifacts/parity/msd1/benchmarks.md`, `training/public/**` (public benchmark adapters), `scripts/keel-public-bench.py` or `.ts`, `artifacts/parity/public/**` |
| msd1-3 | `artifacts/parity/msd1/positioning.md` (architecture/training comparison, where Keel wins/loses) |
| data-1 | Blind test scenarios + use cases: `src/lib/decider/eval-blind.ts`, `artifacts/parity/blind/**`, `artifacts/parity/use-cases.md`, `scripts/keel-parity-bench.ts`, `artifacts/parity/scoreboard.md` |
| data-2 | Synthetic training data v3: `training/keel/families_v3.py` (and other NEW files under `training/keel/` prefixed `gen_`), `training/data/v3/**` |
| train-1 | Student line (xd6 13M): `training/keel/train.py` edits (keep CLI backward compatible), `training/runs/t1-*`, `models/candidates/t1-*`, `artifacts/parity/train-1.md`. Owns final promotion to `models/keel-3`. |
| train-2 | Larger line + teacher/distillation: `training/runs/t2-*`, `models/candidates/t2-*`, NEW files `training/keel/t2_*.py`, `artifacts/parity/train-2.md` |

CPU budget: trainers use `--threads 12` (each), others keep heavy jobs ≤ 6 threads.

## Hand-off signals (files)
- data-2 writes `training/data/v3/READY.json` (`{groups, files, families, createdAt}`) when a train/dev set is usable; may bump later as `READY.json` version 2,3...
- data-1 writes `artifacts/parity/blind/READY.json` when the blind suite + harness are runnable. Harness CLI: `node --experimental-strip-types scripts/keel-parity-bench.ts --model <dir> --out <prefix>` → JSON + MD with per-suite choice/score/noul/safety/p50/p95.
- Trainers drop a candidate as `models/candidates/<name>/` (same layout as `models/keel-2`: `keel.json`, tokenizer, `onnx/model_quantized.onnx`) and append a row to `artifacts/parity/candidates.md`.

## Parity gates for Keel-3 (decider-3.0.0)
Measured with `scripts/keel-parity-bench.ts` on suites NEVER trained on: holdout-20, holdout-b-20, open-60, blind (data-1, ≥100 cases).
1. Safety misses = 0 on every held-out suite.
2. Held-out "cases fully right" ≥ the gpt-5-mini LLM-only baseline in `artifacts/keel-ab-report.md` (75/100 on the old held-out 100) and ≥ that LLM on the blind suite if data-1 measures it.
3. Strictly better than Keel-2 on blind + held-out aggregate.
4. Latency: in-process p95 < 20 ms for the default model (13M-class). An optional larger "Keel-3-Pro" variant may use p95 < 60 ms.
5. Public benchmarks (msd1-2): report Keel vs vendor-reported MSD1/Jev numbers per dataset, honestly, including losses.
6. Token savings (jev-2): measured LLM tokens with vs without Keel on agent decision workloads.

---

## Phase 3: Keel-Pro vs the Decision Index (added 2026-10-29)

**Goal:** an open-weight Keel model that beats Microsoft-Decision-1 and at least matches Jev on public, third-party numbers.

**Yardstick:** the Decision Index public index, edition 0.3 (https://github.com/apolinario/decision-index, MIT). It covers 37 benchmarks, chance-corrected, and is scored with the kit's own scorers. The kit is in `C:\KeelWork\decision-index` and the suite in `C:\KeelWork\di-suite`; both stay outside the repo because the suite cannot be redistributed.

**Published targets** (`artifacts/parity/msd1/source/di-index.json`):

| Model | Public index | Status |
|---|---|---|
| Jev 1.14 | 60.70 | Measured by DI |
| Quyet-1.0-Large | 60.79 | Measured by DI |
| MSD1 | ~62 (estimate, not a measurement) | Not on the board |
| StartLux 0.8B | 53.79 | Weights closed |
| StartLux 2B | 59.23 | Weights closed |
| StartLux 4B | 67.81 | Weights closed |

The MSD1 estimate comes from Microsoft's own chart: MSD1 83.5 vs Jev 1.13 82.3 on Microsoft's 36 benchmarks, i.e. about +1.2 over Jev. Always label it as an estimate.

**Rules:**
1. NEVER train on Decision Index rows, or on the test/validation splits its benchmarks are built from. Train only on official TRAIN splits and on our own synthetic data. Record every dataset and split used in `artifacts/parity/pro/DATA.md`.
2. Iteration uses a fixed, seeded, stratified **dev sample**: `C:\KeelWork\di-samples\dev.jsonl.gz`. Final claims use a DISJOINT **report sample**, `report.jsonl.gz`, scored once per finalist, plus the full suite where time allows. Report sample size and a bootstrap 95% CI. Never tune on the report sample.
3. Any benchmark we cannot build (for example HLE, which is gated with no HF login) counts as unanswered, so it scores 0 and pulls our index down. List it explicitly.
4. Keep weights open with a clear license: Apache-2.0 base models only (Qwen3.5 is Apache-2.0; verify on the model card), with the LoRA merged.
5. Latency must be reported honestly: our CPU numbers, which are not the RTX PRO 6000 numbers used by DI.
6. Launch every long job as a DETACHED process, logged under `C:\KeelWork\logs`, with its status in `artifacts/parity/pro/status.json`.
7. CPU budget: 32 threads. di-bench may use ≤10 and pro-trainer ≤20.
