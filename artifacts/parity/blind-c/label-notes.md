# Blind-C label notes (data-1)

**Restricted.** This file is for the blind-suite owner and the orchestrator only. Trainers and data generators must not open `artifacts/parity/blind-c/**` or `src/lib/decider/eval-blind-c*.ts`.

## Authorship

| Half | Cases | Ids | Safety | Author |
|---|---:|---|---:|---|
| C1 | 52 | 3001–3052 | 14 | data-1 (Claude). Written from scratch without re-reading blind A/B, the training generators or training data. |
| C2 | 48 | 4001–4048 | 15 | Sub-agent on `gemini-4-argon`. Written blind to C1 and to blind A/B. |
| **Total** | **100** | | **29 (29%)** | Covers all 50 use cases: every case has a `uc:<slug>` tag, 50 distinct slugs. |

## Review of C2 (all 48 cases read by data-1)

- **No choice or noul labels were changed.** No label was clearly wrong.
- **Score bands widened (C2 only), before any model or LLM was scored on blind-C.**
  - The sub-agent wrote 12 exact-level bands (`min == max`). Keel and LLM scores are expectation values, so they are fractional. An exact band would demand an impossible point value.
  - These were widened by half a level towards the interior, matching the convention in C1 and blind A/B:
    - `3 → [2.5, 3]`
    - `2 → [1.5, 2]` (top of a 3-level scale)
    - `0 → [0, 0.5]`
  - One case, customer sentiment at the floor, was widened to `[0, 1]`. Its state is clearly negative, but the second-lowest level is defensible.
  - The intended answer did not change for any case.
- **Style caveat, not a label error.** Many C2 option/level descriptions are leading: the criteria text partly restates the facts of the state. This makes C2 somewhat easier than C1 for both Keel and the LLM. Per-half fully-right numbers (tags `blind-c1` / `blind-c2`) are reported in the per-case reports under this folder for that reason.
- **Inverted scale noted.** One accessibility score uses an inverted scale (level 0 = most severe). The label is consistent with its own criteria.
- **Ambiguous cases (graded on `maxConfidence` only):**
  - C1: one case;
  - C2: three cases.

## Review of C1

- **One expectation id was fixed during authoring**, before any scoring: it pointed at a question id that did not exist.
- **One case was tagged `ambiguous`**, because two keys are equally defensible.

## Disputes

None open.
