# Keel-Pro handoff: resume on a GPU machine

Paused 2026-10-29 22:45 PT on the original CPU-only machine (Quadro P620 2 GB) because each training
iteration was going to take hours. All jobs were stopped cleanly. Nothing was pushed or published.

## Goal (from the user)

- Beat Microsoft-Decision-1 (MSD1) and reach at least parity with Jev 1.14 on the public **Decision Index** (DI)
  board. "Don't stop until we make ourselves better. At least 3 iterations."
- Keel stays Apache-2.0 open weights. Prepare for open source, but **never push or publish** without the user's
  explicit go-ahead.

## Targets (DI `public_skill`, edition 0.4 board, public 0.3 suite)

| Model | Score | Source |
|---|---|---|
| Jev 1.14 | **60.70** | published on the DI board (`artifacts/parity/msd1/source/di-index.json`) |
| MSD1 | **~62 (estimate)** | not on DI. Microsoft's chart puts it 1.2 points above Jev 1.13; that delta is applied to Jev 1.14 |
| StartLux on Qwen3.5 0.8B / 2B / 4B / 9B | 53.8 / 59.2 / 67.8 / 70.0 | DI board (closed weights). Shows the bases can get there |
| elephant-1 9B (open) | 72.2 | DI board |
| Encoder models (ModernBERT etc.) | 6–9 | DI board. This is why the 13M Keel-Lite cannot compete here |

Also checked: MSD1 on JevBench (run by TypeSafe, Jev's vendor) scores intelligence 67.1, calibration 92.5 and
composite 77.0. It is unranked, and the scale is not comparable to DI (see `artifacts/parity/msd1/benchmarks.md`).

## State at pause

| Item | State |
|---|---|
| Keel-3 / Keel-Lite (decider-3.0.0) | Shipped and committed (`97befa3`). Docs, security, OSS prep done |
| DI kit | `apolinario/decision-index` @ `25c6ec7`, venv, local patch `scripts/di/di-kit-local.patch` |
| DI suite rebuild | **Partial**: about 1.3 GB downloaded into `di-work` and stopped mid-download. Rerun from scratch on the new machine (it resumes from whatever is present) |
| Samples dev/report | Not built yet |
| Eval service | Spec written (`EVAL.md`); `eval_model.ps1` not written; engine `scripts/di/hybrid_engine.py` drafted |
| Base weights | Qwen3.5 0.8B/2B/4B downloaded (15 GB). Re-download with `scripts/di/download_bases.py` |
| Keel-Pro training | Not started. Only `training/pro/common.py` and `bench_throughput.py` exist |
| Baselines (Keel-Lite, stock Qwen) on DI | Not measured |

The binding rules are in `artifacts/parity/CONTRACT.md`, section "Phase 3". Key points:

- No DI rows, and no test or validation splits of DI's source datasets, in training.
- Use fixed, disjoint dev and report samples, and score the report sample only once.
- HLE counts as 0 unless it is built with an HF login.
- Never fabricate numbers.

## Recommended machine

- **Minimum:** 1× 24 GB GPU (RTX 4090 / L4 / A10). This allows LoRA on the 2B and 4B, and eval of the 4B in minutes.
- **Better:** 1× A100/H100 80 GB. Gives full-sequence LoRA on the 4B (or the 9B) and fast DI evals.
- **Software:** Linux or Windows with CUDA 12.x, Python 3.12, Node 20+, git.
- **Disk:** about 60 GB free (suite 17 GB, models 15–30 GB, checkpoints).
- **Optional:** `HF_TOKEN` with the HLE terms accepted, so HLE can be built instead of counted as 0.

## Setup on the new machine

```bash
# 1. Code. Either unbundle, or clone the private repo if you choose to push to it.
git clone Keel.bundle Keel && cd Keel          # or: git clone https://github.com/neerumsr/Keel.git
npm install && npm run typecheck && npm run test:keel   # expect 43/43
npm run -s keel:token                            # new machine = new per-install secret = new bearer

# 2. Work dir (KEELWORK can be anywhere; the Windows scripts assume C:\KeelWork)
export KEELWORK=$HOME/KeelWork; mkdir -p $KEELWORK/{logs,di-samples,pro,tools}
git clone https://github.com/apolinario/decision-index $KEELWORK/decision-index
cd $KEELWORK/decision-index && git checkout 25c6ec7 && git apply <Keel>/scripts/di/di-kit-local.patch
python -m venv .venv && . .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -e ".[transformers,rebuild]" peft accelerate

# 3. Suite (several hours of download; can run while training data is prepared)
HF_HUB_DISABLE_XET=1 DI_SKIP_BENCHMARKS=45 DI_ALLOW_PARTIAL=1 \
  python -m decision_index suite rebuild --work $KEELWORK/di-work > $KEELWORK/logs/di-rebuild.log 2>&1
python -m decision_index suite import ...         # see the kit README
# If HF_TOKEN has the HLE terms accepted, drop DI_SKIP_BENCHMARKS=45.

# 4. Bases
python <Keel>/scripts/di/download_bases.py         # edit local_dir to $KEELWORK/models
```

On Windows, `scripts/di/di_rebuild.ps1` is the detached wrapper. Fix the paths in it if the new machine's layout differs.

## Plan to resume (in order)

1. **di-bench:**
   - Finish the suite and build seeded, disjoint `dev` samples (~40 rows per benchmark) and `report` samples (~80 rows per benchmark).
   - Write `scripts/di/score_sample.py` (kit scorers plus bootstrap CI) and the eval tool described in `EVAL.md`. It is now GPU, so drop the 10-thread cap.
   - Baselines on dev: Keel-Lite via `--engine http` against `npm run dev`, with `model=decider-3.0.0` and the bearer. Stock Qwen3.5 0.8B/2B/4B via the transformers engine. Use `scripts/di/hybrid_engine.py` if the kit's batched engine crashes on Qwen3.5's hybrid attention.
2. **pro-trainer:**
   - Training data: TRAIN splits only (`training/data/public`, `training/public/registry.py`, plus synthetic v9) converted to DI request format. Log every source, split and license in `artifacts/parity/pro/DATA.md`.
   - LoRA on Qwen3.5-4B, with the 2B as the fast ablation: option-token loss and single-forward option scoring, matching the kit's prompt.
   - At least 3 iterations, changing one lever per iteration. Notebook in `artifacts/parity/pro/train-notes.md`.
   - Stop when dev ≥ 62 with the CI lower bound above 60.7, or after 2 iterations with no gain.
3. **Finalist:**
   - Score once on report.
   - Export GGUF (Q8_0, Q4_K_M) and measure CPU and GPU latency. DI requires median, mean and p80 each ≤ 1 s per request on an RTX PRO 6000.
   - Write `MODEL_CARD.md` and `SERVE.md`, and the sidecar `serve/keel_pro_server.py` (port 8090).
4. **Orchestrator:**
   - Proxy model `decider-pro-1.0.0` from `/api/v1/systemone` and MCP to the sidecar. Keel-Lite stays the default.
   - Update the docs (comparison, benchmarks, model card, README) with DI tables and CIs, then rebuild the HTML (`node docs/build-html.mjs --apply-numbers && node docs/build-html.mjs`).
   - Rerun `npm test`, `node scripts/oss-audit.mjs --fail-on medium` and the MCP smoke test.
   - Commit locally. **Do not push.**

## Prompt to paste into Copilot CLI on the new machine

> Resume the Keel-Pro Decision Index program. Read `artifacts/parity/pro/HANDOFF.md`,
> `artifacts/parity/CONTRACT.md` (Phase 3) and `AGENTS.md` first. This machine has a GPU: confirm it with
> `nvidia-smi`, then follow "Setup" and "Plan to resume". Spawn a di-bench agent and a pro-trainer agent, and run
> at least 3 training iterations. The goal is to beat MSD1 (~62, estimate) and match or beat Jev 1.14 (60.70) on
> DI. Be honest about numbers. Never push or publish.

## Open user decisions (unchanged)

- License review: CC BY-SA training data; ANLI in the base model's training mix.
- npm package name and the `private` flag.
- Squash the git history before publishing: an old bearer is in the history.
- Jev and MSD1 API keys for a live side-by-side comparison.
- An HF token for HLE.
