# Keel-Pro training notes

One lever per iteration. Every number is a real run on the dev sample (`EVAL.md`), recorded in `di-results.md`.
Stop rule (HANDOFF.md): dev ≥ 62 with the CI lower bound above 60.7, or two iterations without a gain.

## Setup shared by all iterations

- Trainer: `training/pro/train_lora.py` (PEFT LoRA on all linear projections of the text model, bf16, gradient
  checkpointing, AdamW, cosine schedule with warmup, length-bucketed token budget per step).
- Loss: LM loss on the gold option-key tokens (from it2, followed by `<|im_end|>`; `--no-end-token` restores the
  kit-faithful target) + `w_list` × listwise cross-entropy over the
  first token of every option at the answer position.
- Prompt: byte-identical to the DI kit's `transformers` engine (`training/pro/common.py`).
- Data: `C:\KeelWork\pro\data\train.jsonl.gz` (330,232 rows from the train splits of 24 DI benchmark sources, see
  `DATA.md`). No DI suite rows, no test/val rows.
- Throughput on the RTX 5090: 4B ≈ 4k tokens/s (compute-bound with checkpointing). Without checkpointing a 4B step
  needs about 68 GB and WDDM silently spills to system RAM, so checkpointing stays on and the trainer caps the process
  at 94% of VRAM so it fails fast instead of spilling.

## it1: Qwen3.5-4B baseline LoRA

- Config: rank 32, lr 1e-4, 64,000 rows (seeded subsample), max length 1536 tokens, 12,288 tokens/step, 1 epoch.
- Ops lessons: an orphaned profiler held 31 GB of VRAM and stalled the first relaunch. Running a DI eval concurrently
  with training stalled both, so GPU jobs now run one at a time.
- Training: 2,515 steps in 133.5 min; holdout LM loss 0.29, holdout first-token accuracy 0.657.
- Result (dev): **45.06** (CI 39.84–47.45) under kit scoring (bare key). BANKING77 and CLINC sat near chance despite
  10–15k training rows each. Cause: their keys are `option_0`…`option_76`, which tokenize digit by digit, so
  `option_1` is a prefix of `option_10`…`option_19` and the bare-key sum always favours the shorter key.
- Fix: the serving policy now scores key + `<|im_end|>` (see `SERVE.md`). Same it1 weights under end-token scoring:
  **49.70** (CI 46.09–53.59). Retrieval 27.1 → 56.0 and tools 63.4 → 71.8; language fell 55.1 → 49.0 because it1 was
  never trained to emit the end token after a key.
- Eval engine fixes found on the way: chunked prefill (SDPA fell back to a full L×L kernel on a 22k-token ToolRet row)
  and option batching sized by prompt length with halve-and-retry on OOM.

## it2: end-token targets, max length 2048

- Lever: train the gold key followed by `<|im_end|>` (matching the serving policy); raise max length to 2048 so
  API-Bank rows dropped in it1 are kept. Everything else as it1.
- Training: 2,530 steps in 127.8 min; holdout first-token accuracy 0.657 (holdout LM loss 0.171 now covers two target
  tokens, so it is not comparable with it1).
- Result (dev, end-token): **48.88** (CI 46.40–51.93), against 49.70 for it1. No gain. Benchmarks with training data
  moved up (BANKING77 +0.13, Home appliance +0.21, API-Bank +0.08, ToolRet +0.05); several benchmarks with no
  training data moved down (40, 42, 56, 25, ANLI). Swings of ±0.2 on ~40-row benchmarks are within sample noise, so
  the 4B looks capped near 49–50 with this data.
- Kept: end-token targets (they match how the model is served).

## it3: Qwen3.5-9B base

- Lever: the 9B base (more knowledge for the benchmarks the corpus does not cover). Same data, loss and end-token
  targets as it2; 48,000 rows and 8,192 tokens/step so a step fits in 32 GB (23 GB peak), ≈ 6 ex/s.
- Training: 2,785 steps in 140.5 min; holdout LM loss 0.160, holdout first-token accuracy 0.658.
- Result (dev, end-token): **54.25** (CI 49.79–57.24), +4.5 over it1/it2. Language understanding 42.7 → 62.5 is the
  main gain (ANLI proxy +0.22, benchmark 42 +0.23, benchmark 38 +0.21). Benchmark 40 moved 0 → 1.0 on a handful of
  rows, so read single-benchmark swings as noise. Median latency 154 ms (RTX 5090), p95 4.6 s on the longest prompts.
- Stock baselines (kit scoring, same dev sample): Qwen3.5-4B 7.02, Qwen3.5-9B 10.13. The fine-tune, not the base,
  carries the score.
- Kept: 9B base.

## it4: Qwen3.5-9B, twice the rows

- Lever: 96,000 training rows instead of 48,000 (same base, loss, targets, length and step size as it3).
- Stopped after 10 minutes (step 150 of 5,565), not evaluated. Its 4-hour slot went to it5: the per-benchmark
  read of it3 and the StartLux-Decision technical report (arXiv:2610.17309, whose 9B single-pass model reaches 70.45
  on the same public 0.3 subset) both point to the prompt and read-out, not row count, as the larger gap.

## it5: lettered options, one read-out position

- Lever: the **letters** policy (`training/pro/common.py`, `prompt_ids_letters`). Options are listed with
  single-token labels (A–Z, then two-letter labels that the Qwen tokenizer encodes as one token, 588 in all; DI's
  largest list has 151 options). Opaque keys (`A`, `3`, `option_7`) are hidden when a description exists, so a label
  never reads "E. A: tides". Thinking is switched off in the chat template (`<think>\n\n</think>\n\n`). The option
  distribution is the softmax over the label logits at the single answer position: no multi-token keys, so no
  prefix or length bias, and one forward pass per question. Training permutes the option order of half the rows
  (`--shuffle 0.5`) so a label carries no positional prior; evaluation and serving use the request's order.
  StartLux-Decision's prompt code (Apache-2.0) uses the same lettered read-out; ours is an independent
  implementation.
- Also changed: 96,000 rows (it4's lever, which was never evaluated alone). Same base, LoRA, length and step size
  as it3. Two levers at once, recorded honestly.
- Result: holdout first-option accuracy 0.86 (it3 0.66); **dev 52.50 (CI 49.29–55.67)**, below it3's 54.25 but
  inside its interval. Median latency fell from 154 ms to 86 ms (one forward pass per question). Areas vs it3:
  K&R 37.5 vs 34.9, LU 50.3 vs 62.5, R&C 52.8 vs 51.7, Tools 82.3 vs 79.1, Arts 41.8 vs 42.4.
  Per benchmark the largest drops were 40 iSarcasm, 38 ACOS, 12 ANLI, 44 CLadder and 61 HoVer; gains on 9, 28, 58,
  23, 56 and 30. The confusion counts behind the drops are small (iSarcasm: 3 of 6 positives found by both; it5
  said "yes" on 16 negatives vs it3's 8), so most of the LU swing is F1 over a handful of positives, not a
  systematic letters failure. Kept letters as the policy: it halves latency and the difference is inside the noise.

## it6: letters on `data2`

- Queued to start after the it5 eval (`C:\KeelWork\tools\it6_queue.ps1`, log `C:\KeelWork\logs\it6.log`).
- Lever: the data. `data2` adds the synthetic families in `DATA.md` (56 PhishNChips, 22 POP909 chords, 33 SATA,
  32 MuSR, 39 FinEntity, 23 color preference) to the it5 corpus. 120,000 rows sampled uniformly, `--max-len 6144` so chord prompts fit. Same base,
  LoRA, read-out and step size as it5.
- Result: **failed** at step 50 with CUDA out of memory (a 6,144-token chord batch on the 9B, 27.6 GB before the
  spike). Not evaluated. Rather than rerun it at a shorter length, the slot went to it7, which tests the base size.

## it7: Qwen3.5-27B, QLoRA

- Lever: base size. Qwen3.5-27B (Apache-2.0) in 4-bit NF4 with double quantization and bf16 compute
  (`train_lora.py --qlora`); LoRA r32 on the same modules. `data2`, 48,000 rows (it3's count), `--max-len 4096`,
  `--tokens 4096`, letters with `--shuffle 0.5`, lr 1e-4. 23.6 GB peak, 1.9 ex/s (≈7 h).
- A 776-row smoke run first checked the QLoRA trainer and the 4-bit eval path (`eval_model.py --load-4bit
  --adapter`). On the same 60 dev rows the 4-bit 27B took 4.0× the 9B's wall time.
- Attempt 1 (00:00–04:12) crashed with CUDA OOM at step ~4,000 of 5,096, right after the step-4,000 holdout pass
  (holdout first-option accuracy 0.826 / 0.845 / 0.848 / 0.872 at steps 1k–4k; it5's 9B ended at 0.861). The
  trainer saved nothing before the end, so the run was lost. Fixes in `train_lora.py`: the adapter is saved at every
  holdout step, the CUDA cache is emptied after the holdout pass, a batch that runs out of memory is skipped and
  logged (`oom_skip`, at most 50) instead of ending the run, and `--init-adapter` + `--start-step` resume a crashed
  run. Attempt 2 restarted the identical configuration at 04:26.
- Attempt 2 (04:26–11:07, 399 min) finished all 5,096 steps with no OOM skip. Holdout first-option accuracy
  0.827 / 0.845 / 0.848 / 0.872 / 0.877 at steps 1k–5k, 0.874 final (attempt 1 matched to three decimals).
- Result: **dev 60.32 (CI 55.09–62.68)**, +6.1 over it3 and 0.4 below Jev 1.14's 60.70. Median latency 319 ms
  (RTX 5090, 4-bit base + adapter), p95 11.8 s (ContractNLI and other long states). Areas: K&R 46.2, LU 64.3,
  R&C 59.1, Tools 86.2, Arts 41.9. The base size helped reasoning most (GPQA 0.27 → 0.40, CRUXEval 0.31 → 0.59).
- Gap found after the run: at `--max-len 4096` the trainer dropped every API-Bank row (benchmark 3, 814 of 814;
  they are 5,700–6,900 tokens because the state carries the tool catalog) and 711 of 715 POP909 chord rows
  (benchmark 22, 3,700–6,200 tokens). API-Bank still scored 0.90 from transfer; chords scored 0.02.

### it7 + TTA-2 (stopped early, 2026-11-01)
- Two option orders per question, averaged. Stopped after 1,049 of 1,633 dev rows to free the GPU.
- Score with the finished TTA rows and the original it7 answers for the rest: **59.83**, against 60.32 without TTA. TTA does not help, so it is dropped.

### it8 prep: long chord rows run out of memory
- Smoke test (27B, max-len 5120, paged-adamw8bit): every chord row of 4,500–5,100 tokens ran out of memory at a 1.9–2.3 GB allocation (base ~17.3 GB allocated). Rows ≤4,096 train fine.
- Switching attention to sdpa (new `--attn` flag, default sdpa) did not change it. Now tracing which buffer grows with the square of the row length.
- **Root cause found and fixed:** transformers calls SDPA with `enable_gqa=True`. With head_dim 256 on Windows there is no flash kernel, and the memory-efficient kernel does not support GQA, so torch fell back to the math path. That path materializes fp32 scores of size heads × seq × seq: 98 bytes × L², ~2.2 GB at 4,900 tokens. The trainer now repeats K/V instead (`use_gqa_in_sdpa → False`). Peak at 5,120 tokens: 29.9 → **23.4 GB**, and the smoke test had no OOM skips (22.6 GB).

### it8 (launched 2026-11-01 14:20)
- Continues from the it7 adapter on fresh rows: `--skip-sample 20261101:48000 --max-rows 16000 --extra-bench 22:1000,23:800,31:1500,33:1200 --max-len 5120 --tokens 5120 --lr 5e-5 --warmup 50 --seed 20261102 --optim paged-adamw8bit --qlora --letters --shuffle 0.5`.
- 19,791 examples, 11.24M tokens, 2,548 steps. 709 rows over 5,120 tokens skipped (mostly API-Bank).
- Why: chords (22, 0.017), cfcolor (23, 0.09), ChessBench (31, 0.15) and SATA (33, 0.09) are the weakest benchmarks. The chord rows never reached it7 because of the 4,096-token cap.
- **it8 result:** training 250 min, 0 OOM skips, holdout first-option accuracy 0.881 (it7 0.874), holdout LM 0.383. **Dev 59.61 (CI 56.52–62.33)**, median latency 320 ms.
  - Areas, it7 → it8: K&R 46.2 → 45.3, LU 64.3 → 57.6, R&C 59.1 → 59.4, Tools 86.2 → 84.8, **Arts 41.9 → 56.1**.
  - Big moves: POP909 chords 0.017 → **0.849** (the long rows now train), cfcolor 0.03 → 0.18, CLadder +0.10; **iSarcasmEval 1.0 → 0.0**, Humicroedit −0.20, SATA −0.13, CRUXEval −0.12.
  - The iSarcasmEval swing is **one tweet**. The dev headline track (A-En, positive-class F1) has 13 rows with a single sarcastic one: it7 p(yes)=0.89, it8 0.44. That one row moves the index by ~1.7 points. The dev sample cannot separate it7 and it8 reliably.
- **soup78:** an exact average of the it7 and it8 adapters (PEFT `cat`, 0.5/0.5, rank 64; delta check rel. error ~1e-3). It aims to keep it7's language and it8's chords in one model. Script: `training/pro/soup_adapters.py`. Dev eval running.
- **soup78 result: dev 62.06 (CI 56.63–64.13)**, median 321 ms, p95 11.9 s. Areas: K&R 44.9, LU 67.3, R&C 60.6, Tools 85.0, Arts 54.0. Chords 0.849, iSarcasmEval 1.0, GSM8K 0.76.
  - **Finalist: soup78.** It is the best of the dev candidates (it7 60.32, it8 59.61, soup78 62.06); three candidates were compared on dev.
  - The CI lower bound (56.6) is well below Jev's 60.70. Like every number here, the dev sample cannot prove that Keel-Pro beats Jev. The report sample (scored once, below) is the number we publish.
- **soup78 GGUF:** merged (merge_shards.py) → bf16 GGUF → Q8_0 29.0 GB, Q4_K_M 16.8 GB. Fidelity vs the soup78 dev run: Q4_K_M 30/30 (CPU median 15.5 s), Q8_0 30/30 (CPU median 15.4 s; the CPU was shared with the report eval).
- **Report eval** (soup78, 3,272 rows, scored once, 115 min): **61.96 (CI 58.98–64.42)**, median 329 ms, p95 11.0 s.
  Areas: knowledge 0.480, language 0.625, retrieval 0.612, tools 0.817, arts 0.621. The report and dev numbers agree
  (61.96 vs 62.06), so the dev selection did not overfit. 61.96 is above Jev 1.14's 60.70 and level with the MSD1 ≈62
  estimate; both lie inside the CI, so we claim parity, not a win.
- **GGUF on GPU:** the first CUDA llama-server timing (12.6 s for 482 tokens) was wrong. Stale CPU llama-server processes
  were still bound to the same port, so the requests never reached the GPU server. On a clean run (`-ngl 99 -np 1
  -c 8192`): Q8_0 30/30, median 243 ms; Q4_K_M 30/30, median 242 ms. That is as fast as the transformers path.
- **Board latency rule (median, mean, p80 ≤ 1 s per request).** The report run failed it: mean 2,082 ms, p80 2,232 ms.
  Cause: multi-question requests (ContractNLI 17 questions, ACOS 59, BRIGHT/ToolRet 32) re-ran the whole shared
  state for each question. Fixes in `scripts/di/hybrid_engine.py`:
  1. Shared-prefix scoring (`prefix_share=1`): run the token prefix all prompts share once; continue right-padded
     suffix batches from copies of that cache (`_repeat_cache`); read each row's last real position with
     `logits_to_keep=<positions>`. Causal attention plus forward-only linear attention means padding never
     reaches a read position.
  2. Suffixes sorted by length; a batch closes at 25% padding (retrieval candidates range 89–660 tokens).
  3. SDPA GQA patch (as in training): repeat K/V so the efficient kernel is used.
  Prefill is compute-bound at ~2.5k tok/s (NF4 + unmerged LoRA), so total tokens per request is what counts.
  Report sample, RTX 5090: **median 316 ms, mean 844 ms, p80 847 ms** (p95 3.1 s); 46 min instead of 114.
  Agreement with the report run: 17,150 / 17,182 answers. Scoring the same run gives **61.66 (CI 58.83–64.28)**. It is
  a second engine, not a second selection, so both numbers are reported. The sidecar (`serve/keel_pro_server.py`)
  got the same batched path: ContractNLI row 8.7 s → 1.4 s, 17/17 same answers.
- **GGUF engine** (`scripts/di/gguf_engine.py`, llama-server Q8_0): 68-row multi-question subset agrees on 1,952 / 1,974
  answers. llama.cpp's prompt cache reuses the prefix (~152 tokens evaluated per question), but questions go one call
  at a time (~140 ms each), so many-question requests are slower than the batched transformers engine (ContractNLI
  7.7 s vs 1.8 s). Use GGUF for single questions; use the transformers engine for the board.
