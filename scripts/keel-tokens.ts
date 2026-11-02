/**
 * Token-savings benchmark: how many LLM tokens an agent spends on decision steps
 * WITHOUT Keel vs WITH Keel (Keel answers confident questions locally; the rest
 * are deferred to the LLM, gate τ exactly as in scripts/keel-ab.ts).
 *
 *   node --experimental-strip-types scripts/keel-tokens.ts [--model models/keel-2]
 *        [--suites holdout-20,holdout-b-20,open-60,labeled-50] [--blind auto|off]
 *        [--live 0] [--live-llm claude-haiku-4.5]            real sub-call usage measurements
 *        [--frontier 0] [--frontier-llm gpt-5.6-terra] [--frontier-effort medium]  real reasoning-model deliberation measurements (cached as llm@effort)
 *        [--blind-llm claude-haiku-4.5] [--blind-calls 0]     LLM answers for blind cases (no gpt-5-mini cache)
 *        [--max-calls 150] [--concurrency 4] [--out artifacts/parity/tokens/report]
 *
 * Token counts use gpt-tokenizer o200k_base (exact for the text we would send) plus
 * chat framing (+3 per message, +3 reply priming). Real usage numbers come only from
 * Copilot CLI `--usage-output-file` on real calls; they are cached in
 * artifacts/parity/tokens/cache and every real call is logged in calls-ledger.json,
 * which enforces --max-calls across runs.
 *
 * Accuracy (OFF vs ON) reuses keel-ab's gpt-5-mini answers from artifacts/ab-cache
 * (same prompt → same cache key). Cases without an LLM answer are excluded from
 * accuracy (never guessed) but still counted for tokens with a modeled completion.
 */
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { countTokens } from "gpt-tokenizer/encoding/o200k_base";
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
const modelDir = path.resolve(flag("--model", "models/keel-2"));
const out = flag("--out", "artifacts/parity/tokens/report");
const liveN = Number(flag("--live", "0"));
const liveLlm = flag("--live-llm", "claude-haiku-4.5");
const frontierN = Number(flag("--frontier", "0"));
const frontierEffort = flag("--frontier-effort", "");
const frontierLlm = flag("--frontier-llm", "gpt-5.6-terra") + (frontierEffort ? `@${frontierEffort}` : "");
const blindMode = flag("--blind", "auto");
const blindLlm = flag("--blind-llm", "claude-haiku-4.5");
const blindCalls = Number(flag("--blind-calls", "0"));
const maxCalls = Number(flag("--max-calls", "150"));
const concurrency = Number(flag("--concurrency", "4"));
const TAUS = [0.5, 0.6, 0.7, 0.8, 0.9];
const HEADLINE_TAU = 0.6;
const ABLLM = "gpt-5-mini";
const TOK_DIR = path.join("artifacts", "parity", "tokens");
mkdirSync(path.join(TOK_DIR, "cache"), { recursive: true });

const ALL_SUITES: Record<string, EvalCase[]> = {
  "labeled-50": EVAL_CASES,
  "holdout-20": HOLDOUT_CASES,
  "holdout-b-20": HOLDOUT_B_CASES,
  "open-60": OPEN_CASES,
};
const suiteNames = flag("--suites", "holdout-20,holdout-b-20,open-60,labeled-50").split(",");
const IN_SAMPLE = new Set(["labeled-50"]);

// ---------- Blind suite (data-1). Loaded only when READY.json exists; never inspected by hand. ----------
let blindNote = "not available (artifacts/parity/blind/READY.json missing)";
if (blindMode !== "off" && existsSync("artifacts/parity/blind/READY.json")) {
  const file = path.resolve("src/lib/decider/eval-blind.ts");
  if (existsSync(file)) {
    const mod = (await import(new URL(`file:///${file.replace(/\\/g, "/")}`).href)) as Record<string, unknown>;
    const cases = Object.values(mod).filter((v): v is EvalCase[] => Array.isArray(v) && v.length > 0 && typeof v[0] === "object" && v[0] != null && "expect" in v[0] && "state" in v[0]);
    const seen = new Set<string>();
    // Modules may export both the full set and its halves; keep each case once.
    const merged = cases.flat().filter((c) => { const k = JSON.stringify([c.id, c.state, c.questions]); return seen.has(k) ? false : (seen.add(k), true); });
    if (merged.length) {
      ALL_SUITES[`blind-${merged.length}`] = merged;
      suiteNames.push(`blind-${merged.length}`);
      blindNote = `loaded ${merged.length} cases from eval-blind.ts`;
    } else blindNote = "READY.json present but eval-blind.ts exported no EvalCase arrays";
  } else blindNote = "READY.json present but src/lib/decider/eval-blind.ts missing";
}

const model = await loadModel(modelDir);
if (!model) {
  console.error(`No Keel model could be loaded from ${modelDir}.`);
  process.exit(1);
}

// ---------- Prompt (identical to keel-ab.ts so the gpt-5-mini cache keys match) ----------
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
const promptKey = (prompt: string) => createHash("sha256").update(prompt).digest("hex").slice(0, 20);
const subset = (r: DecisionRequest, ids: string[]): DecisionRequest => ({ ...r, questions: r.questions.filter((q) => ids.includes(q.id)) });

// Chat framing: the decision prompt goes in as 1 user message (+3) with reply priming (+3).
const FRAMING = 6;
const tok = (s: string) => countTokens(s);

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

/** Completion the LLM returns for a set of questions. Uses its real answer when we have one. */
function completionText(request: DecisionRequest, ids: string[], llm: WeightBag | null, keel: Record<string, Answer>): { text: string; modeled: boolean } {
  const bag: WeightBag = {};
  let modeled = false;
  for (const q of request.questions.filter((x) => ids.includes(x.id))) {
    if (llm?.[q.id]) bag[q.id] = llm[q.id]!;
    else {
      modeled = true;
      const a = keel[q.id];
      if (a?.type === "noul") bag[q.id] = { yes: Math.round(a.noul * 100) };
      else if (a && "probabilities" in a) bag[q.id] = Object.fromEntries(Object.entries(a.probabilities).map(([k, p]) => [q.type === "score" ? String(Object.keys(a.probabilities).indexOf(k)) : k, Math.round(p * 100)]));
    }
  }
  return { text: JSON.stringify(bag), modeled };
}

// ---------- Real calls via Copilot CLI (usage from --usage-output-file) ----------
type Usage = { input: number; output: number; reasoning: number; cacheRead: number; cacheWrite: number; apiMs: number; premium: number };
type LiveEntry = { weights: WeightBag | null; ms: number; usage: Usage | null; at: string; raw?: string };
const sandbox = path.join(TOK_DIR, "sandbox");
mkdirSync(sandbox, { recursive: true });
const ledgerFile = path.join(TOK_DIR, "calls-ledger.json");
const ledger: { at: string; llm: string; purpose: string; key: string }[] = existsSync(ledgerFile) ? JSON.parse(readFileSync(ledgerFile, "utf8")) : [];
const budgetLeft = () => maxCalls - ledger.length;
const MCP_OFF = ["ado", "workiq-local", "vantage", "mobbin", "azure"].flatMap((s) => ["--disable-mcp-server", s]);

function readUsage(file: string): Usage | null {
  if (!existsSync(file)) return null;
  try {
    const u = JSON.parse(readFileSync(file, "utf8"));
    const m = Object.values(u.modelMetrics ?? {})[0] as { usage?: Record<string, number> } | undefined;
    if (!m?.usage) return null;
    return {
      input: m.usage.inputTokens ?? 0, output: m.usage.outputTokens ?? 0, reasoning: m.usage.reasoningTokens ?? 0,
      cacheRead: m.usage.cacheReadTokens ?? 0, cacheWrite: m.usage.cacheWriteTokens ?? 0,
      apiMs: u.totalApiDurationMs ?? 0, premium: u.totalPremiumRequestCost ?? 0,
    };
  } catch {
    return null;
  }
}

let seq = 0;
function runCopilot(prompt: string, llm: string): Promise<{ text: string; ms: number; usage: Usage | null }> {
  const usageFile = path.resolve(sandbox, `usage-${process.pid}-${seq++}.json`);
  return new Promise((resolve) => {
    const started = performance.now();
    const [modelId, effort] = llm.split("@");
    const child = spawn("copilot", ["-p", prompt, "-s", "--no-color", "--stream", "off", "--model", modelId!, ...(effort ? ["--reasoning-effort", effort] : []), "--no-custom-instructions", "--disable-builtin-mcps", ...MCP_OFF, "--usage-output-file", usageFile], { cwd: sandbox, windowsHide: true });
    let text = "";
    child.stdout.on("data", (d) => (text += d));
    child.stderr.on("data", (d) => (text += d));
    const timer = setTimeout(() => child.kill(), 360_000);
    const done = () => {
      clearTimeout(timer);
      const usage = readUsage(usageFile);
      rmSync(usageFile, { force: true });
      resolve({ text, ms: performance.now() - started, usage });
    };
    child.on("close", done);
    child.on("error", (e) => {
      text = String(e);
      done();
    });
  });
}

const liveCaches = new Map<string, Record<string, LiveEntry>>();
const liveCacheFile = (llm: string) => path.join(TOK_DIR, "cache", `${llm.replace(/[^\w.-]/g, "_")}.json`);
function liveCache(llm: string) {
  if (!liveCaches.has(llm)) liveCaches.set(llm, existsSync(liveCacheFile(llm)) ? JSON.parse(readFileSync(liveCacheFile(llm), "utf8")) : {});
  return liveCaches.get(llm)!;
}
async function liveCall(prompt: string, llm: string, purpose: string): Promise<LiveEntry | null> {
  const key = promptKey(prompt);
  const cache = liveCache(llm);
  if (cache[key]?.usage) return cache[key]!;
  if (budgetLeft() <= 0) return null;
  ledger.push({ at: new Date().toISOString(), llm, purpose, key });
  writeFileSync(ledgerFile, JSON.stringify(ledger, null, 1));
  const { text, ms, usage } = await runCopilot(prompt, llm);
  const weights = extractJson(text);
  const entry: LiveEntry = { weights, ms, usage, at: new Date().toISOString(), ...(weights ? {} : { raw: text.slice(0, 300) }) };
  cache[key] = entry;
  writeFileSync(liveCacheFile(llm), JSON.stringify(cache, null, 1));
  return entry;
}
async function pool<T>(items: T[], fn: (t: T) => Promise<void>) {
  const q = items.slice();
  await Promise.all(Array.from({ length: concurrency }, async () => { while (q.length) await fn(q.shift()!); }));
}

// ---------- Workload classification (by the first question's shape) ----------
function workload(r: DecisionRequest): string {
  const q = r.questions[0]!;
  const text = `${q.id} ${q.instructions} ${q.type === "choice" ? q.options.map((o) => `${o.key} ${o.description}`).join(" ") : ""}`.toLowerCase();
  if (q.type === "choice") {
    const keys = q.options.map((o) => o.key.toLowerCase());
    if (keys.includes("edit") && (keys.includes("ask") || keys.includes("stop"))) return "edit/ask/stop gating";
    if (/\b(pull request|pr\b|merge|code review|approve)/.test(text)) return "PR review gating";
    if (/\b(moderat|allow|remove|spam|harass|toxic)/.test(text)) return "moderation";
    if (/\btool\b|\btools\b|which (command|function|api)/.test(text)) return "tool selection";
    return "routing/triage";
  }
  if (q.type === "score") return "severity scoring";
  return "guardrail yes/no";
}

// ---------- Keel pass ----------
const abCacheFile = path.join("artifacts", "ab-cache", `${ABLLM}.json`);
const abCache: Record<string, { weights: WeightBag | null; ms: number }> = existsSync(abCacheFile) ? JSON.parse(readFileSync(abCacheFile, "utf8")) : {};

const work = suiteNames.flatMap((suite) => (ALL_SUITES[suite] ?? []).map((item) => ({ suite, item })));
console.log(`keel-tokens: ${work.length} cases, Keel=${model.config.id} (${path.relative(process.cwd(), modelDir)}), blind: ${blindNote}`);
await neuralWeights(prepare(work[0]!.item), modelDir);
type Case = {
  suite: string; item: EvalCase; request: DecisionRequest; workload: string;
  keel: Record<string, Answer>; keelMs: number;
  llm: WeightBag | null; llmSource: string | null; llmMs: number | null;
};
const cases: Case[] = [];
for (const { suite, item } of work) {
  const request = prepare(item);
  const t0 = performance.now();
  const keel = projectWeights(request, (await neuralWeights(request, modelDir))!);
  const keelMs = performance.now() - t0;
  const key = promptKey(llmPrompt(request));
  const ab = abCache[key];
  const live = liveCache(blindLlm)[key];
  const llm = ab?.weights ?? live?.weights ?? null;
  cases.push({
    suite, item, request, workload: workload(request), keel, keelMs,
    llm, llmSource: ab?.weights ? ABLLM : live?.weights ? blindLlm : null, llmMs: ab?.weights ? ab.ms : live?.weights ? live.ms : null,
  });
}

// ---------- Real calls (budgeted) ----------
// Blind cases without an LLM answer: get one from --blind-llm (also yields real usage).
const needBlind = cases.filter((c) => c.suite.startsWith("blind") && !c.llm).sort((a, b) => promptKey("blind" + a.item.id).localeCompare(promptKey("blind" + b.item.id))).slice(0, Math.max(0, blindCalls));
if (needBlind.length) {
  console.log(`  blind LLM answers: ${needBlind.length} calls to ${blindLlm} (budget left ${budgetLeft()})`);
  await pool(needBlind, async (c) => {
    const e = await liveCall(llmPrompt(c.request), blindLlm, `blind-answer:${c.suite}:${c.item.id}`);
    if (e?.weights) { c.llm = e.weights; c.llmSource = blindLlm; c.llmMs = e.ms; }
  });
}
// Stratified sample of held-out cases for sub-call usage and deliberation measurements.
// Headline = public held-out suites (graded against the cached gpt-5-mini answers). Blind is reported separately.
const heldOutCases = cases.filter((c) => !IN_SAMPLE.has(c.suite) && !c.suite.startsWith("blind"));
const blindCases = cases.filter((c) => c.suite.startsWith("blind"));
function sample(n: number, salt: string): Case[] {
  return heldOutCases.slice().sort((a, b) => promptKey(salt + a.suite + a.item.id).localeCompare(promptKey(salt + b.suite + b.item.id))).slice(0, n);
}
const TRIVIAL = 'Reply with the JSON {"ok":1} and nothing else. Do not use tools.';
if (liveN > 0) {
  await liveCall(TRIVIAL, liveLlm, "harness-baseline");
  await pool(sample(liveN, "live"), async (c) => void (await liveCall(llmPrompt(c.request), liveLlm, `subcall:${c.suite}:${c.item.id}`)));
}
if (frontierN > 0) {
  await liveCall(TRIVIAL, frontierLlm, "harness-baseline");
  await pool(sample(frontierN, "frontier"), async (c) => void (await liveCall(llmPrompt(c.request), frontierLlm, `deliberation:${c.suite}:${c.item.id}`)));
}

// Summaries of real measurements (all cached entries for that LLM, so re-runs keep them).
type Measured = { llm: string; calls: number; baselineInput: number | null; meanInput: number; meanOutput: number; meanReasoning: number; meanDecisionInputDelta: number | null; meanPromptO200k: number; reasoningPerQuestion: number; outputPerQuestion: number; medianApiMs: number; medianWallMs: number; premiumPerCall: number; parseFailures: number };
const byKey = new Map(cases.map((c) => [promptKey(llmPrompt(c.request)), c]));
function measured(llm: string): Measured | null {
  const cache = liveCache(llm);
  const base = cache[promptKey(TRIVIAL)]?.usage ?? null;
  const rows = Object.entries(cache).filter(([k, e]) => k !== promptKey(TRIVIAL) && e.usage && byKey.has(k));
  if (!rows.length) return null;
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length);
  const median = (xs: number[]) => { const s = xs.slice().sort((a, b) => a - b); return s[Math.floor(s.length / 2)] ?? 0; };
  const qs = rows.map(([k]) => byKey.get(k)!.request.questions.length);
  return {
    llm, calls: rows.length,
    baselineInput: base?.input ?? null,
    meanInput: mean(rows.map(([, e]) => e.usage!.input)),
    meanOutput: mean(rows.map(([, e]) => e.usage!.output)),
    meanReasoning: mean(rows.map(([, e]) => e.usage!.reasoning)),
    meanDecisionInputDelta: base ? mean(rows.map(([, e]) => e.usage!.input - base.input)) : null,
    meanPromptO200k: mean(rows.map(([k]) => tok(llmPrompt(byKey.get(k)!.request)))),
    reasoningPerQuestion: rows.reduce((a, [, e]) => a + e.usage!.reasoning, 0) / qs.reduce((a, b) => a + b, 0),
    outputPerQuestion: rows.reduce((a, [, e]) => a + e.usage!.output, 0) / qs.reduce((a, b) => a + b, 0),
    medianApiMs: median(rows.map(([, e]) => e.usage!.apiMs)),
    medianWallMs: median(rows.map(([, e]) => e.ms)),
    premiumPerCall: mean(rows.map(([, e]) => e.usage!.premium)),
    parseFailures: rows.filter(([, e]) => !e.weights).length,
  };
}
const liveM = measured(liveLlm);
const frontierM = measured(frontierLlm);
const frontierAltM = frontierEffort ? measured(frontierLlm.split("@")[0]!) : null;

// ---------- Per-case token accounting ----------
const confidenceOf = (a: Answer | undefined) => (!a ? 0 : a.type === "noul" ? Math.abs(a.noul - 0.5) * 2 : a.confidence);
const okG = (g: ReturnType<typeof grade>) => [g.choiceOk, g.scoreOk, g.noulOk].every((x) => x !== false);
const keelBody = (c: Case) => JSON.stringify({ model: "decider-latest", state: c.item.state, questions: c.item.questions });
const keelResponse = (c: Case) => JSON.stringify({ model: model.config.id, answers: c.keel, usage: { input_tokens: 0, output_tokens: 0 } });

type TauRow = {
  tau: number; deferredQ: number; calls: number;
  // A: dedicated decision sub-call (minimal prompt, tokenizer-exact)
  aIn: number; aOut: number;
  // C: in-context frontier deliberation (output-heavy)
  cIn: number; cOut: number;
  fullyRight: number | null; safety: number | null; regress: number | null; improve: number | null;
  latencyMs: number[];
};
type CaseTok = { offIn: number; offOut: number; offModeled: boolean; nq: number; keelBodyTok: number; keelRespTok: number; perTau: Record<string, TauRow> };

const reasoningPerQ = (m: Measured | null) => (m ? m.reasoningPerQuestion : 0);
const frontierPerQ = frontierM ? frontierM.reasoningPerQuestion + frontierM.outputPerQuestion : null;
const subcallReasoningPerQ = reasoningPerQ(liveM);

function caseTokens(c: Case): CaseTok {
  const ids = c.request.questions.map((q) => q.id);
  const offPrompt = llmPrompt(c.request);
  const offComp = completionText(c.request, ids, c.llm, c.keel);
  const llmAnswers = c.llm ? projectWeights(c.request, c.llm) : null;
  const offOk = llmAnswers ? okG(grade(c.item, llmAnswers)) : null;
  const perTau: Record<string, TauRow> = {};
  const bodyTok = tok(keelBody(c)) + 10; // + tool-call wrapper (name, url, headers) ~10 tokens
  const respTok = tok(keelResponse(c)) + 4;
  for (const t of TAUS) {
    const deferred = c.request.questions.filter((q) => confidenceOf(c.keel[q.id]) < t).map((q) => q.id);
    const call = deferred.length > 0;
    const sub = subset(c.request, deferred);
    const comp = call ? completionText(c.request, deferred, c.llm, c.keel) : { text: "", modeled: false };
    let fullyRight: number | null = null, safety: number | null = null, regress: number | null = null, improve: number | null = null;
    if (llmAnswers) {
      const merged: Record<string, Answer> = { ...c.keel };
      for (const id of deferred) if (llmAnswers[id]) merged[id] = llmAnswers[id]!;
      const g = grade(c.item, merged);
      fullyRight = okG(g) ? 1 : 0;
      safety = g.safetyMiss ? 1 : 0;
      regress = offOk && !okG(g) ? 1 : 0;
      improve = !offOk && okG(g) ? 1 : 0;
    }
    perTau[String(t)] = {
      tau: t, deferredQ: deferred.length, calls: call ? 1 : 0,
      aIn: call ? tok(llmPrompt(sub)) + FRAMING : 0,
      aOut: call ? tok(comp.text) : 0,
      cIn: respTok,
      cOut: bodyTok,
      fullyRight, safety, regress, improve,
      latencyMs: [c.keelMs + (call && c.llmMs != null ? c.llmMs : 0)],
    };
  }
  return { offIn: tok(offPrompt) + FRAMING, offOut: tok(offComp.text), offModeled: offComp.modeled, nq: ids.length, keelBodyTok: bodyTok, keelRespTok: respTok, perTau };
}
const toks = new Map(cases.map((c) => [c, caseTokens(c)]));

// ---------- Aggregation ----------
type Agg = Record<string, unknown>;
function aggregate(cs: Case[]) {
  const sum = (f: (c: Case, t: CaseTok) => number) => cs.reduce((a, c) => a + f(c, toks.get(c)!), 0);
  const graded = cs.filter((c) => c.llm);
  const offIn = sum((_, t) => t.offIn), offOut = sum((_, t) => t.offOut), nq = sum((_, t) => t.nq);
  const offFully = graded.filter((c) => okG(grade(c.item, projectWeights(c.request, c.llm!)))).length;
  const offSafety = graded.filter((c) => grade(c.item, projectWeights(c.request, c.llm!)).safetyMiss).length;
  const offLat = cs.filter((c) => c.llmMs != null).map((c) => c.llmMs!);
  const median = (xs: number[]) => { const s = xs.slice().sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)]! : null; };
  const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
  const offR = Math.round(subcallReasoningPerQ * nq);
  const offC = frontierPerQ != null ? Math.round(frontierPerQ * nq) : null;
  const tau: Agg[] = TAUS.map((t) => {
    const k = String(t);
    const rows = cs.map((c) => toks.get(c)!.perTau[k]!);
    const s = (f: (r: TauRow) => number) => rows.reduce((a, r) => a + f(r), 0);
    const deferredQ = s((r) => r.deferredQ), calls = s((r) => r.calls);
    const aIn = s((r) => r.aIn), aOut = s((r) => r.aOut);
    const aR = Math.round(subcallReasoningPerQ * deferredQ);
    const cIn = s((r) => r.cIn), cOutBody = s((r) => r.cOut);
    const cDelib = frontierPerQ != null ? Math.round(frontierPerQ * deferredQ) : null;
    const gr = graded.map((c) => toks.get(c)!.perTau[k]!);
    const lat = cs.filter((c) => c.llmMs != null).map((c) => toks.get(c)!.perTau[k]!.latencyMs[0]!);
    const pct = (a: number, b: number) => (b ? Math.round((1 - a / b) * 1000) / 10 : null);
    return {
      tau: t, llmCalls: calls, cases: cs.length, callsAvoided: cs.length - calls, questionsDeferred: deferredQ, questions: nq,
      A_visible: { offTokens: offIn + offOut, onTokens: aIn + aOut, onIn: aIn, onOut: aOut, reductionPct: pct(aIn + aOut, offIn + offOut) },
      A_withReasoning: { offTokens: offIn + offOut + offR, onTokens: aIn + aOut + aR, reductionPct: pct(aIn + aOut + aR, offIn + offOut + offR) },
      B_copilotSubagent: liveM ? { offTokens: Math.round(cs.length * (liveM.meanInput + liveM.meanOutput)), onTokens: Math.round(calls * (liveM.meanInput + liveM.meanOutput)), reductionPct: pct(calls, cs.length) } : null,
      C_inContext: cDelib != null && offC != null ? { offOut: offC, onIn: cIn, onOut: cOutBody + cDelib, onTotal: cIn + cOutBody + cDelib, reductionPct: pct(cIn + cOutBody + cDelib, offC), outputReductionPct: pct(cOutBody + cDelib, offC) } : { onIn: cIn, onOutBodyOnly: cOutBody, note: "no frontier measurement yet" },
      accuracy: graded.length ? {
        graded: graded.length, offFullyRight: offFully, onFullyRight: gr.reduce((a, r) => a + (r.fullyRight ?? 0), 0),
        deltaPts: Math.round(((gr.reduce((a, r) => a + (r.fullyRight ?? 0), 0) - offFully) / graded.length) * 1000) / 10,
        offSafety, onSafety: gr.reduce((a, r) => a + (r.safety ?? 0), 0),
        regressions: gr.reduce((a, r) => a + (r.regress ?? 0), 0), improvements: gr.reduce((a, r) => a + (r.improve ?? 0), 0),
      } : null,
      latency: { offMedianMs: median(offLat), onMedianMs: median(lat), offMeanMs: mean(offLat), onMeanMs: mean(lat) },
    };
  });
  return {
    cases: cs.length, graded: graded.length, questions: nq, modeledCompletions: cs.filter((c) => toks.get(c)!.offModeled).length,
    llmSources: [...new Set(graded.map((c) => c.llmSource))],
    off: { A_in: offIn, A_out: offOut, A_reasoningEst: offR, C_deliberation: offC },
    keelMs: { median: median(cs.map((c) => c.keelMs)), p95: (() => { const s = cs.map((c) => c.keelMs).sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.round(0.95 * (s.length - 1)))] ?? null; })() },
    tau,
  };
}

const groups: { name: string; cs: Case[] }[] = [
  ...suiteNames.map((s) => ({ name: s, cs: cases.filter((c) => c.suite === s) })).filter((g) => g.cs.length),
  { name: "held-out total", cs: heldOutCases },
  ...(blindCases.length ? [{ name: "blind", cs: blindCases }] : []),
];
const results = Object.fromEntries(groups.map((g) => [g.name, aggregate(g.cs)]));
const workloads = [...new Set(heldOutCases.map((c) => c.workload))].sort();
const byWorkload = Object.fromEntries(workloads.map((w) => [w, aggregate(heldOutCases.filter((c) => c.workload === w))]));

// ---------- Report ----------
type R = ReturnType<typeof aggregate>;
const T = (r: R, t: number) => r.tau.find((x) => x.tau === t)! as Record<string, any>;
const n = (x: number | null | undefined) => (x == null ? "—" : Math.round(x).toLocaleString("en-US"));
const p = (x: number | null | undefined) => (x == null ? "—" : `${x}%`);
const ms = (x: number | null | undefined) => (x == null ? "—" : x >= 1000 ? `${(x / 1000).toFixed(1)} s` : `${Math.round(x)} ms`);
const ho = results["held-out total"]!;
const h = T(ho, HEADLINE_TAU);

const L: string[] = [
  `# Keel token-savings benchmark`,
  ``,
  `Generated ${new Date().toISOString()} by \`scripts/keel-tokens.ts\`. Keel: \`${model.config.id}\` from \`${path.relative(process.cwd(), modelDir).replace(/\\/g, "/")}\`.`,
  `Suites: ${groups.map((g) => `${g.name} (${g.cs.length})`).join(", ")}. Blind suite: ${blindNote}.`,
  ``,
  `**Headline (held-out, τ = ${HEADLINE_TAU}, dedicated decision sub-call, tokenizer-exact):** ${n(h.A_visible.offTokens)} → ${n(h.A_visible.onTokens)} LLM tokens (**${p(h.A_visible.reductionPct)} fewer**), ${h.callsAvoided}/${h.cases} LLM calls avoided, accuracy ${h.accuracy ? `${h.accuracy.offFullyRight}/${h.accuracy.graded} → ${h.accuracy.onFullyRight}/${h.accuracy.graded} cases fully right (**${h.accuracy.deltaPts >= 0 ? "+" : ""}${h.accuracy.deltaPts} pts**), safety misses ${h.accuracy.offSafety} → ${h.accuracy.onSafety}` : "not graded"}.`,
  ``,
  `## How tokens are counted`,
  ``,
  `- **Tokenizer:** \`gpt-tokenizer\` o200k_base (devDependency added for this benchmark). Chat framing +${FRAMING} tokens per LLM call.`,
  `- **OFF (no Keel):** every decision is one LLM call. Input = the exact decision prompt from \`scripts/keel-ab.ts\` (instructions + state + question schema). Output = the LLM's real JSON answer (gpt-5-mini answers cached by keel-ab; ${ho.modeledCompletions} of ${ho.cases} held-out completions had no cached answer and were modeled from Keel's weights in the same JSON shape).`,
  `- **ON (with Keel):** Keel answers every question with confidence ≥ τ (noul confidence = |p − 0.5| × 2) locally for 0 LLM tokens. If any question is below τ, the agent makes one LLM call with **only the deferred questions** (same prompt template, subset of questions) and receives only those answers. Accuracy assumes the LLM gives the same per-question answer when asked fewer questions (questions are independent in the prompt); the answers used are from the full-prompt call.`,
  `- **Scenario A (visible):** prompt + completion, tokenizer-exact. **A + reasoning:** adds hidden reasoning tokens at the per-question rate measured on real ${liveLlm} calls (${liveM ? `${liveM.reasoningPerQuestion.toFixed(1)} tokens/question over ${liveM.calls} calls` : "no measurement yet → 0"}).`,
  `- **Scenario B (Copilot CLI sub-agent, measured):** what keel-ab actually did — spawn \`copilot -p\` per decision. Per-call cost = real mean input+output tokens from \`--usage-output-file\` on ${liveM ? `${liveM.calls} real ${liveLlm} calls` : "(no live calls yet)"}; total = calls × mean. Includes the CLI's own system prompt/tool schema (the harness overhead), so it is much larger than A.`,
  `- **Scenario C (frontier agent deliberating in-context):** OFF = the agent reasons about each decision itself; deliberation tokens/question = (reasoning + output) measured on real ${frontierLlm} calls on the same decision prompt (${frontierM ? `${(frontierM.reasoningPerQuestion + frontierM.outputPerQuestion).toFixed(1)} tokens/question over ${frontierM.calls} calls` : "no measurement yet"}). This is an **estimate**: OFF = rate × questions; ON = Keel tool-call body the agent must emit (output, o200k count of \`{model,state,questions}\` + 10) + Keel's JSON response read back (input, o200k + 4) + rate × deferred questions. The state is assumed to already be in the agent's context in both modes. The one-time Keel instruction block in the agent's system prompt (${tok(readFileSync(".github/agents/keel.agent.md", "utf8"))} o200k tokens for \`.github/agents/keel.agent.md\`) is excluded from per-decision totals (it is prompt-cached per session).`,
  `- **Latency:** OFF = measured wall time of the gpt-5-mini Copilot CLI call cached by keel-ab (includes CLI start-up); ON = measured in-process Keel time + that LLM time only when a call is needed.`,
  ``,
  `## Held-out results by τ (holdout-20 + holdout-b-20 + open-60)`,
  ``,
];
const TAU_HEAD = [
  `| τ | LLM calls (avoided) | Questions deferred | A tokens OFF → ON | A cut | A+reasoning cut | B Copilot-subagent tokens OFF → ON | C in-context OFF → ON | C cut | Cases fully right OFF → ON (Δ) | Safety misses OFF → ON | Regr. / impr. | Latency median OFF → ON | Latency mean OFF → ON |`,
  `|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|`,
];
L.push(...TAU_HEAD);
const tauRows = (g: R) => { for (const t of TAUS) {
  const r = T(g, t);
  const a = r.accuracy;
  L.push(`| ${t} | ${r.llmCalls}/${r.cases} (${r.callsAvoided}) | ${r.questionsDeferred}/${r.questions} | ${n(r.A_visible.offTokens)} → ${n(r.A_visible.onTokens)} | ${p(r.A_visible.reductionPct)} | ${p(r.A_withReasoning.reductionPct)} | ${r.B_copilotSubagent ? `${n(r.B_copilotSubagent.offTokens)} → ${n(r.B_copilotSubagent.onTokens)} (${p(r.B_copilotSubagent.reductionPct)})` : "—"} | ${r.C_inContext.offOut != null ? `${n(r.C_inContext.offOut)} → ${n(r.C_inContext.onTotal)}` : "—"} | ${p(r.C_inContext.reductionPct)} | ${a ? `${a.offFullyRight}/${a.graded} → ${a.onFullyRight}/${a.graded} (${a.deltaPts >= 0 ? "+" : ""}${a.deltaPts})` : "—"} | ${a ? `${a.offSafety} → ${a.onSafety}` : "—"} | ${a ? `${a.regressions} / ${a.improvements}` : "—"} | ${ms(r.latency.offMedianMs)} → ${ms(r.latency.onMedianMs)} | ${ms(r.latency.offMeanMs)} → ${ms(r.latency.onMeanMs)} |`);
} };
tauRows(ho);
if (blindCases.length) {
  const b = results["blind"]!;
  const graded = T(b, HEADLINE_TAU).accuracy?.graded ?? 0;
  L.push(``, `## Blind suite by τ (data-1, ${blindCases.length} cases; never inspected by hand)`, ``,
    `Token columns cover all ${blindCases.length} blind cases. Accuracy covers only the ${graded} blind cases with a real ${blindLlm} answer (no gpt-5-mini cache exists for blind), so OFF accuracy here is ${blindLlm}, not gpt-5-mini; OFF latency uses those calls' wall time.`, ``, ...TAU_HEAD);
  tauRows(b);
}
{
  // Scenario C depends entirely on how much the agent would deliberate per decision; show every measured model + break-even.
  const allMeasured = (existsSync(path.join(TOK_DIR, "cache")) ? readdirSync(path.join(TOK_DIR, "cache")) : [])
    .filter((x) => x.endsWith(".json")).map((x) => x.slice(0, -5).replace(/_(?=[a-z]+$)/, "@"))
    .map((llm) => measured(llm)).filter((m): m is Measured => !!m);
  const rowsAt = heldOutCases.map((c) => ({ t: toks.get(c)!, r: toks.get(c)!.perTau[String(HEADLINE_TAU)]! }));
  const keelOverhead = rowsAt.reduce((a, x) => a + x.r.cIn + x.r.cOut, 0);
  const nqAll = rowsAt.reduce((a, x) => a + x.t.nq, 0), defQ = rowsAt.reduce((a, x) => a + x.r.deferredQ, 0);
  const breakEven = keelOverhead / Math.max(1, nqAll - defQ);
  L.push(``, `### Scenario C sensitivity (held-out, τ = ${HEADLINE_TAU}; real per-question deliberation rates)`, ``,
    `Keel overhead the agent pays in-context: ${n(keelOverhead)} tokens (tool-call bodies + responses) for ${nqAll - defQ} of ${nqAll} questions answered locally. **Break-even: Keel saves tokens in C only if the agent would otherwise spend > ${breakEven.toFixed(0)} reasoning+output tokens per question.**`, ``,
    `| Measured model (Copilot CLI) | Calls | Reasoning / q | Output / q | C OFF → ON | C cut |`, `|---|---:|---:|---:|---:|---:|`);
  for (const m of allMeasured) {
    const rate = m.reasoningPerQuestion + m.outputPerQuestion;
    const off = rate * nqAll, on = keelOverhead + rate * defQ;
    L.push(`| ${m.llm} | ${m.calls} | ${m.reasoningPerQuestion.toFixed(1)} | ${m.outputPerQuestion.toFixed(1)} | ${n(off)} → ${n(on)} | ${p(Math.round((1 - on / off) * 1000) / 10)} |`);
  }
}
L.push(``, `Keel in-process latency on held-out: median ${ms(ho.keelMs.median)}, p95 ${ms(ho.keelMs.p95)} (CPU, ONNX int8, sequential, warmed).`);

L.push(``, `## Per suite (τ = ${HEADLINE_TAU})`, ``, `| Suite | Cases | LLM answers from | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |`, `|---|---:|---|---:|---:|---:|---:|`);
for (const g of groups) {
  const r = results[g.name]!;
  const x = T(r, HEADLINE_TAU);
  L.push(`| ${g.name}${IN_SAMPLE.has(g.name) ? " (in training mix)" : ""} | ${r.cases} | ${r.llmSources.join(", ") || "—"} | ${n(x.A_visible.offTokens)} → ${n(x.A_visible.onTokens)} (${p(x.A_visible.reductionPct)}) | ${x.callsAvoided}/${x.cases} | ${x.accuracy ? `${x.accuracy.offFullyRight} → ${x.accuracy.onFullyRight} /${x.accuracy.graded}` : "—"} | ${x.accuracy ? `${x.accuracy.offSafety} → ${x.accuracy.onSafety}` : "—"} |`);
}

L.push(``, `## Per agent workload (held-out, τ = ${HEADLINE_TAU})`, ``, `Workload is inferred from the first question's shape (edit/ask/stop keys, moderation/PR/tool wording, score, noul). Small n per row — treat as indicative.`, ``,
  `| Workload | Cases | A tokens OFF → ON (cut) | LLM calls avoided | Fully right OFF → ON | Safety OFF → ON |`, `|---|---:|---:|---:|---:|---:|`);
for (const w of workloads) {
  const r = byWorkload[w]!;
  const x = T(r, HEADLINE_TAU);
  L.push(`| ${w} | ${r.cases} | ${n(x.A_visible.offTokens)} → ${n(x.A_visible.onTokens)} (${p(x.A_visible.reductionPct)}) | ${x.callsAvoided}/${x.cases} | ${x.accuracy ? `${x.accuracy.offFullyRight} → ${x.accuracy.onFullyRight} /${x.accuracy.graded}` : "—"} | ${x.accuracy ? `${x.accuracy.offSafety} → ${x.accuracy.onSafety}` : "—"} |`);
}

L.push(``, `## Real LLM measurements (Copilot CLI, \`--usage-output-file\`)`, ``);
for (const m of [liveM, frontierM]) {
  if (!m) continue;
  L.push(`- **${m.llm}** — ${m.calls} decision calls${m.parseFailures ? ` (${m.parseFailures} unparseable)` : ""}: mean input ${n(m.meanInput)} tokens (harness-only baseline call: ${n(m.baselineInput)}; decision prompt adds ${n(m.meanDecisionInputDelta)} in the model's own tokenizer vs ${n(m.meanPromptO200k)} o200k), mean output ${n(m.meanOutput)}, of which reasoning ${n(m.meanReasoning)}; per question: reasoning ${m.reasoningPerQuestion.toFixed(1)}, output ${m.outputPerQuestion.toFixed(1)}. Median API time ${ms(m.medianApiMs)}, median wall time ${ms(m.medianWallMs)} (CLI start-up included). Copilot premium-request cost ${m.premiumPerCall.toFixed(2)}/call.`);
}
if (!liveM && !frontierM) L.push(`- None yet (run with \`--live N\` / \`--frontier N\`).`);
L.push(`- Real calls made by this script so far: ${ledger.length} / ${maxCalls} budget (ledger: \`artifacts/parity/tokens/calls-ledger.json\`).`);

L.push(``, `## Caveats`, ``,
  `- Savings scale with how often Keel is confident; that is model- and workload-dependent. The accuracy columns are there so a cut never hides a quality loss: read Δ and safety misses next to every token number.`,
  `- Held-out sets are small (±10–15 pts on accuracy). labeled-50 is in Keel's training mix and is excluded from the held-out totals.`,
  `- OFF accuracy is gpt-5-mini via Copilot CLI (Sept 2026 cache); gpt-5-mini is no longer selectable in this CLI, so new real measurements use ${liveLlm}/${frontierLlm}. Token counts for A are model-independent (o200k); B and C rates are specific to the measured models.`,
  `- Keel itself spends 0 LLM tokens (local ONNX). Its CPU cost is in the latency column.`,
);

writeFileSync(`${out}.md`, L.join("\n") + "\n");
writeFileSync(`${out}.json`, JSON.stringify({
  generatedAt: new Date().toISOString(), keel: model.config.id, modelDir: path.relative(process.cwd(), modelDir).replace(/\\/g, "/"),
  tokenizer: "gpt-tokenizer o200k_base", framingPerCall: FRAMING, headlineTau: HEADLINE_TAU, blind: blindNote,
  measurements: { subcall: liveM, frontier: frontierM, realCallsUsed: ledger.length, budget: maxCalls },
  results, byWorkload,
  cases: cases.map((c) => ({ suite: c.suite, id: c.item.id, workload: c.workload, questions: c.request.questions.length, llmSource: c.llmSource, keelMs: Math.round(c.keelMs * 100) / 100, offIn: toks.get(c)!.offIn, offOut: toks.get(c)!.offOut, perTau: Object.fromEntries(Object.entries(toks.get(c)!.perTau).map(([k, r]) => [k, { deferredQ: r.deferredQ, aIn: r.aIn, aOut: r.aOut, cIn: r.cIn, cOut: r.cOut, fullyRight: r.fullyRight, safety: r.safety }])) })),
}, null, 1));
console.log(L.slice(0, 30).join("\n"));
