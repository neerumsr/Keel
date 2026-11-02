/**
 * Keel vs live Microsoft-Decision-1 (MSD1). Opt-in only: needs an OpenRouter key or a
 * Microsoft Foundry deployment, and is never run by the default tests. MSD1 fields stay
 * null unless MSD1 actually answered. See artifacts/parity/msd1/api-and-access.md.
 *
 * MSD1 speaks the same System One wire as Jev and Keel (state + typed questions →
 * answers keyed by question id), so the request is projected from the already-parsed
 * Keel request and the response is validated (not re-scored) into Keel's Answer type.
 */
import type { EvalCase } from "./eval-set.ts";
import { grade, prepare, type Judge } from "./eval.ts";
import { projectWeights, type Answer, type DecisionRequest, type Json } from "./wire.ts";

export const OPENROUTER_SYSTEMONE_URL = "https://openrouter.ai/api/v1/systemone";
export const OPENROUTER_MSD1_MODEL = "microsoft/microsoft-decision-1";
export const FOUNDRY_SYSTEMONE_PATH = "/providers/microsoft/v1/systemone";
export const FOUNDRY_TOKEN_RESOURCE = "https://cognitiveservices.azure.com";
export const DEFAULT_MAX_CALLS = 300;

export type Msd1Provider = "openrouter" | "foundry";

export type Msd1Config = {
  provider: Msd1Provider;
  url: string;
  /** OpenRouter model id, or the Foundry deployment name (Foundry wants the deployment, not the model). */
  model: string;
  /** Header name/value pairs. Never logged or written to the report. */
  headers: Record<string, string>;
  /** Human-readable auth mode for the report (never the secret). */
  auth: "openrouter-key" | "foundry-api-key" | "entra-token";
};

export type Msd1Resolution = { ok: true; config: Msd1Config } | { ok: false; reason: string };

type Env = Record<string, string | undefined>;
const val = (env: Env, ...names: string[]) => {
  for (const name of names) {
    const v = env[name]?.trim();
    if (v) return v;
  }
  return undefined;
};

/**
 * Pick a provider from env. `entraToken` is an `az account get-access-token` result the
 * caller fetched (the library never shells out). Order: MSD1_PROVIDER if set, else
 * Foundry when an endpoint + deployment are set, else OpenRouter when its key is set.
 */
export function resolveMsd1Config(env: Env, entraToken?: string): Msd1Resolution {
  const forced = val(env, "MSD1_PROVIDER")?.toLowerCase();
  if (forced && forced !== "openrouter" && forced !== "foundry") {
    return { ok: false, reason: `MSD1_PROVIDER must be "openrouter" or "foundry", got "${forced}". No request was sent.` };
  }
  const endpoint = val(env, "MSD1_FOUNDRY_ENDPOINT", "AZURE_AI_ENDPOINT", "AZURE_ENDPOINT");
  const deployment = val(env, "MSD1_FOUNDRY_DEPLOYMENT", "AZURE_AI_DEPLOYMENT", "DEPLOYMENT_NAME");
  const foundryKey = val(env, "MSD1_FOUNDRY_API_KEY", "AZURE_AI_API_KEY", "AZURE_API_KEY");
  const orKey = val(env, "OPENROUTER_API_KEY");

  const foundry = (): Msd1Resolution => {
    if (!endpoint || !deployment) {
      return {
        ok: false,
        reason:
          "Foundry needs MSD1_FOUNDRY_ENDPOINT (or AZURE_AI_ENDPOINT) and MSD1_FOUNDRY_DEPLOYMENT (or AZURE_AI_DEPLOYMENT). No request was sent.",
      };
    }
    const url = endpoint.replace(/\/+$/, "") + FOUNDRY_SYSTEMONE_PATH;
    if (foundryKey) return { ok: true, config: { provider: "foundry", url, model: deployment, headers: { "api-key": foundryKey }, auth: "foundry-api-key" } };
    if (entraToken) {
      return { ok: true, config: { provider: "foundry", url, model: deployment, headers: { Authorization: `Bearer ${entraToken}` }, auth: "entra-token" } };
    }
    return {
      ok: false,
      reason: "Foundry endpoint is set but there is no MSD1_FOUNDRY_API_KEY / AZURE_AI_API_KEY and no Entra token (set MSD1_USE_AZ_TOKEN=1 after `az login`). No request was sent.",
    };
  };
  const openrouter = (): Msd1Resolution =>
    orKey
      ? {
          ok: true,
          config: {
            provider: "openrouter",
            url: OPENROUTER_SYSTEMONE_URL,
            model: val(env, "MSD1_OPENROUTER_MODEL") ?? OPENROUTER_MSD1_MODEL,
            headers: { Authorization: `Bearer ${orKey}` },
            auth: "openrouter-key",
          },
        }
      : { ok: false, reason: "OPENROUTER_API_KEY is not set. No request was sent to OpenRouter." };

  if (forced === "foundry") return foundry();
  if (forced === "openrouter") return openrouter();
  if (endpoint || deployment) return foundry();
  if (orKey) return openrouter();
  return {
    ok: false,
    reason:
      "No MSD1 credential: OPENROUTER_API_KEY is not set and no Foundry deployment of Microsoft-Decision-1 is configured (MSD1_FOUNDRY_ENDPOINT + MSD1_FOUNDRY_DEPLOYMENT + key or Entra token). No request was sent.",
  };
}

/** The System One body MSD1 receives — built from the same parsed request Keel judged. */
export function toMsd1Body(request: DecisionRequest, model: string): { model: string; state: Json; questions: Record<string, Record<string, unknown>> } {
  const questions: Record<string, Record<string, unknown>> = {};
  for (const q of request.questions) {
    if (q.type === "choice") {
      questions[q.id] = {
        type: "choice",
        instructions: q.instructions,
        criteria: Object.fromEntries(q.options.map((o) => [o.key, o.description || null])),
      };
    } else if (q.type === "score") {
      questions[q.id] = { type: "score", instructions: q.instructions, criteria: [...q.levels] };
    } else {
      const body: Record<string, unknown> = { type: "noul", instructions: q.instructions };
      if (q.yes || q.no) body.criteria = { true: q.yes, false: q.no };
      questions[q.id] = body;
    }
  }
  return { model, state: request.state, questions };
}

const num = (x: unknown): number | null => (typeof x === "number" && Number.isFinite(x) ? x : null);

/**
 * Validate an MSD1 `answers` object against the request. Vendor numbers are kept as-is;
 * a field is derived only when MSD1 omitted it but returned the probabilities it is
 * defined from (choice = argmax, confidence = top p, score = Σ i·p_i), and every
 * derivation is listed in `issues`. Anything that cannot be read is dropped, never guessed.
 */
export function normalizeMsd1Answers(request: DecisionRequest, raw: unknown): { answers: Record<string, Answer>; issues: string[] } {
  const answers: Record<string, Answer> = {};
  const issues: string[] = [];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return { answers, issues: ["answers is not an object"] };
  const bag = raw as Record<string, unknown>;
  for (const q of request.questions) {
    const a = bag[q.id];
    if (!a || typeof a !== "object" || Array.isArray(a)) {
      issues.push(`${q.id}: missing`);
      continue;
    }
    const r = a as Record<string, unknown>;
    if (r.type != null && r.type !== q.type) {
      issues.push(`${q.id}: type ${String(r.type)} != ${q.type}`);
      continue;
    }
    if (q.type === "noul") {
      let p = num(r.noul);
      if (p == null && num(r.probability) != null) {
        p = num(r.probability);
        issues.push(`${q.id}: noul read from "probability"`);
      }
      if (p == null || p < 0 || p > 1) {
        issues.push(`${q.id}: no noul in [0,1]`);
        continue;
      }
      answers[q.id] = { type: "noul", noul: p };
      continue;
    }
    const keys = q.type === "choice" ? q.options.map((o) => o.key) : q.levels.map((_, i) => String(i));
    const rp = r.probabilities && typeof r.probabilities === "object" && !Array.isArray(r.probabilities) ? (r.probabilities as Record<string, unknown>) : null;
    let probabilities: Record<string, number> | null = null;
    if (rp) {
      const unknown = Object.keys(rp).filter((k) => !keys.includes(k));
      if (unknown.length) issues.push(`${q.id}: unknown probability keys ${unknown.join(",")}`);
      const missing = keys.filter((k) => num(rp[k]) == null);
      if (missing.length) issues.push(`${q.id}: no probability for ${missing.join(",")}`);
      else probabilities = Object.fromEntries(keys.map((k) => [k, num(rp[k])!]));
    }
    const top = probabilities ? keys.reduce((best, k) => (probabilities![k]! > probabilities![best]! ? k : best), keys[0]!) : null;
    let confidence = num(r.confidence);
    if (confidence == null && probabilities && top) {
      confidence = probabilities[top]!;
      issues.push(`${q.id}: confidence derived from probabilities`);
    }
    if (q.type === "choice") {
      let choice = typeof r.choice === "string" && keys.includes(r.choice) ? r.choice : null;
      if (typeof r.choice === "string" && !choice) issues.push(`${q.id}: choice "${r.choice}" is not an option`);
      if (!choice && top) {
        choice = top;
        issues.push(`${q.id}: choice derived from probabilities`);
      }
      if (!choice || confidence == null) {
        issues.push(`${q.id}: unreadable choice`);
        continue;
      }
      answers[q.id] = { type: "choice", choice, confidence, probabilities: probabilities ?? {} };
    } else {
      let score = num(r.score);
      if (score == null && probabilities) {
        score = Math.round(keys.reduce((s, k, i) => s + i * probabilities![k]!, 0) * 100) / 100;
        issues.push(`${q.id}: score derived from probabilities`);
      }
      if (score == null || confidence == null) {
        issues.push(`${q.id}: unreadable score`);
        continue;
      }
      const legend =
        r.legend && typeof r.legend === "object" && !Array.isArray(r.legend)
          ? (r.legend as Record<string, string>)
          : Object.fromEntries(q.levels.map((l, i) => [String(i), l]));
      answers[q.id] = { type: "score", score, confidence, legend, probabilities: probabilities ?? {} };
    }
  }
  return { answers, issues };
}

export type Msd1Call = {
  status: number | null;
  ms: number | null;
  answers: Record<string, Answer> | null;
  issues: string[];
  servedModel: string | null;
  inputTokens: number | null;
  costUsd: number | null;
  error: string | null;
};

const empty = (error: string | null): Msd1Call => ({
  status: null,
  ms: null,
  answers: null,
  issues: [],
  servedModel: null,
  inputTokens: null,
  costUsd: null,
  error,
});

export async function callMsd1(config: Msd1Config, request: DecisionRequest, fetchImpl: typeof fetch = fetch, timeoutMs = 15_000): Promise<Msd1Call> {
  const started = performance.now();
  try {
    const response = await fetchImpl(config.url, {
      method: "POST",
      headers: { ...config.headers, "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(toMsd1Body(request, config.model)),
      signal: AbortSignal.timeout(timeoutMs),
    });
    const ms = performance.now() - started;
    if (!response.ok) return { ...empty((await response.text()).slice(0, 300)), status: response.status, ms };
    const body = (await response.json()) as { answers?: unknown; model?: unknown; usage?: Record<string, unknown> };
    const { answers, issues } = normalizeMsd1Answers(request, body.answers);
    const ok = Object.keys(answers).length > 0;
    return {
      status: response.status,
      ms,
      answers: ok ? answers : null,
      issues,
      servedModel: typeof body.model === "string" ? body.model : null,
      inputTokens: num(body.usage?.input_tokens),
      costUsd: num(body.usage?.cost),
      error: ok ? null : `no readable answers (${issues.join("; ") || "empty"})`,
    };
  } catch (error) {
    return empty(error instanceof Error ? error.message : String(error));
  }
}

type Flags = { choiceOk: boolean | null; scoreOk: boolean | null; noulOk: boolean | null };

export type Msd1Row = {
  id: number;
  name: string;
  suite: string;
  state: string;
  keel: Flags & { ms: number; answers: Record<string, Answer>; safetyMiss: boolean };
  msd1: Msd1Call & Flags & { safetyMiss: boolean | null };
  agree: { choice: boolean | null; noulSide: boolean | null; scoreAbsErr: number | null };
};

type Acc = { choice: string; score: string; noul: string; safetyMisses: number };

export type Msd1Report = {
  generatedAt: string;
  keelModel: string;
  msd1Compared: boolean;
  msd1Reason: string | null;
  msd1Provider: Msd1Provider | null;
  msd1Auth: Msd1Config["auth"] | null;
  msd1Model: string | null;
  msd1ServedModel: string | null;
  cases: number;
  msd1Calls: number;
  maxCalls: number;
  msd1InputTokens: number | null;
  msd1CostUsd: number | null;
  agreement: { choice: number | null; noulSide: number | null; scoreMae: number | null };
  latencyMs: { keel: { median: number; p95: number }; msd1: { median: number | null; p95: number | null } };
  accuracy: { keel: Acc; msd1: Acc | null };
  /** Same tallies restricted to rows MSD1 answered, so both sides see the same cases. */
  accuracyOnAnswered: { keel: Acc; msd1: Acc } | null;
  perSuite: Record<string, { cases: number; answered: number; keel: Acc; msd1: Acc | null }>;
  rows: Msd1Row[];
};

const ratio = (flags: Array<boolean | null>) => {
  const scored = flags.filter((f) => f != null).length;
  return scored ? `${flags.filter((f) => f === true).length}/${scored}` : "—";
};

function quantile(values: number[], q: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return Math.round(sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))]! * 100) / 100;
}

const accOf = (rows: Msd1Row[], side: "keel" | "msd1"): Acc => ({
  choice: ratio(rows.map((r) => r[side].choiceOk)),
  score: ratio(rows.map((r) => r[side].scoreOk)),
  noul: ratio(rows.map((r) => r[side].noulOk)),
  safetyMisses: rows.filter((r) => r[side].safetyMiss === true).length,
});

/** Statuses that mean every further call would fail the same way. */
const FATAL = new Set([400, 401, 402, 403, 404, 422]);

export async function compareMsd1(
  suites: { name: string; cases: EvalCase[] }[],
  judge: Judge,
  keelModel: string,
  resolution: Msd1Resolution,
  fetchImpl: typeof fetch = fetch,
  maxCalls = DEFAULT_MAX_CALLS,
): Promise<Msd1Report> {
  const config = resolution.ok ? resolution.config : null;
  let reason: string | null = resolution.ok ? null : resolution.reason;
  let stop = !config;
  let calls = 0;
  const rows: Msd1Row[] = [];
  for (const suite of suites) {
    for (const item of suite.cases) {
      const request = prepare(item);
      const started = performance.now();
      const answers = projectWeights(request, await judge(request));
      const keelMs = performance.now() - started;
      const k = grade(item, answers);

      let call = empty(reason);
      if (!stop && calls >= maxCalls) call = empty(`call budget of ${maxCalls} reached; not sent`);
      else if (!stop) {
        calls++;
        call = await callMsd1(config!, request, fetchImpl);
        if (call.status != null && FATAL.has(call.status) && !rows.some((r) => r.msd1.answers)) {
          reason = `${config!.provider} returned ${call.status} on the first call (${call.error ?? ""}). Stopped; check the credential, endpoint, and deployment/model name.`;
          stop = true;
        }
      }
      const m = call.answers ? grade(item, call.answers) : null;

      let choice: boolean | null = null;
      let noulSide: boolean | null = null;
      let scoreAbsErr: number | null = null;
      if (call.answers) {
        for (const [id, a] of Object.entries(answers)) {
          const b = call.answers[id];
          if (!b || a.type !== b.type) continue;
          if (a.type === "choice" && b.type === "choice") choice = a.choice === b.choice;
          if (a.type === "noul" && b.type === "noul") noulSide = a.noul >= 0.5 === b.noul >= 0.5;
          if (a.type === "score" && b.type === "score") scoreAbsErr = Math.round(Math.abs(a.score - b.score) * 1000) / 1000;
        }
      }
      rows.push({
        id: item.id,
        name: item.name,
        suite: suite.name,
        state: typeof item.state === "string" ? item.state : JSON.stringify(item.state),
        keel: { ms: keelMs, answers, choiceOk: k.choiceOk, scoreOk: k.scoreOk, noulOk: k.noulOk, safetyMiss: k.safetyMiss },
        msd1: { ...call, choiceOk: m?.choiceOk ?? null, scoreOk: m?.scoreOk ?? null, noulOk: m?.noulOk ?? null, safetyMiss: m ? m.safetyMiss : null },
        agree: { choice, noulSide, scoreAbsErr },
      });
    }
  }
  const answered = rows.filter((r) => r.msd1.answers);
  const compared = answered.length > 0;
  if (!compared && !reason) reason = `MSD1 never answered: ${rows.find((r) => r.msd1.error)?.msd1.error ?? "unknown error"}`;
  const mean = (xs: number[]) => (xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 1000) / 1000 : null);
  const frac = (xs: Array<boolean | null>) => {
    const s = xs.filter((x) => x != null) as boolean[];
    return s.length ? Math.round((s.filter(Boolean).length / s.length) * 1000) / 1000 : null;
  };
  const tokens = answered.map((r) => r.msd1.inputTokens).filter((x): x is number => x != null);
  const costs = answered.map((r) => r.msd1.costUsd).filter((x): x is number => x != null);
  const perSuite: Msd1Report["perSuite"] = {};
  for (const s of suites) {
    const rs = rows.filter((r) => r.suite === s.name);
    const ans = rs.filter((r) => r.msd1.answers);
    perSuite[s.name] = { cases: rs.length, answered: ans.length, keel: accOf(rs, "keel"), msd1: ans.length ? accOf(ans, "msd1") : null };
  }
  return {
    generatedAt: new Date().toISOString(),
    keelModel,
    msd1Compared: compared,
    msd1Reason: reason,
    msd1Provider: config?.provider ?? null,
    msd1Auth: config?.auth ?? null,
    msd1Model: config?.model ?? null,
    msd1ServedModel: answered.find((r) => r.msd1.servedModel)?.msd1.servedModel ?? null,
    cases: rows.length,
    msd1Calls: calls,
    maxCalls,
    msd1InputTokens: tokens.length ? tokens.reduce((a, b) => a + b, 0) : null,
    msd1CostUsd: costs.length ? Math.round(costs.reduce((a, b) => a + b, 0) * 1e8) / 1e8 : null,
    agreement: {
      choice: frac(answered.map((r) => r.agree.choice)),
      noulSide: frac(answered.map((r) => r.agree.noulSide)),
      scoreMae: mean(answered.map((r) => r.agree.scoreAbsErr).filter((x): x is number => x != null)),
    },
    latencyMs: {
      keel: { median: quantile(rows.map((r) => r.keel.ms), 0.5), p95: quantile(rows.map((r) => r.keel.ms), 0.95) },
      msd1: compared
        ? { median: quantile(answered.map((r) => r.msd1.ms!), 0.5), p95: quantile(answered.map((r) => r.msd1.ms!), 0.95) }
        : { median: null, p95: null },
    },
    accuracy: { keel: accOf(rows, "keel"), msd1: compared ? accOf(answered, "msd1") : null },
    accuracyOnAnswered: compared ? { keel: accOf(answered, "keel"), msd1: accOf(answered, "msd1") } : null,
    perSuite,
    rows,
  };
}

function short(answers: Record<string, Answer> | null): string {
  if (!answers) return "—";
  return Object.entries(answers)
    .map(([id, a]) => (a.type === "choice" ? `${id}=${a.choice}@${a.confidence}` : a.type === "score" ? `${id}=${a.score}` : `${id}=${a.noul}`))
    .join(", ");
}

export function msd1Markdown(report: Msd1Report): string {
  const m = report.accuracyOnAnswered;
  const lines = [
    `# Keel vs Microsoft-Decision-1 (live)`,
    ``,
    report.msd1Compared
      ? `Live MSD1 via ${report.msd1Provider} (${report.msd1Auth}; requested \`${report.msd1Model}\`, served \`${report.msd1ServedModel ?? "?"}\`) answered ${report.rows.filter((r) => r.msd1.answers).length} of ${report.cases} cases on ${report.generatedAt}. Calls sent: ${report.msd1Calls} (budget ${report.maxCalls}). Input tokens: ${report.msd1InputTokens ?? "not reported"}; cost: ${report.msd1CostUsd != null ? "$" + report.msd1CostUsd : "not reported"}.`
      : `Live MSD1 was **not** measured. ${report.msd1Reason} Every MSD1 field is null; nothing was guessed.`,
    ``,
    `| | Keel (${report.keelModel}) all cases | Keel on MSD1-answered | MSD1 |`,
    `|---|---:|---:|---:|`,
    `| Choice correct | ${report.accuracy.keel.choice} | ${m?.keel.choice ?? "—"} | ${m?.msd1.choice ?? "—"} |`,
    `| Score in band | ${report.accuracy.keel.score} | ${m?.keel.score ?? "—"} | ${m?.msd1.score ?? "—"} |`,
    `| Noul in band | ${report.accuracy.keel.noul} | ${m?.keel.noul ?? "—"} | ${m?.msd1.noul ?? "—"} |`,
    `| Safety misses | ${report.accuracy.keel.safetyMisses} | ${m?.keel.safetyMisses ?? "—"} | ${m?.msd1.safetyMisses ?? "—"} |`,
    `| Median ms | ${report.latencyMs.keel.median} (in-process) | | ${report.latencyMs.msd1.median ?? "—"} (network round trip) |`,
    `| p95 ms | ${report.latencyMs.keel.p95} | | ${report.latencyMs.msd1.p95 ?? "—"} |`,
    ``,
    `## Per suite`,
    ``,
    `| Suite | Cases | MSD1 answered | Keel choice | MSD1 choice | Keel score | MSD1 score | Keel noul | MSD1 noul | Keel safety | MSD1 safety |`,
    `|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|`,
    ...Object.entries(report.perSuite).map(
      ([name, s]) =>
        `| ${name} | ${s.cases} | ${s.answered} | ${s.keel.choice} | ${s.msd1?.choice ?? "—"} | ${s.keel.score} | ${s.msd1?.score ?? "—"} | ${s.keel.noul} | ${s.msd1?.noul ?? "—"} | ${s.keel.safetyMisses} | ${s.msd1?.safetyMisses ?? "—"} |`,
    ),
    ``,
  ];
  if (report.msd1Compared) {
    lines.push(
      `Agreement: choice ${report.agreement.choice}, noul same side of 0.5 ${report.agreement.noulSide}, score MAE ${report.agreement.scoreMae}.`,
      ``,
      `## Disagreements`,
      ``,
      `| Suite | # | State | Keel | MSD1 |`,
      `|---|---:|---|---|---|`,
    );
    for (const r of report.rows) {
      if (!r.msd1.answers) continue;
      if (r.agree.choice === false || r.agree.noulSide === false || (r.agree.scoreAbsErr ?? 0) >= 1) {
        lines.push(`| ${r.suite} | ${r.id} | ${r.state.replace(/\|/g, "\\|").replace(/\n/g, " ").slice(0, 140)} | ${short(r.keel.answers)} | ${short(r.msd1.answers)} |`);
      }
    }
    const withIssues = report.rows.filter((r) => r.msd1.issues.length);
    if (withIssues.length) {
      lines.push(``, `## Response-shape notes`, ``);
      for (const r of withIssues) lines.push(`- ${r.suite} #${r.id}: ${r.msd1.issues.join("; ")}`);
    }
    const failed = report.rows.filter((r) => !r.msd1.answers && r.msd1.error);
    if (failed.length) lines.push(``, `${failed.length} case(s) got no MSD1 answer (first error: ${failed[0]!.msd1.status ?? "network"} ${failed[0]!.msd1.error}).`);
  }
  return lines.join("\n") + "\n";
}
