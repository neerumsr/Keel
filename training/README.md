# Keel training guide

Environment setup, data build, CPU and GPU training, teacher distillation, export/calibration, benchmark, promotion, and verification.

## Environment setup

Use Python 3.12. Install the Python stack in a virtual environment that includes PyTorch, Transformers, ONNX Runtime, Datasets, and NumPy.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch transformers onnx onnxruntime datasets numpy
```

For CUDA, install the PyTorch wheel that matches the GPU host and CUDA runtime from the official PyTorch selector, then install the remaining packages.

## Fetch base weights

For serving the zero-shot base:

```powershell
npm run model:fetch
```

For training the xd6 student:

```powershell
npm run model:fetch -- --train
```

## Export eval fixtures

```powershell
npm run keel:export-evals
```

This writes `training\data\evals.json` for Python and hypothesis fixtures under `artifacts\`. The Python and TypeScript hypothesis builders should stay aligned.

## Build data

```powershell
npm run model:data
```

Equivalent command:

```powershell
python training\keel\build_data.py --n 40000 --seed 7 --nli 6000
```

The builder writes `training\data\train.jsonl` and `training\data\dev.jsonl`, drops generated rows with 6-gram overlap against holdout/open states, and can include MNLI replay rows.

## Train on CPU

```powershell
npm run model:train
```

Initial xd6 command:

```powershell
python training\keel	rain.py --base models/base-xd6 --out training/runs/xd6 --epochs 3
```

Final model facts: xd6 trained 1,200 steps on data v1 (30,865 groups), then warm-started for 2 epochs / 3,292 steps at `lr=4e-5` on data v2 (33,224 groups). Data v2 adds compositional stop, ask, and vulnerability generators. Total CPU time was about 60 minutes.

Warm-start command:

```powershell
python training\keel	rain.py --base training/runs/xd6/best --out training/runs/xd6-v2 --epochs 2 --lr 4e-5
```

## Train on a GPU machine

Install a CUDA-enabled PyTorch build, copy or fetch the base weights, and increase throughput with a larger `--pairs-per-batch` if memory allows.

```powershell
python training\keel\train.py --base models/base-xd6 --out training/runs/xd6-gpu --epochs 3 --pairs-per-batch 192
```

Teacher command from the train.py docstring:

```powershell
python training\keel\train.py --base models/keel-base --out training/runs/deberta --epochs 2 --lr 3e-5
```

## Distillation

Distill a larger teacher into the xd6 student using the documented command:

```powershell
python training\keel\train.py --base models/base-xd6 --out training/runs/xd6-kd --teacher training/runs/deberta/best --kd 0.5
```

Distillation adds a KL term to the group distribution while keeping listwise and pointwise losses.

## Export and calibrate

```powershell
npm run model:export
```

Equivalent command:

```powershell
python training\keel\export.py --ckpt training/runs/xd6/best --out models/keel-2
```

Export uses a `TraceableBert` wrapper because Transformers 5 mask helpers do not trace cleanly. It exports ONNX opset 17, applies dynamic int8 quantization, copies tokenizer/config files, and writes an approximately 13 MB artifact plus `keel.json`.

Final calibration: temperature `choice=1.0`, `score=1.0`, `noul=1.5`; abstain threshold `0.06`; lexical fusion `choice=0.75`, `score=0.3`, `noul=0.3`. The blend was selected as the smallest blend with 0 safety misses on labeled-50; holdout/open were not used for selection.

## Bench and compare

```powershell
npm run keel:bench
```

Bench suites are labeled-50, holdout-20, holdout-b-20, and open-60. For live Jev comparison only when intentionally provided:

```powershell
$env:TYPESAFE_API_KEY="..."
npm run keel:compare-jev
```

The final run did not measure live Jev because no `TYPESAFE_API_KEY` was set; `artifacts\keel-vs-jev.md` records that no Jev fields were guessed.

## Promote and verify

Promote by writing the calibrated export to `models\keel-2`. Then verify:

```powershell
npm run test:keel
npm run keel:bench
```

Before publishing claims, inspect safety misses, latency, and the caveat that current holdout/open suites were authored by the same person as the training banks.
