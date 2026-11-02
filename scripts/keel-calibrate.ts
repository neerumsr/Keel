/**
 * Fit per-type temperature, lexical blend, and the abstain threshold for an exported Keel model on DEV
 * data only (training/data/dev.jsonl or --dev), using the exact Node runtime path
 * (int8 ONNX margins + lexical judge). Held-out/open/blind suites are never read.
 *
 *   node --experimental-strip-types scripts/keel-calibrate.ts --model models/candidates/t1-r0 [--dev training/data/dev.jsonl] [--write]
 */
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { localWeights } from "../src/lib/decider/local.ts";
import { groupProbabilities, rawMargins, readConfig, type KeelConfig } from "../src/lib/decider/neural.server.ts";
import { distribute, tryParse } from "../src/lib/decider/wire.ts";

const args = process.argv.slice(2);
const flag = (name: string) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const dir = path.resolve(flag("--model") ?? "models/keel-2");
const devPath = path.resolve(flag("--dev") ?? "training/data/dev.jsonl");
const write = args.includes("--write");

type Row = { family: string; state: unknown; question: { type: "choice" | "score" | "noul" } & Record<string, unknown>; target: number[] };
const rows = readFileSync(devPath, "utf8")
  .split(/\r?\n/)
  .filter((line) => line.trim())
  .map((line) => JSON.parse(line) as Row)
  .filter((row) => row.family !== "nli" && row.question);

type Item = { type: "choice" | "score" | "noul"; raw: number[]; lex: number[]; target: number[] };
const items: Item[] = [];
for (const row of rows) {
  const parsed = tryParse({ state: row.state as never, questions: { q: row.question } });
  if (!parsed.ok) continue;
  const request = parsed.request;
  const question = request.questions[0]!;
  const raw = (await rawMargins(request, dir))?.[0]?.margins;
  if (!raw) throw new Error(`model at ${dir} did not load`);
  const bag = localWeights(request)[question.id];
  let lex: number[];
  if (question.type === "noul") {
    const p = Number(bag?.yes ?? 50) / 100;
    lex = [Math.log(Math.max(p, 1e-3) / Math.max(1 - p, 1e-3))];
  } else {
    const keys = question.type === "choice" ? question.options.map((o) => o.key) : question.levels.map((_, i) => String(i));
    lex = distribute(keys.map((key) => Number(bag?.[key] ?? 1))).map((p) => Math.log(Math.max(p, 1e-4)));
  }
  items.push({ type: question.type, raw, lex, target: row.target });
}

const base = readConfig(dir);
const temps = [0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 4, 5];
const blends = [0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 1];
const sig = (x: number) => 1 / (1 + Math.exp(-x));

function score(type: Item["type"], t: number, b: number, abstain = base.abstain.threshold) {
  let nll = 0;
  let correct = 0;
  let n = 0;
  for (const it of items) {
    if (it.type !== type) continue;
    n++;
    if (type === "noul") {
      const p = sig((it.raw[0]! - it.raw[1]!) / t + base.noulBias + b * it.lex[0]!);
      const y = it.target[0]!;
      nll -= y * Math.log(Math.max(p, 1e-6)) + (1 - y) * Math.log(Math.max(1 - p, 1e-6));
      correct += Number(p >= 0.5 === y >= 0.5);
      continue;
    }
    const cfg: KeelConfig = {
      ...base,
      temperature: { ...base.temperature, [type]: t },
      lexicalBlend: { ...base.lexicalBlend, [type]: b },
      abstain: { ...base.abstain, threshold: abstain },
    };
    const probs = groupProbabilities(cfg, type, it.raw, it.lex);
    nll -= it.target.reduce((acc, y, i) => acc + y * Math.log(Math.max(probs[i] ?? 0, 1e-6)), 0);
    if (Math.max(...it.target) >= 0.5) correct += Number(probs.indexOf(Math.max(...probs)) === it.target.indexOf(Math.max(...it.target)));
    else correct += 1;
  }
  return { nll: nll / Math.max(1, n), acc: correct / Math.max(1, n), n };
}

const chosen: Record<string, { temperature: number; blend: number; nll: number; acc: number; n: number }> = {};
for (const type of ["choice", "score", "noul"] as const) {
  let best = { temperature: 1, blend: 0, nll: Infinity, acc: 0, n: 0 };
  for (const t of temps) {
    for (const b of blends) {
      const s = score(type, t, b);
      if (s.nll < best.nll - 1e-9) best = { temperature: t, blend: b, ...s };
    }
  }
  chosen[type] = best;
}
let abstain = { threshold: base.abstain.threshold, nll: Infinity };
for (const th of [0, 0.03, 0.06, 0.1, 0.15, 0.2, 0.3]) {
  const c = chosen.choice!;
  const sc = chosen.score!;
  const nll = score("choice", c.temperature, c.blend, th).nll * c.n + score("score", sc.temperature, sc.blend, th).nll * sc.n;
  if (nll < abstain.nll - 1e-9) abstain = { threshold: th, nll };
}
for (const type of ["choice", "score"] as const) {
  Object.assign(chosen[type]!, score(type, chosen[type]!.temperature, chosen[type]!.blend, abstain.threshold));
}
console.log(JSON.stringify({ dir, dev: devPath, groups: items.length, abstain: abstain.threshold, chosen }, null, 2));

if (write) {
  const file = path.join(dir, "keel.json");
  const config = JSON.parse(readFileSync(file, "utf8"));
  config.temperature = Object.fromEntries(Object.entries(chosen).map(([k, v]) => [k, v.temperature]));
  config.lexicalBlend = Object.fromEntries(Object.entries(chosen).map(([k, v]) => [k, v.blend]));
  config.abstain = { ...config.abstain, threshold: abstain.threshold };
  config.lexicalBlendSelection = `min dev NLL on ${path.relative(process.cwd(), devPath)} via Node runtime (keel-calibrate.ts); held-out/open/blind not used`;
  config.calibrationNode = chosen;
  writeFileSync(file, JSON.stringify(config, null, 2));
  console.log("wrote", file);
}
