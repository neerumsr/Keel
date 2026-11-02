# Licenses of downloaded weights / data

| Artifact | Source | License | Redistribution of fine-tuned weights under Apache-2.0 | Added by | Notes |
|---|---|---|---|---|---|
| models/teacher-deberta-xsmall | https://huggingface.co/MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33 (config `_name_or_path` microsoft/deberta-v3-xsmall; pre-existing on disk, origin inferred from config + ONNX layout) | MIT (model card) | Yes (MIT is permissive; keep MIT notice) | train-2 (recorded) | "all-33" NLI mix includes datasets with mixed licenses (e.g. ANLI CC-BY-NC); weights themselves MIT. Prefer `-c` models for release lineage. |
| models/teacher-deberta-base-c | https://huggingface.co/MoritzLaurer/deberta-v3-base-zeroshot-v2.0-c | MIT | Yes (keep MIT notice) | train-2 | "-c" = trained only on commercially-friendly data (Mixtral synthetic + MNLI + FEVER-NLI). Base: microsoft/deberta-v3-base (MIT). |

## Public benchmark datasets (added by msd1-2)

Downloaded via Hugging Face `datasets` for evaluation (`training/public/eval/`) and, where marked, converted train splits (`training/data/public/`). Raw data is not redistributed by us; converted train groups inherit the source license (share-alike where noted).

| Dataset (HF id) | Source / license URL | License | Used for | Train groups OK? | Added by | Notes |
|---|---|---|---|---|---|---|
| nyu-mll/glue sst2 | https://nlp.stanford.edu/sentiment/ | unspecified (research use customary) | eval (validation) | No (unclear license) | msd1-2 | |
| fancyzhx/ag_news | http://groups.di.unipi.it/~gulli/AG_corpus_of_news_articles.html | unspecified; academic/non-commercial terms | eval (test) | No | msd1-2 | |
| dair-ai/emotion (split) | https://huggingface.co/datasets/dair-ai/emotion | educational/research use only | eval (test) | No | msd1-2 | |
| nyu-mll/glue mnli | https://cims.nyu.edu/~sbowman/multinli/ | OANC + CC BY-SA 3.0 portions | eval (validation_matched) + train groups | Yes (attribute; share-alike parts) | msd1-2 | keel-2 already replayed MNLI train |
| facebook/anli | https://github.com/facebookresearch/anli | CC BY-NC 4.0 | eval (test_r1-r3) | **No (non-commercial)** | msd1-2 | |
| PolyAI/banking77 | https://huggingface.co/datasets/PolyAI/banking77 | CC BY 4.0 | eval (test) + train groups | Yes | msd1-2 | |
| clinc/clinc_oos plus | https://github.com/clinc/oos-eval | CC BY 3.0 | eval (test) + train groups | Yes | msd1-2 | |
| allenai/winogrande winogrande_xl | https://github.com/allenai/winogrande | CC BY 4.0 | eval (validation) + train groups | Yes | msd1-2 | |
| Rowan/hellaswag | https://github.com/rowanz/hellaswag | MIT | eval (validation) + train groups | Yes | msd1-2 | |
| allenai/ai2_arc (Easy, Challenge) | https://allenai.org/data/arc | CC BY-SA 4.0 | eval (test) + train groups | Yes (share-alike) | msd1-2 | |
| cais/mmlu all | https://github.com/hendrycks/test | MIT | eval (test) | n/a (no train split used) | msd1-2 | |
| google/boolq | https://github.com/google-research-datasets/boolean-questions | CC BY-SA 3.0 | eval (validation) + train groups | Yes (share-alike) | msd1-2 | |
| nyu-mll/glue rte | https://aclweb.org/aclwiki/Recognizing_Textual_Entailment | unspecified | eval (validation) | No (unclear) | msd1-2 | |
| nyu-mll/glue mrpc | https://www.microsoft.com/en-us/download/details.aspx?id=52398 | MSR Paraphrase Corpus license | eval (test) | No | msd1-2 | |
| google/civil_comments | https://huggingface.co/datasets/google/civil_comments | CC0 1.0 | eval (test prefix) + train groups | Yes | msd1-2 | |
| nyu-mll/glue stsb | https://ixa2.si.ehu.eus/stswiki/index.php/STSbenchmark | mixed sources; CC BY-SA 3.0 annotations | eval (validation) + train groups | Yes (share-alike; mixed text sources, check before release) | msd1-2 | |
| tasksource/esci | https://github.com/amazon-science/esci-data | Apache 2.0 | eval (test prefix, US) + train groups | Yes | msd1-2 | |
| apolinario/decision-index board JSON | https://github.com/apolinario/decision-index | MIT | third-party Jev numbers (artifacts/parity/msd1/source/di-*.json) | n/a | msd1-2 | numbers only |

## SDKs installed for wire-parity proofs (added by jev-1)

Installed only in the session scratch folder (not in the repo, not redistributed) to prove drop-in compatibility; see `artifacts/parity/jev/wire-audit.md` §4.

| Package | Source | License | Used for | Added by |
|---|---|---|---|---|
| @typesafe-ai/sdk 0.7.0 | https://www.npmjs.com/package/@typesafe-ai/sdk (github.com/typesafe-ai/typesafe-sdk-js) | MIT | end-to-end client test against local Keel | jev-1 |
| typesafe-sdk 0.7.5 (+ deps httpx2, pydantic, tenacity, anyio, truststore) | https://pypi.org/project/typesafe-sdk/ | MIT (`License-Expression: MIT`) | end-to-end client test against local Keel | jev-1 |
