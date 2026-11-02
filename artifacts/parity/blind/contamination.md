# Blind suite contamination check (6-gram)

Generated 2026-10-29T05:20:58.596Z by `artifacts/parity/blind/contamination-check.ts` (programmatic; training content was never read by the blind-suite authors).

Method: lower-cased Unicode word tokens; every distinct 6-gram of each blind case state (all string leaves of `state`) is looked up in every `training/data/**/*.jsonl` line (all string leaves). "In any training line" = share of a case's 6-grams that occur anywhere in training; "best single line" = most 6-grams shared with one training line (near-duplicate signal).

Thresholds: **contaminated** if best single line ≥ 50% or any-line ≥ 50%; **watch** if ≥ 20%.

## Result: 0 contaminated, 3 watch, 11/234 cases share at least one 6-gram

## Files scanned

| file | lines | lines sharing ≥1 blind 6-gram | blind cases touched |
|---|---:|---:|---:|
| training/data/dev.jsonl | 1415 | 0 | 0 |
| training/data/dev.v1.jsonl | 1291 | 0 | 0 |
| training/data/public/arc_challenge.jsonl | 1113 | 0 | 0 |
| training/data/public/arc_easy.jsonl | 2243 | 1 | 1 |
| training/data/public/banking77.jsonl | 5000 | 3 | 1 |
| training/data/public/boolq.jsonl | 5000 | 0 | 0 |
| training/data/public/civil_comments.jsonl | 5002 | 2 | 2 |
| training/data/public/clinc150.jsonl | 5000 | 0 | 0 |
| training/data/public/esci.jsonl | 5000 | 0 | 0 |
| training/data/public/hellaswag.jsonl | 5000 | 7 | 1 |
| training/data/public/mnli_m.jsonl | 5000 | 0 | 0 |
| training/data/public/stsb.jsonl | 5000 | 0 | 0 |
| training/data/public/winogrande.jsonl | 5000 | 0 | 0 |
| training/data/train.jsonl | 33224 | 1 | 1 |
| training/data/train.v1.jsonl | 30865 | 1 | 1 |
| training/data/v3/dev.jsonl | 3001 | 18 | 1 |
| training/data/v3/seeds/a_ecom_intent.jsonl | 450 | 0 | 0 |
| training/data/v3/seeds/a_moderation.jsonl | 300 | 0 | 0 |
| training/data/v3/seeds/a_noul.jsonl | 360 | 0 | 0 |
| training/data/v3/seeds/a_review_stars.jsonl | 300 | 0 | 0 |
| training/data/v3/seeds/a_sentiment.jsonl | 700 | 0 | 0 |
| training/data/v3/seeds/b_contract_clause.jsonl | 396 | 9 | 3 |
| training/data/v3/seeds/b_email_urgency.jsonl | 224 | 0 | 0 |
| training/data/v3/seeds/b_hr_route.jsonl | 288 | 0 | 0 |
| training/data/v3/seeds/b_incident_severity.jsonl | 432 | 0 | 0 |
| training/data/v3/seeds/b_lead.jsonl | 396 | 0 | 0 |
| training/data/v3/seeds/b_news_topic.jsonl | 396 | 0 | 0 |
| training/data/v3/seeds/b_noul.jsonl | 252 | 0 | 0 |
| training/data/v3/seeds/b_support_route.jsonl | 540 | 1 | 1 |
| training/data/v3/seeds/c_agent_action.jsonl | 852 | 0 | 0 |
| training/data/v3/seeds/c_answer_grade.jsonl | 255 | 0 | 0 |
| training/data/v3/seeds/c_change_risk.jsonl | 307 | 0 | 0 |
| training/data/v3/seeds/c_injection.jsonl | 272 | 0 | 0 |
| training/data/v3/seeds/c_model_route.jsonl | 266 | 0 | 0 |
| training/data/v3/seeds/c_rag.jsonl | 262 | 0 | 0 |
| training/data/v3/seeds/c_security_noul.jsonl | 415 | 0 | 0 |
| training/data/v3/seeds/c_tool_route.jsonl | 474 | 3 | 3 |
| training/data/v3/train.jsonl | 117925 | 83 | 2 |
| training/data/v3/v2/dev.jsonl | 6000 | 22 | 2 |
| training/data/v3/v2/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v2/train.jsonl | 363631 | 276 | 10 |

## Contaminated (≥ 50%)

None.

## Watch (20–50%)

| id | name | 6-grams | in any training line | best single line | best file:line | sample shared 6-gram (blind side) |
|---:|---|---:|---:|---:|---|---|
| 16 | Explain a concept | 7 | 42.9% | 42.9% | training/data/v3/seeds/c_tool_route.jsonl:374 | the difference between a mutex and |
| 119 | Wants human | 12 | 33.3% | 33.3% | training/data/v3/seeds/c_tool_route.jsonl:456 | this is the third time the |
| 49 | Wrong size | 11 | 27.3% | 27.3% | training/data/v3/dev.jsonl:264 | a size too small how do |

## Top 15 by overlap (all cases)

| id | name | 6-grams | in any training line | best single line | best file:line | sample shared 6-gram (blind side) |
|---:|---|---:|---:|---:|---|---|
| 16 | Explain a concept | 7 | 42.9% | 42.9% | training/data/v3/seeds/c_tool_route.jsonl:374 | the difference between a mutex and |
| 119 | Wants human | 12 | 33.3% | 33.3% | training/data/v3/seeds/c_tool_route.jsonl:456 | this is the third time the |
| 49 | Wrong size | 11 | 27.3% | 27.3% | training/data/v3/dev.jsonl:264 | a size too small how do |
| 65 | Late fees | 22 | 18.2% | 18.2% | training/data/v3/seeds/b_contract_clause.jsonl:9 | accrue interest at 1 5 per |
| 99 | Fully specified | 6 | 16.7% | 16.7% | training/data/v3/seeds/c_tool_route.jsonl:50 | convert 72 degrees fahrenheit to celsius |
| 141 | Do not store secret | 9 | 11.1% | 11.1% | training/data/public/civil_comments.jsonl:1171 | so you don t have to |
| 74 | Partial answer | 11 | 9.1% | 9.1% | training/data/public/arc_easy.jsonl:1140 | the three primary colors of light |
| 50 | Moved house | 17 | 5.9% | 5.9% | training/data/v3/seeds/b_support_route.jsonl:76 | i don t want to cancel |
| 1042 | Renewal notice clause | 23 | 4.3% | 4.3% | training/data/v3/seeds/b_contract_clause.jsonl:45 | unless either party gives written notice |
| 71 | Paraphrase relevant | 24 | 4.2% | 4.2% | training/data/public/banking77.jsonl:2559 | can i get my money back |
| 63 | Long liability clause | 218 | 7.3% | 2.3% | training/data/v3/seeds/b_contract_clause.jsonl:50 | in the twelve 12 months preceding |
| 1 | Rename helper with path | 14 | 0.0% | 0.0% | - | - |
| 2 | Which config file | 28 | 0.0% | 0.0% | - | - |
| 3 | Disable auth for demo | 21 | 0.0% | 0.0% | - | - |
| 4 | Injection in issue body | 29 | 0.0% | 0.0% | - | - |

## Notes (data-1)

- Re-run on 2026-10-29 after data v3 version 2 became READY. That run included `training/data/v3/v2/**` and the new seed banks.
- The three watch cases (16, 119, 49) share 3–4 short, everyday phrases with LLM-written seeds. Examples: "the difference between a mutex and", "this is the third time the". These are short, generic phrases, not near-duplicates, so none of the three cases is treated as contaminated.
- Disclosure from data-2: a mistyped command printed 8 `safetyMiss` spec lines from `eval-blind-b.ts` to data-2's console. Those lines showed question ids, gold keys and unsafe keys, but no state text. The disclosure is recorded in `training/data/v3/NOTES.md`. The 6-gram check cannot detect leaks at the label level. Half B's `safetyMiss` cases should therefore be read with that caveat; half A was not exposed.
