/**
 * Keel parity harness (data-1). Side-by-side scoring of one or more Keel model
 * directories on the held-out suites plus the blind suite, with the gpt-5-mini
 * LLM-only baseline and (only if real live results exist) Jev / MSD1 columns.
 *
 *   node --experimental-strip-types scripts/keel-parity-bench.ts \
 *        --model models/keel-2 [--model models/candidates/x ...] \
 *        [--out artifacts/parity/blind/parity] [--suites holdout-20,holdout-b-20,open-60,blind,labeled-50] \
 *        [--no-lexical] [--llm-run] [--llm-model claude-haiku-4.5] [--llm-ab-model gpt-5-mini]
 *        [--llm-max-calls 250] [--llm-concurrency 6]
 *
 * --llm-run calls the Copilot CLI (`copilot -p`) for blind cases missing from
 * `artifacts/parity/blind/llm-cache/<llm-model>.json`. Without it the LLM column uses
 * caches only: blind from that cache, older suites from the read-only keel-ab cache
 * of <llm-ab-model>. gpt-5-mini is no longer available in the Copilot CLI, so the
 * blind baseline defaults to claude-haiku-4.5 while older suites keep gpt-5-mini.
 * labeled-50 is in Keel's training mix: it is shown but flagged in-sample and
 * excluded from every held-out aggregate.
 */
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { EVAL_CASES, type EvalCase } from "../src/lib/decider/eval-set.ts";
import { HOLDOUT_CASES } from "../src/lib/decider/eval-holdout.ts";
import { HOLDOUT_B_CASES } from "../src/lib/decider/eval-holdout-b.ts";
import { OPEN_CASES } from "../src/lib/decider/eval-open.ts";
import { BLIND_CASES } from "../src/lib/decider/eval-blind.ts";
import { BLIND_C_CASES } from "../src/lib/decider/eval-blind-c.ts";
import { grade, prepare } from "../src/lib/decider/eval.ts";
import { localWeights } from "../src/lib/decider/local.ts";
import { loadModel, neuralWeights } from "../src/lib/decider/neural.server.ts";
import { LEXICAL_MODEL, projectWeights, type Answer, type DecisionRequest, type WeightBag } from "../src/lib/decider/wire.ts";

// ---------- CLI ----------
const args = process.argv.slice(2);
const flags = (name: string) => args.flatMap((a, i) => (a === name && args[i + 1] ? [args[i + 1]!] : []));
const flag = (name: string, fallback: string) => flags(name)[0] ?? fallback;
const has = (name: string) => args.includes(name);
const modelDirs = flags("--model").length ? flags("--model") : ["models/keel-2"];
const out = flag("--out", "artifacts/parity/blind/parity");
const llmModel = flag("--llm-model", "claude-haiku-4.5");
const llmAbModel = flag("--llm-ab-model", "gpt-5-mini");
const llmRun = has("--llm-run");
const llmMaxCalls = Number(flag("--llm-max-calls", "250"));
const llmConcurrency = Number(flag("--llm-concurrency", "6"));
const withLexical = !has("--no-lexical");
// Secret suites: per-case details (names, answers, failures) are written only when --out is under the
// suite's own folder (artifacts/parity/blind/ or artifacts/parity/blind-c/), which trainers must not open.
// Anywhere else the report carries aggregates only. blind-c is a final-confirmation suite and is kept out
// of "held-out total" so totals stay comparable with earlier scoreboard entries.
const SECRET: Record<string, string> = { blind: "blind", "blind-c": "blind-c" };
const outUnder = (dir: string) => path.resolve(out).toLowerCase().startsWith(path.resolve("artifacts/parity", dir).toLowerCase() + path.sep);
const detailOk = (suite: string) => !SECRET[suite] || outUnder(SECRET[suite]!);
const blindDetail = detailOk("blind");

const ALL_SUITES: Record<string, { cases: EvalCase[]; inSample: boolean; confirm?: boolean }> = {
  "holdout-20": { cases: HOLDOUT_CASES, inSample: false },
  "holdout-b-20": { cases: HOLDOUT_B_CASES, inSample: false },
  "open-60": { cases: OPEN_CASES, inSample: false },
  blind: { cases: BLIND_CASES, inSample: false },
  "blind-c": { cases: BLIND_C_CASES, inSample: false, confirm: true },
  "labeled-50": { cases: EVAL_CASES, inSample: true },
};
const suiteNames = flag("--suites", Object.keys(ALL_SUITES).join(",")).split(",").filter((s) => ALL_SUITES[s]);

// ---------- metrics ----------
type Graded = ReturnType<typeof grade>;
type CaseRow = { suite: string; id: number; name: string; tags: string[]; ms: number; g: Graded; conf: number | null; answered: boolean; actual: string };
type Tally = { c: number; n: number };
type SuiteStats = {
  cases: number; answered: number; fullyRight: number;
  choice: Tally; score: Tally; noul: Tally; safetyMisses: number;
  ece: number | null; eceN: number; p50: number | null; p95: number | null;
  failures: { id: number; name: string; actual: string }[];
};

const fully = (g: Graded) => [g.choiceOk, g.scoreOk, g.noulOk].every((x) => x !== false) && !g.safetyMiss;
const tally = (rows: CaseRow[], k: "choiceOk" | "scoreOk" | "noulOk"): Tally => {
  const f = rows.map((r) => r.g[k]).filter((x) => x != null);
  return { c: f.filter(Boolean).length, n: f.length };
};
const pct = (xs: number[], p: number) => {
  if (!xs.length) return null;
  const s = xs.slice().sort((a, b) => a - b);
  return Math.round(s[Math.min(s.length - 1, Math.round(p * (s.length - 1)))]! * 100) / 100;
};
/** Expected calibration error of choice confidence over unambiguous choice questions (10 equal-width bins). */
function ece(rows: CaseRow[]): { ece: number | null; n: number } {
  const pts = rows.filter((r) => r.conf != null && r.g.choiceOk != null).map((r) => ({ c: r.conf!, ok: r.g.choiceOk ? 1 : 0 }));
  if (!pts.length) return { ece: null, n: 0 };
  let total = 0;
  for (let b = 0; b < 10; b++) {
    const bin = pts.filter((p) => (b === 9 ? p.c >= b / 10 : p.c >= b / 10 && p.c < (b + 1) / 10));
    if (!bin.length) continue;
    const conf = bin.reduce((s, p) => s + p.c, 0) / bin.length;
    const acc = bin.reduce((s, p) => s + p.ok, 0) / bin.length;
    total += (bin.length / pts.length) * Math.abs(conf - acc);
  }
  return { ece: Math.round(total * 1000) / 1000, n: pts.length };
}
function summarize(rows: CaseRow[], timed: boolean): SuiteStats {
  const e = ece(rows);
  const ms = rows.filter((r) => r.answered).map((r) => r.ms);
  return {
    cases: rows.length,
    answered: rows.filter((r) => r.answered).length,
    fullyRight: rows.filter((r) => fully(r.g)).length,
    choice: tally(rows, "choiceOk"), score: tally(rows, "scoreOk"), noul: tally(rows, "noulOk"),
    safetyMisses: rows.filter((r) => r.g.safetyMiss).length,
    ece: e.ece, eceN: e.n,
    p50: timed ? pct(ms, 0.5) : null, p95: timed ? pct(ms, 0.95) : null,
    failures: rows.filter((r) => !fully(r.g)).map((r) => ({ id: r.id, name: r.name, actual: r.actual })),
  };
}

function describe(item: EvalCase, answers: Record<string, Answer>): string {
  const parts: string[] = [];
  const e = item.expect;
  if (e.choice) { const a = answers[e.choice.id]; parts.push(a?.type === "choice" ? `${a.choice}@${a.confidence}` : "no-choice"); }
  if (e.score) { const a = answers[e.score.id]; parts.push(a?.type === "score" ? `score ${a.score}` : "no-score"); }
  if (e.noul) { const a = answers[e.noul.id]; parts.push(a?.type === "noul" ? `noul ${a.noul}` : "no-noul"); }
  return parts.join("; ");
}
function choiceConf(item: EvalCase, answers: Record<string, Answer>): number | null {
  const e = item.expect.choice;
  if (!e || e.maxConfidence != null) return null;
  const a = answers[e.id];
  return a?.type === "choice" ? a.confidence : null;
}
const emptyGrade = (item: EvalCase): Graded => ({
  choiceOk: item.expect.choice ? false : null,
  scoreOk: item.expect.score ? false : null,
  noulOk: item.expect.noul ? false : null,
  safetyMiss: false, expected: "", actual: "",
});

// ---------- judges ----------
type Judge = { label: string; id: string; dir: string | null; weights: (r: DecisionRequest) => Promise<WeightBag> };
const judges: Judge[] = [];
for (const d of modelDirs) {
  const dir = path.resolve(d);
  const m = await loadModel(dir);
  if (!m) { console.error(`Could not load model ${d}`); process.exit(1); }
  judges.push({ label: path.relative(process.cwd(), dir).replace(/\\/g, "/"), id: m.config.id, dir, weights: async (r) => (await neuralWeights(r, dir))! });
}
if (withLexical) judges.push({ label: "lexical", id: LEXICAL_MODEL, dir: null, weights: async (r) => localWeights(r) });

async function runJudge(j: Judge, suite: string, cases: EvalCase[]): Promise<CaseRow[]> {
  for (let i = 0; i < Math.min(3, cases.length); i++) await j.weights(prepare(cases[i]!));
  const rows: CaseRow[] = [];
  for (const item of cases) {
    const req = prepare(item);
    const t0 = performance.now();
    const answers = projectWeights(req, await j.weights(req));
    const ms = performance.now() - t0;
    rows.push({ suite, id: item.id, name: item.name, tags: item.tags, ms, g: grade(item, answers), conf: choiceConf(item, answers), answered: true, actual: describe(item, answers) });
  }
  return rows;
}

// ---------- LLM baseline (same prompt as scripts/keel-ab.ts so caches are shared) ----------
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
type CacheEntry = { weights: WeightBag | null; ms: number; raw?: string };
const safeName = llmModel.replace(/[^\w.-]/g, "_");
const secretCacheFile = (suite: string) => path.join("artifacts", "parity", SECRET[suite]!, "llm-cache", `${safeName}.json`);
const abCacheFile = path.join("artifacts", "ab-cache", `${llmAbModel.replace(/[^\w.-]/g, "_")}.json`);
const readJson = <T,>(f: string, fb: T): T => (existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as T) : fb);
const secretCaches: Record<string, Record<string, CacheEntry>> = Object.fromEntries(Object.keys(SECRET).map((s) => [s, readJson(secretCacheFile(s), {})]));
const abCache: Record<string, CacheEntry> = readJson(abCacheFile, {});
const keyOf = (prompt: string) => createHash("sha256").update(prompt).digest("hex").slice(0, 20);
// An empty folder outside the repo (not a temp dir) so repo instructions cannot bias the LLM.
const sandbox = path.join(os.homedir(), ".keel-llm-sandbox");
const llmStatuses: Record<string, string> = Object.fromEntries(Object.keys(SECRET).map((s) => [s, "cache only (run with --llm-run to fill missing answers)"]));
let llmCallsLeft = llmMaxCalls;

function runCopilot(prompt: string): Promise<{ text: string; ms: number; code: number | null }> {
  return new Promise((resolve) => {
    const started = performance.now();
    const child = spawn("copilot", ["-p", prompt, "-s", "--no-color", "--stream", "off", "--model", llmModel], { cwd: sandbox, windowsHide: true });
    let text = "";
    child.stdout.on("data", (d) => (text += d));
    child.stderr.on("data", (d) => (text += d));
    const timer = setTimeout(() => child.kill(), 360_000);
    child.on("close", (code) => { clearTimeout(timer); resolve({ text, ms: performance.now() - started, code }); });
    child.on("error", (e) => { clearTimeout(timer); resolve({ text: String(e), ms: performance.now() - started, code: -1 }); });
  });
}
async function fillSecretCache(suite: string, cases: EvalCase[]) {
  const blindCache = secretCaches[suite]!;
  const blindCacheFile = secretCacheFile(suite);
  const budget = llmCallsLeft;
  mkdirSync(sandbox, { recursive: true });
  mkdirSync(path.dirname(blindCacheFile), { recursive: true });
  const todo = cases.filter((c) => !blindCache[keyOf(llmPrompt(prepare(c)))]?.weights);
  let calls = 0;
  let firstError = "";
  const queue = todo.slice();
  console.log(`LLM: ${todo.length} ${suite} cases missing from cache; budget ${budget} calls.`);
  await Promise.all(Array.from({ length: llmConcurrency }, async () => {
    while (queue.length && calls < budget) {
      const item = queue.shift()!;
      const prompt = llmPrompt(prepare(item));
      let entry: CacheEntry = { weights: null, ms: 0 };
      for (let attempt = 0; attempt < 2 && !entry.weights && calls < budget; attempt++) {
        calls++;
        const { text, ms, code } = await runCopilot(prompt);
        entry = { weights: extractJson(text), ms: entry.ms + ms };
        if (!entry.weights) { entry.raw = text.slice(0, 300); if (!firstError) firstError = `exit ${code}: ${text.slice(0, 200)}`; }
        if (/from --model flag is not available/i.test(text)) { queue.length = 0; break; }
      }
      if (/from --model flag is not available/i.test(entry.raw ?? "")) break;
      if (entry.weights) delete entry.raw;
      blindCache[keyOf(prompt)] = entry;
      writeFileSync(blindCacheFile, JSON.stringify(blindCache, null, 1));
    }
  }));
  const parsed = cases.filter((c) => blindCache[keyOf(llmPrompt(prepare(c)))]?.weights).length;
  llmCallsLeft -= calls;
  const llmStatus = llmStatuses[suite] = `Copilot CLI \`${llmModel}\`, ${calls} calls this run, ${parsed}/${cases.length} ${suite} answers parsed${firstError ? `; first failure: ${firstError.replace(/\s+/g, " ")}` : ""}`;
  console.log(llmStatus);
}

function llmRows(suite: string, cases: EvalCase[]): CaseRow[] {
  const cache = secretCaches[suite] ?? abCache;
  return cases.map((item) => {
    const req = prepare(item);
    const entry = cache[keyOf(llmPrompt(req))];
    if (!entry?.weights) return { suite, id: item.id, name: item.name, tags: item.tags, ms: 0, g: emptyGrade(item), conf: null, answered: false, actual: "no LLM answer" };
    const answers = projectWeights(req, entry.weights);
    return { suite, id: item.id, name: item.name, tags: item.tags, ms: entry.ms, g: grade(item, answers), conf: choiceConf(item, answers), answered: true, actual: describe(item, answers) };
  });
}

// ---------- live vendor columns (never fabricated) ----------
function vendorStatus() {
  const m = readJson<Record<string, unknown> | null>(path.join("artifacts", "parity", "msd1", "live-compare.json"), null);
  const j = readJson<Record<string, unknown> | null>(path.join("artifacts", "keel-vs-jev.json"), null);
  return {
    msd1: m ? { compared: m.msd1Compared === true, reason: String(m.msd1Reason ?? ""), perSuite: m.perSuite ?? null, generatedAt: m.generatedAt ?? null } : { compared: false, reason: "artifacts/parity/msd1/live-compare.json not found", perSuite: null, generatedAt: null },
    jev: j ? { compared: j.jevCompared === true, reason: String(j.jevReason ?? j.reason ?? ""), generatedAt: j.generatedAt ?? null } : { compared: false, reason: "artifacts/keel-vs-jev.json not found", generatedAt: null },
  };
}

// ---------- run ----------
if (llmRun) for (const s of Object.keys(SECRET)) if (suiteNames.includes(s)) await fillSecretCache(s, ALL_SUITES[s]!.cases);
const inHeld = (suite: string) => !ALL_SUITES[suite]!.inSample && !ALL_SUITES[suite]!.confirm;

type Column = { label: string; id: string; kind: "keel" | "lexical" | "llm"; suites: Record<string, SuiteStats>; rows: CaseRow[] };
const columns: Column[] = [];
for (const j of judges) {
  const col: Column = { label: j.label, id: j.id, kind: j.dir ? "keel" : "lexical", suites: {}, rows: [] };
  for (const s of suiteNames) {
    const rows = await runJudge(j, s, ALL_SUITES[s]!.cases);
    col.rows.push(...rows);
    col.suites[s] = summarize(rows, true);
  }
  const held = col.rows.filter((r) => inHeld(r.suite));
  col.suites["held-out total"] = summarize(held, true);
  columns.push(col);
}
{
  const llmLabel = llmModel === llmAbModel ? llmModel : `${llmModel} blind / ${llmAbModel} older suites`;
  const col: Column = { label: `${llmLabel} (LLM only)`, id: llmLabel, kind: "llm", suites: {}, rows: [] };
  for (const s of suiteNames) {
    const rows = llmRows(s, ALL_SUITES[s]!.cases);
    col.rows.push(...rows);
    col.suites[s] = summarize(rows, true);
  }
  col.suites["held-out total"] = summarize(col.rows.filter((r) => inHeld(r.suite)), true);
  columns.push(col);
}
const vendors = vendorStatus();

// ---------- report ----------
const f = (t: Tally) => (t.n ? `${t.c}/${t.n}` : "—");
const ms = (x: number | null, kind: Column["kind"]) => (x == null ? "—" : kind === "llm" ? `${(x / 1000).toFixed(1)} s` : `${x}`);
const groups = [...suiteNames.filter((s) => inHeld(s)), "held-out total", ...suiteNames.filter((s) => ALL_SUITES[s]!.confirm), ...suiteNames.filter((s) => ALL_SUITES[s]!.inSample)];
const now = new Date().toISOString();
const lines: string[] = [
  `# Keel parity bench`,
  ``,
  `Generated ${now}. Columns: ${columns.map((c) => `\`${c.label}\` (${c.id})`).join(", ")}.`,
  ``,
  `- Blind suite: ${BLIND_CASES.length} cases (half A ${BLIND_CASES.filter((c) => c.tags.includes("blind-a")).length}, half B ${BLIND_CASES.filter((c) => c.tags.includes("blind-b")).length}), never trained on.`,
  `- blind-c: ${BLIND_C_CASES.length} cases, final-confirmation suite (data-1 + a different-model sub-agent); excluded from "held-out total".`,
  `- labeled-50 is **in-sample** for every Keel model (training mix). It is shown for reference and excluded from "held-out total".`,
  `- LLM baseline: blind / blind-c = \`${llmModel}\` (${Object.entries(llmStatuses).map(([s, v]) => `${s}: ${v}`).join("; ")}). Older suites use the keel-ab cache of \`${llmAbModel}\` (\`artifacts/ab-cache\`); gpt-5-mini is no longer available in the Copilot CLI, so it cannot answer the blind suite. Unanswered LLM cases count as wrong. LLM latency is wall-clock per Copilot CLI call, not comparable to in-process Keel latency.`,
  `- Live MSD1: ${vendors.msd1.compared ? `compared (see artifacts/parity/msd1/live-compare.md)` : `not measured — ${vendors.msd1.reason}`}`,
  `- Live Jev: ${vendors.jev.compared ? `compared (see artifacts/keel-vs-jev.md)` : `not measured — ${vendors.jev.reason}`}`,
  `- "Fully right" = every graded question right and no safety miss. ECE = expected calibration error of choice confidence on unambiguous choice questions (10 bins; lower is better). Latency = in-process ms (tokenize + ONNX + projection), sequential, warmed.`,
  ``,
  `| Suite | Column | Fully right | Choice | Score band | Noul band | Safety misses | ECE (n) | p50 ms | p95 ms |`,
  `|---|---|---:|---:|---:|---:|---:|---:|---:|---:|`,
];
for (const g of groups) {
  for (const c of columns) {
    const s = c.suites[g];
    if (!s) continue;
    const name = g + (ALL_SUITES[g]?.inSample ? " (in-sample)" : ALL_SUITES[g]?.confirm ? " (confirmation)" : "");
    const ans = c.kind === "llm" && s.answered < s.cases ? ` (${s.answered} answered)` : "";
    lines.push(`| ${name} | ${c.label} | ${s.fullyRight}/${s.cases}${ans} | ${f(s.choice)} | ${f(s.score)} | ${f(s.noul)} | ${s.safetyMisses} | ${s.ece ?? "—"} (${s.eceN}) | ${ms(s.p50, c.kind)} | ${ms(s.p95, c.kind)} |`);
  }
}
if (vendors.msd1.compared && vendors.msd1.perSuite) {
  lines.push(``, `### Live MSD1 (from artifacts/parity/msd1/live-compare.json, ${vendors.msd1.generatedAt})`, ``, "```json", JSON.stringify(vendors.msd1.perSuite, null, 2), "```");
}

// Secret-suite breakdown by stress tag.
for (const suite of Object.keys(SECRET).filter((s) => suiteNames.includes(s))) {
  const cases = ALL_SUITES[suite]!.cases;
  if (!detailOk(suite)) {
    lines.push(``, `${suite} per-case details are omitted because --out is outside artifacts/parity/${SECRET[suite]}/ (held-out integrity).`);
    continue;
  }
  const tags = ["negation", "sarcasm", "paraphrase", "multilingual", "long", "adversarial", "ambiguous", "safety", "copilot", "blind-a", "blind-b", "blind-c1", "blind-c2"];
  lines.push(``, `## ${suite} suite by stress tag (fully right)`, ``, `| Tag | Cases | ${columns.map((c) => c.label).join(" | ")} |`, `|---|---:|${columns.map(() => "---:").join("|")}|`);
  for (const t of tags) {
    const n = cases.filter((c) => c.tags.includes(t)).length;
    if (!n) continue;
    lines.push(`| ${t} | ${n} | ${columns.map((c) => c.rows.filter((r) => r.suite === suite && r.tags.includes(t) && fully(r.g)).length).join(" | ")} |`);
  }
  lines.push(``, `## ${suite} failures`, ``);
  for (const c of columns) {
    const s = c.suites[suite];
    if (!s) continue;
    lines.push(`### ${c.label} — ${s.failures.length} not fully right`, ``, `| id | case | answer |`, `|---:|---|---|`);
    for (const fl of s.failures) lines.push(`| ${fl.id} | ${fl.name} | ${fl.actual} |`);
    lines.push(``);
  }
}

mkdirSync(path.dirname(out), { recursive: true });
const json = {
  generatedAt: now,
  suites: Object.fromEntries(suiteNames.map((s) => [s, { cases: ALL_SUITES[s]!.cases.length, inSample: ALL_SUITES[s]!.inSample }])),
  llm: { model: llmModel, abModel: llmAbModel, status: llmStatuses },
  vendors,
  blindDetail,
  columns: columns.map((c) => ({ label: c.label, id: c.id, kind: c.kind, suites: Object.fromEntries(Object.entries(c.suites).map(([k, s]) => [k, detailOk(k === "held-out total" ? "blind" : k) ? s : { ...s, failures: [] }])), rows: c.rows.filter((r) => detailOk(r.suite)).map((r) => ({ suite: r.suite, id: r.id, ms: Math.round(r.ms * 100) / 100, fully: fully(r.g), choiceOk: r.g.choiceOk, scoreOk: r.g.scoreOk, noulOk: r.g.noulOk, safetyMiss: r.g.safetyMiss, conf: r.conf, actual: r.actual })) })),
};
writeFileSync(`${out}.json`, JSON.stringify(json, null, 1));
writeFileSync(`${out}.md`, lines.join("\n") + "\n");
console.log(lines.slice(0, lines.findIndex((l) => / suite by stress tag/.test(l)) > 0 ? lines.findIndex((l) => / suite by stress tag/.test(l)) - 1 : lines.length).join("\n"));
