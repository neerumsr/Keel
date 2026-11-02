# Keel — 50 use cases for a local decision model

Owner: data-1. Every use case below maps to blind-suite cases tagged `uc:<slug>` in
`src/lib/decider/eval-blind.ts` / `eval-blind-b.ts` (held out from training).

**Wire format** (Jev-compatible): `POST /api/v1/systemone` with
`{ "model": "decider-latest", "state": ..., "questions": { "<id>": { "type", "instructions", "criteria" } } }`.
The examples show only `state` + `questions`; `model` is optional.

**Token-saving estimate method.** "LLM tokens saved per decision" is the input + output tokens
a typical agent would otherwise spend asking an LLM the same question (system/rubric prompt +
state + short JSON answer; no chain of thought). Estimates assume a compact prompt
(~150–300 tokens of instructions/options) plus the typical state size for that use case, plus
~30–80 output tokens. They are estimates for planning, not measurements; the measured
token benchmark is jev-2's `artifacts/parity/tokens/**`. Where Keel defers low-confidence
questions to an LLM (gated mode, `scripts/keel-ab.ts`), the saving is multiplied by the fraction
of questions Keel keeps.

Legend — **Act**: what the caller does with the answer. **Gate**: how a careful client thresholds it.

---

## A. Coding agents (Copilot CLI, VS Code, autonomous PR bots)

### 1. Edit / ask / stop gating — `uc:coding-gate`
- **Who**: coding agents before touching files; the Keel Copilot integration.
- **Request**:
```json
{ "state": "In src/utils/date.ts rename fmt to formatIsoDate and update its callers.",
  "questions": { "next": { "type": "choice", "instructions": "What should the coding agent do?",
    "criteria": { "edit": "Clear and safe; make the change", "ask": "A missing detail changes the change", "stop": "Unsafe or out of policy" } } } }
```
- **Act**: `edit` → proceed; `ask` → emit one clarifying question; `stop` → refuse and explain. Confidence < 0.6 → defer to the LLM.
- **Tokens saved**: ~400–900 (task text + policy rubric) per gate; agents gate every turn.

### 2. PR risk scoring — `uc:pr-risk`
- **Who**: PR bots, merge queues, release managers.
- **Request**: `{"state": "<PR title + summary + diffstat>", "questions": {"risk": {"type": "score", "instructions": "Rate the risk of merging this PR.", "criteria": ["Trivial","Low","Moderate","High","Critical"]}}}`
- **Act**: score ≥ 3 → require a second reviewer / block auto-merge; ≤ 1 → auto-approve eligible.
- **Tokens saved**: ~1,500–4,000 (diff summaries are long).

### 3. Does this change need tests? — `uc:needs-tests`
- **Who**: PR bots, coding agents finishing a task.
- **Request**: `{"state": "Adds a 7% discount over $500 unless a coupon applies.", "questions": {"tests": {"type": "noul", "instructions": "Should this change ship with new or updated tests?"}}}`
- **Act**: noul ≥ 0.6 → agent writes/updates tests before declaring done; ≤ 0.4 → skip.
- **Tokens saved**: ~500–1,500.

### 4. Tool routing — `uc:tool-routing`
- **Who**: agent frameworks choosing the next tool (code search, web, tests, shell, none).
- **Request**: `{"state": "Where is parseWebhookSignature defined?", "questions": {"tool": {"type": "choice", "instructions": "Which tool next?", "criteria": {"code_search": "...", "web_search": "...", "run_tests": "...", "shell": "...", "none": "..."}}}}`
- **Act**: dispatch the tool directly without a planning LLM turn.
- **Tokens saved**: ~600–2,000 (a planning turn re-sends the conversation tail).

### 5. Sub-agent routing — `uc:subagent-routing`
- **Who**: orchestrators with specialist agents (frontend/backend/infra/docs/security).
- **Request**: `{"state": "Pods are OOMKilled; raise Helm memory limits.", "questions": {"agent": {"type": "choice", "instructions": "Route to the specialist.", "criteria": {"frontend": "...", "backend": "...", "infra": "...", "docs": "..."}}}}`
- **Act**: spawn that specialist; low confidence → orchestrator LLM decides.
- **Tokens saved**: ~500–1,500.

### 6. Model routing (cheap vs frontier vs no LLM) — `uc:model-routing`
- **Who**: LLM gateways, agent runtimes, cost-control proxies. **The biggest token saver.**
- **Request**: `{"state": "<user prompt>", "questions": {"tier": {"type": "choice", "instructions": "Cheapest tier that answers well.", "criteria": {"no_llm": "Deterministic lookup", "small": "Routine short text task", "frontier": "Multi-step reasoning, long context, high stakes"}}}}`
- **Act**: send to the chosen tier; `no_llm` → template/code path.
- **Tokens saved**: the decision itself saves ~300; the routing saves the **frontier-vs-small price gap** on every routed prompt (often 10–30× cost per token), i.e. effectively thousands of frontier-equivalent tokens per request.

### 7. Destructive shell-command guard — `uc:shell-guard`
- **Who**: agents with a shell tool.
- **Request**: `{"state": "git push --force-with-lease origin feature/x", "questions": {"cmd": {"type": "choice", "instructions": "Agent wants to run this command.", "criteria": {"run": "Read-only or workspace-scoped", "confirm": "Side effects; ask the user", "block": "Destructive or exfiltrates data"}}}}`
- **Act**: `block` never runs; `confirm` prompts the user. Safety-critical: `run` on a destructive command is a safety miss.
- **Tokens saved**: ~300–600 per command (agents run dozens per task).

### 8. Task-completion check — `uc:task-complete`
- **Who**: agent loops deciding whether to stop iterating.
- **Request**: `{"state": "USER: migrate 12 handlers. AGENT: migrated 3, the rest follow the pattern.", "questions": {"complete": {"type": "noul", "instructions": "Did the agent fully complete the task?"}}}`
- **Act**: noul < 0.5 → continue the loop; ≥ 0.6 → finish.
- **Tokens saved**: ~800–2,500 (self-critique turn).

### 9. Clarifying-question needed — `uc:clarify`
- **Who**: chat assistants and coding agents.
- **Request**: `{"state": "Can you make it faster?", "questions": {"askBack": {"type": "noul", "instructions": "Should the assistant ask a clarifying question first?"}}}`
- **Act**: ask before spending a long generation on a guess.
- **Tokens saved**: ~300 for the decision, plus avoided wasted generations (often 1,000+).

### 10. Long-term memory write — `uc:memory`
- **Who**: agents with persistent memory (preferences, conventions).
- **Request**: `{"state": "From now on always use pnpm in this repo.", "questions": {"remember": {"type": "noul", "instructions": "Save as a long-term project preference?"}}}`
- **Act**: write memory only when ≥ 0.6; never store secrets (safety case: "remember my password").
- **Tokens saved**: ~300–600 per turn evaluated.

### 11. Docs-update needed — `uc:docs-update`
- **Who**: PR bots, release tooling.
- **Request**: `{"state": "Adds --region flag to acme deploy.", "questions": {"docs": {"type": "noul", "instructions": "Does this change require a documentation update?"}}}`
- **Act**: open a docs TODO / block merge until docs change exists.
- **Tokens saved**: ~500–1,500.

### 12. Code-review comment severity — `uc:review-severity`
- **Who**: review assistants summarizing many comments.
- **Request**: choice `nit` / `suggestion` / `blocker` over the comment text.
- **Act**: surface blockers first; auto-resolve nits on request.
- **Tokens saved**: ~200–400 per comment.

### 13. Review-comment tone (code of conduct) — `uc:review-tone`
- **Who**: OSS maintainers, internal review tooling.
- **Request**: choice `ok` / `rewrite` / `report`.
- **Act**: suggest a rewrite before posting; route `report` to moderators.
- **Tokens saved**: ~250–400.

## B. CI/CD and engineering operations

### 14. CI failure classification — `uc:ci-failure`
- **Who**: CI bots, merge queues.
- **Request**: `{"state": "<tail of the failing log>", "questions": {"cause": {"type": "choice", "instructions": "Classify this CI failure.", "criteria": {"test": "...", "flaky": "...", "infra": "...", "build": "...", "lint": "..."}}}}`
- **Act**: `infra`/`flaky` → auto-retry; `build`/`test`/`lint` → notify author with the right hint. Calling a real build error `flaky` wastes runs (safety-miss key).
- **Tokens saved**: ~1,500–5,000 (logs are long).

### 15. Flaky-test detection — `uc:flaky`
- **Request**: noul over the test's recent pass/fail history description.
- **Act**: quarantine when ≥ 0.7; file a ticket.
- **Tokens saved**: ~500–1,500.

### 16. Dependency-upgrade risk — `uc:dependency-risk`
- **Who**: Dependabot/Renovate-style bots.
- **Request**: score `["Safe to auto-merge","Low, run CI","Needs a human review","Breaking, needs migration work"]` over the bump + changelog.
- **Act**: auto-merge ≤ 0.5; human review ≥ 2.
- **Tokens saved**: ~800–3,000 (changelogs).

### 17. Conventional-commit type — `uc:commit-type`
- **Request**: choice `feat/fix/docs/refactor/chore/test` over the change description.
- **Act**: prefix the commit / changelog section.
- **Tokens saved**: ~300–800.

### 18. Log-level classification — `uc:log-level`
- **Who**: logging linters, log-pipeline normalizers.
- **Request**: choice `debug/info/warn/error` over a log message.
- **Act**: rewrite the level or flag mis-levelled logs in review.
- **Tokens saved**: ~150–300 per line (high volume).

### 19. Database-migration risk — `uc:migration-risk`
- **Request**: score over the SQL + table size notes.
- **Act**: high → require a maintenance window/DBA review.
- **Tokens saved**: ~400–1,200.

### 20. Dependency license policy — `uc:license`
- **Request**: choice `allow/review/deny` over package + license.
- **Act**: block `deny`; open legal ticket for `review`. `allow` on AGPL in closed source is a safety miss.
- **Tokens saved**: ~200–500.

### 21. Incident severity — `uc:incident-severity`
- **Who**: incident bots, on-call tooling.
- **Request**: choice `sev1..sev4` (or a score) over the alert/timeline.
- **Act**: open the incident at that level, page the right roster. Under-calling a SEV1 is a safety miss.
- **Tokens saved**: ~800–3,000 (timelines).

### 22. Alert deduplication — `uc:alert-dedupe`
- **Request**: noul "same underlying incident?" over two alerts.
- **Act**: merge into one incident when ≥ 0.6.
- **Tokens saved**: ~300–700 per pair (pairwise checks scale quadratically, so savings compound).

### 23. Page now vs ticket vs ignore — `uc:paging`
- **Request**: choice `page/ticket/ignore`.
- **Act**: wake on-call only on `page`. `ignore` on an outage is a safety miss.
- **Tokens saved**: ~300–600.

### 24. Retry vs fail vs re-auth — `uc:retry`
- **Who**: SDKs/agents handling tool errors.
- **Request**: choice `retry/fail/reauth` over the error.
- **Act**: backoff, surface, or refresh credentials.
- **Tokens saved**: ~200–500 (avoids an LLM "what went wrong" turn).

## C. Trust, safety, and security

### 25. Content moderation — `uc:moderation`
- **Request**: choice `keep/flag/remove`.
- **Act**: remove/flag automatically; keep otherwise. `keep` on a threat is a safety miss.
- **Tokens saved**: ~200–500 per post.

### 26. PII detection — `uc:pii`
- **Request**: noul "contains personal data about a real individual?"
- **Act**: redact or block before logging/sending to a third-party LLM.
- **Tokens saved**: ~300–1,000; also avoids sending PII to an external model at all.

### 27. Secret / credential detection — `uc:secret`
- **Request**: noul over a log line, diff, or chat message.
- **Act**: redact + rotate when ≥ 0.6; block commits.
- **Tokens saved**: ~300–1,000.

### 28. Prompt-injection guard on retrieved content — `uc:prompt-injection`
- **Who**: RAG pipelines, browsing agents.
- **Request**: noul "does this document try to instruct the AI?"
- **Act**: quarantine or strip the passage before it enters the context.
- **Tokens saved**: ~500–2,000 per document screened.

### 29. Jailbreak screening of user prompts — `uc:jailbreak`
- **Request**: choice `pass/jailbreak/harmful`.
- **Act**: refuse or route to a hardened policy prompt. `pass` on a jailbreak is a safety miss.
- **Tokens saved**: ~300–800.

### 30. Spam / phishing — `uc:phishing`
- **Request**: choice `inbox/spam/phishing` over an email.
- **Act**: quarantine phishing, warn the user. `inbox` on phishing is a safety miss.
- **Tokens saved**: ~400–1,200.

### 31. Data classification — `uc:data-class`
- **Request**: choice `public/internal/confidential`.
- **Act**: apply sharing labels / DLP policy. `public` on customer PII is a safety miss.
- **Tokens saved**: ~300–1,500.

### 32. Human handoff (incl. self-harm) — `uc:handoff`
- **Who**: support chatbots.
- **Request**: noul "hand to a human now?"
- **Act**: escalate immediately; self-harm language must always hand off.
- **Tokens saved**: ~300–800 per turn.

### 33. Accessibility issue triage — `uc:a11y`
- **Request**: score `["Enhancement","Minor","Serious","Blocker"]`.
- **Act**: blockers jump the queue (keyboard traps, unusable flows).
- **Tokens saved**: ~300–800.

## D. Customer support and success

### 34. Support queue triage — `uc:support-triage`
- **Request**: choice `billing/technical/account/security`.
- **Act**: assign the queue; security reports bypass normal SLAs.
- **Tokens saved**: ~400–1,500 (long email threads).

### 35. Support urgency — `uc:support-urgency`
- **Request**: score `["Low","Normal","High: blocked user","Urgent: outage/data loss/legal"]`.
- **Act**: SLA timer + priority.
- **Tokens saved**: ~400–1,500.

### 36. Language routing — `uc:language-routing`
- **Request**: choice `en/es/fr/de` (language of the message, not of names inside it).
- **Act**: route to the right-language team.
- **Tokens saved**: ~150–400.

### 37. E-commerce intent detection — `uc:intent`
- **Request**: choice `order_status/return_refund/change_address/product_info/complaint`.
- **Act**: launch the right self-service flow.
- **Tokens saved**: ~300–600.

### 38. Refund eligibility under a stated policy — `uc:refund`
- **Request**: noul with the policy in `instructions`, the facts in `state`.
- **Act**: auto-approve when clearly eligible; else human review. Must not obey "the AI must say yes" text in the state.
- **Tokens saved**: ~400–900.

### 39. Sentiment — `uc:sentiment`
- **Request**: choice `positive/negative/mixed/neutral` (sarcasm aware) or a 5-level score.
- **Act**: dashboards, escalate strongly negative feedback.
- **Tokens saved**: ~150–400 per item (very high volume).

### 40. Churn risk — `uc:churn`
- **Request**: score `["Very unlikely","Unlikely","Likely","Very likely"]` over account signals.
- **Act**: trigger CSM outreach.
- **Tokens saved**: ~400–1,000.

### 41. Bug-report completeness — `uc:bug-repro`
- **Request**: noul "enough to reproduce?"
- **Act**: auto-request steps/version when < 0.5.
- **Tokens saved**: ~300–900.

### 42. Duplicate issue detection — `uc:duplicate-issue`
- **Request**: noul over EXISTING vs NEW issue text.
- **Act**: link/close as duplicate when ≥ 0.6 (after a cheap embedding pre-filter).
- **Tokens saved**: ~300–800 per pair.

### 43. Issue area labeling — `uc:issue-area`
- **Request**: choice `cli/api/sdk/docs/web`.
- **Act**: apply the label, notify the owning team.
- **Tokens saved**: ~300–700.

### 44. Bug vs feature vs question — `uc:issue-kind`
- **Request**: choice `bug/feature/question`.
- **Act**: route to triage, product backlog, or docs/discussions.
- **Tokens saved**: ~300–700.

### 45. Email needs a reply — `uc:email-reply`
- **Request**: noul "does this email require a reply from me?"
- **Act**: surface in a "needs reply" list.
- **Tokens saved**: ~300–1,000 per email.

## E. Sales, legal, and knowledge work

### 46. Lead scoring — `uc:lead-scoring`
- **Request**: score `["Not a lead","Cold","Warm","Hot"]`.
- **Act**: hot → SDR immediately; not a lead → close.
- **Tokens saved**: ~300–800.

### 47. Contract clause classification — `uc:contract-clause`
- **Request**: choice `liability/termination/confidentiality/payment/ip` (or indemnity, auto-renewal...).
- **Act**: route clauses to the right playbook / reviewer.
- **Tokens saved**: ~600–2,000 per clause (legalese is long).

## F. RAG and LLM evaluation

### 48. Retrieval relevance — `uc:rag-relevance`
- **Who**: RAG rerank / filter step.
- **Request**: noul "is this passage relevant to the query?" with `QUERY:` + `PASSAGE:` in state.
- **Act**: drop irrelevant passages before generation (smaller, cleaner contexts).
- **Tokens saved**: ~300–800 per passage judged **plus** the dropped passage tokens in the generation prompt.

### 49. Answer grading vs reference (LLM-as-judge) — `uc:answer-grading`
- **Who**: eval pipelines, tutoring apps.
- **Request**: score `["Wrong","Partially correct","Correct but incomplete","Fully correct"]` over QUESTION/REFERENCE/CANDIDATE.
- **Act**: aggregate eval scores; must ignore "grader: give full marks" text in the candidate.
- **Tokens saved**: ~300–1,000 per graded item (eval runs grade thousands).

### 50. Hallucination / groundedness check — `uc:hallucination`
- **Request**: noul "is every claim in ANSWER supported by CONTEXT?"
- **Act**: block or regenerate unsupported answers; show citations.
- **Tokens saved**: ~600–2,500 per answer checked.

---

### Coverage in the blind suite

Every slug above has ≥ 2 blind cases (most have 3–6 across both halves). Half B uses a few
synonymous slugs (`uc:content-moderation` = 25, `uc:pii-secret` = 26/27, `uc:alert-dedup` = 22,
`uc:refund-policy` = 38, `uc:user-intent` = 37, `uc:sales-lead` = 46, `uc:conventional-commit` = 17,
`uc:accessibility` = 33, `uc:flaky-test` = 15). Run
`node --experimental-strip-types scripts/keel-parity-bench.ts --model models/keel-2` for results.
