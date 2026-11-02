# Jev (TypeSafe AI "System One") — published quality / latency / cost claims

Owner: jev-2. Every number below is **vendor-reported** by TypeSafe AI (typesafe.ai /
docs.typesafe.ai) and has **not** been independently verified by us unless the
"Reproducible on Keel?" column says otherwise. Retrieved 2026 (pages as live at time of
writing). Nothing here is a Keel measurement — Keel's own token numbers are in
`artifacts/parity/tokens/report.md`.

## 1. Headline claims

| Claim (vendor-reported) | Source URL | What it is measured on | Notes |
|---|---|---|---|
| "193.6x Faster, 444.6x Cheaper" than LLMs | https://typesafe.ai | TypeSafe workflow evals (https://evals.typesafe.ai) | Blog says these are "on the higher end" of their eval results |
| Demo: TypeSafe $0.000081 / 0.114 s vs LLMs $0.013880 / 8.566 s | https://typesafe.ai | Single homepage demo run | One example, not a benchmark |
| "$42 per billion input tokens"; "238x lower input price than Claude Fable 5.1" | https://typesafe.ai | List price comparison | Price ratio, not measured spend |
| "Zero Hallucinations" | https://typesafe.ai | — | Structural claim (constrained typed output); blog states Jev's 0% is not an empirical measurement; LLM hallucination rates quoted from OpenRouter |
| Jev latency 70–500 ms end-to-end, "40x–200x faster" | https://typesafe.ai/blog/introducing-system-one-models-and-jev | Their API, end-to-end | Frontier LLMs quoted at 3–329 s, citing llm-benchmarks.diegoromero.es |
| Comparable model = GPT-5.6 Terra (default reasoning) | same | Side-by-side demo | Vendor's own choice of most comparable LLM |
| Choice cardinality up to 255 | same | API limit | — |
| Doom demo: 10 queries/s ≈ $7/hour | same | Demo | — |

## 2. Workflow evals (evals.typesafe.ai)

- Source: https://typesafe.ai/blog/introducing-system-one-models-and-jev → https://evals.typesafe.ai
- 4 workflows (e.g. expense-claim processing). Reference answers = average of GPT-6 Astra and
  Fable 5.1 (i.e. **LLM-as-reference, not human gold**). LLM baselines run through the
  public `system-one-adapter-python` wrapper (https://github.com/typesafe-ai/system-one-adapter-python, MIT).
- Speed/cost ratios (193.6x / 444.6x) come from these evals. **Vendor-reported.**
- Reproducible on Keel? **Partially** — workflow definitions are viewable on the evals site, but
  the reference-answer generation depends on GPT-6 Astra + Fable 5.1 calls; we have not re-run them.

## 3. Case study — Jack & Jill (replaced Gemini 3.1 Flash Lite)

Source: https://typesafe.ai/blog/jack-jill-jev-case-study — **vendor-reported, private data, not reproducible.**

| Metric | Gemini 3.1 Flash Lite | Jev |
|---|---|---|
| Cost per 1,000 candidates screened | $0.755 | $0.092 (88% lower) |
| Median time to screen a role | 20.3 s | 10.3 s |
| Winners kept on shortlist | 93.9% | 94.6% (CI −0.4 to +1.8 pts) |
| AUC | 0.924 | 0.933 |
| Profile-check latency | 3.6 s | 0.2 s |
| List price per MTok | $0.25 in / $1.50 out | $0.042 in / free out |

Projected savings $500K/yr ($265K at current volume). 150 live roles.

## 4. Cookbooks with numbers (docs.typesafe.ai)

Public example code + JSON caches: https://github.com/typesafe-ai/typesafe-public-examples (MIT).

| Cookbook | URL | Dataset (public?) | Vendor-reported result | Reproducible on Keel? |
|---|---|---|---|---|
| Parallel questions (jev-1.12) | https://docs.typesafe.ai/cookbooks/parallel_questions.md | GDPR Wikipedia article rev 1363040264, 53,777 chars (public) | 13 questions batched: $0.000497 / 0.27 s vs 13 single calls $0.006090 / 2.71 s → "12.2x cheaper, 10.0x faster" | **Yes** (state public; but long state > Keel context — would need chunking) |
| Skill suggestion | https://docs.typesafe.ai/cookbooks/skill_suggestion.md | 182 skills (Nous Hermes catalog), 488 requests, agent = claude-haiku-4-5 (public catalog) | Wrong skill loaded 16.8% → 7.3% with Jev suggestion (oracle 2.5%); loads a skill when none fits 9.8% → 4.0% (oracle 1.2%) | **Yes, likely** (182-way choice exceeds typical Keel option count; needs shortlist) |
| Re-ranking | https://docs.typesafe.ai/cookbooks/rerank_typesafe.md | CLERC legal, 3,565 passages, 40 queries, BM25 top-30 (public) | Top-1 5% → 18%; top-10 38% → 62% | **Yes** (one noul/score per query–passage pair) |
| SDE cascade | https://docs.typesafe.ai/cookbooks/sde_cascade.md | 100 prompts from scrapegraphai/scrapegraphai-100k (public HF) | gpt-5.4-mini → gpt-5.5 cascade gated by Jev verifier (FIRE_T 0.7) beats every single model on cost/quality frontier; gpt-5.5-reasoning alone ≈0.81 quality at ≈$0.10/extraction | Partially (needs LLM extraction calls + their quality judge) |
| Guardrails (jev-1.12, 2026-08-15) | https://docs.typesafe.ai/cookbooks (llm_guardrails) | 10 prompts / 5 replies; jailbreaks from TrustAIRLab in-the-wild-jailbreak-prompts (public HF) | Qualitative demo, tiny n | Yes (tiny) |
| Self-consistency: choices | https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook.md | 1 synthetic borderline post, 8 Choice questions × 15 repeats (in cookbook) | Jev plurality-label agreement 90.8% (LLMs 87.5–100%); with ≥0.60 confidence gate agreement 99.2% at 74.2% automatic answers; flips on 2/8 questions | **Yes** (Keel is deterministic → 100% agreement trivially; gate coverage comparable) |
| Others (SEC 75 industry groups, entity alignment of beer catalogue, Twitch chat filter, citation check, RAG passage classification, date extraction, OCR) | https://docs.typesafe.ai/llms.txt | Mostly public inputs in typesafe-public-examples | Mostly qualitative / per-example | Case-by-case |

## 5. Latency band and pricing (vendor-reported)

- Latency: **70–500 ms end-to-end** per request (blog). Cookbook examples: 0.114 s (homepage),
  0.27 s for 13 batched questions over a 54k-char state.
- Price (https://docs.typesafe.ai/models): jev-1.14.0 / jev-1.13.0 **$0.042 per MTok input
  ($42/Btok), output free**; billed on input tokens; response includes `usage`.
- Context: 64k tokens/request, 32k per question; 262k with long-context header (1.14 "danger zone").
- LLM reference prices quoted by TypeSafe (consistency cookbook, "as of 2026-07"): claude-haiku-4-5
  $1/$5, gpt-5.4-mini $0.75/$4.50, gpt-5.5 $5/$30, claude-opus-4-8 $5/$25 per MTok.

## 6. The token-savings pitch

TypeSafe does **not** publish a "% of agent tokens saved" number. The pitch is cost/latency ratio
plus four patterns that remove LLM tokens:

1. **Intent / confidence-gated routing** (https://docs.typesafe.ai/patterns/confidence-routing.md):
   classify first; only send requests that need it to the expensive LLM; below 0.6 confidence →
   human/LLM. This is exactly Keel's τ gate.
2. **Skill suggestion**: Jev picks the skill so the agent need not load all 182 skill
   descriptions into context (fewer input tokens *and* fewer wrong-skill loads).
3. **Cascade / verifier** (SDE cascade): cheap LLM first, Jev decides whether to escalate.
4. **Batching** (parallel questions): one request with many questions instead of N calls →
   "12.2x cheaper".

Output tokens are free and the "answer" is a probability vector, so the only priced unit is input.

## 7. What is NOT published

- No standard public benchmark table (MMLU/GLUE/etc.) by design — see
  https://typesafe.ai/blog/antibenchmaxxing.
- Jev 1.14 blog (https://typesafe.ai/blog/jev-1-14) shows an intelligence chart vs open-weight
  models only; no numeric values extracted.
- Known weaknesses self-reported on the jaggedness page (jev-1.13): literal reading, math, dates,
  indirection, large states, adversarial content, contradictory criteria, choice-order bias,
  generation.

## 8. What we can reproduce on Keel (summary)

| Item | Public data | Keel-reproducible now |
|---|---|---|
| Re-ranking (CLERC 40 queries) | Yes | Yes |
| Skill suggestion (182 skills, 488 requests) | Yes | Yes with shortlist |
| Self-consistency (8 Q × 15) | Yes | Yes |
| Guardrails (TrustAIRLab) | Yes | Yes |
| Parallel questions (GDPR) | Yes | Needs chunking (state length) |
| SDE cascade (scrapegraphai) | Yes | Needs LLM spend |
| Workflow evals (193.6x / 444.6x) | Partly | Not without frontier reference calls |
| Jack & Jill | No | No |

Token-savings comparison for Keel (measured, not vendor-reported): `artifacts/parity/tokens/report.md`.
Apples-to-apples note: TypeSafe's pitch is $/latency per decision vs an LLM call. Keel's measured
analogue is the "dedicated decision sub-call" scenario (A/B) in that report; Keel output and input
are both free (local), so its marginal price per decision is $0 plus CPU time. The report also shows
where gating does **not** save tokens (an agent that already holds the state and answers without
deliberating), which TypeSafe's material does not discuss.
