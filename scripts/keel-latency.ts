/**
 * In-process latency of a Keel model dir: warm-up, then N sequential calls over the labeled-50 states.
 * Each model runs in its own child process: an onnxruntime session keeps its intra-op threads spinning,
 * so timing a second model in the same process roughly doubles its p95.
 *
 *   node --experimental-strip-types scripts/keel-latency.ts --model models/keel-2 [--model ...] [--calls 200] [--warm 20]
 */
import { execFileSync } from "node:child_process";
import path from "node:path";
import { EVAL_CASES } from "../src/lib/decider/eval-set.ts";
import { prepare } from "../src/lib/decider/eval.ts";
import { loadModel, neuralWeights } from "../src/lib/decider/neural.server.ts";

const args = process.argv.slice(2);
const flags = (name: string) => args.flatMap((a, i) => (a === name && args[i + 1] ? [args[i + 1]] : []));
const calls = Number(flags("--calls")[0] ?? 200);
const warm = Number(flags("--warm")[0] ?? 20);
const requests = EVAL_CASES.map(prepare);
const q = (xs: number[], p: number) => xs[Math.min(xs.length - 1, Math.floor(p * xs.length))];

const models = flags("--model");
if (models.length > 1) {
  for (const m of models) {
    const rest = args.filter((a, i) => a !== "--model" && args[i - 1] !== "--model");
    process.stdout.write(execFileSync(process.execPath, [...process.execArgv, process.argv[1], "--model", m, ...rest]));
  }
  process.exit(0);
}

for (const m of models) {
  const dir = path.resolve(m);
  const model = await loadModel(dir);
  if (!model) throw new Error(`cannot load ${m}`);
  for (let i = 0; i < warm; i++) await neuralWeights(requests[i % requests.length], dir);
  const ms: number[] = [];
  for (let i = 0; i < calls; i++) {
    const t = performance.now();
    await neuralWeights(requests[i % requests.length], dir);
    ms.push(performance.now() - t);
  }
  ms.sort((a, b) => a - b);
  console.log(JSON.stringify({ model: m, id: model.config.id, threads: model.config.threads, calls, p50: +q(ms, 0.5).toFixed(2), p95: +q(ms, 0.95).toFixed(2), max: +ms[ms.length - 1].toFixed(2) }));
}
