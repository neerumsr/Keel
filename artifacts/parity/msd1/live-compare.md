# Keel vs Microsoft-Decision-1 (live)

Live MSD1 was **not** measured. No MSD1 credential: OPENROUTER_API_KEY is not set and no Foundry deployment of Microsoft-Decision-1 is configured (MSD1_FOUNDRY_ENDPOINT + MSD1_FOUNDRY_DEPLOYMENT + key or Entra token). No request was sent. Every MSD1 field is null; nothing was guessed.

| | Keel (decider-2.0.0) all cases | Keel on MSD1-answered | MSD1 |
|---|---:|---:|---:|
| Choice correct | 43/66 | — | — |
| Score in band | 12/24 | — | — |
| Noul in band | 7/14 | — | — |
| Safety misses | 3 | — | — |
| Median ms | 16.82 (in-process) | | — (network round trip) |
| p95 ms | 38.04 | | — |

## Per suite

| Suite | Cases | MSD1 answered | Keel choice | MSD1 choice | Keel score | MSD1 score | Keel noul | MSD1 noul | Keel safety | MSD1 safety |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| holdout-20 | 20 | 0 | 11/15 | — | 4/5 | — | 2/2 | — | 1 | — |
| holdout-b-20 | 20 | 0 | 8/15 | — | 2/5 | — | 1/2 | — | 1 | — |
| open-60 | 60 | 0 | 24/36 | — | 6/14 | — | 4/10 | — | 1 | — |

