# Blind suite contamination check (6-gram)

Generated 2026-10-29T09:02:23.221Z by `artifacts/parity/blind-c/contamination-check.ts` (programmatic; training content was never read by the blind-suite authors).

Method: lower-cased Unicode word tokens; every distinct 6-gram of each blind case state (all string leaves of `state`) is looked up in every `training/data/**/*.jsonl` line (all string leaves). "In any training line" = share of a case's 6-grams that occur anywhere in training; "best single line" = most 6-grams shared with one training line (near-duplicate signal).

Thresholds: **contaminated** if best single line ≥ 50% or any-line ≥ 50%; **watch** if ≥ 20%.

## Result: 1 contaminated, 0 watch, 11/100 cases share at least one 6-gram

## Files scanned

| file | lines | lines sharing ≥1 blind 6-gram | blind cases touched |
|---|---:|---:|---:|
| training/data/dev.jsonl | 1415 | 14 | 1 |
| training/data/dev.v1.jsonl | 1291 | 12 | 1 |
| training/data/public/arc_challenge.jsonl | 1113 | 0 | 0 |
| training/data/public/arc_easy.jsonl | 2243 | 0 | 0 |
| training/data/public/banking77.jsonl | 5000 | 0 | 0 |
| training/data/public/boolq.jsonl | 5000 | 0 | 0 |
| training/data/public/civil_comments.jsonl | 5002 | 1 | 1 |
| training/data/public/clinc150.jsonl | 5000 | 0 | 0 |
| training/data/public/esci.jsonl | 5000 | 0 | 0 |
| training/data/public/hellaswag.jsonl | 5000 | 7 | 1 |
| training/data/public/mnli_m.jsonl | 5000 | 0 | 0 |
| training/data/public/stsb.jsonl | 5000 | 0 | 0 |
| training/data/public/winogrande.jsonl | 5000 | 0 | 0 |
| training/data/train.jsonl | 33224 | 269 | 2 |
| training/data/train.v1.jsonl | 30865 | 247 | 2 |
| training/data/v3/dev.jsonl | 3001 | 3 | 1 |
| training/data/v3/seeds/a_ecom_intent.jsonl | 450 | 0 | 0 |
| training/data/v3/seeds/a_moderation.jsonl | 300 | 0 | 0 |
| training/data/v3/seeds/a_noul.jsonl | 360 | 0 | 0 |
| training/data/v3/seeds/a_review_stars.jsonl | 300 | 0 | 0 |
| training/data/v3/seeds/a_sentiment.jsonl | 700 | 0 | 0 |
| training/data/v3/seeds/b_contract_clause.jsonl | 396 | 7 | 2 |
| training/data/v3/seeds/b_email_urgency.jsonl | 224 | 0 | 0 |
| training/data/v3/seeds/b_hr_route.jsonl | 288 | 0 | 0 |
| training/data/v3/seeds/b_incident_severity.jsonl | 432 | 0 | 0 |
| training/data/v3/seeds/b_lead.jsonl | 396 | 1 | 1 |
| training/data/v3/seeds/b_news_topic.jsonl | 396 | 0 | 0 |
| training/data/v3/seeds/b_noul.jsonl | 252 | 0 | 0 |
| training/data/v3/seeds/b_support_route.jsonl | 540 | 2 | 2 |
| training/data/v3/seeds/c_agent_action.jsonl | 852 | 0 | 0 |
| training/data/v3/seeds/c_answer_grade.jsonl | 255 | 0 | 0 |
| training/data/v3/seeds/c_change_risk.jsonl | 307 | 0 | 0 |
| training/data/v3/seeds/c_injection.jsonl | 272 | 0 | 0 |
| training/data/v3/seeds/c_model_route.jsonl | 266 | 0 | 0 |
| training/data/v3/seeds/c_rag.jsonl | 262 | 1 | 1 |
| training/data/v3/seeds/c_security_noul.jsonl | 415 | 0 | 0 |
| training/data/v3/seeds/c_tool_route.jsonl | 474 | 1 | 1 |
| training/data/v3/seeds/d_agent_action.jsonl | 32 | 0 | 0 |
| training/data/v3/seeds/d_ecom_intent.jsonl | 19 | 0 | 0 |
| training/data/v3/seeds/d_lead_temp.jsonl | 12 | 0 | 0 |
| training/data/v3/seeds/d_multilingual.jsonl | 60 | 0 | 0 |
| training/data/v3/seeds/d_noul.jsonl | 27 | 0 | 0 |
| training/data/v3/seeds/d_sentiment.jsonl | 43 | 0 | 0 |
| training/data/v3/seeds/d_support_route.jsonl | 45 | 0 | 0 |
| training/data/v3/teacher_t2dxs_v7core.jsonl | 35354 | 59 | 6 |
| training/data/v3/train.jsonl | 117925 | 91 | 2 |
| training/data/v3/v2/dev.jsonl | 6000 | 6 | 1 |
| training/data/v3/v2/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v2/train.jsonl | 363631 | 431 | 9 |
| training/data/v3/v3/core.jsonl | 80000 | 139 | 9 |
| training/data/v3/v3/dev.jsonl | 6000 | 6 | 1 |
| training/data/v3/v3/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v3/train.jsonl | 367512 | 441 | 9 |
| training/data/v3/v4/core.jsonl | 80000 | 159 | 8 |
| training/data/v3/v4/dev.jsonl | 6000 | 3 | 1 |
| training/data/v3/v4/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v4/train.jsonl | 369521 | 437 | 9 |
| training/data/v3/v5/core.jsonl | 80000 | 156 | 8 |
| training/data/v3/v5/dev.jsonl | 6000 | 0 | 0 |
| training/data/v3/v5/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v5/train.jsonl | 369692 | 424 | 9 |
| training/data/v3/v6/core.jsonl | 80000 | 128 | 9 |
| training/data/v3/v6/dev.jsonl | 6000 | 4 | 1 |
| training/data/v3/v6/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v6/train.jsonl | 369258 | 453 | 9 |
| training/data/v3/v7/core.jsonl | 80000 | 121 | 8 |
| training/data/v3/v7/dev.jsonl | 6000 | 3 | 1 |
| training/data/v3/v7/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v7/train.jsonl | 369363 | 433 | 10 |
| training/data/v3/v8/core.jsonl | 80000 | 78 | 9 |
| training/data/v3/v8/dev.jsonl | 6000 | 3 | 1 |
| training/data/v3/v8/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v8/train.jsonl | 369248 | 432 | 10 |
| training/data/v3/v9/core.jsonl | 80000 | 88 | 7 |
| training/data/v3/v9/dev.jsonl | 6000 | 4 | 1 |
| training/data/v3/v9/dev_ood.jsonl | 4000 | 0 | 0 |
| training/data/v3/v9/train.jsonl | 369384 | 405 | 10 |

## Contaminated (≥ 50%)

| id | name | 6-grams | in any training line | best single line | best file:line | sample shared 6-gram (blind side) |
|---:|---|---:|---:|---:|---|---|
| 3018 | Unit conversion: no model | 1 | 100.0% | 100.0% | training/data/v3/seeds/c_tool_route.jsonl:50 | convert 72 degrees fahrenheit to celsius |

## Watch (20–50%)

None.

## Top 15 by overlap (all cases)

| id | name | 6-grams | in any training line | best single line | best file:line | sample shared 6-gram (blind side) |
|---:|---|---:|---:|---:|---|---|
| 3018 | Unit conversion: no model | 1 | 100.0% | 100.0% | training/data/v3/seeds/c_tool_route.jsonl:50 | convert 72 degrees fahrenheit to celsius |
| 3052 | RAG keyword-only overlap | 24 | 8.3% | 8.3% | training/data/v3/v8/core.jsonl:14998 | the api key for the billing |
| 3024 | Do not memorize a secret | 15 | 6.7% | 6.7% | training/data/public/civil_comments.jsonl:1171 | so you don t have to |
| 3002 | Backdoor injected via code comment | 46 | 4.3% | 4.3% | training/data/dev.jsonl:154 | task fix the off by one |
| 4020 | intent-paraphrased-workspace-ownership-transfer | 50 | 4.0% | 4.0% | training/data/v3/seeds/b_lead.jsonl:103 | at the end of the month |
| 4005 | prompt-injection-buried-in-vendor-invoice-rag | 222 | 5.0% | 3.2% | training/data/v3/seeds/b_contract_clause.jsonl:11 | 1 5 per month or the |
| 4027 | bug-repro-complete-deterministic-curl-and-stacktrace | 76 | 2.6% | 2.6% | training/data/v3/seeds/b_support_route.jsonl:25 | typeerror cannot read properties of null |
| 4034 | contract-clause-unlimited-indemnity-and-ip-assignment-trap | 203 | 6.4% | 2.5% | training/data/v3/seeds/b_contract_clause.jsonl:6 | customer may terminate this agreement for |
| 4014 | handoff-enterprise-custom-baa-negotiation | 49 | 2.0% | 2.0% | training/data/v3/seeds/b_support_route.jsonl:78 | your hipaa business associate agreement baa |
| 4017 | support-triage-ambiguous-seat-limit-403-on-api | 68 | 1.5% | 1.5% | training/data/v3/v7/train.jsonl:353030 | we can t tell if the |
| 4038 | answer-grading-accurate-http-429-retry-after-explanation | 96 | 1.0% | 1.0% | training/data/v3/seeds/c_rag.jsonl:214 | http 429 too many requests indicates |
| 3001 | Skip TLS verification in prod | 23 | 0.0% | 0.0% | - | - |
| 3003 | Clear rename with negation | 26 | 0.0% | 0.0% | - | - |
| 3004 | Vague performance request | 0 | 0.0% | 0.0% | - | - |
| 3005 | German: add null check | 17 | 0.0% | 0.0% | - | - |

## data-1 note (2026-10-29 02:02 local)

- **The flagged case (3018) is a coincidental overlap, not a leak.**
  - Its whole state is one six-word stock phrase (a textbook unit-conversion request). That phrase also appears in an LLM seed bank, so the case shares its only 6-gram.
  - The seed file was written on 2026-10-28 21:08–21:15, about 4.5 h **before** blind-C existed (01:53 on 10-29). The overlap therefore cannot come from blind-C.
  - It does make 3018 an "easy" in-distribution case. I am keeping it and noting it here. Excluding it would change blind-C by at most 1/100.
- **All other cases** are at 8.3% or below for best single line. The shared 6-grams are generic phrases.
- **Verdict:** no material contamination of blind-C.
