# Licenses and data provenance

Keel's code and its fine-tuned weights are released under the **Apache License 2.0**. This page lists every upstream model, dataset and SDK that went into Keel, what licence each one carries, and how it was used. The full working record is `artifacts/parity/licenses.md`; the release audit is `artifacts/parity/oss-audit.md`.

## Licence decisions (maintainer, 2026-11-02)

We follow common open-model practice. This is our policy, not legal advice.

| Question | Decision | Why this is the usual practice |
|---|---|---|
| **CC BY-SA training data** (MNLI portions, SNLI, ARC, BoolQ, STS-B, HoVer + Wikipedia) | **Keep.** Weights stay Apache-2.0. Every source is attributed here, in `artifacts/parity/pro/DATA.md` and in the model cards. No dataset rows, raw or converted, are redistributed: the repository ships only the code that fetches and converts them. | Permissive models trained on share-alike text are the norm. For example, BERT (Apache-2.0) was trained on English Wikipedia (CC BY-SA). Share-alike binds redistributed or adapted *data*; whether trained weights count as an adaptation is unsettled, so we attribute and do not redistribute the data. |
| **Non-commercial data (ANLI, CC BY-NC 4.0)** | **Never trained on.** ANLI is eval-only for Keel-Lite and replaced by MNLI/SNLI for Keel-Pro. MMLU `auxiliary_train` (RACE) is excluded the same way. | Exclude NC data from anything released under a commercial-friendly licence. |
| **ANLI in an upstream base's history** (`MoritzLaurer/*-all-33`, base of Keel-Lite) | **Inherit the upstream licence (MIT) and disclose the lineage.** Keep the upstream notice. The `-c` variants (commercial-friendly data only) are the planned base for a future Keel-Lite. | Downstream fine-tunes take the licence the upstream author published, and say what they know about the upstream data. |
| **Short strings borrowed from eval code** (`jev-phishing-bench`, Decision Index kit) | **Keep with attribution.** The DI kit is MIT. `jev-phishing-bench` has no LICENSE file, but its README states the content is MIT; we use nine short task prompts and credit the source. | Attribution of short, functional prompts under the author's stated licence. |
| **Base model** | Qwen3.5-27B / 9B / 4B are Apache-2.0; Qwen's notice is kept in `hf/keel-pro/NOTICE`. | Standard Apache-2.0 notice preservation. |

## Keel itself

| Component | Licence | Notes |
|---|---|---|
| Source code (server, wire layer, MCP server, scripts, training code) | Apache-2.0 | See `LICENSE` in the repository root. |
| Fine-tuned weights (`models/keel-3`, `models/keel-2`, candidates) | Apache-2.0 | Derived from MIT-licensed bases; keep the upstream MIT notices. |
| Documentation (this folder) | Apache-2.0 | |

Today the Keel-2 ONNX file ships in the repository and `npm run model:fetch` downloads the MIT base model. The release plan (`artifacts/parity/oss-audit.md`) moves new weights to a GitHub Release asset and Hugging Face, fetched with a pinned revision and SHA-256 check, rather than Git LFS.

## Upstream models

| Model | Licence | Role in Keel | Lineage note |
|---|---|---|---|
| [MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33](https://huggingface.co/MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33) | MIT | Base of the ~13M-parameter Keel models | All-33 mix includes ANLI (CC BY-NC 4.0). MIT inherited; lineage disclosed (see decisions). |
| [MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33](https://huggingface.co/MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33) | MIT | Base of the 70M "Pro" line and of the distillation teacher | Same all-33 mix, includes ANLI. MIT inherited; lineage disclosed. |
| [MoritzLaurer/deberta-v3-base-zeroshot-v2.0-c](https://huggingface.co/MoritzLaurer/deberta-v3-base-zeroshot-v2.0-c) | MIT | Candidate teacher | `-c`: commercially friendly data only (synthetic, MNLI, FEVER-NLI). |
| [Qwen/Qwen3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B) | Apache-2.0 | Base of Keel-Pro 27B (QLoRA r32 adapter, it7+; merged for GGUF) | Adapter and GGUF released under Apache-2.0 with Qwen's notice kept. |
| [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) (and the 4B used for it1–it2) | Apache-2.0 | Base of Keel-Pro (LoRA r32, merged) | Keel-Pro weights are released under Apache-2.0 with Qwen's notice kept. |

## Public datasets

Raw data is never redistributed. Converted training groups inherit the source licence.

| Dataset | Licence | Used for | Trained on? |
|---|---|---|---|
| MNLI (GLUE) | OANC + CC BY-SA 3.0 portions | Eval and training | Yes. Share-alike: attributed, not redistributed. |
| ARC Easy and Challenge | CC BY-SA 4.0 | Eval and training | Yes. Share-alike: attributed, not redistributed. |
| BoolQ | CC BY-SA 3.0 | Eval and training | Yes. Share-alike: attributed, not redistributed. |
| STS-B (GLUE) | Mixed sources, CC BY-SA 3.0 annotations | Eval and training | Yes. Share-alike: attributed, not redistributed. |
| BANKING77 | CC BY 4.0 | Eval and training | Yes (attribute) |
| CLINC150 (oos-eval) | CC BY 3.0 | Eval and training | Yes (attribute) |
| WinoGrande | CC BY 4.0 | Eval and training | Yes (held out of some runs) |
| HellaSwag | MIT | Eval and training | Yes |
| civil_comments | CC0 1.0 | Eval and training | Yes |
| ESCI (Amazon shopping queries) | Apache-2.0 | Eval and training | Yes |
| MMLU | MIT | Eval only | No |
| ANLI | CC BY-NC 4.0 | Eval only | **No (non-commercial)** |
| AG News | Academic, non-commercial terms | Eval only | No |
| emotion | Research/educational use | Eval only | No |
| SST-2, RTE (GLUE) | Unspecified | Eval only | No |
| MRPC | MSR Paraphrase Corpus licence | Eval only | No |

Release candidates from `t1-r1` onward trained on a subsample of the public training splits listed as "Yes"; Keel-2 saw about 6k MNLI pairs. Treat public-benchmark gains on those datasets as in-distribution. See [Benchmarks](benchmarks.md).

The rest of the training data is synthetic, generated for this project from decision "families" (gating, routing, severity, safety and so on), and is covered by the repository licence.

### Keel-Pro (Qwen LoRA) corpus

The Keel-Pro corpus (`training/pro/data/`) uses train splits only. The full table, with revisions, row counts and exclusions, is in `artifacts/parity/pro/DATA.md`. In addition to the datasets above, it uses:

| Licence | Datasets |
|---|---|
| Apache-2.0 | ToolACE, glaive-function-calling-v2, MedMCQA, API-Bank tool schemas |
| MIT | API-Bank training data, GSM8K, CommonsenseQA, iSarcasmEval, RAGTruth |
| CC BY 4.0 | ContractNLI, QASC, searchless_chess data, Habermas Machine, When2Call, New Yorker caption contest |
| CC BY-SA 4.0 (attributed, not redistributed) | SNLI, HoVer |

Excluded:

- **Non-commercial or research-only:** ANLI and MMLU `auxiliary_train` (it contains RACE).
- **No stated licence:** ToolRet-Training, OpenBookQA, ACOS, VAST, NLI4CT and Humicroedit. The last four are opt-in only, via `--include-unlicensed`.

Synthetic Keel-Pro generators borrow short strings from evaluation code, never data rows:

- `synth_chords.py` imports the chord templates and the 129-label vocabulary from the Decision Index kit (MIT).
- `synth_phish.py` reuses the nine PhishNChips question texts from `jev-phishing-bench/run_jev.py`. That repository
  has no LICENSE file (its README calls the dataset content MIT). Kept with attribution (see decisions); the strings are short
  task prompts.
- `synth_sata.py` is built from QASC (CC BY 4.0, listed above). `synth_home.py` reuses the kit's `home_appliance`
  resolver, scenario list and question texts (MIT). `synth_finentity.py` reuses the kit's FinEntity instruction text
  (MIT). `synth_musr.py` and `synth_color.py` are original; CFColor's own ratings (no stated licence) are not used.

## Third-party numbers and SDKs

| Item | Licence | Use |
|---|---|---|
| [apolinario/decision-index](https://github.com/apolinario/decision-index) board JSON | MIT | Third-party per-dataset Jev numbers quoted in [Comparison](comparison.md) |
| `typesafe-sdk` 0.7.5 (Python) | MIT | Wire-parity test of the Jev client against local Keel |
| `@typesafe-ai/sdk` 0.7.0 (Node) | MIT | Wire-parity test of the Jev client against local Keel |

Keel does not include or redistribute Jev or Microsoft-Decision-1 code or weights. "Jev", "TypeSafe", "Microsoft" and "Microsoft-Decision-1" are trademarks of their owners and are used only to describe wire compatibility.

## Security items from the release audit

These are not licensing questions; they were raised in `artifacts/parity/oss-audit.md` and have been addressed:

- **Per-install bearer secret (fixed).** The bearer token used to be derived from a public built-in constant. It is now an HMAC of `KEEL_SECRET` or, by default, of a random secret generated on first use and stored outside the repo in `~/.keel/secret` (mode 0600). No two installs share a token. Get yours with `npm run keel:token`; these docs only ever write `<KEEL_TOKEN>`.
- **Loopback by default (fixed).** The dev server binds `127.0.0.1:8080`; `KEEL_HOST` is an explicit opt-in for other interfaces. The bench UI serves the token only to loopback requests.
- **Agent files are safe to commit.** `npm run keel:agents` writes `<KEEL_TOKEN>` placeholders into the repo copies and the real token only into `~/.copilot/`.
