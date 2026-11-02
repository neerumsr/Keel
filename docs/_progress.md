# Docs progress (docs-writer-3)

Resume notes. Facts and number sources: see `_numbers.json` once written.

## Done
- Fact-checked every `<!-- num:key -->` marker in README + existing docs (all correct).
- `docs/assets/build-docs.mjs` -> generates `docs/use-cases.md` (50 cases) from `use-cases.data.mjs`.
- `docs/licenses.md` (maintainer-review callouts: CC BY-SA train data, ANLI in base all-33 mix).
- `docs/faq.md`
- `docs/release-notes.md` (Keel 3.0.0-rc.1 draft + 2.0.0 + 1.2.0)

- index.md hub; help-guide, design-doc, why-keel rewritten
- _numbers.json via docs/assets/collect-numbers.mjs (108 keys)
- docs/build-html.mjs (parser, template, 11 SVG diagrams, number + link validation) -> 18 html pages, 0 warnings

- Playwright: 72 screenshots (18 pages x light/dark x 1440/390) in screenshots/docs/, no overflow or console errors; nav, mobile tab, bar charts and diagram arrows fixed.
- Token-leak check: real default token appears in no file under docs/ or README.md.

## Next
- None. When models/keel-3 is promoted: update docs/_numbers.json, run `node docs/build-html.mjs --apply-numbers`, then `node docs/build-html.mjs`.


## 2026-10-29 auth update
- Per-install secret (~/.keel/secret, KEEL_SECRET_FILE), npm run keel:token, keel:agents placeholders, rotation, 127.0.0.1 + KEEL_HOST documented in README, quickstart, api-reference, help-guide, faq, licenses, design-doc, release-notes (Security fixes), integrations, architecture. HTML rebuilt; leak check clean.

## Round 4: Keel-3 promoted (t1-r11)
- _numbers.json regenerated (119 keys; sources point at t1-r11-parity.md, train-r2.md, models/keel-3); --apply-numbers + rebuild: 18 pages, 0 warnings; 72 screenshots refreshed.
- blind-c regression disclosed in README, benchmarks, model-card, release-notes, faq, index; hybrid / pin decider-2.0.0 recommended.
- Token savings stay labelled t1-r2e RC (no keel-3 token report).
- Examples re-captured from decider-3.0.0; alias tables, model search order, dev vs build+start server documented; no Grok/Vercel/sign-in leftovers.
- Next: rerun npm run keel:tokens and public benchmarks on keel-3, then refresh numbers.
