// Collects every <!-- num:key -->value<!-- /num --> marker in README.md and docs/*.md
// and writes docs/_numbers.json as { key: { value, source } }.
// Run: node docs/assets/collect-numbers.mjs
// When a new model is promoted, update the values in _numbers.json, then run
// `node docs/build-html.mjs --apply-numbers` to push them into every markdown file.
import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const docs = join(dirname(fileURLToPath(import.meta.url)), "..");
const root = join(docs, "..");
const files = [join(root, "README.md"), ...readdirSync(docs).filter((f) => f.endsWith(".md") && !f.startsWith("_")).map((f) => join(docs, f))];
const re = /<!-- num:([\w.\-]+) -->([\s\S]*?)<!-- \/num -->/g;

const SB = "artifacts/parity/scoreboard.md";
const sources = [
  [/^k2\.p50\.clean$/, "artifacts/parity/msd1/positioning.md:21; artifacts/parity/jev/model-audit.md:25 (warm, short prompts)"],
  [/^k2\.size$/, "models/keel-2/onnx/model_quantized.onnx (12,970,711 bytes)"],
  [/^k3\.size$/, "models/keel-3/onnx/model_quantized.onnx (17,744,999 bytes)"],
  [/^pro\.size$/, "models/candidates/t2-dxs-b3/onnx (108,366,341 bytes)"],
  [/^k3\.train\.steps$/, "training/runs/t1-r2/done.json; artifacts/parity/train-1.md:58"],
  [/^k[23]\.p95\.idle$/, "artifacts/parity/train-r2.md (idle latency, scripts/keel-latency.ts, one model per process; training/runs/latency-idle-separate.json)"],
  [/^k3\.final\.pass$/, "artifacts/parity/train-r2.md (t1-r11 pass)"],
  [/^k[23]\.blindc/, "artifacts/parity/t1-r11-parity.md (blind-c confirmation rows)"],
  [/^llm\.blindc/, "artifacts/parity/t1-r11-parity.md (claude-haiku-4.5 cache, 39 of 100 answered)"],
  [/^k2\.blind\.(lat|p50)$/, "artifacts/parity/t1-r11-parity.md (loaded process, several models)"],
  [/^k2\./, `${SB} (Keel-2 baseline, parity harness)`],
  [/^k3\./, "artifacts/parity/t1-r11-parity.md; " + SB + " (Keel-3 promotion entry, t1-r11)"],
  [/^pro\./, `${SB} (t2-dxs-b3 entry)`],
  [/^lex\./, `${SB} (lexical decider-1.2.0)`],
  [/^llm\.(h20|hb20|open60|h100)$/, `${SB}; artifacts/keel-ab-report.md (gpt-5-mini via Copilot CLI)`],
  [/^llm\./, `${SB} (claude-haiku-4.5 via Copilot CLI, blind/held-out 334)`],
  [/^pub\.k2\./, "artifacts/parity/public/keel-2.md"],
  [/^pub\.t1r1\./, "artifacts/parity/public/t1-r1.md"],
  [/^tok\.k2\./, "artifacts/parity/tokens/report.md (Keel-2, tau 0.6)"],
  [/^tok\.k3\./, "artifacts/parity/tokens/report-t1-r2e.md (Keel-3 RC t1-r2e)"],
];

const out = {};
const conflicts = [];
for (const f of files) {
  const text = readFileSync(f, "utf8");
  for (const m of text.matchAll(re)) {
    const [, key, value] = m;
    if (out[key] && out[key].value !== value) conflicts.push(`${key}: "${out[key].value}" vs "${value}" in ${f}`);
    if (!out[key]) {
      const src = sources.find(([r]) => r.test(key));
      out[key] = { value, source: src ? src[1] : "UNKNOWN" };
    }
  }
}
const sorted = Object.fromEntries(Object.keys(out).sort().map((k) => [k, out[k]]));
writeFileSync(join(docs, "_numbers.json"), JSON.stringify(sorted, null, 2) + "\n", "utf8");
console.log(`${Object.keys(sorted).length} keys -> docs/_numbers.json`);
for (const c of conflicts) console.warn(`CONFLICT ${c}`);
for (const [k, v] of Object.entries(sorted)) if (v.source === "UNKNOWN") console.warn(`NO SOURCE ${k}`);
