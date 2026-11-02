# Keel-2 model audit vs Jev design and ML practice (jev-3)

Scope: open weights `models/keel-2` (decider-2.0.0, xsmall cross-encoder student, ~13M params, int8 ONNX), its serving math
(`neural.server.ts`), calibration parameters in `keel.json`, and the training/export pipeline (`training/keel/*.py`).
Ranked fix list for trainers and data-2: **`recommendations.md`** (written first; this file is the evidence).

Honesty rules followed: blind suites and `eval-blind*` were never opened. All tuned values were selected on
`training/data/dev.jsonl`; every number on labeled/holdout/open suites is **HELD = diagnosis only**. Jev/MSD1 numbers are
vendor-reported and cited; nothing about them was measured here.

Artifacts in this folder: `keel2-baseline.{md,json}` (bench, shipped int8), `keel2-fp32.{md,json}` (bench, fp32 export of the
same checkpoint), `dump-margins.ts` → `margins*.json`, `audit.py` → `audit*.json`/`audit*-output.md`, `parity.py` → `parity.json`,
`quant.py` → `quant.json`.

## 1. How Jev works (public sources only)

| Topic | Jev (public) | Keel-2 | Gap |
|---|---|---|---|
| Model / training | "System One" models, trained with **RLCD — reinforcement learning for calibrated decisions**; no architecture, size, or data published ([ML primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md), [System One](https://docs.typesafe.ai/concepts/system-one.md)) | NLI-style cross-encoder; one (state, question, option-hypothesis) pair → margin; listwise CE + 0.5 pointwise BCE (+ optional KD) | Different family; we can't copy RLCD. Our equivalent lever is calibration-aware loss + OOD-shaped calibration data |
| Calibration claim | "trained for calibrated decisions… measured across groups" ([System One](https://docs.typesafe.ai/concepts/system-one.md)); no public ECE/Brier | post-hoc temperature per primitive, fitted on an in-distribution dev | Our calibration holds in-distribution only (§3) |
| Choice confidence | `(p_max − 1/n)/(1 − 1/n)` ([confidence](https://docs.typesafe.ai/confidence.md)) | `confidence = p_max` (`wire.ts confidenceFrom`) | **Different scale** — owner jev-1 |
| Score | expected level, may be fractional; each level judged on its own against the state ([score](https://docs.typesafe.ai/primitives/score.md)); confidence `max(0, 1 − Σp_i\|i−m\| / MAD_unif)` | softmax over level margins → expected level | Same idea; our levels compress OOD (§5) |
| Noul | P(yes) only, no confidence; criteria optional; 0.7 / 0.3 suggested thresholds ([noul](https://docs.typesafe.ai/primitives/noul.md), [confidence](https://docs.typesafe.ai/confidence.md)) | σ((m_yes−m_no)/T + bias + blend·logit(lex)) | Bias never fitted; instructions-only nouls absent from training |
| Abstain / routing | Low confidence (< 0.5 suggested) → route to a human ([confidence](https://docs.typesafe.ai/confidence.md)) | blend toward uniform if max σ(margin) < 0.06 | Our abstain is a no-op and cannot see confident-wrong cases (§4) |
| Latency / cost | vendor-reported 70–500 ms; $0.042 / M input tokens, output free; 64k context ([models](https://docs.typesafe.ai/models.md), [blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)) | local, ~6–12 ms p50 idle (shipped report) | Our advantage; keep it |
| MSD1 | vendor-reported: Qwen3.5-9B post-trained, calibrated per-option probabilities, 1.3% perturbation flip rate | — | Perturbation flips are worth measuring for Keel too (we flip 22% from quantization alone) |

## 2. Correctness checks

| Check | Result |
|---|---|
| `npm run test:keel` | 21/21 pass |
| `hypothesis.py` ≡ `hypothesis.ts` (`test_hypothesis.py`) | 154 fixtures, 0 mismatches |
| served tokenizer vs checkpoint tokenizer (382 groups) | 0 id mismatches |
| max token length of any pair (labeled/holdout/open/dev) | ≤ 160 → train 160 / serve 256 skew is harmless today |
| PyTorch `xd6-v2/best` vs ONNX fp32 | max margin diff **2.9e-5** — export graph is correct |
| ONNX fp32 vs shipped int8 | mean per-group max diff **2.20**, max **6.18**, **83/382 argmax flips (22%)**, 36/200 on dev |
| int8: question alone vs whole-request batch | max diff 2.44, 4 flips (e.g. holdout-20 #117 ask→stop) |
| fp32: batched (bench) vs alone (audit.py) | identical fully-right counts on all suites |
| dev ↔ train overlap | 907/1415 dev groups share an exact `state` with train; 519 share (state, instructions) |

### Quantization recipes (`quant.py`, vs fp32, 382 groups; latency on a loaded shared machine, onnxruntime-python)

| recipe | size MB | mean max-diff | max diff | argmax flips | p50 / p95 ms per question |
|---|---|---|---|---|---|
| fp32 | 51.1 | 0 | 0 | 0 | 21.1 / 45.4 |
| **shipped** dynamic QInt8, all ops | 13.0 | 2.20 | 6.18 | 83 | 23.9 / 48.7 |
| dynamic QInt8 per-channel | 13.0 | 2.01 | 5.82 | 65 | 21.1 / 45.8 |
| dynamic QInt8 MatMul-only | 36.8 | 2.23 | 6.26 | 81 | 25.2 / 68.0 |
| MatMul-only per-channel | 36.9 | 2.01 | 5.86 | 67 | 24.1 / 55.2 |
| QUInt8 reduce_range | 13.0 | 2.95 | 6.12 | 122 | 36.4 / 94.5 |
| train-1 `--quant mixed` (t1-q0; measured via Node margins on 1597 questions) | 17.7 | 0.08 | 1.15 | 18/1597 (1.1%) | — |

Shipped int8 on the same 1597-question set: 327 flips (20%), mean max-diff 2.13. t1-q0 HELD fully right 66/100 (fp32 68,
shipped 58); bench-style grading: labeled 50/50, holdout-20 16/20, holdout-b 15/20 (safety 2), open-60 35/60.

Dynamic activation quantization is the problem, not the embedding table. Latency numbers are contention-dominated (trainers
running); re-measure on an idle box before deciding against the p95 < 20 ms gate.

## 3. Calibration metrics (shipped `keel.json`: T 1.0/1.0/1.5, abstain 0.06, blend 0.75/0.3/0.3, noulBias 0)

ECE = 10-bin top-label; NLL/Brier on the full distribution. HELD choice n=62, score n=24, noul n=14 — small, read as direction.

| metric | int8 dev | fp32 dev | int8 HELD | fp32 HELD |
|---|---|---|---|---|
| choice accuracy | 0.855 | 1.000 | 0.613 | 0.742 |
| choice mean confidence | — | — | 0.791 | 0.867 |
| choice ECE | 0.056 | 0.011 | **0.255** | 0.152 |
| choice NLL | 0.547 | 0.187 | 1.207 | 0.911 |
| choice Brier | 0.219 | 0.001 | 0.568 | 0.428 |
| ambiguous-family mean conf | 0.298 | 0.295 | 0.267 | 0.340 |
| score MAE (levels; HELD = vs band midpoint) | 0.385 | 0.059 | 0.712 | 0.647 |
| score slope pred-vs-true (normalized) | 0.656 | 0.969 | — | — |
| noul NLL / Brier | 0.439 / 0.076 | 0.256 / 0.003 | — / 0.260 | — / 0.290 |
| noul acc@0.5 | 0.862 | 1.000 | 0.571 | 0.571 |
| noul mean P(yes) on yes-cases | — | — | 0.36 | 0.37 |

Bench (Node, batched serving path; `keel2-baseline.md` vs `keel2-fp32.md`):

| suite | int8 choice / score / noul / safety | fp32 choice / score / noul / safety |
|---|---|---|
| labeled-50 | 33/34 · 13/14 · 8/8 · 0 | 34/34 · 14/14 · 8/8 · 0 |
| holdout-20 | 11/15 · 4/5 · 2/2 · 1 | 11/15 · 5/5 · 2/2 · 1 |
| holdout-b-20 | 8/15 · 2/5 · 1/2 · 1 | 11/15 · 5/5 · 2/2 · **2** |
| open-60 | 24/36 · 6/14 · 4/10 · 1 | 27/36 · 5/14 · 4/10 · 1 |
| HELD fully right (audit.py) | 58/100 | 68/100 |

Reading: Keel-2 is calibrated in-distribution and overconfident OOD (int8 HELD confidence 0.79 vs accuracy 0.61). fp32 removes
most in-distribution error and ~40% of the OOD ECE, but OOD overconfidence remains, and fp32 has one more safety miss.

## 4. Weight / span assignment (dev-selected; HELD shown only as diagnosis)

**Lexical blend, choice (0.75 shipped; picked on in-sample labeled-50).**
int8: dev NLL is flat over blend 0–1 (best 0.5 @ T 1: 0.544 vs 0.547 shipped). HELD: 0.75 causes open-60 #211 "Threat"
`review`→`allow` (safety miss); it also rescues #209/#216/#246/#120 and causes #306. fp32: dev best blend 0.1 @ T 1.3
(NLL 0.167); HELD fully-right moves only 66–69/100 across blend 0–1. Verdict: the prior is a patch over model weakness;
keep ≤ 0.25 and plan to drop it.

**Temperature.** Dev (leaky, §2) always picks T_choice ≈ 1.0–1.3. HELD NLL keeps falling to T ≈ 1.6–2.5
(int8 1.21 → 0.97; fp32 neural-only 0.88 → 0.74, ECE 0.147 → 0.105 at T 1.6). The mismatch is a property of the dev split,
not of the model: fit T on a leave-family-out dev. Score: T 0.5 sharpens (int8 slope 0.66 → 0.755, MAE 0.385 → 0.319) but
worsens NLL; keep T_score ≈ 1 and fix with data/loss.

**Abstain threshold 0.06.** 5th-percentile top-σ on dev is 0.02 (int8) / 0.019 (fp32), so it rarely fires. Raising it to 0.5
only increases dev NLL (int8 0.545 → 0.623; fp32 0.187 → 0.188, HELD NLL 0.914 → 0.944). The confident OOD errors have top-σ
≈ 0.9+, so no threshold on max-σ catches them. A none-of-the-above hypothesis or ensemble disagreement is needed.

**Noul bias / T.** int8: dev best bias +1.0 @ T 1 (NLL 0.466 → 0.400; HELD 7 → 9/14). fp32: dev best bias 0 @ T 1.5, blend 0
(NLL 0.251). The "no" bias is mostly a quantization artifact → always fit (T, bias) per shipped artifact (Platt scaling).

## 5. Held-out failure taxonomy (34 cases fail under shipped or neural-only, fp32; same families under int8)

| failure mode | cases (suite #) | mechanism | fix (recommendations.md) |
|---|---|---|---|
| Catch-all over-entailment | sentiment #202 #204 #205 #248 (`neutral` ≥ 0.97 on emotional, negated or sarcastic text); edits #318 (`clarify`) | option *name* learned from templates; description ignored | P1-7 key-dropout, contrastive catch-alls; P1-8 sentiment |
| Security vs access/identity | #102, #104, #304 (0.998 wrong), #316 CORS wildcard → proceed, #115 skip signature check → edit | access/login vocabulary dominates; no IDOR/token-reuse negatives | P1-9 |
| Negated noul criterion entailed | PII #234 #236 #255; phishing #231 #233; deadline #237 | `false` text "No personal identifiers" is entailed lexically | P1-10, P2-15 |
| Score compression / no level entailed | #221 #224 #225 (all margins ≈ −2.2) #226 #228 #247 #258 #260 | unseen scale wording → flat distribution → middle | P1-11, P2-12 |
| Score negation | #223 "No user impact" → 2.4 | negation not modelled on levels | P1-11 |
| Domain shift (no family in train) | e-commerce #206 #207 #251; legal #245; moderation #254 "heated but fine" → remove | missing families | P1-8 |
| Lexical-blend override | #211 harm (blend → allow), #306 blend causes miss; #209 #251 #245 blend-dependent | bag-of-words prior | P0-2 |
| Batch path (int8 only) | #117 ask→stop | dynamic activation quant differs by batch | P0-0, P0-5 |

No held-out label looked wrong; #109 "Records gone" is a near miss (band 2.2–3, Keel 2.15–2.21 under int8).

## 6. Design review against ML practice

- **Good:** hypothesis construction is shared and parity-tested; listwise objective matches the decision unit; per-primitive
  temperature; export graph is exact; tokenizer is exact; tests pass.
- **Weak:** (1) quantization shipped without a fidelity gate; (2) calibration/selection on a dev that shares states with train;
  (3) blend weights chosen on in-sample labeled-50; (4) abstain signal (max σ) is orthogonal to the failure it should catch;
  (5) no ordinal objective for score; (6) noul bias not fitted; (7) training data lacks the OOD families the held-out suites
  and real users exercise; (8) confidence scale differs from Jev's documented one.
- Model capacity is not the first bottleneck: fp32 of the same 13M student fits dev perfectly; held-out errors are confident
  semantic errors that data and objective changes address. A larger teacher (train-2) mainly helps via soft labels on the new
  P1 families.

## 7. Ranked recommendations

See `recommendations.md` (authoritative, same ranking). Summary:

1. **P0-0** ship fp32/fp16 or train-1's `--quant mixed` (verified: 1.1% flips vs fp32, 17.7 MB); calibrate on the shipped
   artifact; gate on flip rate.
2. **P0-1** fit noul (T, bias) per artifact. **P0-2** lexicalBlend.choice ≤ 0.25 → 0. **P0-3** leave-family-out dev for T
   (expect 1.6–2.5). **P0-4** abstain 0 until a real OOD signal. **P0-5** batch-invariance test. **P0-6** (low) max-len 256.
3. **P1 (data-2)** key-dropout + contrastive catch-alls; sentiment/PII/phishing/moderation/e-commerce/legal families;
   security-vs-access negatives; negated-criterion and instructions-only nouls; ordinal scales 2–10 with negation.
4. **P2 (train-1/train-2)** expected-level MSE (w 0.2–0.5) or CORAL for score; label smoothing 0.05 + confidence penalty;
   teacher KD incl. score EV, teacher T 2.0; noul pointwise weight 0.5 → 0.1; none-of-the-above hypothesis for abstain.
5. Cross-team: jev-1 adopt Jev's normalized confidence (or document the difference); never run `npm run keel:bench -- --out`
   (the script's own `--out` wins and overwrites `artifacts/keel-2-report.*`; call `scripts/keel-bench.ts` directly).
