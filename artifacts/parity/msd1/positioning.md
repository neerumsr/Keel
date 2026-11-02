# Keel vs Jev vs MSD1: positioning

Owner: msd1-3. Status: research snapshot, 2026-10. All Jev and MSD1 numbers are **vendor-reported** unless marked otherwise. We have **not** run a live head-to-head: no TypeSafe key and no Foundry deployment were available, so no Jev or MSD1 accuracy number here is measured by us. Keel numbers come from our own small suites (`docs/model-card.md`, `docs/why-keel.md`) and carry about ±10–15 pp of noise.

## 1. What each one is

| | **Keel-2** (`decider-2.0.0`) | **Jev** (TypeSafe System One, `jev-1.14.0`) | **MSD1** (Microsoft-Decision-1) |
|---|---|---|---|
| Builder | This repo (open source) | TypeSafe ([intro](https://typesafe.ai/blog/introducing-system-one-models-and-jev)) | Microsoft Office of the CTO ([announcement](https://commandline.microsoft.com/microsoft-decision-1-model-foundry/)) |
| Base | `xtremedistil-l6-h256-zeroshot` NLI cross-encoder | Proprietary "new architecture" with a "parallel sampler" ([models](https://docs.typesafe.ai/models)) | Qwen3.5-9B, post-trained ([Learn](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision), [MarkTechPost](https://www.marktechpost.com/2026/10/09/microsoft-ai-releases-microsoft-decision-1-a-qwen3-5-9b-decision-scoring-model/)) |
| Size | ~13M params, ~13 MB ONNX int8 | Undisclosed | ~9B (exact count undisclosed) |
| Calibration approach | Each option is scored as an independent (state, hypothesis) pair; listwise CE + 0.5 pointwise BCE; per-type temperatures in `keel.json`; optional lexical blend; optional KD | "RLCD" (RL for calibrated decisions), per the TypeSafe primer ([primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md)). Evaluated against GPT-6 Astra + Fable 5.1 averaged reference probabilities | Single pass, one calibrated probability per option. **Loss, head and data mix not disclosed.** Training data is public datasets plus synthetic data |
| Order invariance | By construction (options scored independently) | Not stated | Vendor-reported 0 flips on option paraphrase/reverse/shuffle; 1.3% flips across 8 perturbations |
| Hardware | Any CPU (onnxruntime-node); no GPU | Hosted; undisclosed | Hosted on Azure; undisclosed |
| Weights | **Open, MIT** (inherits the MIT license of the base) | Closed; same weights for every customer; not fine-tunable | **Closed.** No download and no quantized builds, even though the Qwen3.5 base is Apache-2.0. OpenRouter notes the weights update continually |
| Availability | Local HTTP (`/api/v1/systemone`), MCP server (`mcp/keel-mcp-server.mjs`) | TypeSafe API, `typesafe_sdk` / `@typesafe-ai/sdk` | Azure AI Foundry (`<endpoint>/providers/microsoft/v1/systemone`; Entra or `api-key`) and OpenRouter Decisions API ([OpenRouter](https://openrouter.ai/microsoft/microsoft-decision-1)) |
| Wire | System One (`state`, `questions` with choice/score/noul) | System One (origin) | System One-compatible; `model` is the Foundry deployment name |
| Context | `state` ≤ 8000 chars on the wire, but **the model reads only 256 tokens** per (state, hypothesis) pair; longer states are truncated | 64k per request / 32k per question; 262k with the `TypeSafe-Danger-Zone-Long-Context` header | 32,768 tokens |
| Languages | English only (English synthetic data and English base) | English is best; other languages are "less good" | Multilingual set evaluated; no explicit support list |
| Rationales | None | None | None ("no rationales") |
| Latency | **p50 6–12 ms in-process, ~31 ms warm HTTP** (measured by us on a laptop CPU) | 70–500 ms from the US West Coast (vendor) | p50 85 ms / p95 125 ms (vendor); "35× faster than GPT-6 Sol" (3.01 s) |
| Privacy | Fully offline; state never leaves the machine | Cloud; no training on customer data; ZDR for enterprise | Cloud (Azure data-zone / global deployments) |
| Price | $0 marginal (your CPU) | $0.042 / 1M input tokens; output free | $0.042 / 1M input tokens; output free |

### Accuracy, honestly

| | Claim | Who measured |
|---|---|---|
| MSD1 | 83.5% mean over 36 benchmarks / 147,137 questions; calibration score 92.2 | Microsoft (vendor) |
| Jev 1.13.0 | 82.3% on the same Microsoft table | Microsoft (competitor-reported) |
| Jev (own) | "193.6× faster / 444.6× cheaper" on workflow evals, scored relative to frontier reference probabilities, not ground truth | TypeSafe (vendor) |
| Third party | Benchmark Heaven JevBench composite: H2O-Lightning-4B 75.98, Liquid d1 72.82, MSD1 69.08, OpenAI Decisions 62.37. H2O disputes JevBench's "adjusted median" latency (it doubles the measured time and adds 0.15 s) | Benchmark Heaven / H2O ([H2O card](https://huggingface.co/h2oai/h2o-lightning-4b)) |
| Keel-2 | Held-out 100: 59/100 alone, 69/100 gated at τ 0.6, vs 75/100 for an LLM-only baseline (gpt-5-mini). holdout-b-20 choice 8/15. Small suites written by the same author | Us |

**There is no evidence yet that Keel matches Jev or MSD1 on accuracy.** On open-domain breadth, Keel-2 is almost certainly behind both: it has 13M params versus about 9B for MSD1 and an undisclosed size for Jev. The CONTRACT parity gates are what will settle this; this document does not.

Critiques of MSD1 from the press: it is a closed derivative of an Apache-2.0 open model, every benchmark is vendor-run, and it is built on a Chinese-lab base, which raises geopolitical questions. Sources: [TNW](https://thenextweb.com/news/microsoft-decision-1-qwen-decision-model), [The Register](https://www.theregister.com/ai-and-ml/2026/10/10/microsoft-leans-on-open-weight-model-from-chinese-ai-lab-to-challenge-jev/5302473), [dev.to](https://dev.to/techpulse01239/microsoft-launches-decision-1-fast-decision-scoring-model-built-on-qwen35-9b-1lom), [Tech Insider](https://tech-insider.org/microsoft-decision-1-ai-model-35x-speed-2026/). Microsoft's own docs say the scores are best used for relative ordering and thresholds.

## 2. Cost per 1M decisions

**Assumption.** One decision is one request. The request averages **654 input tokens**, which is H2O's measured mean on JevBench ([H2O card](https://huggingface.co/h2oai/h2o-lightning-4b)). We show 300 and 2,000 tokens as sensitivity cases. Output is free for both Jev and MSD1, so only input tokens count.

```
hosted cost / 1M decisions = tokens_per_decision × 1,000,000 × price_per_token
price_per_token (Jev, MSD1) = $0.042 / 1,000,000 = $4.2e-8

 300 tok:   300 × 1e6 × 4.2e-8 = $12.60
 654 tok:   654 × 1e6 × 4.2e-8 = $27.47
2000 tok:  2000 × 1e6 × 4.2e-8 = $84.00
(GPT-6 Luna Decisions at $0.10/M input, 654 tok: $65.40)
```

Keel has no per-token price. Its cost is compute you already own:

```
CPU time = 1e6 decisions × ~10 ms = 10,000 s ≈ 2.8 CPU-hours (single thread, measured p50 6–12 ms)
electricity (assume 15 W extra package power, $0.15/kWh):
  2.8 h × 0.015 kW × $0.15 ≈ $0.006
rented vCPU instead (assume $0.05 / vCPU-hour): 2.8 × $0.05 ≈ $0.14
```

| Per 1M decisions (654 tok) | Keel-2 | Jev | MSD1 |
|---|---|---|---|
| Cash | ≈ $0.01–0.14 (assumed power or vCPU) | **$27.47** | **$27.47** |
| Wall time at 1 req in flight | ~3 h (10 ms) | ~19–139 h (70–500 ms) | ~24 h (85 ms p50) |

The cost gap is about 200–4,000×, but it is small in absolute terms: $27 per million is cheap. Keel's real advantages are **offline operation, privacy, and having no account or key**, not the bill. Caveat: Keel reads only 256 tokens, so on a 2,000-token state it is reading a truncated input, not doing the same work as a 32k–64k model.

## 3. Integration surface

| Client | Keel | Jev | MSD1 |
|---|---|---|---|
| GitHub Copilot CLI | MCP server + `~/.copilot/agents/keel.agent.md` + custom instructions (shipped) | HTTP from instructions / custom MCP | HTTP via Foundry key / custom MCP |
| VS Code Copilot agent mode | MCP (`.vscode/mcp.json` or `.mcp.json`) + `.github/agents/keel.agent.md` | Same pattern, cloud key | Same pattern, Azure auth |
| Claude Code | MCP (`claude mcp add`), `CLAUDE.md`, subagent | Same pattern | Same pattern |
| Codex CLI | MCP (`~/.codex/config.toml`), `AGENTS.md` | Same pattern | Same pattern |
| Cursor | MCP (`.cursor/mcp.json`) | Same pattern | Same pattern |
| Needs network/key | **No** (localhost bearer only) | Yes (TypeSafe key) | Yes (Entra or `api-key`) |

None of the three vendors ships an official MCP server that we could find. Keel now has one (`mcp/keel-mcp-server.mjs`, smoke-tested); see `integrations.md`. Because the wire is shared, the same MCP server could target Jev or MSD1 by changing `KEEL_URL` and the auth header. That is a small follow-up and is not implemented: MSD1 uses `api-key` or Entra, and its path differs.

## 4. Where each wins

**Keel wins on:**
- Offline, air-gapped and privacy-sensitive use. Nothing leaves the machine.
- Latency. It is about 10× faster than MSD1's vendor p50 and 7–50× faster than Jev's range, with no network jitter.
- Open MIT weights you can fine-tune on your own decision families. Jev forbids fine-tuning, and MSD1 ships no weights.
- Zero marginal cost and no account. It suits high-volume, low-stakes gating, such as an agent's inner-loop "edit / ask / stop" decisions.
- Order invariance, which is guaranteed by its architecture rather than measured.

**Jev wins on:**
- Breadth and accuracy. It is vendor-reported at about 82% on Microsoft's table; Keel is not comparable yet.
- Long context: 64k, up to 262k.
- Calibration designed in through RLCD.
- A mature SDK and a stable versioned API.

**MSD1 wins on:**
- Top vendor-reported accuracy (83.5% over 36 benchmarks) and published robustness numbers.
- 32k context.
- A multilingual evaluation.
- Azure enterprise posture: data zones, Entra, Foundry governance.
- Being the same price as Jev at a lower vendor p50.

**Where none of them wins yet:**
- Independent evaluation. All accuracy claims are self-run, and third-party JevBench rankings disagree with the vendors' own tables.

**Recommended positioning for Keel's open-source release:**
- Call it "the local, open-weight System One-compatible decider".
- Use it as a first-pass gate that answers confidently in about 10 ms and escalates low-confidence or high-risk questions to a hosted judge (Jev/MSD1) or an LLM. This is the τ-gated design measured in `docs/why-keel.md`.
- Do not claim accuracy parity until the CONTRACT gates pass.
