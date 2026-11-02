# jev-3 → trainers / data-2: ranked fix list for Keel-3

Author: jev-3 (model audit). Early drop; evidence and tables are in `model-audit.md`, `audit-output.md`, `audit.json`, `parity.json`.
All tuning numbers below were selected on **dev** (`training/data/dev.jsonl`) only. Held-out numbers are **diagnosis only** and marked HELD.
Reproduce: `node --experimental-strip-types artifacts/parity/jev/dump-margins.ts --model models/keel-2 --out artifacts/parity/jev/margins.json && python artifacts/parity/jev/audit.py`
(`parity.py` / `quant.py` for the quantization evidence). **Note:** `npm run keel:bench -- --out X` still writes the shared
`artifacts/keel-2-report.*` (the script's own `--out` wins); call `node --experimental-strip-types scripts/keel-bench.ts --model … --out …` directly.

## What's wrong with Keel-2, in one paragraph
Keel-2 is well calibrated **in-distribution** (dev choice ECE 0.056, acc 0.85) and badly overconfident **out of distribution**
(HELD choice: mean confidence 0.79 vs accuracy 0.61, ECE 0.255, NLL 1.21). Confident errors are not "ambiguous input" — the
model strongly entails a wrong hypothesis (`neutral` for "Absolutely love the new update" at 0.97; `clarify` for fully specified
edits at 0.99; `identity` for a reset-token security bug at 0.996). Abstain cannot catch these (it keys on max entailment, which is
high). Score levels are compressed toward the middle (dev slope pred-vs-true 0.66; HELD MAE 0.71 levels), and noul is biased
toward "no" (HELD mean P(yes) on yes-cases 0.36; PII/phishing misses). Jev's public contract is "calibrated probabilities,
low confidence = route to a human" (docs.typesafe.ai/confidence.md, /concepts/system-one.md); we break exactly that promise OOD.
**Update after quantization audit:** a large part of the in-distribution error is the int8 export, not the network (P0-0):
the same checkpoint in fp32 gets dev choice acc 1.00 / ECE 0.011 and HELD 68/100 fully right (vs 58). The OOD
overconfidence remains in fp32 (HELD choice conf 0.87 vs acc 0.74, ECE 0.15), so P1/P2 still apply.

## Ranked recommendations

### P0-0 — STOP shipping the current dynamic-int8 ONNX (biggest single loss; train-1 + whoever runs export)
`export.py` applies `quantize_dynamic(QInt8)` to every op. Against the fp32 export of the *same* checkpoint
(`training/runs/xd6-v2/best`; torch↔fp32-ONNX max diff 2.9e-5, so the export itself is correct) the int8 model has
**mean max-logit error 2.2, max 6.2, and 83/382 argmax flips (22%; 36/200 on dev)** — see `parity.json`, `quant.json`.
Same weights, same `keel.json`, fp32 ONNX (Node bench, `keel2-fp32.md`):

| suite (fully right / choice) | int8 shipped | fp32 |
|---|---|---|
| labeled-50 | 48/50 · 33/34 | 50/50 · 34/34 |
| holdout-20 (HELD) | 14–15/20 · 11/15 | 16/20 · 11/15 (score 5/5) |
| holdout-b-20 (HELD) | 10/20 · 8/15 | 16/20 · 11/15 (score 5/5, noul 2/2) |
| open-60 (HELD) | 34/60 · 24/36 | 36/60 · 27/36 |
| dev choice acc / ECE / NLL | 0.85 / 0.056 / 0.547 | 1.00 / 0.011 / 0.187 |
| dev score MAE / slope | 0.385 / 0.66 | 0.059 / 0.97 |

Held-out fully-right **58 → 68 / 100** with zero retraining. Caveat (honest): fp32 has **4** held-out safety misses vs 3
(holdout-b gets 2: #304 identity-vs-security, #316 CORS wildcard → proceed). Other recipes tried (`quant.py`, vs fp32, 382 groups):

| recipe | size MB | mean max-diff | argmax flips |
|---|---|---|---|
| fp32 | 51.1 | 0 | 0 |
| shipped dynamic QInt8, all ops | 13.0 | 2.20 | 83 |
| dynamic QInt8 per-channel | 13.0 | 2.01 | 65 |
| dynamic QInt8 MatMul-only (fp32 embeddings) | 36.8 | 2.23 | 81 |
| MatMul-only per-channel | 36.9 | 2.01 | 67 |
| QUInt8 reduce_range | 13.0 | 2.95 | 122 |

No dynamic-int8 recipe is acceptable — the error is in the activations of this tiny (13M) model, not embeddings.
**Independent check of train-1's `--quant mixed` export** (`models/candidates/t1-q0`: FFN-output dense + pooler/classifier
fp32, per-channel int8 elsewhere, 17.7 MB; its own keel.json) on all 1597 questions vs fp32 margins: **18 flips (1.1%; 13/1415
dev), mean max-diff 0.08, max 1.15** — vs 327 flips (20%) for the shipped int8. HELD fully-right 66/100 (fp32 68, shipped int8
58); dev choice ECE 0.029, score slope 0.94. **Endorse `--quant mixed` as the Keel-3 default**; still gate each candidate on
flip rate ≤ ~1–2% vs its own fp32 export (`artifacts/parity/jev/dump-margins.ts` + the comparison in model-audit.md §2).
Actions: (a) ship **fp32** (51 MB is fine for an open-weight local model) or test **fp16** (`onnxconverter_common.float16`,
keep_io_types) and accept only if flips ≤ 1%; (b) if size matters, use **static QDQ int8 with calibration data** (≥ 500 dev
groups) or **QAT**, accept only if flips ≤ 1% vs fp32; (c) make `export.py` **fit temperature/bias on the artifact that ships**
and print a `quant_flip_rate` gate; (d) the candidate gate must evaluate the shipped ONNX, not the torch checkpoint.
Latency: on this shared, loaded machine fp32 was not slower than int8 in onnxruntime-python (p50 21 vs 24 ms/question) and
Node bench p95 was 42–67 ms for both — re-measure on an idle machine against the p95 < 20 ms gate before choosing.

### P0 — cheap, config/export-level (train-1 owns `export.py` usage; do these for any candidate)
1. **Fit `noulBias` + `T_noul` at export on the shipped artifact, don't hard-code 0.** int8: dev NLL bias 0 → 0.466, bias +1.0
   → 0.403; HELD noul 7/14 → 9/14. fp32: dev-optimal is bias 0, T 1.5, blend 0 (dev NLL 0.251) — i.e. the "no" bias was largely
   a quantization artifact, which is exactly why it must be fitted per artifact. Add Platt scaling to `export.py`
   (fit `a·(m_yes−m_no)+b`, T=1/a, bias=b) on a leave-family-out dev (see 3).
2. **Set `lexicalBlend.choice` ≤ 0.25 (dev-optimal region 0.25–0.5; 0.75 was chosen on in-sample labeled-50).** Dev NLL is flat
   (0.547 @0.25 vs 0.547 @0.75) so 0.75 buys nothing on dev; HELD it adds +1 safety miss (open-60 #211 "Threat": blend flips
   `review`→`allow`). If you keep a lexical prior, select it on dev + a safety-weighted objective, never on labeled-50.
   Better: drop lexical fusion for choice entirely once the P1 data fixes land (it is a hand-written bag-of-words; Jev has nothing
   like it). Keep `score` 0.3 / `noul` 0.3 only if dev says so (dev: score blend is neutral, noul blend 0 ≈ 0.3).
   fp32 re-check: dev-best is blend 0.1, T 1.3 (NLL 0.167); blend 0–1 moves HELD fully-right only 66–69/100 — on a good
   model the lexical prior is nearly irrelevant, more evidence it can go.
3. **Calibrate temperature on an OOD-shaped dev, not on a random split of the same templates.** The current dev leaks:
   907/1415 dev groups share an identical `state` with a train group and 519 share (state, instructions); fp32 dev choice
   accuracy is 1.000. Any parameter selected on it is selected in-distribution. Dev picks T_choice=1.0, but
   HELD NLL falls monotonically to T≈2.5 (1.21 → 0.97) and ECE 0.255 → ~0.16. Split dev **by family** (leave-3-families-out) or
   by template id, fit T there. Expect T_choice ≈ 1.6–2.5 (fp32 HELD: T 1.0 → 1.6 takes NLL 0.88 → 0.74, ECE 0.147 → 0.105,
   neural-only). This is the biggest calibration lever after P0-0 and costs nothing. data-2: emit `dev_ood.jsonl` by family.
4. **Retire / re-fit the abstain threshold.** 0.06 is effectively a no-op (5th-percentile top-sigmoid on dev is 0.02). Sweeping
   0→0.5 only *hurts* dev NLL (0.545 → 0.623) and fully-right counts; the confidently-wrong OOD cases have high top-sigmoid so
   abstain never fires on them. Keep threshold 0 (or ≤0.06) until a real OOD/none-of-the-above signal exists (P2-9).
5. **Batch-composition determinism (see parity.json).** Served answers come from one ONNX batch over *all* questions' hypotheses
   (padding + dynamic int8 activation quantization), while `export.py` calibrates per question. Verify per question alone vs
   whole-request batch; if `argmax_flips_int8_alone_vs_batched > 0`, run each question as its own batch (or sort/pad to fixed
   buckets) in `neural.server.ts`, and calibrate exactly as served. (holdout-20 #117 flips `ask`→`stop` between the two paths
   under int8: alone-vs-batched max diff 2.44, 4 flips.) With fp32 the Node bench (batched) and my per-question reproduction
   agree on every fully-right count, so shipping fp32 largely removes this; keep a test anyway.
6. **(Low priority) Train/serve max-length skew:** `train.py --max-len 160` vs served `maxLength 256`. Measured: no pair in
   labeled/holdout/open/dev exceeds 160 tokens, so it is harmless today; align to 256 when P1 adds longer states.

### P1 — data (data-2) — the confident OOD errors are data gaps, not model capacity
7. **Description-grounded option semantics.** The model keys on option *names* learned from templates and ignores descriptions:
   `neutral` ("Factual, no clear feeling") beats `positive`/`negative` on obviously emotional text (open #201/202/204/205/250, all
   ≥0.97); `clarify` beats `proceed` ("Clear, safe, and scoped: make the change") on file-scoped edits (#313/318/320 ≥0.9).
   Generate: (a) **key-name dropout** — replace keys with opaque ids (`a`,`opt_3`) so only the description carries meaning,
   30% of choice groups; (b) **description paraphrase + key renaming** for every family (edit/proceed/implement/apply…);
   (c) **contrastive "default/neutral/other" options** where the right answer is NOT the catch-all (neutral, other, unclear,
   clarify, review). Currently catch-alls are over-entailed.
8. **New families covering OOD failures** (none exist in train today): sentiment incl. sarcasm & negation ("not bad at all",
   "wasn't happy", "Great, another update that deletes my settings"); PII detection (phones, addresses, SSNs, emails, cards);
   phishing/spam; threats/moderation (`remove` vs `review` vs `allow`, heated-but-allowed); e-commerce intents (track/return/
   cancel/exchange); legal clause typing; lead stage; HR benefits vs payroll; news topic (sports vs politics). Write them with
   *different* authors/templates than any held-out suite; keep the 6-gram filter.
9. **Security-flavoured routing negatives:** "password reset link still works for another account" = appsec, not identity
   (#304, 0.996 wrong); "URL id lets me see another company's data" = security (#104); "skip/comment out signature check in
   production" = stop (#115). Add IDOR/broken-auth/token-reuse/CORS-wildcard/disable-verification paraphrases with the
   *access/login* vocabulary present so the model learns that access words ≠ account queue when someone else's data is exposed.
10. **Noul with negative criteria:** `false: "No personal identifiers"` gets entailed (margin 2.0) over `true` (0.99) for
    "Call me back at 415-555-0137". Generate noul groups whose `false` text is a negation of the `true` text, plus
    instructions-only nouls (Jev allows `criteria` omitted — docs.typesafe.ai/primitives/noul.md), balanced 50/50 yes/no.
11. **Ordinal scales of every length 2–10** with level texts that are *degrees* (`1 star`…`5 stars`, "Harmless"…, priority P0–P3)
    and both directions of negation ("No user impact" must be level 0, #223). Today all-negative margins (#225 star rating: every
    level ≈ −2.2) collapse to a flat distribution → score ≈ middle.

### P2 — training objective / architecture (train-1 student, train-2 teacher)
12. **Ordinal loss for score** (train.py `group_loss`, score groups only): add expected-level MSE
    `w_ev · (Σ i·p_i − Σ i·t_i)² / (n−1)²` with **w_ev = 0.2–0.5**, and/or a CORAL-style cumulative head: hypotheses
    "at least level k" (k=1..n−1) scored by the same cross-encoder, P(level ≥ k) = σ(margin_k), monotonicity enforced by
    cumulative max. Evidence: in-distribution the fp32 model is already well placed (dev slope 0.97, MAE 0.06 — the int8
    slope 0.66 was mostly quantization), but OOD it collapses to the middle: open-60 score band 5/14, HELD MAE 0.65 levels,
    star ratings with every level margin ≈ −2.2 → score ≈ 2. The ordinal term mainly helps once P1-11 adds varied scales; do
    not expect post-hoc T to fix it (dev T_score 0.5 sharpens but worsens NLL).
13. **Listwise label smoothing + OOD regularization** instead of in-distribution T: train with target smoothing ε=0.05 and add a
    confidence penalty (−β·H(p), β=0.1) on groups from held-out-style families; this is the cheapest route toward the
    "calibrated across groups" behavior Jev advertises (RLCD — vendor term, no public details).
14. **Teacher distillation (train-2):** distil from a larger NLI cross-encoder (deberta-v3-base/large zeroshot) or an LLM-labeled
    soft-target set on the P1 families. `--kd 0.5` exists; also distil **score EV** (MSE on expected level) not only KL.
    Use teacher temperature 2.0 for softer targets; it transfers dark knowledge about catch-all options.
15. **Noul head:** served noul = σ((m_yes − m_no)/T + bias). The 2-way listwise term already equals BCE on the difference, but
    the pointwise BCE on each hypothesis separately (weight 0.5) pulls the two margins independently and the trained model
    still under-predicts "yes" even in-distribution (dev prefers bias +1.0). Down-weight pointwise for noul (0.5 → 0.1), add
    balanced yes/no data (P1-10), and always fit bias at export (P0-1).
16. **Abstention that works:** add an explicit none-of-the-above hypothesis to every training group ("None of the options fits")
    with target mass on ambiguous/irrelevant states (`ambiguous` family), and expose its probability as the abstain signal
    instead of max-sigmoid. Or ensemble 3 seeds / MC-dropout on the 13M student (≤3× latency; p95 now 10–20 ms single).

### Cross-team notes (not my files — owners decide)
- **jev-1 (wire.ts):** Keel `confidence` = top probability. Jev documents choice confidence = (p_max − 1/n)/(1 − 1/n) and score
  confidence = max(0, 1 − Σp_i|i−m| / MAD_unif) (https://docs.typesafe.ai/confidence.md). Our A/B gate τ=0.6 and any
  thresholds users port from Jev are on a different scale. Noul has no confidence field in Jev (matches us).
- **data-1 / test owner:** #109 "Records gone" band 2.2–3 vs Keel 2.15–2.21 is a near miss; labels look right. #117 depends on
  batch path (P0-5). No held-out labels look wrong to me.
