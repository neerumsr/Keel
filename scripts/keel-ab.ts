/**
 * Keel ON vs OFF A/B test.
 *
 *   OFF       = the Copilot model answers every decision (what happens without Keel).
 *   ON-gated  = Keel-2 answers each question it is confident about; the rest are
 *               deferred to the same Copilot model (one call per case, only if needed).
 *   ON-only   = Keel-2 answers everything (no fallback) — shown for reference.
 *
 * The LLM is called through the Copilot CLI (`copilot -p`) from an empty temp
 * folder so repo instructions cannot bias it. Its answers are cached per model in
 * artifacts/ab-cache so reruns are free.
 *
 *   node --experimental-strip-types scripts/keel-ab.ts [--model gpt-5-mini] [--suites holdout-20,holdout-b-20,open-60]
 *        [--concurrency 6] [--tau 0.6] [--out artifacts/keel-ab-report]
 *
 * Gate: Keel keeps a question when its confidence >= tau (choice/score: the answer's
 * confidence; noul: |p - 0.5| * 2). A sweep over tau is always reported.
 */
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { EVAL_CASES, type EvalCase } from "../src/lib/decider/eval-set.ts";
import { HOLDOUT_CASES } from "../src/lib/decider/eval-holdout.ts";
import { HOLDOUT_B_CASES } from "../src/lib/decider/eval-holdout-b.ts";
import { OPEN_CASES } from "../src/lib/decider/eval-open.ts";
import { grade, prepare } from "../src/lib/decider/eval.ts";
import { loadModel, neuralWeights } from "../src/lib/decider/neural.server.ts";
import { projectWeights, type Answer, type DecisionRequest, type WeightBag } from "../src/lib/decider/wire.ts";

const args = process.argv.slice(2);
const flag = (name: string, fallback: string) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1]! : fallback;
};
const llmModel = flag("--model", "gpt-5-mini");
const concurrency = Number(flag("--concurrency", "6"));
const tau = Number(flag("--tau", "0.6"));
const SWEEP = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.01];
const out = flag("--out", "artifacts/keel-ab-report");
const ALL_SUITES: Record<string, EvalCase[]> = {
  "labeled-50": EVAL_CASES,
  "holdout-20": HOLDOUT_CASES,
  "holdout-b-20": HOLDOUT_B_CASES,
  "open-60": OPEN_CASES,
};
const suiteNames = flag("--suites", "labeled-50,holdout-20,holdout-b-20,open-60").split(",");

const model = await loadModel();
if (!model) {
  console.error("No Keel-2 model could be loaded (models/keel-2).");
  process.exit(1);
}

// ---------- LLM (the "Keel OFF" path) ----------
function llmPrompt(request: DecisionRequest): string {
  const qs = request.questions.map((q) => {
    if (q.type === "choice") return { id: q.id, type: "choice", instructions: q.instructions, options: Object.fromEntries(q.options.map((o) => [o.key, o.description])) };
    if (q.type === "score") return { id: q.id, type: "score", instructions: q.instructions, levels: Object.fromEntries(q.levels.map((l, i) => [String(i), l])) };
    return { id: q.id, type: "noul", instructions: q.instructions, yes: q.yes, no: q.no };
  });
  return [
    "You are a decision function. Do not use any tools. Reply with ONE JSON object and nothing else.",
    "For every question, give each option a weight 0-100 reflecting how well it fits the STATE (weights need not sum to 100).",
    'choice -> {"<option key>": weight, ...}; score -> {"<level index>": weight, ...}; noul -> {"yes": probability-of-yes 0-100}.',
    'Output shape: {"<question id>": {...weights}, ...}',
    "",
    "STATE:",
    request.stateText,
    "",
    "QUESTIONS:",
    JSON.stringify(qs, null, 2),
  ].join("\n");
}

function extractJson(text: string): WeightBag | null {
  text = text.replace(/\r?\n/g, "");
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    const parsed = JSON.parse(text.slice(start, end + 1));
    return parsed && typeof parsed === "object" ? (parsed as WeightBag) : null;
  } catch {
    return null;
  }
}

const sandbox = mkdtempSync(path.join(os.tmpdir(), "keel-ab-"));
function runCopilot(prompt: string): Promise<{ text: string; ms: number }> {
  return new Promise((resolve) => {
    const started = performance.now();
    const child = spawn("copilot", ["-p", prompt, "-s", "--no-color", "--stream", "off", "--model", llmModel], { cwd: sandbox, windowsHide: true });
    let text = "";
    child.stdout.on("data", (d) => (text += d));
    child.stderr.on("data", (d) => (text += d));
    const timer = setTimeout(() => child.kill(), 360_000);
    child.on("close", () => {
      clearTimeout(timer);
      resolve({ text, ms: performance.now() - started });
    });
    child.on("error", (e) => {
      clearTimeout(timer);
      resolve({ text: String(e), ms: performance.now() - started });
    });
  });
}

const cacheFile = path.join("artifacts", "ab-cache", `${llmModel.replace(/[^\w.-]/g, "_")}.json`);
mkdirSync(path.dirname(cacheFile), { recursive: true });
type CacheEntry = { weights: WeightBag | null; ms: number; raw?: string };
const cache: Record<string, CacheEntry> = existsSync(cacheFile) ? JSON.parse(readFileSync(cacheFile, "utf8")) : {};
const saveCache = () => writeFileSync(cacheFile, JSON.stringify(cache, null, 1));

async function llmWeights(request: DecisionRequest): Promise<CacheEntry> {
  const prompt = llmPrompt(request);
  const key = createHash("sha256").update(prompt).digest("hex").slice(0, 20);
  if (cache[key]?.weights) return cache[key]!;
  let entry: CacheEntry = { weights: null, ms: 0 };
  for (let attempt = 0; attempt < 2 && !entry.weights; attempt++) {
    const { text, ms } = await runCopilot(prompt);
    entry = { weights: extractJson(text), ms: entry.ms + ms, raw: entry.weights ? undefined : text.slice(0, 400) };
  }
  if (entry.weights) delete entry.raw;
  cache[key] = entry;
  saveCache();
  return entry;
}

// ---------- Run ----------
type Mode = "off" | "gated" | "keel";
type Row = {
  suite: string; id: number; name: string;
  deferred: string[]; questions: number;
  keelMs: number; llmMs: number; llmOk: boolean;
  grades: Record<Mode, ReturnType<typeof grade>>;
  sweep: Record<string, { deferred: number; grade: ReturnType<typeof grade> }>;
};

function confidenceOf(a: Answer | undefined): number {
  if (!a) return 0;
  if (a.type === "noul") return Math.abs(a.noul - 0.5) * 2;
  return a.confidence;
}
function merge(request: DecisionRequest, keel: Record<string, Answer>, llm: Record<string, Answer>, t: number) {
  const deferred = request.questions.filter((q) => confidenceOf(keel[q.id]) < t).map((q) => q.id);
  const answers: Record<string, Answer> = { ...keel };
  for (const id of deferred) if (llm[id]) answers[id] = llm[id]!;
  return { deferred, answers };
}

const work = suiteNames.flatMap((suite) => (ALL_SUITES[suite] ?? []).map((item) => ({ suite, item })));
console.log(`A/B: ${work.length} cases, LLM=${llmModel}, tau=${tau}, concurrency=${concurrency}`);
// Keel pass first, sequential and warmed up, so its latency is not polluted by concurrent LLM processes.
await neuralWeights(prepare(work[0]!.item));
const keelPass = new Map<string, { answers: Record<string, Answer>; ms: number }>();
for (const { suite, item } of work) {
  const request = prepare(item);
  const t0 = performance.now();
  const answers = projectWeights(request, (await neuralWeights(request))!);
  keelPass.set(`${suite}:${item.id}`, { answers, ms: performance.now() - t0 });
}
const rows: Row[] = [];
let done = 0;
async function one({ suite, item }: { suite: string; item: EvalCase }) {
  const request = prepare(item);
  const { answers: keelAnswers, ms: keelMs } = keelPass.get(`${suite}:${item.id}`)!;
  const llm = await llmWeights(request);
  const llmAnswers = llm.weights ? projectWeights(request, llm.weights) : {};
  const { deferred, answers: gatedAnswers } = merge(request, keelAnswers, llmAnswers, tau);
  const sweep: Record<string, { deferred: number; grade: ReturnType<typeof grade> }> = {};
  for (const t of SWEEP) {
    const m = merge(request, keelAnswers, llmAnswers, t);
    sweep[String(t)] = { deferred: m.deferred.length, grade: grade(item, m.answers) };
  }
  rows.push({
    suite, id: item.id, name: item.name, deferred, questions: request.questions.length,
    keelMs, llmMs: llm.ms, llmOk: !!llm.weights, sweep,
    grades: { off: grade(item, llmAnswers), gated: grade(item, gatedAnswers), keel: grade(item, keelAnswers) },
  });
  done++;
  if (done % 10 === 0 || done === work.length) console.log(`  ${done}/${work.length}`);
}
const queue = work.slice();
await Promise.all(Array.from({ length: concurrency }, async () => { while (queue.length) await one(queue.shift()!); }));
rows.sort((a, b) => a.suite.localeCompare(b.suite) || a.id - b.id);

// ---------- Report ----------
const tally = (rs: Row[], mode: Mode, k: "choiceOk" | "scoreOk" | "noulOk") => {
  const f = rs.map((r) => r.grades[mode][k]).filter((x) => x != null);
  return { c: f.filter(Boolean).length, n: f.length };
};
const fmt = (t: { c: number; n: number }) => (t.n ? `${t.c}/${t.n}` : "—");
const allOk = (r: Row, m: Mode) => [r.grades[m].choiceOk, r.grades[m].scoreOk, r.grades[m].noulOk].every((x) => x !== false);
const med = (xs: number[]) => { const s = xs.slice().sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)]! : 0; };

const summary: Record<string, unknown>[] = [];
const lines = [
  `# Keel ON vs OFF (A/B)`,
  ``,
  `Generated ${new Date().toISOString()}. Keel: \`${model.config.id}\`. OFF baseline LLM: \`${llmModel}\` via Copilot CLI (empty folder, no tools).`,
  `Gate τ = ${tau}: Keel keeps a question when its confidence ≥ τ (noul confidence = |p − 0.5| × 2); otherwise that question is deferred to the LLM.`,
  ``,
  `| Suite | Mode | Cases fully right | Choice | Score band | Noul band | Safety misses | LLM calls | Median latency / case |`,
  `|---|---|---:|---:|---:|---:|---:|---:|---:|`,
];
const groups = [...suiteNames.map((s) => ({ name: s, rs: rows.filter((r) => r.suite === s) })), { name: "held-out total", rs: rows.filter((r) => r.suite !== "labeled-50") }];
for (const g of groups) {
  if (!g.rs.length) continue;
  for (const mode of ["off", "gated", "keel"] as Mode[]) {
    const calls = mode === "off" ? g.rs.length : mode === "gated" ? g.rs.filter((r) => r.deferred.length).length : 0;
    const lat = g.rs.map((r) => (mode === "off" ? r.llmMs : mode === "gated" ? r.keelMs + (r.deferred.length ? r.llmMs : 0) : r.keelMs));
    const s = {
      suite: g.name, mode,
      fullyRight: g.rs.filter((r) => allOk(r, mode)).length, cases: g.rs.length,
      choice: tally(g.rs, mode, "choiceOk"), score: tally(g.rs, mode, "scoreOk"), noul: tally(g.rs, mode, "noulOk"),
      safety: g.rs.filter((r) => r.grades[mode].safetyMiss).length, llmCalls: calls, medianMs: Math.round(med(lat)),
    };
    summary.push(s);
    const label = { off: "OFF (LLM only)", gated: "ON (Keel + LLM fallback)", keel: "Keel only" }[mode];
    lines.push(`| ${g.name} | ${label} | ${s.fullyRight}/${s.cases} | ${fmt(s.choice)} | ${fmt(s.score)} | ${fmt(s.noul)} | ${s.safety} | ${s.llmCalls} | ${s.medianMs >= 1000 ? (s.medianMs / 1000).toFixed(1) + " s" : s.medianMs + " ms"} |`);
  }
}

const heldOut = rows.filter((r) => r.suite !== "labeled-50");
const regress = heldOut.filter((r) => allOk(r, "off") && !allOk(r, "gated"));
const improve = heldOut.filter((r) => !allOk(r, "off") && allOk(r, "gated"));
const llmFail = rows.filter((r) => !r.llmOk);
lines.push(
  ``,
  `## Degradation check (held-out only)`,
  ``,
  `- Cases OFF got fully right but ON got wrong (**regressions**): **${regress.length}**`,
  `- Cases OFF got wrong but ON got fully right (improvements): ${improve.length}`,
  `- LLM calls avoided by Keel: ${heldOut.filter((r) => !r.deferred.length).length}/${heldOut.length}`,
  `- LLM answers that failed to parse (graded as wrong for OFF): ${llmFail.length}`,
  ``,
  regress.length ? `| Suite | # | Case | Deferred to LLM |\n|---|---:|---|---|\n` + regress.map((r) => `| ${r.suite} | ${r.id} | ${r.name} | ${r.deferred.join(", ") || "none (Keel was confident)"} |`).join("\n") : "",
  ``,
  `labeled-50 is in Keel's training mix, so only held-out rows count for the verdict. Every set is small (±10–15 pts).`,
);

const okG = (g: ReturnType<typeof grade>) => [g.choiceOk, g.scoreOk, g.noulOk].every((x) => x !== false);
lines.push(``, `## Threshold sweep (held-out)`, ``, `τ = 0 is Keel only; τ > 1 is LLM only.`, ``,
  `| τ | LLM calls | Questions deferred | Cases fully right | Safety misses | Regressions vs OFF | Improvements vs OFF |`, `|---:|---:|---:|---:|---:|---:|---:|`);
for (const t of SWEEP) {
  const k = String(t);
  const calls = heldOut.filter((r) => r.sweep[k]!.deferred > 0).length;
  const qd = heldOut.reduce((n, r) => n + r.sweep[k]!.deferred, 0);
  const qn = heldOut.reduce((n, r) => n + r.questions, 0);
  lines.push(`| ${t > 1 ? "LLM only" : t} | ${calls}/${heldOut.length} | ${qd}/${qn} | ${heldOut.filter((r) => okG(r.sweep[k]!.grade)).length} | ${heldOut.filter((r) => r.sweep[k]!.grade.safetyMiss).length} | ${heldOut.filter((r) => allOk(r, "off") && !okG(r.sweep[k]!.grade)).length} | ${heldOut.filter((r) => !allOk(r, "off") && okG(r.sweep[k]!.grade)).length} |`);
}

mkdirSync(path.dirname(out), { recursive: true });
writeFileSync(`${out}.json`, JSON.stringify({ keel: model.config.id, llm: llmModel, tau, summary, rows }, null, 2));
writeFileSync(`${out}.md`, lines.join("\n"));
console.log(lines.join("\n"));
