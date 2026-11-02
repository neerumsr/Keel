---
# Hugging Face model card for the Keel weights. Staged here; nothing in hf/ is uploaded automatically.
# Fill every "TBD" from docs/benchmarks before upload (RELEASE_CHECKLIST.md, steps 1 and 9).
license: apache-2.0
language:
  - en
library_name: onnxruntime
pipeline_tag: zero-shot-classification
base_model: MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33
base_model_relation: finetune
tags:
  - keel
  - decision-model
  - system-one
  - cross-encoder
  - natural-language-inference
  - zero-shot-classification
  - onnx
  - int8
  - cpu
  - local-first
  - coding-agents
  - mcp
datasets:
  # Only datasets whose rows (or derived groups) were used in training. Eval-only datasets
  # are listed in the benchmark section, not here. Confirm against training/README.md and
  # docs/licenses.md for the promoted run before upload.
  - nyu-mll/glue
  - PolyAI/banking77
  - clinc/clinc_oos
  - allenai/winogrande
  - Rowan/hellaswag
  - allenai/ai2_arc
  - google/boolq
  - google/civil_comments
  - tasksource/esci
metrics:
  - accuracy
  - mae
model-index:
  - name: keel-3
    results:
      # Placeholders. Numbers come from docs/benchmarks (scripts/keel-parity-bench.ts);
      # never fill them from candidate notes or vendor claims.
      - task:
          type: text-classification
          name: Typed decisions (choice)
        dataset:
          type: keel-blind
          name: Keel blind held-out suite
        metrics:
          - type: accuracy
            name: Cases fully right
            value: TBD
      - task:
          type: text-classification
          name: Typed decisions (choice)
        dataset:
          type: keel-holdout-b-20
          name: Keel holdout-b-20
        metrics:
          - type: accuracy
            name: Choice accuracy
            value: TBD
---

# Keel-3 (`decider-3.0.0`)

Keel is a small, open-weight **decision model** for coding agents. It answers typed questions
about a piece of state — **choice** (pick one label), **score** (an ordered level) and **noul**
(a yes/no probability) — with calibrated probabilities. It runs in-process on CPU through ONNX
Runtime and makes **no network call** on the decision path.

- Code, server, MCP bridge and training pipeline: https://github.com/neerumsr/Keel
- Full model card (training data, procedure, limitations): `docs/model-card.md` in the code repo
- Benchmarks and how they were measured: `docs/benchmarks` in the code repo

> If Keel-3 is not promoted before release, this card ships for **Keel-2 (`decider-2.0.0`)**:
> replace "Keel-3"/`decider-3.0.0` and the model-index name, and point the numbers at the
> Keel-2 rows. See `hf/FILES.md`.

## Model details

| Field | Value |
|---|---|
| Model id | `decider-3.0.0` |
| Architecture | BERT-style NLI cross-encoder (6 layers, hidden 256), ~13M parameters |
| Base | [`MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33`](https://huggingface.co/MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33) (MIT), itself from `microsoft/xtremedistil-l6-h256-uncased` (MIT) |
| Format | ONNX, int8 (`onnx/model_quantized.onnx`), plus tokenizer and `keel.json` calibration |
| Max input | 256 tokens per (state, hypothesis) pair |
| Latency | p95 TBD ms in-process on CPU (see `docs/benchmarks`) |
| License | Apache-2.0 (weights and code); base weights MIT |

## How it works

Every question is turned into a group of (state, hypothesis) pairs — one hypothesis per label,
level or yes/no side. The cross-encoder scores each pair for entailment; the scores are
normalized within the group, temperature-calibrated, optionally blended with a lexical prior, and
returned as probabilities. Settings live in `keel.json` (`temperature`, `abstain`,
`lexicalBlend`, `hypothesisVersion`). The hypothesis templates are part of the model contract:
use the exact ones in the code repo (`src/lib/decider/hypothesis.ts`, mirrored in
`training/keel/hypothesis.py`).

## Usage

The intended runtime is the Keel server (HTTP `POST /api/v1/systemone`) or the `keel-mcp` MCP
bridge from the code repo:

```bash
git clone https://github.com/neerumsr/Keel && cd keel
npm install
npm run model:fetch     # downloads these weights into models/
npm run dev             # http://localhost:8080
```

```json
{
  "model": "decider-latest",
  "state": "The user asked to rotate the production database password in the deploy script.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "What should the agent do next?",
      "criteria": { "edit": "Specified enough to implement", "ask": "A missing fact would change the edit", "stop": "Unsafe or out of scope" }
    },
    "risk": { "type": "score", "instructions": "How risky is proceeding?", "criteria": ["Cosmetic", "Local and reversible", "Behavior change", "Data, auth, or secrets"] },
    "tests": { "type": "noul", "instructions": "Should this step add or update a test?" }
  }
}
```

Using the ONNX file directly (without the server) requires reproducing the hypothesis
templates and the calibration in `keel.json`; raw entailment logits are not calibrated decisions.

## Training data

Synthetic decision groups generated by the families in `training/keel/` (6-gram contamination
filter against all held-out and blind states), MNLI replay, and converted train splits of the
public datasets listed in the front matter. Eval-only datasets (including any with
non-commercial or research-only terms) were **not** used for training. Per-dataset licenses:
`docs/licenses.md`. TBD: confirm the final data mix of the promoted run.

## Evaluation

All numbers are produced by `scripts/keel-parity-bench.ts` on suites never trained on
(holdout-20, holdout-b-20, open-60 and a blind suite of 100+ cases), plus public benchmark
adapters. Competitor numbers are either measured live by scripts in the repo or quoted as
**vendor-reported** with a link. See `docs/benchmarks`.

| Suite | Cases fully right | Choice | Score | Noul | Safety misses | p95 ms |
|---|---|---|---|---|---|---|
| holdout-20 | TBD | TBD | TBD | TBD | TBD | TBD |
| holdout-b-20 | TBD | TBD | TBD | TBD | TBD | TBD |
| open-60 | TBD | TBD | TBD | TBD | TBD | TBD |
| blind | TBD | TBD | TBD | TBD | TBD | TBD |

## Intended use and limitations

- **Intended:** fast, local, typed branch decisions inside agent loops — routing, severity,
  edit/ask/stop gates, yes/no checks — where a probability over a fixed schema is needed.
- **Not intended:** free-form generation, chat, or as the sole control for high-stakes,
  irreversible or safety-critical actions. Keep a human or a stronger check in the loop.
- Trained mostly on synthetic English data written for software-engineering agents; quality
  drops on other domains, languages and long inputs (> 256 tokens are truncated).
- Small eval suites: expect roughly ±10 percentage points of noise per suite.
- Known failure modes are listed in `docs/model-card.md`.

## License and attribution

Apache-2.0. Includes a fine-tune of `MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33`
(MIT). See `NOTICE` and `LICENSE` in this repository. "Jev", "System One" and "TypeSafe" are
names of TypeSafe AI; "Microsoft-Decision-1" is a name of Microsoft. Keel is independent and not
affiliated with or endorsed by either.

## Citation

```bibtex
@software{keel_2026,
  title   = {Keel: an open-weight, local System One decision model},
  author  = {{The Keel Authors}},
  year    = {2026},
  version = {3.0.0},
  url     = {https://github.com/neerumsr/Keel},
  license = {Apache-2.0}
}
```
