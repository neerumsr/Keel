# Training guide

How to rebuild Keel from scratch, fine-tune it on your own decisions, distil it from a larger teacher, export a mixed-int8 ONNX model, and check it against the release gates.

<!-- diagram:training-pipeline -->

## 1. Environment

The commands below use Python 3.12 and a CPU. A GPU speeds up training but is not required. Keel-2 trained in about an hour on a laptop-class CPU.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch transformers onnx onnxruntime datasets numpy
```

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install torch transformers onnx onnxruntime datasets numpy
```

Fetch the base model, and optionally the training extras. Then export the evaluation fixtures, which are used for decontamination and reporting:

```bash
npm run model:fetch                # models/keel-2 (runtime)
npm run model:fetch -- --train     # adds models/base-xd6 (training base)
npm run keel:export-evals          # training/data/evals.json
```

## 2. Data

Every training row is a **group**: one state, one question, and a soft label over its options.

```json
{"state": "rm -rf ./build && npm run build", "question": {"type": "choice", "instructions": "Should the agent run this?", "criteria": {"run": "...", "confirm": "...", "block": "..."}}, "label": [0.85, 0.15, 0.0], "family": "gate"}
```

| Data set | Path | Size | Notes |
|---|---|---|---|
| v1 / v2 | `training/data/train.jsonl` | About 33k groups | Keel-2's data: templated families plus about 6k MNLI pairs |
| v3 | `training/data/v3/train.jsonl` | 117,925 groups, 60 families | Adds sentiment, PII, intent, moderation, injected text and "none of the above" |
| v5 to v7 core | `training/data/v3/v7/core.jsonl` | 80k groups, family-balanced | Safety families weighted ×2, plus `gate_menu` and gate yes/no variants |
| Public | `training/data/public/*.jsonl` | About 12k groups | Only datasets whose licenses allow training. 200 per dataset are held back for calibration. |
| Teacher labels | `training/data/v3/teacher_t2dxs_v7core.jsonl` | 35,354 groups | Keel-3-Pro margins for distillation |

Build the classic data set:

```bash
npm run model:data   # = python training/keel/build_data.py --n 40000 --seed 7 --nli 6000
```

`build_data.py` drops any generated state that shares a 6-gram with a held-out or blind evaluation state. Keep this decontamination step when you add families. Without it, your benchmark numbers mean nothing.

### Adding your own decisions

The quickest win is a family of your own: a few hundred groups of real or templated states with the question you actually ask. Mix it in with `--extra-train mine.jsonl@3`, where `@3` repeats it three times, and keep v2 replay so general skills do not regress. Hold back 10–20% of your states as a dev set, and never calibrate on your test set.

## 3. Train the student

The base recipe for Keel-2:

```bash
python training/keel/train.py --base models/base-xd6 --out training/runs/xd6 --epochs 3
```

The round-1 recipe that produced `t1-r2`, the base of the Keel-3 line. It warm-starts from the previous best checkpoint, mixes the v5 core with a 20% v2 replay, and adds ordinal, smoothing, shuffling and EMA:

```bash
python training/keel/train.py --base training/runs/t1-r1/best --out training/runs/t1-r2 \
  --train training/data/v3/v5/core.jsonl --dev training/data/v3/v5/dev.jsonl \
  --extra-train training/data/train.jsonl@0.2 \
  --lr 3e-5 --schedule cosine --warmup 0.05 --pairs-per-batch 64 --max-len 256 \
  --ordinal 0.5 --label-smoothing 0.05 --shuffle-options 0.5 --hard-neg 0.2 \
  --pointwise-noul 0.1 --ema 0.998 --bucket 50
```

That run took <!-- num:k3.train.steps -->2,723 steps in 49.7 CPU minutes<!-- /num --> and reached a dev loss of 0.983.

| Flag | What it does | `t1-r2` |
|---|---|---|
| `--extra-train a.jsonl b.jsonl@k` | Mix extra files; `@k` repeats (k ≥ 1) or subsamples (k < 1) | v2 at 0.2 |
| `--ordinal W` | EMD plus expected-level loss on score groups | 0.5 |
| `--label-smoothing` | Softens one-hot labels | 0.05 |
| `--shuffle-options p` | Permutes choice options, which protects order invariance | 0.5 |
| `--hard-neg w` | Group weight 1 + w × (1 − p_gold) | 0.2 |
| `--pointwise`, `--pointwise-noul` | Weight of the pointwise binary cross-entropy term | 0.5 / 0.1 |
| `--schedule cosine --warmup f` | LR schedule | cosine, 0.05 |
| `--grad-accum`, `--ema` | Gradient accumulation; EMA weights used for eval and saving | 1, 0.998 |
| `--bucket N` | Length-bucketed batches, which is faster on CPU | 50 |
| `--dev-max` | Cap dev groups per evaluation | n/a |
| `--teacher-labels f --kd w --kd-temp T` | Offline distillation from precomputed teacher margins | Round 2 |
| `--safety-neg w --safety-families re` | Unlikelihood penalty on wrong options in safety families | Round 2 |

**Select checkpoints by dev loss only.** Never select on held-out or blind results. Report those, but do not tune on them.

## 4. Distillation from Keel-3-Pro

Keel-3-Pro is a 70M-parameter DeBERTa-v3-xsmall cross-encoder (<!-- num:pro.size -->108 MB<!-- /num -->). It is more accurate on choice questions but about six times slower. Use it as a teacher:

```bash
# 1. Train the teacher (wall-clock budgeted; freezes embeddings and the first 2 layers)
python training/keel/t2_train.py --base models/teacher-deberta-xsmall --out training/runs/t2-dxs-b3 \
  --train training/data/v3/v7/core.jsonl --max-len 192 --lr 2.5e-5 --freeze-embeddings --freeze-layers 2 --minutes 90

# 2. Precompute soft labels (margins per option, keyed by group)
python training/keel/t2_label.py --teacher training/runs/t2-dxs-b3/best --data training/data/v3/v7/core.jsonl \
  --out training/data/v3/teacher_t2dxs_v7core.jsonl --per-family 300 --max-len 192

# 3. Distil into the small student
python training/keel/train.py --base training/runs/t1-r2/best --out training/runs/t1-r5 \
  --train training/data/v3/v7/core.jsonl --teacher-labels training/data/v3/teacher_t2dxs_v7core.jsonl --kd 0.5 --kd-temp 2 --lr 2.5e-5
```

Groups without a teacher label are trained on gold labels only. Run `--help` on each script for its full flag list.

## 5. Export

```bash
python training/keel/export.py --ckpt training/runs/t1-r2/best --out models/candidates/t1-r2e \
  --id decider-3.0.0-rc.t1-r2e --trained-on "v5 core + v2@0.2" \
  --quant mixed --dev training/data/v3/v5/dev.jsonl
```

- **`--quant mixed`** (the default) applies per-channel int8 everywhere except the FFN output projections and the classifier, which stay fp32. On the xtremedistil base this gave **0/300 argmax flips** against fp32 at 17.7 MB. Plain `dynamic` int8 is smaller (about 13 MB) but flips more answers.
- **`--dev`** fits per-type temperatures and the abstain threshold on dev data only, and records the files in `keel.json` → `calibrationSet`.
- **DeBERTa-v3 warning.** Per-channel and mixed int8 are broken for DeBERTa-v3 in ONNX Runtime 1.20. Export the Pro teacher with `t2_export.py`, which keeps fp32 where needed.

## 6. Bench and promote

```bash
KEEL_MODEL_DIR=models/candidates/t1-r2e npm run dev           # try it in the bench UI
node --experimental-strip-types scripts/keel-parity-bench.ts --model models/candidates/t1-r2e --out artifacts/parity/blind/cand-t1-r2e
npm run keel:tokens                                            # token-savings report
npm run test:keel                                              # wire and engine tests
```

Keel-3 (`t1-r11`) was promoted under the round-2 rule, which a candidate must pass against the current default model:

| Rule | Requirement |
|---|---|
| (a) | No more safety misses than the current model on blind and on all held-out suites |
| (b) | Strictly more cases fully right on blind and on all held-out suites |
| (c) | In-process p95 under 20 ms on an idle CPU, one model per process |

Also run the blind-c confirmation suite and report it even when it regresses, as it did for Keel-3. The stricter contract gates G1 (zero safety misses) and G2 (match the LLM) are not met yet; see [Benchmarks](benchmarks.md#promotion-gates). To promote, export the candidate to `models/keel-3` (as `npm run model:export` does); the server loads `models/keel-3` first. Measure latency with each model in its own process:

```bash
node --experimental-strip-types scripts/keel-latency.ts --model models/keel-3 --model models/keel-2 --calls 200
```

## Tips

- Change `hypothesis.ts` and `hypothesis.py` together, and bump `HYPOTHESIS_VERSION`. A mismatch silently degrades accuracy.
- Keep a replay of general data (v2 or MNLI) in every fine-tune, so that narrow data cannot erase broad skills.
- Re-run calibration whenever the data mix changes. A good model with stale temperatures reports misleading confidence.
- On a shared CPU, `--bucket 50` and `--max-len 192` roughly halve the time per step.
