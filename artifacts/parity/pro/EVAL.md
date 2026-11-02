# DI eval service (for pro-trainer)

Owner: di-bench. Measures a local Hugging Face model directory (e.g. a merged LoRA), or the Keel HTTP API, on a fixed
Decision Index sample with the DI kit's prompt and scorers, and records the result.

## Usage (kit venv python, GPU)

```powershell
$py = "C:\KeelWork\decision-index\.venv\Scripts\python.exe"
& $py scripts\di\eval_model.py --model-dir <merged HF dir> --sample dev [--name <label>] [--limit N] [--boot 200]
& $py scripts\di\eval_model.py --engine http --base-url http://127.0.0.1:8080/api/v1 --http-model decider-3.0.0 --sample dev --name keel-lite
```

| Argument | Meaning |
|---|---|
| `--model-dir` | Local HF model directory (config.json, weights, tokenizer and chat template). |
| `--sample` | `dev` (iterate on this) or `report` (final numbers only, **do not tune on report**, CONTRACT Phase 3). |
| `--limit` | Only the first N rows (smoke test; the score is then NOT comparable and no di-results.md row is written). |
| `--name` | Label for the run; default = leaf folder name of `--model-dir`. |
| `--resume` | Existing run directory to resume. |

Run one GPU job at a time. On Windows (WDDM) a second process that pushes VRAM past 32 GB spills into system RAM and
both jobs slow down by orders of magnitude (observed: training and a 0.8B eval both stalled).

Samples (built once by `scripts/di/make_samples.py`, seed 20261030; never regenerated in place):

- `C:\KeelWork\di-samples\dev.jsonl.gz`: 1,633 rows, about 40 per scored benchmark (whole case groups)
- `C:\KeelWork\di-samples\report.jsonl.gz`: 3,272 rows, about 80 per benchmark, disjoint from dev
- `C:\KeelWork\di-samples\samples.json`: per-benchmark counts

## Outputs

- Run directory `C:\KeelWork\di-runs\<name>-<sample>-<yyyyMMdd-HHmmss>\`: the kit's `results.jsonl`, `run.log`, the
  kit score files, and `sample-score.json`.
- One JSON line appended to `C:\KeelWork\di-samples\history.jsonl`.
- One row appended to the "Eval service history" table in `artifacts/parity/pro/di-results.md`.

## What the number means

- The engine is the DI kit's `transformers` prompt and scoring (`render_prompt`, system prompt, the model's chat
  template, summed log-probability of each option key, softmax over options, no truncation), computed exactly for
  Qwen3.5 hybrid attention by `scripts/di/hybrid_engine.py`, because the kit's batched engine crashes on Qwen3.5.
- The score is the kit's 0.3 public index computed by the kit's own `score_run_v02` on the sample rows
  (`scripts/di/score_sample.py`), so it is an **estimate** of the full-suite index. The 95% CI is a bootstrap over whole
  case groups, stratified by benchmark.
- HLE (gated; not built) is scored 0, as the board does for a missing benchmark (CONTRACT Phase 3).
- Suite provenance: rebuilt locally with `suite rebuild --edition 0.3`. Per-benchmark request counts equal the
  official manifest for every benchmark except HLE (0 of 513), but the file hashes differ from the frozen suite, so
  rows may differ from the official bytes in content. Treat absolute numbers as estimates, and compare models on the same
  sample.
