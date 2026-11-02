# Design doc

Why Keel is a tiny local cross-encoder, how it turns typed questions into calibrated answers, how it is meant to be combined with an LLM, and what is still open. This covers Keel-2 (shipped) and the Keel-3 line (in training). For the moving parts and file map, see [Architecture](architecture.md).

## Problem

Agents make many small, typed decisions: edit, ask or stop; which tool or sub-agent; how severe; is this command safe; does this answer match the reference. Asking an LLM each time costs tokens and seconds, sends context to a third party, and returns free text that has to be parsed. Hosted decision models (TypeSafe Jev, Microsoft-Decision-1) fix the format and cut latency, but are still network calls billed per token.

Keel's job is narrow: read the supplied state, answer typed questions with probabilities, on the local CPU, with the same wire format as those hosted models. It does not write code or prose and does not look anything up.

## Goals and non-goals

| Goal | Target |
|---|---|
| Wire compatibility | Accept Jev and MSD1 requests (`choice`, `score`, `noul`) and return the same answer shapes |
| Offline | No network on the decision path; `usage` is always zero tokens |
| Fast | Warm in-process decisions in tens of milliseconds on a laptop CPU, no GPU |
| Small and open | Tens of MB, Apache-2.0, fine-tunable on a CPU |
| Honest | Report suites the model never saw; label vendor figures; write "not measured" where we could not measure |
| Composable | Calibrated confidence so callers can send uncertain cases to an LLM |

Non-goals: generating text, world-knowledge questions, long documents, images, multi-tenant billing, or replacing human review of destructive actions.

## Key decision: an NLI cross-encoder, not a small LLM

Every question becomes a set of natural-language hypotheses, one per option. A cross-encoder reads the state and one hypothesis together and outputs an entailment margin; the margins over a question's options become its probabilities. This gives a semantic judge that is small enough to run in-process, deterministic, and naturally calibrated per option.

| Alternative | Why not (for the default model) |
|---|---|
| Lexical rules only (Keel-1) | Kept as fallback and `decider-1.x` pin, but misses paraphrases |
| Small generative LLM | Hundreds of MB to GBs, slower, needs output parsing, harder to calibrate |
| LLM judge | Seconds per call, token-billed, not local |
| DeBERTa-v3-xsmall (70M) | More accurate; became the retired Keel-Pro DeBERTa line, but several times slower (<!-- num:pro.blind.lat -->117 / 242 ms<!-- /num --> p50 / p95 on blind) |
| MiniLM-L6-H768, ModernBERT | Measured around 110 ms and 350 ms on the CPU path |
| **xtremedistil-L6-H256 (13M)** | **Chosen**: compact int8 ONNX (<!-- num:k3.size -->17.7 MB<!-- /num --> for Keel-3, <!-- num:k2.size -->13 MB<!-- /num --> for Keel-2), <!-- num:k3.p95.idle -->13.7–14.3 ms<!-- /num --> p95 warm decision |

## Hypothesis formulation

TypeScript and Python mirror each other exactly (`src/lib/decider/hypothesis.ts`, `training/keel/hypothesis.py`), and parity fixtures check it.

```text
`${instructions} Answer: ${answer}.` + optional ` ${detail}`
```

For `choice`, each option key becomes readable text plus its description. For `score`, each ordered level is a hypothesis. For `noul`, the pair is always yes and no.

## Training objective

Training rows are groups of (state, hypothesis) pairs. The margin is `logit(entailment) - logit(not_entailment)`, identical to the runtime.

- **Keel-2:** listwise cross-entropy over each group plus 0.5 × pointwise BCE, on synthetic decision families (data v1 and v2), about 60 CPU minutes.
- **Keel-3 line:** the same base objective plus an ordinal loss for score questions, a pointwise yes/no term against the "no" bias, label smoothing, option shuffling, hard negatives and EMA weights. Data: synthetic families v3 (60 families including sentiment, PII, intent, moderation and injected-text cases), a subsample of public training splits ([Licenses](licenses.md)) and a replay of v2. The best candidate, `t1-r2e`, trained for <!-- num:k3.train.steps -->2,723 steps in 49.7 CPU minutes<!-- /num -->.
- **Distillation:** the 70M teacher `t2-dxs-b3` produced soft labels for 35k groups, used by later 13M runs.

## Calibration, abstention and fallback

Export fits a temperature per question type on a development set, using the quantised ONNX graph that Node serves. At runtime Keel applies that temperature, an optional lexical blend, ordinal smoothing for scores, and an abstain threshold that pulls a group towards uniform when no hypothesis is entailed. The result is a confidence you can gate on: blind-suite calibration error fell from <!-- num:k2.ece.blind -->0.182<!-- /num --> (Keel-2) to <!-- num:k3.ece.blind -->0.108<!-- /num --> (Keel-3 RC).

If the neural model fails to load, Keel falls back to the lexical judge and says so in `status` and in each response's `model` field.

## The hybrid: Keel first, LLM fallback

<!-- diagram:tau-gate -->

Keel is not meant to be the last word on hard cases. The intended deployment puts Keel in front of the LLM call an agent would otherwise make: if Keel's confidence is at least τ, act on it; otherwise ask the LLM. Because Keel is calibrated, raising τ trades tokens for accuracy smoothly. Measured on the held-out suites at τ = 0.6 with the Keel-3 RC, this avoided <!-- num:tok.k3.ho.avoided -->75/100<!-- /num --> LLM calls, cut LLM tokens by <!-- num:tok.k3.ho.cut -->75.8%<!-- /num --> and raised accuracy (<!-- num:tok.k3.ho.acc -->75 → 89 of 100 cases fully right<!-- /num -->). On the harder blind suite it cut <!-- num:tok.k3.blind.cut -->44.9%<!-- /num --> for <!-- num:tok.k3.blind.acc -->64/71 → 63/71 (−1.4 pts)<!-- /num -->. See [Token savings](token-savings.md).

## Runtime policy

`parse → switch check → rate limit → neural judge → lexical fallback → project weights → response`

- Switch off: `409`, no scoring.
- Rate limit: 120 decisions per 60 s per process, `429`.
- Auth: bearer token on `/api/v1/systemone` and `/api/v1/switch`; `api-key` header on the MSD1 route. The token is an HMAC of `KEEL_SECRET` or of a random per-install secret in `~/.keel/secret`, so no two installs share one. The server binds `127.0.0.1` by default (`KEEL_HOST` opts in to other interfaces).
- State bodies are not logged.

## Evaluation methodology

| Suite | Size | Trained on? | Role |
|---|---|---|---|
| labeled-50 | 50 | Yes | Regression only |
| holdout-20, holdout-b-20, open-60 | 100 | No | Held-out 100, comparable with the earlier LLM A/B |
| blind | 234 | No, and trainers may not open it | Main quality number; written by a separate author, tagged by use case |
| Public benchmarks | Up to 1,000 items per dataset | Partly (some train splits) | Reported honestly, including losses ([Benchmarks](benchmarks.md)) |

Results today (cases fully right):

| Model | Held-out 100 | Blind 234 | Blind safety misses |
|---|---|---|---|
| Lexical (Keel-1) | <!-- num:lex.h100 -->42/100<!-- /num --> | <!-- num:lex.blind -->87/234<!-- /num --> | <!-- num:lex.blind.safety -->22<!-- /num --> |
| Keel-2 | <!-- num:k2.h100 -->59/100<!-- /num --> | <!-- num:k2.blind -->92/234<!-- /num --> | <!-- num:k2.blind.safety -->11<!-- /num --> |
| Keel-3 `t1-r11` (default) | <!-- num:k3.h100 -->88/100<!-- /num --> | <!-- num:k3.blind -->125/234<!-- /num --> | <!-- num:k3.blind.safety -->11<!-- /num --> |
| Keel-Pro DeBERTa `t2-dxs-b3` (retired) | <!-- num:pro.h100 -->85/100<!-- /num --> | <!-- num:pro.blind -->134/234<!-- /num --> | <!-- num:pro.blind.safety -->11<!-- /num --> |
| LLM (gpt-5-mini held-out; claude-haiku-4.5 blind) | <!-- num:llm.h100 -->75/100<!-- /num --> | <!-- num:llm.blind -->215/234<!-- /num --> | <!-- num:llm.blind.safety -->0<!-- /num --> |

## Comparison policy

Keel may claim local execution, latency, zero marginal cost, privacy, open weights and wire compatibility. It must not claim accuracy parity with Jev or Microsoft-Decision-1: neither was measured live (no credentials). Vendor figures are quoted only as vendor-reported, with sources, in [Comparison](comparison.md).

## Risks

| Risk | Mitigation |
|---|---|
| Safety misses on unseen cases | Release gate G1; document that Keel can tighten but never solely approve destructive actions |
| Overconfidence off-distribution | Calibration per type, abstain threshold, τ gate to an LLM |
| Silent lexical fallback | `status` exposes `engine` and `neural.*`; responses name the judge |
| Contamination of held-out suites | Trainers may not open the blind suite; overlap checks on public data |
| Leaked or shared token | Random per-install secret (`~/.keel/secret`, mode 0600) or `KEEL_SECRET`; loopback bind by default; repo agent files hold only `<KEEL_TOKEN>`; rotate by deleting the secret file |
| Upstream data licences | Maintainer review of CC BY-SA and ANLI lineage ([Licenses](licenses.md)) |

## Roadmap

- Keel-3 was promoted under the round-2 rule; next, close the blind-c regression and reach the contract gates G1 and G2 ([Release notes](release-notes.md#release-gates)).
- Close the safety gap with targeted data and distillation from the 70M teacher.
- A faster Pro variant (6-layer pruned teacher with distillation).
- Multilingual coverage once English quality stabilises.
