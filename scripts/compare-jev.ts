/**
 * Live comparison against TypeSafe Jev. Opt-in; costs well under one cent.
 *
 *   $env:TYPESAFE_API_KEY="..."; node --experimental-strip-types scripts/compare-jev.ts [--suite labeled|all]
 *
 * Without the key it still writes the report, with jevCompared:false and the reason.
 * Do not loop this script.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { EVAL_CASES } from "../src/lib/decider/eval-set.ts";
import { HOLDOUT_CASES } from "../src/lib/decider/eval-holdout.ts";
import { HOLDOUT_B_CASES } from "../src/lib/decider/eval-holdout-b.ts";
import { OPEN_CASES } from "../src/lib/decider/eval-open.ts";
import { compare, compareMarkdown } from "../src/lib/decider/jev-compare.ts";
import { localWeights } from "../src/lib/decider/local.ts";
import { neuralWeights } from "../src/lib/decider/neural.server.ts";
import { CONCRETE_MODEL, LEXICAL_MODEL, type DecisionRequest } from "../src/lib/decider/wire.ts";

const all = process.argv.includes("--suite") && process.argv[process.argv.indexOf("--suite") + 1] === "all";
const suites = [{ name: "labeled-50", cases: EVAL_CASES }];
if (all) suites.push({ name: "holdout-20", cases: HOLDOUT_CASES }, { name: "holdout-b-20", cases: HOLDOUT_B_CASES }, { name: "open-60", cases: OPEN_CASES });

let keelModel = CONCRETE_MODEL;
const judge = async (request: DecisionRequest) => {
  const bag = await neuralWeights(request);
  if (bag) return bag;
  keelModel = LEXICAL_MODEL;
  return localWeights(request);
};

const report = await compare(suites, judge, CONCRETE_MODEL, process.env.TYPESAFE_API_KEY?.trim() || undefined);
report.keelModel = keelModel;
mkdirSync("artifacts", { recursive: true });
writeFileSync("artifacts/keel-vs-jev.json", JSON.stringify(report, null, 2));
const md = compareMarkdown(report);
writeFileSync("artifacts/keel-vs-jev.md", md);
console.log(md.split("\n").slice(0, 14).join("\n"));
