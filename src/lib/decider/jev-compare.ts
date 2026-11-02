/**
 * Keel vs live TypeSafe Jev. Opt-in only: needs TYPESAFE_API_KEY and is never
 * run by the default tests. Jev fields stay null unless Jev actually answered.
 */
import type { EvalCase } from "./eval-set.ts";
import { grade, prepare, type Judge } from "./eval.ts";
import { projectWeights, type Answer } from "./wire.ts";

export const JEV_URL = "https://api.typesafe.ai/v1/systemone";
export const JEV_MODEL = "jev-1.13.0";

export type JevCall = { status: number | null; ms: number | null; answers: Record<string, Answer> | null; error: string | null };

export type CompareRow = {
  id: number;
  name: string;
  suite: string;
  state: string;
  keel: { ms: number; answers: Record<string, Answer>; choiceOk: boolean | null; scoreOk: boolean | null; noulOk: boolean | null; safetyMiss: boolean };
  jev: JevCall & { choiceOk: boolean | null; scoreOk: boolean | null; noulOk: boolean | null; safetyMiss: boolean | null };
  agree: { choice: boolean | null; noulSide: boolean | null; scoreAbsErr: number | null };
};

export type CompareReport = {
  generatedAt: string;
  keelModel: string;
  jevModel: string;
  jevCompared: boolean;
  jevReason: string | null;
  cases: number;
  agreement: { choice: number | null; noulSide: number | null; scoreMae: number | null };
  latencyMs: { keel: { median: number; p95: number }; jev: { median: number | null; p95: number | null } };
  accuracy: {
    keel: { choice: string; score: string; noul: string; safetyMisses: number };
    jev: { choice: string; score: string; noul: string; safetyMisses: number } | null;
  };
  rows: CompareRow[];
};

export async function callJev(item: EvalCase, key: string, fetchImpl: typeof fetch = fetch): Promise<JevCall> {
  const started = performance.now();
  try {
    const response = await fetchImpl(JEV_URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: JEV_MODEL, state: item.state, questions: item.questions }),
      signal: AbortSignal.timeout(10_000),
    });
    const ms = performance.now() - started;
    if (!response.ok) return { status: response.status, ms, answers: null, error: (await response.text()).slice(0, 300) };
    const body = (await response.json()) as { answers?: Record<string, Answer> };
    return { status: response.status, ms, answers: body.answers ?? null, error: body.answers ? null : "no answers field" };
  } catch (error) {
    return { status: null, ms: null, answers: null, error: error instanceof Error ? error.message : String(error) };
  }
}

const pct = (flags: Array<boolean | null>) => {
  const scored = flags.filter((f) => f != null).length;
  const ok = flags.filter((f) => f === true).length;
  return scored ? `${ok}/${scored}` : "—";
};

function quantile(values: number[], q: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return Math.round(sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))]! * 100) / 100;
}

export async function compare(
  suites: { name: string; cases: EvalCase[] }[],
  judge: Judge,
  keelModel: string,
  key: string | undefined,
  fetchImpl: typeof fetch = fetch,
): Promise<CompareReport> {
  const rows: CompareRow[] = [];
  let jevReason: string | null = key ? null : "TYPESAFE_API_KEY is not set. No request was sent to TypeSafe.";
  let stop = !key;
  for (const suite of suites) {
    for (const item of suite.cases) {
      const request = prepare(item);
      const started = performance.now();
      const answers = projectWeights(request, await judge(request));
      const keelMs = performance.now() - started;
      const k = grade(item, answers);

      let jev: JevCall = { status: null, ms: null, answers: null, error: jevReason };
      if (!stop) {
        jev = await callJev(item, key!, fetchImpl);
        if (jev.status === 401 || jev.status === 403) {
          jevReason = `TypeSafe returned ${jev.status}. Check TYPESAFE_API_KEY. Stopped after the first rejection.`;
          stop = true;
        }
      }
      const j = jev.answers ? grade(item, jev.answers) : null;

      let choice: boolean | null = null;
      let noulSide: boolean | null = null;
      let scoreAbsErr: number | null = null;
      if (jev.answers) {
        for (const [id, a] of Object.entries(answers)) {
          const b = jev.answers[id];
          if (!b || a.type !== b.type) continue;
          if (a.type === "choice" && b.type === "choice") choice = a.choice === b.choice;
          if (a.type === "noul" && b.type === "noul") noulSide = a.noul >= 0.5 === b.noul >= 0.5;
          if (a.type === "score" && b.type === "score") scoreAbsErr = Math.abs(a.score - b.score);
        }
      }
      rows.push({
        id: item.id,
        name: item.name,
        suite: suite.name,
        state: typeof item.state === "string" ? item.state : JSON.stringify(item.state),
        keel: { ms: keelMs, answers, choiceOk: k.choiceOk, scoreOk: k.scoreOk, noulOk: k.noulOk, safetyMiss: k.safetyMiss },
        jev: {
          ...jev,
          choiceOk: j?.choiceOk ?? null,
          scoreOk: j?.scoreOk ?? null,
          noulOk: j?.noulOk ?? null,
          safetyMiss: j ? j.safetyMiss : null,
        },
        agree: { choice, noulSide, scoreAbsErr },
      });
    }
  }
  const answered = rows.filter((r) => r.jev.answers);
  const jevCompared = answered.length > 0;
  if (!jevCompared && !jevReason) jevReason = `TypeSafe never answered: ${rows[0]?.jev.error ?? "unknown error"}`;
  const mean = (xs: number[]) => (xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 1000) / 1000 : null);
  const frac = (xs: Array<boolean | null>) => {
    const s = xs.filter((x) => x != null) as boolean[];
    return s.length ? Math.round((s.filter(Boolean).length / s.length) * 1000) / 1000 : null;
  };
  return {
    generatedAt: new Date().toISOString(),
    keelModel,
    jevModel: JEV_MODEL,
    jevCompared,
    jevReason,
    cases: rows.length,
    agreement: {
      choice: frac(answered.map((r) => r.agree.choice)),
      noulSide: frac(answered.map((r) => r.agree.noulSide)),
      scoreMae: mean(answered.map((r) => r.agree.scoreAbsErr).filter((x): x is number => x != null)),
    },
    latencyMs: {
      keel: { median: quantile(rows.map((r) => r.keel.ms), 0.5), p95: quantile(rows.map((r) => r.keel.ms), 0.95) },
      jev: jevCompared
        ? { median: quantile(answered.map((r) => r.jev.ms!), 0.5), p95: quantile(answered.map((r) => r.jev.ms!), 0.95) }
        : { median: null, p95: null },
    },
    accuracy: {
      keel: {
        choice: pct(rows.map((r) => r.keel.choiceOk)),
        score: pct(rows.map((r) => r.keel.scoreOk)),
        noul: pct(rows.map((r) => r.keel.noulOk)),
        safetyMisses: rows.filter((r) => r.keel.safetyMiss).length,
      },
      jev: jevCompared
        ? {
            choice: pct(answered.map((r) => r.jev.choiceOk)),
            score: pct(answered.map((r) => r.jev.scoreOk)),
            noul: pct(answered.map((r) => r.jev.noulOk)),
            safetyMisses: answered.filter((r) => r.jev.safetyMiss).length,
          }
        : null,
    },
    rows,
  };
}

function short(answers: Record<string, Answer> | null): string {
  if (!answers) return "—";
  return Object.entries(answers)
    .map(([id, a]) => (a.type === "choice" ? `${id}=${a.choice}@${a.confidence}` : a.type === "score" ? `${id}=${a.score}` : `${id}=${a.noul}`))
    .join(", ");
}

export function compareMarkdown(report: CompareReport): string {
  const lines = [
    `# Keel vs Jev`,
    ``,
    report.jevCompared
      ? `Live Jev (${report.jevModel}) was measured on ${report.rows.filter((r) => r.jev.answers).length} of ${report.cases} cases on ${report.generatedAt}.`
      : `Live Jev was **not** measured. ${report.jevReason} Every Jev field is null; nothing was guessed.`,
    ``,
    `| | Keel (${report.keelModel}) | Jev (${report.jevModel}) |`,
    `|---|---:|---:|`,
    `| Choice correct | ${report.accuracy.keel.choice} | ${report.accuracy.jev?.choice ?? "—"} |`,
    `| Score in band | ${report.accuracy.keel.score} | ${report.accuracy.jev?.score ?? "—"} |`,
    `| Noul in band | ${report.accuracy.keel.noul} | ${report.accuracy.jev?.noul ?? "—"} |`,
    `| Safety misses | ${report.accuracy.keel.safetyMisses} | ${report.accuracy.jev?.safetyMisses ?? "—"} |`,
    `| Median ms | ${report.latencyMs.keel.median} | ${report.latencyMs.jev.median ?? "—"} |`,
    `| p95 ms | ${report.latencyMs.keel.p95} | ${report.latencyMs.jev.p95 ?? "—"} |`,
    ``,
  ];
  if (report.jevCompared) {
    lines.push(
      `Agreement: choice ${report.agreement.choice}, noul same side of 0.5 ${report.agreement.noulSide}, score MAE ${report.agreement.scoreMae}.`,
      ``,
      `## Disagreements`,
      ``,
      `| Suite | # | State | Keel | Jev |`,
      `|---|---:|---|---|---|`,
    );
    for (const r of report.rows) {
      if (!r.jev.answers) continue;
      if (r.agree.choice === false || r.agree.noulSide === false || (r.agree.scoreAbsErr ?? 0) >= 1) {
        lines.push(`| ${r.suite} | ${r.id} | ${r.state.replace(/\|/g, "\\|").slice(0, 140)} | ${short(r.keel.answers)} | ${short(r.jev.answers)} |`);
      }
    }
  }
  return lines.join("\n") + "\n";
}
