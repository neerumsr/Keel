/**
 * Keel benchmark: Keel-3 (neural) vs Keel-1 (lexical) vs Keel-off (naive) on
 * the 50 labeled cases, the 20 held-out cases, and the 60 open-domain cases.
 *
 *   node --experimental-strip-types scripts/keel-bench.ts [--model models/keel-3] [--out artifacts/keel-3-report]
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { EVAL_CASES } from "../src/lib/decider/eval-set.ts";
import { HOLDOUT_CASES } from "../src/lib/decider/eval-holdout.ts";
import { HOLDOUT_B_CASES } from "../src/lib/decider/eval-holdout-b.ts";
import { OPEN_CASES } from "../src/lib/decider/eval-open.ts";
import { evaluate, reportMarkdown, type EvalReport } from "../src/lib/decider/eval.ts";
import { localWeights } from "../src/lib/decider/local.ts";
import { loadModel, neuralWeights } from "../src/lib/decider/neural.server.ts";
import { CONCRETE_MODEL, LEXICAL_MODEL } from "../src/lib/decider/wire.ts";

const args = process.argv.slice(2);
const flag = (name: string) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const dir = flag("--model") ? path.resolve(flag("--model")!) : undefined;
const out = flag("--out") ?? "artifacts/keel-3-report";

const model = await loadModel(dir);
if (!model) {
  console.error("No Keel model could be loaded.");
  process.exit(1);
}
const neural = async (request: Parameters<typeof localWeights>[0]) => (await neuralWeights(request, dir))!;

const suites = [
  { name: "labeled-50", cases: EVAL_CASES },
  { name: "holdout-20", cases: HOLDOUT_CASES },
  { name: "holdout-b-20", cases: HOLDOUT_B_CASES },
  { name: "open-60", cases: OPEN_CASES },
];

type Row = { suite: string; judge: string; report: EvalReport };
const results: Row[] = [];
for (const suite of suites) {
  results.push({ suite: suite.name, judge: LEXICAL_MODEL, report: await evaluate(suite.cases, localWeights, { model: LEXICAL_MODEL }) });
  results.push({
    suite: suite.name,
    judge: model.config.id,
    report: await evaluate(suite.cases, neural, { model: model.config.id, latencyBudgetMs: 50 }),
  });
}

const pct = (x: { correct: number; scored: number }) => (x.scored ? `${x.correct}/${x.scored} (${Math.round((100 * x.correct) / x.scored)}%)` : "—");
const lines: string[] = [
  `# Keel benchmark`,
  ``,
  `Generated ${new Date().toISOString()}. Keel weights: \`${path.relative(process.cwd(), model.dir)}\` (${model.config.id}${model.config.trainedOn ? `, trained on ${model.config.trainedOn}` : ", zero-shot base"}).`,
  ``,
  `Jev was not compared here. Live Jev runs only through \`scripts/compare-jev.ts\` with TYPESAFE_API_KEY.`,
  ``,
  `| Suite | Judge | Choice | Score band | Noul band | Safety misses | Naive choice | p50 ms | p95 ms |`,
  `|---|---|---:|---:|---:|---:|---:|---:|---:|`,
];
for (const row of results) {
  const r = row.report;
  lines.push(
    `| ${row.suite} | ${row.judge} | ${pct(r.keelOn.choice)} | ${pct(r.keelOn.score)} | ${pct(r.keelOn.noul)} | ${r.keelOn.safetyMisses} | ${pct(r.keelOffNaive.choice)} | ${r.keelOn.latencyMs.median} | ${r.keelOn.latencyMs.p95} |`,
  );
}
lines.push("");
for (const row of results.filter((r) => r.judge !== LEXICAL_MODEL)) {
  lines.push(reportMarkdown(row.report, `${row.suite} · ${row.judge}`).replace(/^# /, "## "));
}

mkdirSync(path.dirname(out), { recursive: true });
writeFileSync(`${out}.json`, JSON.stringify({ model: model.config.id, concrete: CONCRETE_MODEL, dir: model.dir, results }, null, 2));
writeFileSync(`${out}.md`, lines.join("\n"));
console.log(lines.slice(0, 8 + results.length).join("\n"));
