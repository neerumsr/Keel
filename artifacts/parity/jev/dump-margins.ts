/**
 * jev-3 audit helper. Dumps raw entailment margins + lexical priors for every
 * question in the non-blind suites and training/data/dev.jsonl, so calibration
 * and blend sweeps can be done offline in Python (artifacts/parity/jev/audit.py).
 *
 *   node --experimental-strip-types artifacts/parity/jev/dump-margins.ts [--model models/keel-2] [--out artifacts/parity/jev/margins.json]
 *
 * Does NOT read eval-blind*.ts.
 */
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { EVAL_CASES } from "../../../src/lib/decider/eval-set.ts";
import { HOLDOUT_CASES } from "../../../src/lib/decider/eval-holdout.ts";
import { HOLDOUT_B_CASES } from "../../../src/lib/decider/eval-holdout-b.ts";
import { OPEN_CASES } from "../../../src/lib/decider/eval-open.ts";
import { prepare } from "../../../src/lib/decider/eval.ts";
import { localWeights } from "../../../src/lib/decider/local.ts";
import { loadModel, rawMargins } from "../../../src/lib/decider/neural.server.ts";
import { tryParse, distribute, type DecisionRequest } from "../../../src/lib/decider/wire.ts";

const args = process.argv.slice(2);
const flag = (name: string) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const dir = path.resolve(flag("--model") ?? "models/keel-2");
const out = flag("--out") ?? "artifacts/parity/jev/margins.json";
if (!(await loadModel(dir))) throw new Error("model failed to load");

function lexFor(request: DecisionRequest) {
  const bag = localWeights(request);
  const res: Record<string, number[]> = {};
  for (const q of request.questions) {
    if (q.type === "noul") res[q.id] = [Number(bag[q.id]?.yes ?? 50) / 100];
    else {
      const keys = q.type === "choice" ? q.options.map((o) => o.key) : q.levels.map((_, i) => String(i));
      res[q.id] = distribute(keys.map((k) => Number(bag[q.id]?.[k] ?? 1)));
    }
  }
  return res;
}

async function record(request: DecisionRequest) {
  const m = (await rawMargins(request, dir))!;
  const lex = lexFor(request);
  return request.questions.map((q) => ({
    qid: q.id,
    type: q.type,
    keys: q.type === "choice" ? q.options.map((o) => o.key) : q.type === "score" ? q.levels.map((_, i) => String(i)) : ["yes", "no"],
    margins: m.find((x) => x.id === q.id)!.margins,
    lex: lex[q.id],
  }));
}

const rows: unknown[] = [];
const suites = [
  ["labeled-50", EVAL_CASES],
  ["holdout-20", HOLDOUT_CASES],
  ["holdout-b-20", HOLDOUT_B_CASES],
  ["open-60", OPEN_CASES],
] as const;
for (const [suite, cases] of suites) {
  for (const item of cases) {
    const request = prepare(item);
    rows.push({ suite, id: item.id, name: item.name, tags: item.tags, state: request.stateText, expect: item.expect, questions: await record(request) });
  }
}

const dev = readFileSync("training/data/dev.jsonl", "utf8").split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
let i = 0;
for (const row of dev) {
  if (row.family === "nli") continue;
  const parsed = tryParse({ model: "decider-latest", state: row.state, questions: { q: row.question } });
  if (!parsed.ok) continue;
  rows.push({ suite: "dev", id: i++, family: row.family, target: row.target, questions: await record(parsed.request) });
}

writeFileSync(out, JSON.stringify({ model: dir, rows }));
console.log(`wrote ${rows.length} rows to ${out}`);
