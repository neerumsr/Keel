/**
 * Public benchmark runner: scores a Keel model on the stratified public-dataset samples
 * produced by training/public/build_eval.py, through the production path
 * (tryParse -> neuralWeights -> projectWeights, as in judge.server.ts).
 *
 *   node --experimental-strip-types scripts/keel-public-bench.ts --model models/keel-2 --out artifacts/parity/public/keel-2 [--limit 1000] [--only a,b]
 *
 * If a dataset's label set exceeds the wire's current LIMITS.choiceOptions, production tryParse
 * rejects it; such rows are reported as unsupported and additionally run as a clearly labelled
 * diagnostic that parses the options in LIMITS-sized chunks and concatenates them (same
 * per-option normalization), bypassing only the count limit.
 * Threads: ONNX intra-op threads come from keel.json (4); requests run sequentially.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { loadModel, neuralWeights } from "../src/lib/decider/neural.server.ts";
import { LIMITS, projectWeights, tryParse, type DecisionRequest } from "../src/lib/decider/wire.ts";

const args = process.argv.slice(2);
const flag = (name: string) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const dir = path.resolve(flag("--model") ?? "models/keel-2");
const out = flag("--out") ?? `artifacts/parity/public/${path.basename(dir)}`;
const limit = Number(flag("--limit") ?? 1000);
const only = (flag("--only") ?? "").split(",").filter(Boolean);
const EVAL_DIR = "training/public/eval";

const model = await loadModel(dir);
if (!model) {
  console.error(`No Keel model could be loaded from ${dir}.`);
  process.exit(1);
}

type Item = { id: string; dataset: string; kind: "choice" | "noul" | "score"; request: any; gold: any };
type Pred = { id: string; gold: number; pred: number; conf: number; probs: number[]; expected?: number; target?: number; ms: number };

const manifestFile = path.join(EVAL_DIR, "MANIFEST.json");
const manifest = (existsSync(manifestFile) ? JSON.parse(readFileSync(manifestFile, "utf8")) : {}) as Record<string, any>;
const di = existsSync("artifacts/parity/msd1/source/di-index.json")
  ? JSON.parse(readFileSync("artifacts/parity/msd1/source/di-index.json", "utf8"))
  : null;
// Decision Index (third-party, MIT) benchmark ids for datasets that overlap ours; Jev 1.14 raw score.
const DI_IDS: Record<string, string> = {
  banking77: "4", clinc150: "5", anli: "12", mmlu: "24", arc_easy: "26", arc_challenge: "27",
  winogrande: "28", hellaswag: "29", esci: "37",
};
const jevDI = (name: string) => {
  const id = DI_IDS[name];
  const b = id && di?.jev?.benchmarks?.[id];
  if (!b || typeof b.raw !== "number") return null;
  return { raw: b.raw, metric: di.benchmarks[id].metric as string, benchmark: di.benchmarks[id].dataset as string };
};

function chunkedParse(raw: any): DecisionRequest | null {
  const q = raw.questions.answer;
  const keys = Object.keys(q.criteria);
  const options: any[] = [];
  let base: DecisionRequest | null = null;
  for (let i = 0; i < keys.length; i += LIMITS.choiceOptions) {
    let part = keys.slice(i, i + LIMITS.choiceOptions);
    if (part.length < 2) part = keys.slice(i - 1, i + 1);
    const crit = Object.fromEntries(part.map((k) => [k, q.criteria[k]]));
    const parsed = tryParse({ ...raw, questions: { answer: { ...q, criteria: crit } } });
    if (!parsed.ok) return null;
    base ??= parsed.request;
    const opts = (parsed.request.questions[0] as any).options as any[];
    for (const o of opts) if (!options.some((x) => x.key === o.key)) options.push(o);
  }
  if (!base) return null;
  return { ...base, questions: [{ ...(base.questions[0] as any), options }] };
}

function wilson(k: number, n: number, z = 1.96): [number, number] {
  if (!n) return [0, 0];
  const p = k / n;
  const d = 1 + (z * z) / n;
  const c = (p + (z * z) / (2 * n)) / d;
  const h = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [c - h, c + h];
}

function macroF1(gold: number[], pred: number[]): number {
  const labels = [...new Set(gold)];
  let sum = 0;
  for (const l of labels) {
    let tp = 0, fp = 0, fn = 0;
    for (let i = 0; i < gold.length; i++) {
      if (pred[i] === l && gold[i] === l) tp++;
      else if (pred[i] === l) fp++;
      else if (gold[i] === l) fn++;
    }
    sum += tp ? (2 * tp) / (2 * tp + fp + fn) : 0;
  }
  return labels.length ? sum / labels.length : 0;
}

function ece(conf: number[], correct: boolean[], bins = 10): number {
  let e = 0;
  for (let b = 0; b < bins; b++) {
    const idx = conf.map((c, i) => [c, i] as const).filter(([c]) => (b === 0 ? c >= 0 : c > b / bins) && c <= (b + 1) / bins).map(([, i]) => i);
    if (!idx.length) continue;
    const acc = idx.filter((i) => correct[i]).length / idx.length;
    const avg = idx.reduce((s, i) => s + conf[i], 0) / idx.length;
    e += (idx.length / conf.length) * Math.abs(acc - avg);
  }
  return e;
}

function rank(xs: number[]): number[] {
  const order = xs.map((x, i) => [x, i] as const).sort((a, b) => a[0] - b[0]);
  const r = new Array(xs.length);
  for (let i = 0; i < order.length; ) {
    let j = i;
    while (j + 1 < order.length && order[j + 1][0] === order[i][0]) j++;
    for (let k = i; k <= j; k++) r[order[k][1]] = (i + j) / 2;
    i = j + 1;
  }
  return r;
}

function spearman(a: number[], b: number[]): number {
  const ra = rank(a), rb = rank(b);
  const n = a.length;
  const ma = ra.reduce((s, x) => s + x, 0) / n, mb = rb.reduce((s, x) => s + x, 0) / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) {
    num += (ra[i] - ma) * (rb[i] - mb);
    da += (ra[i] - ma) ** 2;
    db += (rb[i] - mb) ** 2;
  }
  return da && db ? num / Math.sqrt(da * db) : 0;
}

const pctl = (xs: number[], q: number) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length ? s[Math.min(s.length - 1, Math.floor(q * s.length))] : 0;
};

async function score(request: DecisionRequest, item: Item): Promise<Pred> {
  const t0 = performance.now();
  const bag = await neuralWeights(request, dir);
  const answer = projectWeights(request, bag!).answer as any;
  const ms = performance.now() - t0;
  if (answer.type === "noul") {
    const p = answer.noul as number;
    return { id: item.id, gold: item.gold ? 1 : 0, pred: p >= 0.5 ? 1 : 0, conf: Math.max(p, 1 - p), probs: [p], ms };
  }
  const probs = Object.values(answer.probabilities as Record<string, number>);
  let best = 0;
  for (let i = 1; i < probs.length; i++) if (probs[i] > probs[best]) best = i;
  if (answer.type === "choice") {
    const keys = Object.keys(answer.probabilities);
    const pred = keys.indexOf(answer.choice);
    return { id: item.id, gold: item.gold, pred, conf: probs[pred], probs, ms };
  }
  return {
    id: item.id, gold: item.gold.level, pred: Math.round(answer.score), conf: probs[best], probs,
    expected: answer.score, target: item.gold.target, ms,
  };
}

function summarize(name: string, kind: string, preds: Pred[], rejected: number, diagnostic: boolean) {
  const n = preds.length;
  const correct = preds.map((p) => p.pred === p.gold);
  const k = correct.filter(Boolean).length;
  const [lo, hi] = wilson(k, n);
  const res: Record<string, any> = {
    dataset: name, kind, n, rejected, diagnostic, accuracy: n ? k / n : null, ci95: [lo, hi],
    macroF1: macroF1(preds.map((p) => p.gold), preds.map((p) => p.pred)),
    ece: ece(preds.map((p) => p.conf), correct),
    p50ms: pctl(preds.map((p) => p.ms), 0.5), p95ms: pctl(preds.map((p) => p.ms), 0.95),
  };
  if (kind === "noul") {
    res.brier = preds.reduce((s, p) => s + (p.probs[0] - p.gold) ** 2, 0) / Math.max(1, n);
    res.positiveRate = preds.filter((p) => p.pred === 1).length / Math.max(1, n);
  }
  if (kind === "score") {
    const argmaxPred = preds.map((p) => p.probs.indexOf(Math.max(...p.probs)));
    res.accuracyArgmax = argmaxPred.filter((x, i) => x === preds[i].gold).length / Math.max(1, n);
    res.macroF1Argmax = macroF1(preds.map((p) => p.gold), argmaxPred);
    res.within1 = preds.filter((p) => Math.abs(p.expected! - p.gold) <= 1).length / Math.max(1, n);
    res.spearman = spearman(preds.map((p) => p.expected!), preds.map((p) => p.target!));
    res.mae = preds.reduce((s, p) => s + Math.abs(p.expected! - p.target!), 0) / Math.max(1, n);
  }
  const counts = new Map<number, number>();
  for (const p of preds) counts.set(p.gold, (counts.get(p.gold) ?? 0) + 1);
  res.majorityBaseline = n ? Math.max(...counts.values()) / n : null;
  return res;
}

const files = readdirSync(EVAL_DIR).filter((f) => f.endsWith(".jsonl")).map((f) => f.replace(/\.jsonl$/, ""));
const order = [...new Set([...Object.keys(manifest), ...files])].filter((n) => files.includes(n) && (!only.length || only.includes(n)));
const results: any[] = [];
for (const name of order) {
  const items = readFileSync(path.join(EVAL_DIR, `${name}.jsonl`), "utf8").split("\n").filter(Boolean).slice(0, limit).map((l) => JSON.parse(l) as Item);
  const kind = items[0].kind;
  const preds: Pred[] = [];
  const diag: Pred[] = [];
  let rejected = 0;
  const reasons = new Map<string, number>();
  for (const item of items) {
    const parsed = tryParse(item.request);
    if (parsed.ok) {
      preds.push(await score(parsed.request, item));
      continue;
    }
    rejected++;
    const reason = parsed.message.replace(/"[^"]*"/g, '"…"');
    reasons.set(reason, (reasons.get(reason) ?? 0) + 1);
    if (kind === "choice") {
      const req = chunkedParse(item.request);
      if (req) diag.push(await score(req, item));
    }
  }
  const row = summarize(name, kind, preds, rejected, false);
  row.rejectReasons = Object.fromEntries(reasons);
  row.manifest = manifest[name];
  row.jevDI = jevDI(name);
  if (diag.length) row.diagnosticOver12 = summarize(name, kind, diag, 0, true);
  results.push(row);
  const fmt = (x: number | null) => (x == null ? "—" : (100 * x).toFixed(1));
  console.log(`${name}: n=${preds.length} rej=${rejected} acc=${fmt(row.accuracy)} f1=${fmt(row.macroF1)}${diag.length ? ` diag(n=${diag.length}) acc=${fmt(row.diagnosticOver12.accuracy)} f1=${fmt(row.diagnosticOver12.macroF1)}` : ""}`);
}

const pct = (x: number | null | undefined) => (x == null || Number.isNaN(x) ? "—" : (100 * x).toFixed(1));
const scored = results.filter((r) => r.n > 0);
const macroAvg = scored.length ? scored.reduce((s, r) => s + r.accuracy, 0) / scored.length : 0;
const lines = [
  `# Keel public benchmarks — \`${path.basename(dir)}\``,
  ``,
  `Generated ${new Date().toISOString()} (wire LIMITS.choiceOptions = ${LIMITS.choiceOptions}) by \`scripts/keel-public-bench.ts\` (production path: tryParse → neuralWeights → projectWeights). Model: \`${path.relative(process.cwd(), dir)}\` (${model.config.id}).`,
  ``,
  `**MSD1 per-benchmark numbers do not exist publicly.** Microsoft reports only an aggregate: 83.5% average accuracy over 36 undisclosed benchmarks / 147,137 questions (vendor-reported; see \`artifacts/parity/msd1/benchmarks.md\`). The "MSD1" column therefore shows "n/p" (not published) and no delta can be computed per dataset. The Jev column is third-party: Decision Index board, Jev 1.14, different sample, prompts and sometimes metric (shown) — indicative only.`,
  ``,
  `Accuracy: choice = argmax option; noul = P(yes) ≥ 0.5; score = round(expected level) == round(gold). CI = Wilson 95%. Samples are stratified, ≤${limit} per dataset (civil_comments class-balanced). Prompt framing is ours (MSD1's is unpublished); see \`training/public/registry.py\`.`,
  ``,
  `| Dataset | Type | n | Keel acc % (95% CI) | Majority % | Keel macro-F1 % | ECE | MSD1 (vendor) | Δ vs MSD1 | Jev 1.14 (DI, 3rd-party) | p50 ms | Notes |`,
  `|---|---|---:|---|---:|---:|---:|---|---|---|---:|---|`,
];
for (const r of results) {
  const jev = r.jevDI ? `${pct(r.jevDI.raw)} (${r.jevDI.metric})` : "—";
  const notes: string[] = [];
  if (r.manifest?.notes) notes.push(r.manifest.notes);
  if (r.rejected) notes.push(`${r.rejected} rejected by production wire (${Object.keys(r.rejectReasons).join("; ")})`);
  if (r.kind === "score") notes.push(`argmax acc ${pct(r.accuracyArgmax)}, within-1 ${pct(r.within1)}, Spearman ${r.spearman.toFixed(3)}, argmax macro-F1 ${pct(r.macroF1Argmax)}`);
  if (r.kind === "noul") notes.push(`Brier ${r.brier.toFixed(3)}, predicted-yes ${pct(r.positiveRate)}%`);
  const acc = r.n ? `${pct(r.accuracy)} (${pct(r.ci95[0])}–${pct(r.ci95[1])})` : `unsupported (>${LIMITS.choiceOptions} options)`;
  lines.push(`| ${r.dataset} | ${r.kind} | ${r.n} | ${acc} | ${r.n ? pct(r.majorityBaseline) : "—"} | ${r.n ? pct(r.macroF1) : "—"} | ${r.n ? r.ece.toFixed(3) : "—"} | n/p | n/a | ${jev} | ${r.n ? r.p50ms.toFixed(1) : "—"} | ${notes.join(" ")} |`);
}
const diagRows = results.filter((r) => r.diagnosticOver12);
if (diagRows.length) {
  lines.push(``, `## Diagnostic: label sets above the ${LIMITS.choiceOptions}-option wire limit`, ``,
    `Not reachable through the production API (tryParse rejects >${LIMITS.choiceOptions} options). Options were parsed in ${LIMITS.choiceOptions}-option chunks with production tryParse and concatenated; scoring then used the production neuralWeights/projectWeights unchanged.`, ``,
    `| Dataset | Options | n | Keel acc % (95% CI) | Keel macro-F1 % | ECE | Jev 1.14 (DI) | p50 ms |`, `|---|---:|---:|---|---:|---:|---|---:|`);
  for (const r of diagRows) {
    const d = r.diagnosticOver12;
    const opts = r.dataset === "banking77" ? 77 : r.dataset === "clinc150" ? 151 : "?";
    lines.push(`| ${r.dataset} | ${opts} | ${d.n} | ${pct(d.accuracy)} (${pct(d.ci95[0])}–${pct(d.ci95[1])}) | ${pct(d.macroF1)} | ${d.ece.toFixed(3)} | ${r.jevDI ? `${pct(r.jevDI.raw)} (${r.jevDI.metric})` : "—"} | ${d.p50ms.toFixed(1)} |`);
  }
}
lines.push(``, `Unweighted mean accuracy over the ${scored.length} production-supported datasets: **${pct(macroAvg)}%**. This is NOT comparable to MSD1's 83.5% (different, undisclosed benchmark set and prompts).`);
const readyFile = "training/data/public/READY.json";
const publicTrain = new Set(existsSync(readyFile) ? Object.keys(JSON.parse(readFileSync(readyFile, "utf8")).datasets ?? {}) : []);
const mean = (rs: any[]) => (rs.length ? rs.reduce((s, r) => s + r.accuracy, 0) / rs.length : null);
const trainable = scored.filter((r) => publicTrain.has(r.dataset));
const evalOnly = scored.filter((r) => !publicTrain.has(r.dataset));
lines.push(``, `Split by exposure to \`training/data/public\` train groups: datasets with public train groups (${trainable.length}; in-distribution for any model trained on them) mean **${pct(mean(trainable))}%**; eval-only datasets (${evalOnly.length}: ${evalOnly.map((r) => r.dataset).join(", ")}) mean **${pct(mean(evalOnly))}%**.`);
mkdirSync(path.dirname(out), { recursive: true });
writeFileSync(`${out}.md`, lines.join("\n") + "\n");
writeFileSync(`${out}.json`, JSON.stringify({ model: path.relative(process.cwd(), dir), id: model.config.id, generated: new Date().toISOString(), limit, meanAccuracy: macroAvg, meanPublicTrainDatasets: mean(trainable), meanEvalOnlyDatasets: mean(evalOnly), results }, null, 2));
console.log(`wrote ${out}.md / .json  mean=${pct(macroAvg)}`);
