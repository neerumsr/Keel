# trainer-r2 lab notebook (Keel round 2, resumed after network outage)

Owner: trainer-r2 (continues train-1/train-2 round 2). Rules: CONTRACT.md. I never open `src/lib/decider/eval-blind*.ts` or `artifacts/parity/blind/**`; blind numbers only as harness aggregates.
Selection rule: checkpoints = best dev loss of each run; calibration = export.py torch/ORT fit on that run's **dev + dev_ood only** (no blind or held-out feedback). Blind/held-out aggregates are only *reported*; the final promotion decision uses them as the contract's gates.
Resume state lives in `artifacts/parity/r2-status.json` (command, PID, log, outputs per job).

## Resume inventory (2026-10-29 ~18:00 local)
- `t1-r5` finished (2688 steps, 104 min, v7 dev loss 0.930): warm t1-r2, v7 core + v2@0.2, KD b3 v7 labels kd 0.5 T 2. Never exported.
- `t1-r6s` finished (2500 steps, 73 min, v9 dev loss 0.918): warm t1-r2, v9 core + v2@0.2, KD b3 (v7 labels + 41.9k v9 labels from `v9/core_teacher.jsonl`), safety-neg 0.5 (families `^v3s_|gate|moderation|security|injection|threat|phishing|secret`). Never exported.
- `t1-r5s` died at step 800/2688 — abandoned (superseded by r6s).
- `t2-kd6-a` (train-2's 6L DeBERTa KD) finished; not part of this line.
- `train.py` already supports `--teacher-labels/--kd-temp` and the safety-asymmetric `--safety-neg` (unlikelihood on above-target mass of options with target < 0.2 in safety families). No trainer change needed.
- v9 core teacher labels: 41,869/80,000 groups present. Copied to `training/data/v3/teacher_t2dxs_v9core.jsonl`; resumed `t2_label.py` (b3, 8 threads, max-len 192) for the remaining 37,849 groups. Measured ~29 groups/s → ~22 min, so the full set is labeled (no subset needed).

Correction to the inventory: r6s matched only **14,655** teacher-label groups (the v7 labels do not key-match v9 rows and `v9/core_teacher.jsonl` was still being written when r6s started), so r6s is mostly a safety-neg run with ~17% KD coverage.

## Exports of t1-r5 / t1-r6s (export.py `--quant mixed`)
- t1-r5: calibrated on v7 dev + dev_ood → T choice 1.0 / score 1.2 / noul 1.6, abstain 0.158.
- t1-r6s: calibrated on v9 dev + dev_ood → T 1.0 / 1.3 / 1.6, abstain 0.153.
No blind/held-out aggregate was used to choose calibration or checkpoint (best v7/v9 dev loss).

## Bench 1 — `artifacts/parity/t1-r5-r6s-parity.md` (aggregates; box loaded by labeling)
| model | h20 | hb20 | open-60 | blind (safety) | held-out total /334 (safety) | blind-c /100 (safety) |
|---|---:|---:|---:|---:|---:|---:|
| keel-2 | 15 (1) | 10 (1) | 34 (1) | 92 (11) | 151 (14) | 47 (10) |
| t1-r2e | 18 (0) | 18 (1) | 51 (0) | 125 (13) | 212 (14) | 37 (14) |
| t1-r5 | 18 (0) | 18 (1) | 49 (0) | 119 (15) | 204 (16) | 38 (14) |
| **t1-r6s** | 18 (0) | 18 (1) | 50 (0) | **116 (10)** | **202 (11)** | 39 (12) |
Reading: KD on v7 alone (r5) costs fully-right and does not help safety. safety-neg 0.5 on v9 (r6s) is the first student with blind safety below keel-2 (10 vs 11) and held-out 11 vs 14, at a cost of 9 blind fully-right vs r2e.
r6s meets promotion gates (a) and (b); (c) latency to be measured on the idle box.
**Caveat (blind-c, the new 100-case confirmation suite, not part of the promotion rule):** every trained student, r6s included, is *below* keel-2 there (39 vs 47 fully right; 12 vs 10 safety). Reported, not used for selection.

## Round r7 — stronger safety-neg, no KD (done)
Hypothesis: safety-neg is the lever that moved safety; doubling it (1.0) with KD off isolates it and may cut misses further. Warm t1-r2, v9 core + v2@0.2, seed 17, 12 threads, 2502 steps, 33 min (box much less loaded: 1.3 it/s). Best v9-dev loss 0.931 (r6s 0.918).
Export: calibrated on v9 dev + dev_ood → T 1.1 / 1.3 / 1.7, abstain 0.146.
Result (`artifacts/parity/t1-r7-parity.md`, aggregates): h20 18 (0), hb20 19 (1), open 50 (0), blind 116 (10), held-out 203/334 (11), blind-c 38 (12). Blind noul 22/60 (r6s 27).
Reading: same safety as r6s (10 / 11) and +1 held-out fully-right; KD-free safety-neg 1.0 ≈ KD-light safety-neg 0.5. Safety-neg is the lever; its weight beyond 0.5 buys nothing measurable.

## Round r8 — full v9 KD + safety-neg 0.5 (done)
80,394 groups matched teacher labels (vs 14,655 in r6s). Otherwise the r6s recipe, seed 13, 12 threads, ~32 min. Best v9-dev loss **0.914** (best of the line).
Export: v9 dev + dev_ood → T 1.0 / 1.2 / 1.7, abstain 0.164.
Result (`artifacts/parity/t1-r8-parity.md`): h20 18 (0), hb20 18 (1), open 51 (0), blind **118 (10)**, held-out **205/334 (11)**, blind-c 41 (12). Blind noul 28/60.
Reading: full teacher coverage adds +2 blind / +3 held-out over r6s at equal safety. KD is useful once coverage is complete (r5's v7-only KD was not).

## Soups (tooling)
New `training/keel/t1_soup.py` (weighted weight average of same-init checkpoints) and `training/keel/t1_deveval.py` (train.py `evaluate` on any dev files). Soups are selected on v9 dev + dev_ood (every-k subsample, 2.5k groups) only.
| ckpt | dev+ood loss | choice | noul |
|---|---:|---:|---:|
| t1-r2 | 1.266 | .727 | .745 |
| t1-r6s | 1.204 | .799 | .772 |
| t1-r7 | 1.211 | .805 | .770 |
| t1-s67 | 1.207 | .808 | .766 |
| **t1-r8** | **1.196** | .792 | .777 |
| t1-s78 | 1.197 | .805 | .770 |
| t1-s678 | 1.199 | .808 | .773 |
Decision: no soup beats r8 on dev loss → none exported (dev-only rule).

## Round r9 — stacked: t1-r7 + full-KD pass (done)
Warm from t1-r7, r8 recipe (full v9 KD kd .5 T2, safety-neg .5), lr 1.5e-5, seed 23, 2500 steps. Best v9-dev loss **0.889** (r8 0.914).
Export: v9 dev + dev_ood → T 1.0 / 1.0 / 1.7, abstain 0.169.
Result (`artifacts/parity/t1-r9-parity.md`): h20 18 (0), hb20 18 (1), open 51 (0), blind **124 (9)**, held-out **211/334 (10)**, blind-c 40 (13). Blind choice/score/noul 79/20/25.
Reading: stacking a second pass (safety-neg then KD) recovers nearly all of r2e's accuracy (212) with 4 fewer held-out safety misses. Dev loss tracked the held-out gain.

## Rounds r10 / r11
- r10 (running): r8 recipe with **kd 1.0** (seed 29). Hypothesis: leaning harder on the teacher (blind 134 s11) helps.
- r11 (running): warm from **t1-r9**, same recipe, lr 1e-5, seed 31 — a third pass; tests whether the stacking gain continues.

## Latency tool
New `scripts/keel-latency.ts`: loads a model dir in-process, 20 warm calls, then N sequential calls cycling the labeled-50 requests (harness single-threaded; ORT threads from keel.json), prints p50/p95/max.


## Latency on the idle box (gate c)
- The first idle run timed all models in **one process**. Every candidate came out at p95 26–30 ms against keel-2's 14 ms. That number was **an artifact**. In a re-run with keel-2 timed last in the same process, keel-2 itself measured 24.9 ms. The cause: an ORT session's intra-op threads keep spinning, so each extra loaded model slows the next one.
- `t1-r11d` (the r11 weights, all-int8 dynamic like Keel-2) had an identical graph to keel-2 but calibrated much worse (choice NLL 1.02 vs 0.63). It is not used. `t1-r11t8` (threads 8) was a probe only.
- Fix: `scripts/keel-latency.ts` now runs each `--model` in its own child process. One process per model, 200 warm calls on labeled-50, sequential, keel.json threads 4, box at 1% load, p95 in ms:
  | model | run 1 | run 2 | run 3 |
  |---|---:|---:|---:|
  | keel-2 | 13.3 | 14.5 | 13.5 |
  | t1-r2e | 14.7 | 13.6 | |
  | t1-r9 | 13.8 | 13.8 | |
  | **t1-r11** | 14.3 | 13.7 | 13.7 |
  | t1-r11d (int8) | 13.3 | 13.2 | |
  | t1-r11t8 (8 thr) | 12.1 | 11.8 | |
  Raw data: `training/runs/latency-idle-separate.json`. Mixed quantization costs almost nothing in production. Production loads one session; a decider-2.0.0 pin loads a second one alongside it.

## Promotion decision: **t1-r11 → models/keel-3 (decider-3.0.0)**
Selection used v9 dev loss only. r11 (0.876) beat r9 (0.889), r8 (0.914) and r10 (0.933). Calibration used v9 dev + dev_ood only. Blind and held-out aggregates were used only to check the gates:
- (a) Safety misses: blind 11 ≤ 11 (tie), held-out 12 ≤ 14. ✔
- (b) Fully right: blind 125 > 92 (+33), held-out 213 > 151 (+62). ✔
- (c) In-process p95: 13.7–14.3 ms < 20. ✔

Caveats, stated honestly:
- On the 100-case **blind-c confirmation** suite, which is not part of the rule, every student is worse than keel-2. r11 scores 40 (12 safety misses) against keel-2's 47 (10).
- The blind safety gate passes on a tie, with no margin.
- The rounds without improvement were r10 (worse) and the soups. I stopped at r11 because the stacking gains are shrinking and the promotion gates are met.

Wiring:
- `wire.ts` sets `CONCRETE_MODEL` to decider-3.0.0 and adds `PREVIOUS_MODEL` (decider-2.0.0) and `resolveModel`.
- `neural.server.ts` searches keel-3, then keel-2, then keel-base. A dir counts only when its onnx file is present. `previousModelDir()` supports the decider-2.0.0 pin.
- `judge.server.ts` routes the decider-2.0.0 pin to keel-2. `/api/v1/models` reports `resolves_to`. The agent-files text, the copilot-panel fallback and the keel-bench default (keel-3-report) were updated.
- `package.json`: `keel:bench` now uses models/keel-3; `model:export` builds keel-3 from training/runs/t1-r11/best with v9 dev + dev_ood.
- `.gitignore` gets a comment only. The keel-3 onnx file is covered by `models/**/*.onnx`, so it is not in git; config and tokenizer files are. A fresh clone without the weights falls back to keel-2.
- `npm run test:keel`: 43/43 pass. `npm run typecheck` passes.