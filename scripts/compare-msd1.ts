/**
 * Live comparison against Microsoft-Decision-1 (MSD1). Opt-in; ~100 short states cost
 * well under one cent at $0.042 per million input tokens. Do not loop this script.
 *
 * OpenRouter:
 *   $env:OPENROUTER_API_KEY="..."; npm run keel:compare-msd1
 * Microsoft Foundry (deployment of Microsoft-Decision-1):
 *   $env:MSD1_FOUNDRY_ENDPOINT="https://<resource>.services.ai.azure.com"   # or AZURE_AI_ENDPOINT
 *   $env:MSD1_FOUNDRY_DEPLOYMENT="<deployment-name>"                        # or AZURE_AI_DEPLOYMENT
 *   $env:MSD1_FOUNDRY_API_KEY="..."   # or AZURE_AI_API_KEY; or $env:MSD1_USE_AZ_TOKEN="1" to use `az login`
 *   npm run keel:compare-msd1
 *
 * Options: --suites holdout-20,holdout-b-20,open-60[,blind][,labeled-50]  --max-calls 300
 *          --out artifacts/parity/msd1/live-compare
 * `blind` is added by default only when artifacts/parity/blind/READY.json exists.
 * Without a credential it still writes the report, with msd1Compared:false and the reason.
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { pathToFileURL } from "node:url";
import type { EvalCase } from "../src/lib/decider/eval-set.ts";
import { EVAL_CASES } from "../src/lib/decider/eval-set.ts";
import { HOLDOUT_CASES } from "../src/lib/decider/eval-holdout.ts";
import { HOLDOUT_B_CASES } from "../src/lib/decider/eval-holdout-b.ts";
import { OPEN_CASES } from "../src/lib/decider/eval-open.ts";
import { localWeights } from "../src/lib/decider/local.ts";
import { compareMsd1, DEFAULT_MAX_CALLS, FOUNDRY_TOKEN_RESOURCE, msd1Markdown, resolveMsd1Config } from "../src/lib/decider/msd1-compare.ts";
import { neuralWeights } from "../src/lib/decider/neural.server.ts";
import { CONCRETE_MODEL, LEXICAL_MODEL, type DecisionRequest } from "../src/lib/decider/wire.ts";

const arg = (name: string) => {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
};
const blindReady = existsSync("artifacts/parity/blind/READY.json");
const wanted = (arg("--suites") ?? ["holdout-20", "holdout-b-20", "open-60", ...(blindReady ? ["blind"] : [])].join(","))
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const maxCalls = Number(arg("--max-calls") ?? DEFAULT_MAX_CALLS);
const out = arg("--out") ?? "artifacts/parity/msd1/live-compare";

const isCase = (x: unknown): x is EvalCase => !!x && typeof x === "object" && "state" in x && "questions" in x && "expect" in x;

async function blindCases(): Promise<EvalCase[]> {
  if (!blindReady) throw new Error("blind suite requested but artifacts/parity/blind/READY.json does not exist yet");
  const mod = (await import(pathToFileURL("src/lib/decider/eval-blind.ts").href)) as Record<string, unknown>;
  const lists = Object.values(mod).filter((v): v is EvalCase[] => Array.isArray(v) && v.length > 0 && v.every(isCase));
  if (!lists.length) throw new Error("eval-blind.ts exports no EvalCase[]");
  return lists.sort((a, b) => b.length - a.length)[0]!;
}

const known: Record<string, () => EvalCase[] | Promise<EvalCase[]>> = {
  "labeled-50": () => EVAL_CASES,
  "holdout-20": () => HOLDOUT_CASES,
  "holdout-b-20": () => HOLDOUT_B_CASES,
  "open-60": () => OPEN_CASES,
  blind: blindCases,
};
const suites: { name: string; cases: EvalCase[] }[] = [];
for (const name of wanted) {
  if (!known[name]) throw new Error(`unknown suite ${name}; known: ${Object.keys(known).join(", ")}`);
  suites.push({ name, cases: await known[name]!() });
}

let entraToken: string | undefined;
if (process.env.MSD1_USE_AZ_TOKEN === "1") {
  try {
    entraToken = execFileSync("az", ["account", "get-access-token", "--resource", FOUNDRY_TOKEN_RESOURCE, "--query", "accessToken", "-o", "tsv"], {
      encoding: "utf8",
      shell: process.platform === "win32",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim() || undefined;
  } catch {
    entraToken = undefined;
  }
}

let keelModel = CONCRETE_MODEL;
const judge = async (request: DecisionRequest) => {
  const bag = await neuralWeights(request);
  if (bag) return bag;
  keelModel = LEXICAL_MODEL;
  return localWeights(request);
};

const report = await compareMsd1(suites, judge, CONCRETE_MODEL, resolveMsd1Config(process.env, entraToken), fetch, maxCalls);
report.keelModel = keelModel;
mkdirSync(dirname(out), { recursive: true });
writeFileSync(`${out}.json`, JSON.stringify(report, null, 2));
const md = msd1Markdown(report);
writeFileSync(`${out}.md`, md);
console.log(md.split("\n").slice(0, 22).join("\n"));
