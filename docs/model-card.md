---
license: apache-2.0
language: en
library_name: onnxruntime
pipeline_tag: zero-shot-classification
base_model: MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33
tags: [decision, nli, cross-encoder, system-one, onnx, int8, agents]
---

# Model card: Keel

Keel is a small open-weight decision model. It scores typed questions (choice, score, yes/no) about a piece of text and returns calibrated probabilities, locally, in milliseconds. This card covers **Keel-3** (`decider-3.0.0`), the default since release 3.0.0, and the previous **Keel-2** (`decider-2.0.0`), which stays available as a pinned model.

## Model details

| Field | Keel-2 | Keel-3 |
|---|---|---|
| Model id | `decider-2.0.0` | `decider-3.0.0` (training run `t1-r11`) |
| Status | Previous default; pin with `"model": "decider-2.0.0"` | **Default.** `decider-latest`, `jev-*` and Microsoft-Decision-1 aliases resolve to it. |
| Architecture | NLI cross-encoder (6 layers, hidden size 256), about 13M parameters | Same |
| Base model | [`MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33`](https://huggingface.co/MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33), MIT | Same |
| Format | ONNX, dynamic int8 | ONNX, mixed int8 (per-channel; FFN output and classifier kept in fp32) |
| File size | <!-- num:k2.size -->13 MB<!-- /num --> | <!-- num:k3.size -->17.7 MB<!-- /num --> |
| Input window | 256 tokens per (state, hypothesis) pair | Same |
| Runtime | `onnxruntime-node` on CPU; no GPU needed | Same |
| Fallback | Keel-1 lexical judge, `decider-1.2.0` | Same |
| License | Apache-2.0 (weights and code); base MIT | Same |
| Developed by | The Keel authors | Same |

### How it works

Each option is turned into a hypothesis sentence, for example "The ticket should be handled by billing: payments, refunds, invoices." The model scores whether the state entails each hypothesis. Keel then converts the entailment margins into a probability distribution, using per-type temperatures from `keel.json`:

- **choice**: a softmax over the options;
- **score**: a distribution over ordered levels, plus the expected level;
- **noul**: a calibrated P(yes).

Because each option is scored independently, the answer does not depend on option order.

## Intended use

- **Typed branches inside agents and apps**: routing a ticket, picking a sub-agent or tool, deciding edit, ask or stop, rating severity, gating a command, flagging prompt injection or PII.
- **A first pass in front of an LLM.** Accept Keel's answer when confidence ≥ τ and defer the rest. See [Token savings](token-savings.md).
- **Local, offline or private settings** where text must not leave the machine.
- **Clients that already speak the System One wire** (Jev and Microsoft-Decision-1), through Keel's compatible API.

## Out-of-scope use

- **Sole authority over destructive, irreversible or safety-critical actions.** No Keel model is at zero safety misses yet. Always keep a human or a stronger model in that loop.
- **Decisions that need world knowledge or multi-step reasoning**, such as exam questions, arithmetic or legal conclusions. Keel is at chance on MMLU, ARC and HellaSwag.
- **Long documents.** The model reads about 256 tokens per pair, so later text is truncated.
- **Languages other than English**, and images.
- **Decisions about people** in high-stakes domains: hiring, credit, housing, medical triage, law enforcement.
- **Generating text or rationales.** Keel returns probabilities only.

## Training data

All training data is generated or public. No customer or user data was used.

| Data | Keel-2 | Keel-3 |
|---|---|---|
| Synthetic decision families (`training/keel/families.py`) | Data v1 and v2: about 33k groups, including compositional stop, ask and vulnerability generators | Data v3 to v5: 60+ families, including agent gating, safety, injection, PII, moderation, sentiment and intent, with "none of the above" and injected-text variants. The final passes use the data v9 core, about 80k family-balanced groups, with soft labels from the 70M Keel-3-Pro teacher on every group. |
| Replay | About 6k MNLI pairs | Data v2 at 20–25% weight |
| Public train splits | None | About 12k groups from datasets whose licenses allow training. See [Licenses](licenses.md). |
| Decontamination | Generated states that share a 6-gram with any held-out state are dropped | Same, extended to the blind suite |

The open-60 domains are deliberately absent from the families. The blind suite was written by a separate author and never shown to the trainers.

## Training procedure

- Every question becomes a group of (state, hypothesis) pairs.
- **Loss**: listwise cross-entropy over the group, plus 0.5 × pointwise binary cross-entropy. Keel-3 adds an ordinal loss on score groups (weight 0.5), label smoothing (0.05), option-order shuffling (0.5), hard-negative weighting (0.2), a pointwise noul term (0.1) and EMA weights (0.998).
- **Keel-2**: about 60 CPU minutes in two phases: 1,200 steps on data v1, then a warm start of 3,292 steps at lr 4e-5 on data v2.
- **Keel-3**: a chain of warm starts on CPU. Keel-2 → round 1 → `t1-r2` (v5 core) → `t1-r7` (v9 core, safety loss 1.0) → `t1-r9` (full distillation from Keel-3-Pro at weight 0.5, temperature 2, plus the safety loss at 0.5) → `t1-r11`, a third pass with the same recipe at lr 1e-5: <!-- num:k3.final.pass -->2,500 steps in about 33 CPU minutes<!-- /num -->. The **safety loss** is an unlikelihood term that penalises probability mass on harmful options in safety families. Checkpoints were chosen on dev loss only (`t1-r11`: 0.876, the best of the line).
- **Calibration**: per-type temperatures are fitted on development splits only (v9 dev and dev_ood), never on held-out or blind suites. Keel-3 temperatures are choice 1.0, score 1.0 and noul 1.7, with an abstain threshold of 0.166 and no lexical blend.

Details: [Training guide](training-guide.md).

## Evaluation

Suites: three older held-out suites (holdout-20, holdout-b-20 and open-60, 100 cases in total), a 234-case blind suite, and blind-c, a 100-case confirmation suite that was not used for selection or promotion. A case is "fully right" when all of its questions are answered correctly. A safety miss is a harmful answer on a safety-critical case.

| Metric | Keel-2 | Keel-3 | LLM baseline |
|---|---:|---:|---:|
| Held-out 100, fully right | <!-- num:k2.h100 -->59/100<!-- /num --> | <!-- num:k3.h100 -->88/100<!-- /num --> | <!-- num:llm.h100 -->75/100<!-- /num --> (gpt-5-mini) |
| Blind 234, fully right | <!-- num:k2.blind -->92/234<!-- /num --> | <!-- num:k3.blind -->125/234<!-- /num --> | <!-- num:llm.blind -->215/234<!-- /num --> (claude-haiku-4.5) |
| Safety misses, all 334 held-out cases | <!-- num:k2.heldout.safety -->14<!-- /num --> | <!-- num:k3.heldout.safety -->12<!-- /num --> | <!-- num:llm.heldout.safety -->2<!-- /num --> |
| **blind-c 100, fully right (safety misses)** | <!-- num:k2.blindc -->47/100<!-- /num --> (<!-- num:k2.blindc.safety -->10<!-- /num -->) | **<!-- num:k3.blindc -->40/100<!-- /num --> (<!-- num:k3.blindc.safety -->12<!-- /num -->)** | <!-- num:llm.blindc -->37/100 (39 answered)<!-- /num --> |
| Choice ECE, blind | <!-- num:k2.ece.blind -->0.182<!-- /num --> | <!-- num:k3.ece.blind -->0.108<!-- /num --> | <!-- num:llm.ece.blind -->0.080<!-- /num --> |
| Public datasets, mean accuracy (18) | <!-- num:pub.k2.mean -->42.8%<!-- /num --> | not measured | not measured |
| In-process p95, idle CPU | <!-- num:k2.p95.idle -->13.3–14.5 ms<!-- /num --> | <!-- num:k3.p95.idle -->13.7–14.3 ms<!-- /num --> | <!-- num:llm.p50 -->55.7 s<!-- /num --> p50 (CLI wall time) |

**Known regression.** On blind-c, Keel-3 is at <!-- num:k3.blindc.delta -->−7<!-- /num --> cases fully right and <!-- num:k3.blindc.safety.delta -->+2<!-- /num --> safety misses against Keel-2; the loss is mostly in yes/no questions. For safety-critical gates, use Keel with an LLM fallback below τ, or pin `decider-2.0.0`. Details: [Benchmarks](benchmarks.md#the-blind-c-regression).

Full tables, suite descriptions and vendor-reported comparisons are in [Benchmarks](benchmarks.md).

## Bias, risks and safety

- **Safety misses.** Keel-3 has <!-- num:k3.blind.safety -->11<!-- /num --> safety misses on the blind suite (the same as Keel-2) and <!-- num:k3.blindc.safety -->12<!-- /num --> on blind-c (Keel-2: <!-- num:k2.blindc.safety -->10<!-- /num -->). Typical failures are choosing a convenient but risky branch, such as trusting an injected instruction or approving a destructive command whose text sounds routine. Treat any `run`, `approve` or "not harmful" answer on a high-risk action as advisory.
- **Prompt injection.** The state is untrusted text. Keel cannot be instructed by it (no generation, no tools), but adversarial wording can still shift the probabilities. Keep injection detection and command gating as separate questions, and defer when confidence is low.
- **Synthetic-data bias.** Most training data comes from templates written by a small team. Phrasings, domains and cultural contexts outside those templates are less reliable.
- **Base-model inheritance.** The base NLI model was trained on a mix of public NLI datasets and inherits their biases.
- **Over-trust.** Calibrated probabilities can look authoritative. Log them, review samples, and re-measure on your own traffic.

## Limitations

- An LLM is far more accurate on the blind suite.
- Score bands and yes/no questions are the weakest areas.
- 256-token window, English only, text only.
- Keel abstains by flattening its distribution, not by refusing. "None of the above" must be an explicit option or a client-side rule.
- Latency was measured on one idle CPU with `scripts/keel-latency.ts`. Measure on your hardware.
- Keel-3 is worse than Keel-2 on the blind-c confirmation suite.

## How to use

```bash
npm install && npm run dev
curl -s http://localhost:8080/api/v1/systemone -H "Authorization: Bearer $KEEL_TOKEN" -H "Content-Type: application/json" \
  -d '{"state":"rm -rf ./build","questions":{"cmd":{"type":"choice","instructions":"Should the agent run this?","criteria":{"run":"Safe, workspace-scoped","confirm":"Ask the user first","block":"Destructive"}}}}'
```

Keel-3 answers by default. To use Keel-2 for one request, send `"model": "decider-2.0.0"`; to make it the default, set `KEEL_MODEL_DIR=models/keel-2` before `npm run dev`. See [Quickstart](quickstart.md).

## License and attribution

Keel's code and weights are released under [Apache-2.0](../LICENSE). The base model is MIT-licensed, by Moritz Laurer, built on Microsoft's xtremedistil. Training-data licenses and the open review items are listed in [Licenses](licenses.md). See [NOTICE](../NOTICE).

## Citation

```bibtex
@software{keel_2026,
  title   = {Keel: an open-weight, local System One decision model},
  author  = {{The Keel Authors}},
  year    = {2026},
  license = {Apache-2.0},
  url     = {https://github.com/neerumsr/Keel}
}
```
