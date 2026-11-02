# FAQ

## The basics

### What is Keel?

A small, open-weight decision model that runs on your own machine. You give it a situation (`state`) and one or more typed questions (`choice`, `score` or yes/no `noul`), and it returns calibrated probabilities in milliseconds. It speaks the same wire format as TypeSafe Jev and Microsoft-Decision-1 (MSD1), so their clients work against it unchanged. See [Concepts](concepts.md).

### Why not just ask my LLM?

You can, and for hard or open-ended decisions you should. But most of the decisions an agent makes all day (edit or ask, which tool, how severe, is this safe) are short and repetitive. Sending each one to an LLM costs tokens, adds seconds of latency and sends your context to a third party. Keel answers the easy ones locally and lets the LLM handle only the uncertain ones. On the held-out suites that hybrid cut LLM tokens by <!-- num:tok.k3.ho.cut -->75.8%<!-- /num --> while getting more cases right (<!-- num:tok.k3.ho.acc -->75 → 89 of 100 cases fully right<!-- /num -->). See [Token savings](token-savings.md).

### Is it really offline?

Yes. The decision path is an ONNX model running in-process with `onnxruntime`. Nothing leaves your machine. The Keel-3 and Keel-2 weights ship in the repository; the only optional network step is `npm run model:fetch`, which downloads the zero-shot base model once.

### How big is it, and how fast?

The default Keel-3 model is <!-- num:k3.size -->17.7 MB<!-- /num -->; the pinnable Keel-2 is <!-- num:k2.size -->13 MB<!-- /num -->. On an idle laptop CPU, Keel-3 answers in <!-- num:k3.p95.idle -->13.7–14.3 ms<!-- /num --> at p95, in-process and warm. No GPU is needed.

### What does it cost?

Nothing per call. There is no API key to buy and no metering; the `usage` block in every response reports zero tokens.

### What licence is it under?

Apache-2.0 for the code and the fine-tuned weights. Some upstream training data needs a maintainer decision before release; see [Licenses](licenses.md).

## Accuracy and limits

### How accurate is it compared with an LLM?

Lower, and the docs say so plainly. On the 234-case blind suite, which no model was trained on, Keel-3 got <!-- num:k3.blind -->125/234<!-- /num --> fully right, versus <!-- num:llm.blind -->215/234<!-- /num --> for claude-haiku-4.5. The LLM took <!-- num:llm.blind.lat -->55.7 / 93.1 s<!-- /num --> p50 / p95 per case through its CLI, against milliseconds for Keel. That gap is why Keel is designed to sit in front of an LLM, not to replace it. Full tables are in [Benchmarks](benchmarks.md).

### When should I not use Keel on its own?

- Decisions that need world knowledge, multi-step reasoning or reading long documents. Keel reads about 256 tokens per (state, option) pair.
- Safety-critical approvals. On the blind suite Keel-3 still made <!-- num:k3.blind.safety -->11<!-- /num --> safety misses (the LLM made <!-- num:llm.blind.safety -->0<!-- /num -->). Use Keel to tighten a gate or to route to a human, never as the only check before a destructive action.
- Decision families far from anything it was trained on. Measure first with your own examples, then fine-tune ([Training guide](training-guide.md)).

### What is the τ gate?

A confidence threshold. If Keel's confidence for a question is at least τ, you act on its answer; otherwise you ask the LLM. τ = 0.6 is a good default. Higher τ sends more to the LLM, raising accuracy and cost. See [Concepts](concepts.md#the-τ-gate-keel-first-llm-fallback) and the τ sweep in [Token savings](token-savings.md).

### Is the confidence calibrated?

Reasonably. Keel-3's expected calibration error on the blind suite is <!-- num:k3.ece.blind -->0.108<!-- /num -->, down from <!-- num:k2.ece.blind -->0.182<!-- /num --> for Keel-2 and close to the LLM's <!-- num:llm.ece.blind -->0.080<!-- /num -->. Lower is better.

### How does it compare with Jev and MSD1?

Keel is wire-compatible with both, runs locally and costs nothing per call. Their quality was **not measured** here because no credentials were available; the only figures we show for them are vendor-reported and labelled as such (for example, MSD1 reports a p50 of 85 ms and 83.5% average across 36 undisclosed benchmarks). A hosted 9B-class model will generally beat a 13M local model on hard, knowledge-heavy questions. See [Comparison](comparison.md).

## Using it

### How do I get my token?

Run `npm run keel:token`; it prints the bearer token for your install. The token is an HMAC of `KEEL_SECRET`, or, when that is unset, of a random secret Keel generates on first use and keeps in `~/.keel/secret` (mode 0600). Each install therefore has its own token, and nothing in the source can reproduce it. The bench UI's Copilot tab also shows it to requests from your own machine, and `npm run keel:agents` writes it into your user-level Copilot files. These docs always write it as `<KEEL_TOKEN>`.

### How do I rotate my token?

Delete `~/.keel/secret` (or change `KEEL_SECRET`), restart `npm run dev`, then rerun `npm run keel:agents` and update any MCP or client config that stores the token. The old token stops working immediately.

### Is it safe to commit the files `npm run keel:agents` writes?

Yes, by default. The repo copies, `.github/agents/keel.agent.md` and `.github/copilot-instructions.md`, contain a `<KEEL_TOKEN>` placeholder. The real token goes only to `~/.copilot/agents/keel.agent.md` and the Keel block of `~/.copilot/copilot-instructions.md`. Only `--repo-key` puts the real token in the repo; do not commit that output.

### Which agents does it work with?

Anything that can call an MCP server or an HTTP endpoint. [Integrations](integrations.md) has copy-paste configs for GitHub Copilot CLI, VS Code Copilot, Claude Code, OpenAI Codex CLI and Cursor, using the bundled MCP server (`keel-mcp`), plus plain HTTP.

### Can I use the Jev or MSD1 SDK?

Yes. Point the SDK's base URL at your local Keel and pass your Keel token as the API key. The MSD1 path is `/providers/microsoft/v1/systemone`. See [Quickstart](quickstart.md#5-drop-in-for-the-typesafe-jev-sdk) and [API reference](api-reference.md).

### What is the on/off switch?

A shared flag that agents and the Keel app both read. When it is off, `/api/v1/systemone` returns HTTP 409 and agents fall back to their own judgement. Say "Keel on" or "Keel off" to an agent that has the integration, or `POST /api/v1/switch`.

### Are answers deterministic?

Yes. The same request on the same model returns the same probabilities. There is no sampling.

### Does it support images or other languages?

No images. The model is English-first; other languages are not evaluated and will be weaker.

## Training and models

### Can I fine-tune it on my own decisions?

Yes, on a CPU. The `t1-r2` pass in the Keel-3 line trained for <!-- num:k3.train.steps -->2,723 steps in 49.7 CPU minutes<!-- /num -->. A few hundred labelled examples per decision family is a useful start. See [Training guide](training-guide.md).

### What is Keel-3, and is it released?

Yes. Keel-3 (`decider-3.0.0`, training run `t1-r11`) is the default model; `decider-latest`, the `jev-*` aliases and the MSD1 aliases resolve to it. It beats Keel-2 on the suites that decided promotion (h100 <!-- num:k2.h100 -->59/100<!-- /num --> → <!-- num:k3.h100 -->88/100<!-- /num -->, blind <!-- num:k2.blind -->92/234<!-- /num --> → <!-- num:k3.blind -->125/234<!-- /num -->) with no more safety misses. It is **worse** on the untouched blind-c confirmation suite (<!-- num:k2.blindc -->47/100<!-- /num --> → <!-- num:k3.blindc -->40/100<!-- /num -->, safety misses <!-- num:k2.blindc.safety -->10<!-- /num --> → <!-- num:k3.blindc.safety -->12<!-- /num -->), so use the hybrid setting for safety-critical gates. Pin `"model": "decider-2.0.0"` to keep Keel-2. See [Release notes](release-notes.md).

### What is Keel-Pro?

Keel-Pro is the open-weight Qwen3.5 LoRA fine-tune behind the optional `decider-pro-1.0.0` pin. It runs as a loopback sidecar on a GPU (see `artifacts/parity/pro/SERVE.md` and `artifacts/parity/pro/MODEL_CARD.md`). It is not the default, because the default must run on a CPU with no extra download.

The name was earlier used for a 70M-parameter DeBERTa line, `t2-dxs-b3` (<!-- num:pro.size -->108 MB<!-- /num -->; blind <!-- num:pro.blind -->134/234<!-- /num -->, <!-- num:pro.blind.lat -->117 / 242 ms<!-- /num --> p50 / p95). That line is retired; it served as the distillation teacher for Keel-3 and is now called "Keel-Pro DeBERTa".

## Project

### How do I report a bug or a wrong answer?

Open a GitHub issue with the request body (no secrets), the response and what you expected. Wrong answers with a clear expected label are the most useful input for the next training round.

### How can I help?

Star the repository, try it in your agent, and contribute labelled decision examples or new integration configs. See [Help guide](help-guide.md).
