// Programmatic 6-gram contamination check: blind-C eval states vs every training jsonl.
// Prints only statistics, ids and n-grams taken from the blind side, so the author
// stays blind to training content.
// Usage: node --experimental-strip-types artifacts/parity/blind-c/contamination-check.ts
import { createReadStream, readdirSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { BLIND_C_CASES as BLIND_CASES } from "../../../src/lib/decider/eval-blind-c.ts";

const N = 6;
const root = path.join("training", "data");
const out = path.join("artifacts", "parity", "blind-c", "contamination.md");

function leaves(v: unknown, acc: string[] = []): string[] {
  if (typeof v === "string") acc.push(v);
  else if (Array.isArray(v)) v.forEach((x) => leaves(x, acc));
  else if (v && typeof v === "object") Object.values(v).forEach((x) => leaves(x, acc));
  return acc;
}
const tokens = (s: string) => s.toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
function grams(text: string): Set<string> {
  const t = tokens(text);
  const g = new Set<string>();
  for (let i = 0; i + N <= t.length; i++) g.add(t.slice(i, i + N).join(" "));
  return g;
}

type Case = { id: number; name: string; grams: Set<string>; hit: Set<string>; best: { file: string; line: number; shared: number } };
const cases: Case[] = BLIND_CASES.map((c) => ({
  id: c.id, name: c.name,
  grams: grams(leaves(c.state).join("\n")),
  hit: new Set<string>(), best: { file: "", line: 0, shared: 0 },
}));
const owners = new Map<string, Case[]>();
for (const c of cases) for (const g of c.grams) (owners.get(g) ?? owners.set(g, []).get(g)!).push(c);

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = path.join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : p.endsWith(".jsonl") ? [p] : [];
  });
}

const files = walk(root);
const perFile: { file: string; lines: number; linesWithHit: number; casesTouched: number }[] = [];
for (const file of files) {
  let lines = 0, linesWithHit = 0;
  const touched = new Set<number>();
  const rl = readline.createInterface({ input: createReadStream(file, "utf8"), crlfDelay: Infinity });
  for await (const raw of rl) {
    if (!raw.trim()) continue;
    lines++;
    let text = raw;
    try { text = leaves(JSON.parse(raw)).join("\n"); } catch { /* raw line */ }
    const shared = new Map<Case, number>();
    for (const g of grams(text)) {
      const os = owners.get(g);
      if (!os) continue;
      for (const c of os) { c.hit.add(g); shared.set(c, (shared.get(c) ?? 0) + 1); }
    }
    if (shared.size) linesWithHit++;
    for (const [c, n] of shared) {
      touched.add(c.id);
      if (n > c.best.shared) c.best = { file, line: lines, shared: n };
    }
  }
  perFile.push({ file, lines, linesWithHit, casesTouched: touched.size });
  console.log(`${file}: ${lines} lines, ${linesWithHit} with any shared 6-gram, ${touched.size} blind cases touched`);
}

const rows = cases.map((c) => ({
  ...c,
  frac: c.grams.size ? c.hit.size / c.grams.size : 0,
  bestFrac: c.grams.size ? c.best.shared / c.grams.size : 0,
})).sort((a, b) => b.bestFrac - a.bestFrac || b.frac - a.frac);
const flagged = rows.filter((r) => r.bestFrac >= 0.5 || r.frac >= 0.5);
const watch = rows.filter((r) => !flagged.includes(r) && (r.bestFrac >= 0.2 || r.frac >= 0.2));
const anyHit = rows.filter((r) => r.hit.size > 0);
const pct = (x: number) => `${(100 * x).toFixed(1)}%`;
const table = (rs: typeof rows) => [
  "| id | name | 6-grams | in any training line | best single line | best file:line | sample shared 6-gram (blind side) |",
  "|---:|---|---:|---:|---:|---|---|",
  ...rs.map((r) => `| ${r.id} | ${r.name} | ${r.grams.size} | ${pct(r.frac)} | ${pct(r.bestFrac)} | ${r.best.file ? `${r.best.file.replace(/\\/g, "/")}:${r.best.line}` : "-"} | ${[...r.hit][0] ?? "-"} |`),
];

const md = [
  "# Blind suite contamination check (6-gram)",
  "",
  `Generated ${new Date().toISOString()} by \`artifacts/parity/blind-c/contamination-check.ts\` (programmatic; training content was never read by the blind-suite authors).`,
  "",
  `Method: lower-cased Unicode word tokens; every distinct ${N}-gram of each blind case state (all string leaves of \`state\`) is looked up in every \`training/data/**/*.jsonl\` line (all string leaves). "In any training line" = share of a case's 6-grams that occur anywhere in training; "best single line" = most 6-grams shared with one training line (near-duplicate signal).`,
  "",
  `Thresholds: **contaminated** if best single line ≥ 50% or any-line ≥ 50%; **watch** if ≥ 20%.`,
  "",
  `## Result: ${flagged.length} contaminated, ${watch.length} watch, ${anyHit.length}/${rows.length} cases share at least one 6-gram`,
  "",
  "## Files scanned",
  "",
  "| file | lines | lines sharing ≥1 blind 6-gram | blind cases touched |",
  "|---|---:|---:|---:|",
  ...perFile.map((f) => `| ${f.file.replace(/\\/g, "/")} | ${f.lines} | ${f.linesWithHit} | ${f.casesTouched} |`),
  "",
  "## Contaminated (≥ 50%)",
  "",
  ...(flagged.length ? table(flagged) : ["None."]),
  "",
  "## Watch (20–50%)",
  "",
  ...(watch.length ? table(watch) : ["None."]),
  "",
  "## Top 15 by overlap (all cases)",
  "",
  ...table(rows.slice(0, 15)),
  "",
].join("\n");
writeFileSync(out, md);
console.log(`flagged=${flagged.length} watch=${watch.length} anyHit=${anyHit.length}/${rows.length} -> ${out}`);
