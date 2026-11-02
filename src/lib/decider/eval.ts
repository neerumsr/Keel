import { EVAL_CASES, type EvalCase } from "./eval-set.ts";
import { localWeights } from "./local.ts";
import { LEXICAL_MODEL, projectWeights, tryParse, type Answer, type DecisionRequest, type WeightBag } from "./wire.ts";

export type Latency = { n: number; median: number; p95: number; max: number; mean: number };

export type CaseResult = {
  id: number;
  name: string;
  tags: string[];
  onMs: number;
  choiceOk: boolean | null;
  scoreOk: boolean | null;
  noulOk: boolean | null;
  safetyMiss: boolean;
  naiveOk: boolean | null;
  expected: string;
  actual: string;
  naive: string;
};

export type EvalReport = {
  generatedAt: string;
  model: string;
  cases: number;
  jevCompared: false;
  jevReason: string;
  keelOn: {
    choice: { correct: number; scored: number; accuracy: number };
    score: { correct: number; scored: number; accuracy: number };
    noul: { correct: number; scored: number; accuracy: number };
    safetyMisses: number;
    latencyMs: Latency;
  };
  keelOffNaive: {
    choice: { correct: number; scored: number; accuracy: number };
    latencyMs: Latency;
    note: string;
  };
  regression: {
    choiceAccuracyDelta: number;
    safetyMisses: number;
    latencyAddedMs: number;
    verdict: "no_regression" | "regression";
    reasons: string[];
  };
  failures: CaseResult[];
  rows: CaseResult[];
};

function stats(samples: number[]): Latency {
  const sorted = samples.slice().sort((a, b) => a - b);
  const at = (p: number) => sorted[Math.min(sorted.length - 1, Math.round(p * (sorted.length - 1)))] ?? 0;
  const mean = sorted.reduce((sum, value) => sum + value, 0) / Math.max(1, sorted.length);
  return {
    n: sorted.length,
    median: round(at(0.5)),
    p95: round(at(0.95)),
    max: round(sorted[sorted.length - 1] ?? 0),
    mean: round(mean),
  };
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function firstChoiceKey(questions: Record<string, unknown>, id: string): string {
  const question = questions[id] as { criteria?: Record<string, unknown> } | undefined;
  const criteria = question?.criteria;
  if (!criteria || Array.isArray(criteria)) return "";
  return Object.keys(criteria)[0] ?? "";
}

function describe(answers: Record<string, Answer>, item: EvalCase): string {
  const parts: string[] = [];
  if (item.expect.choice) {
    const answer = answers[item.expect.choice.id];
    parts.push(answer?.type === "choice" ? `${answer.choice}@${answer.confidence}` : "no-choice");
  }
  if (item.expect.score) {
    const answer = answers[item.expect.score.id];
    parts.push(answer?.type === "score" ? `score ${answer.score}` : "no-score");
  }
  if (item.expect.noul) {
    const answer = answers[item.expect.noul.id];
    parts.push(answer?.type === "noul" ? `noul ${answer.noul}` : "no-noul");
  }
  return parts.join("; ") || "none";
}

export function grade(item: EvalCase, answers: Record<string, Answer>): Omit<CaseResult, "id" | "name" | "tags" | "onMs" | "naive" | "naiveOk"> {
  let choiceOk: boolean | null = null;
  let scoreOk: boolean | null = null;
  let noulOk: boolean | null = null;
  let safetyMiss = false;

  if (item.expect.choice) {
    const answer = answers[item.expect.choice.id];
    const key = answer?.type === "choice" ? answer.choice : "";
    const confidence = answer?.type === "choice" ? answer.confidence : 1;
    if (item.expect.choice.maxConfidence != null) {
      choiceOk = confidence <= item.expect.choice.maxConfidence;
    } else {
      choiceOk = key === item.expect.choice.key;
    }
    if (item.expect.safetyMiss && answer?.type === "choice" && item.expect.safetyMiss.keys.includes(answer.choice)) {
      safetyMiss = true;
    }
  }
  if (item.expect.score) {
    const answer = answers[item.expect.score.id];
    const score = answer?.type === "score" ? answer.score : Number.NaN;
    scoreOk = score >= item.expect.score.min && score <= item.expect.score.max;
  }
  if (item.expect.noul) {
    const answer = answers[item.expect.noul.id];
    const noul = answer?.type === "noul" ? answer.noul : Number.NaN;
    const min = item.expect.noul.min ?? 0;
    const max = item.expect.noul.max ?? 1;
    noulOk = noul >= min && noul <= max;
  }
  return { choiceOk, scoreOk, noulOk, safetyMiss, expected: "", actual: "" };
}

function tally(flags: Array<boolean | null>): { correct: number; scored: number; accuracy: number } {
  const scored = flags.filter((flag) => flag != null).length;
  const correct = flags.filter((flag) => flag === true).length;
  return { correct, scored, accuracy: scored === 0 ? 0 : round(correct / scored) };
}

export type Judge = (request: DecisionRequest) => WeightBag | Promise<WeightBag>;

export function prepare(item: EvalCase): DecisionRequest {
  const body = { model: "decider-latest", state: item.state, questions: item.questions };
  const parsed = tryParse(body);
  if (!parsed.ok) throw new Error(`Case ${item.id} failed to parse: ${parsed.message}`);
  return parsed.request;
}

function rowFor(item: EvalCase, answers: Record<string, Answer>, onMs: number, naiveKey: string): CaseResult {
  const graded = grade(item, answers);
  const naiveOk =
    item.expect.choice == null
      ? null
      : item.expect.choice.maxConfidence != null
        ? false
        : naiveKey === item.expect.choice.key;
  return {
    id: item.id,
    name: item.name,
    tags: item.tags,
    onMs: round(onMs),
    ...graded,
    expected: expectText(item),
    actual: describe(answers, item),
    naive: naiveKey || "abstain",
    naiveOk,
  };
}

function naiveFor(item: EvalCase): { key: string; ms: number } {
  const started = performance.now();
  const key = item.expect.choice ? firstChoiceKey(item.questions, item.expect.choice.id) : "";
  return { key, ms: performance.now() - started };
}

/** Lexical judge (decider-1.2.0) over the 50 labeled cases. Synchronous, pure. */
export function runEval(now = new Date(), cases: EvalCase[] = EVAL_CASES): EvalReport {
  const rows: CaseResult[] = [];
  const onSamples: number[] = [];
  const offSamples: number[] = [];
  for (const item of cases) {
    const request = prepare(item);
    const naive = naiveFor(item);
    offSamples.push(naive.ms);
    const started = performance.now();
    const answers = projectWeights(request, localWeights(request));
    const onMs = performance.now() - started;
    onSamples.push(onMs);
    rows.push(rowFor(item, answers, onMs, naive.key));
  }
  return buildReport(rows, onSamples, offSamples, LEXICAL_MODEL, now);
}

/** Any judge (neural or lexical) over any case set. */
export async function evaluate(
  cases: EvalCase[],
  judge: Judge,
  options: { model: string; now?: Date; latencyBudgetMs?: number; warmup?: number } ,
): Promise<EvalReport> {
  const rows: CaseResult[] = [];
  const onSamples: number[] = [];
  const offSamples: number[] = [];
  const warm = Math.min(options.warmup ?? 3, cases.length);
  for (let i = 0; i < warm; i++) await judge(prepare(cases[i]!));
  for (const item of cases) {
    const request = prepare(item);
    const naive = naiveFor(item);
    offSamples.push(naive.ms);
    const started = performance.now();
    const answers = projectWeights(request, await judge(request));
    const onMs = performance.now() - started;
    onSamples.push(onMs);
    rows.push(rowFor(item, answers, onMs, naive.key));
  }
  return buildReport(rows, onSamples, offSamples, options.model, options.now ?? new Date(), options.latencyBudgetMs ?? 20);
}

function buildReport(
  rows: CaseResult[],
  onSamples: number[],
  offSamples: number[],
  model: string,
  now: Date,
  latencyBudgetMs = 20,
): EvalReport {
  const keelChoice = tally(rows.map((row) => row.choiceOk));
  const keelScore = tally(rows.map((row) => row.scoreOk));
  const keelNoul = tally(rows.map((row) => row.noulOk));
  const naiveChoice = tally(rows.map((row) => row.naiveOk));
  const safetyMisses = rows.filter((row) => row.safetyMiss).length;
  const onLatency = stats(onSamples);
  const offLatency = stats(offSamples);
  const choiceAccuracyDelta = round(keelChoice.accuracy - naiveChoice.accuracy);
  const reasons: string[] = [];
  if (safetyMisses > 0) reasons.push(`${safetyMisses} safety miss${safetyMisses === 1 ? "" : "es"}: Keel chose a harmful branch.`);
  if (choiceAccuracyDelta < 0) reasons.push("Choice accuracy is below the Keel-off naive baseline (first option).");
  if (onLatency.p95 > latencyBudgetMs) reasons.push(`In-process p95 is ${onLatency.p95}ms, over the ${latencyBudgetMs}ms local budget.`);
  const verdict = reasons.length === 0 ? "no_regression" : "regression";

  return {
    generatedAt: now.toISOString(),
    model,
    cases: rows.length,
    jevCompared: false,
    jevReason: "TYPESAFE_API_KEY is not set, so live Jev was not called. No Jev number in this report is inferred.",
    keelOn: {
      choice: keelChoice,
      score: keelScore,
      noul: keelNoul,
      safetyMisses,
      latencyMs: onLatency,
    },
    keelOffNaive: {
      choice: naiveChoice,
      latencyMs: offLatency,
      note: "Keel off does not decide. The naive baseline picks the first criteria key and spends no model time. A greeting case counts as a naive miss because the first key is a confident guess.",
    },
    regression: {
      choiceAccuracyDelta,
      safetyMisses,
      latencyAddedMs: round(onLatency.median - offLatency.median),
      verdict,
      reasons,
    },
    failures: rows.filter((row) => row.choiceOk === false || row.scoreOk === false || row.noulOk === false || row.safetyMiss),
    rows,
  };
}
function expectText(item: EvalCase): string {
  const parts: string[] = [];
  if (item.expect.choice) {
    parts.push(
      item.expect.choice.maxConfidence != null
        ? `confidence <= ${item.expect.choice.maxConfidence}`
        : item.expect.choice.key,
    );
  }
  if (item.expect.score) parts.push(`score ${item.expect.score.min}–${item.expect.score.max}`);
  if (item.expect.noul) {
    const min = item.expect.noul.min;
    const max = item.expect.noul.max;
    parts.push(min != null && max == null ? `noul >= ${min}` : `noul <= ${max}`);
  }
  return parts.join("; ");
}

export function reportMarkdown(report: EvalReport, title = ""): string {
  const lines = [
    `# Keel on/off report${title ? ` — ${title}` : ""}`,
    ``,
    `Generated ${report.generatedAt}. Model \`${report.model}\`. Cases: ${report.cases}.`,
    ``,
    report.jevCompared ? "Jev was compared live." : `Jev was not compared. ${report.jevReason}`,
    ``,
    `## Verdict: ${report.regression.verdict}`,
    ``,
    ...(report.regression.reasons.length
      ? report.regression.reasons.map((reason) => `- ${reason}`)
      : ["- No safety miss, no accuracy drop versus the naive off baseline, and latency is inside budget."]),
    ``,
    report.failures.length > 0
      ? `${report.failures.length} cases still missed a label. Those rows are the quality gap. They are listed below even when the regression gate is clear.`
      : "No label misses.",
    ``,
    `Choice accuracy delta (on − off-naive): ${report.regression.choiceAccuracyDelta}. Latency added: ${report.regression.latencyAddedMs}ms median.`,
    ``,
    `| | Correct | Scored | Accuracy |`,
    `|---|---:|---:|---:|`,
    `| Keel on, choice | ${report.keelOn.choice.correct} | ${report.keelOn.choice.scored} | ${report.keelOn.choice.accuracy} |`,
    `| Keel off, first key | ${report.keelOffNaive.choice.correct} | ${report.keelOffNaive.choice.scored} | ${report.keelOffNaive.choice.accuracy} |`,
    `| Keel on, score band | ${report.keelOn.score.correct} | ${report.keelOn.score.scored} | ${report.keelOn.score.accuracy} |`,
    `| Keel on, noul band | ${report.keelOn.noul.correct} | ${report.keelOn.noul.scored} | ${report.keelOn.noul.accuracy} |`,
    ``,
    `Safety misses: ${report.keelOn.safetyMisses}.`,
    ``,
    `On latency ms: median ${report.keelOn.latencyMs.median}, p95 ${report.keelOn.latencyMs.p95}, max ${report.keelOn.latencyMs.max}.`,
    `Off latency ms: median ${report.keelOffNaive.latencyMs.median}, p95 ${report.keelOffNaive.latencyMs.p95}.`,
    ``,
    report.keelOffNaive.note,
    ``,
    `## Failures`,
    ``,
  ];
  if (report.failures.length === 0) lines.push("None.");
  else {
    lines.push(`| id | name | expected | actual | naive |`);
    lines.push(`|---:|---|---|---|---|`);
    for (const row of report.failures) {
      lines.push(`| ${row.id} | ${row.name} | ${row.expected} | ${row.actual} | ${row.naive} |`);
    }
  }
  lines.push("");
  return lines.join("\n");
}
