/** System One wire — the shape Jev clients already speak. Client-safe. */

/** Keel-3: the neural cross-encoder. Every alias except an explicit pin resolves here. */
export const CONCRETE_MODEL = "decider-3.0.0";
/** Keel-2: the previous neural model, still answering when pinned with model "decider-2.0.0". */
export const PREVIOUS_MODEL = "decider-2.0.0";
/** Keel-1: the lexical system-one. Pin it with model "decider-1.2.0"; also the fallback when no weights are on disk. */
export const LEXICAL_MODEL = "decider-1.2.0";
/** Keel-Pro: the open-weight LLM decider, served by the optional loopback sidecar (serve/keel_pro_server.py). Opt-in pin only. */
export const PRO_MODEL = "decider-pro-1.0.0";

export const MODEL_ALIASES = [
  "decider-latest",
  "decider-3.0.0",
  "decider-pro-1.0.0",
  "decider-2.0.0",
  "decider-1.2.0",
  "decider-1.1.0",
  "decider-1.0.0",
  "decider-preview",
  "jev-latest",
  "jev-1.14.0",
  "jev-1.13.0",
  "jev-preview",
  // Microsoft-Decision-1 names (Foundry model / OpenRouter ids), per artifacts/parity/msd1/api-and-access.md.
  "microsoft-decision-1",
  "Microsoft-Decision-1",
  "microsoft/microsoft-decision-1",
  "microsoft/microsoft-decision-1-20261009",
] as const;

/** decider-1.x names pin the lexical judge; everything else asks for the neural model. */
export function wantsLexical(model: string): boolean {
  return /^decider-1\./.test(model);
}

/** The concrete model an alias answers as: lexical pins, the decider-2.0.0 or decider-pro-1.0.0 pin, or Keel-3. */
export function resolveModel(model: string): string {
  if (wantsLexical(model)) return LEXICAL_MODEL;
  if (model === PREVIOUS_MODEL) return PREVIOUS_MODEL;
  if (model === PRO_MODEL) return PRO_MODEL;
  return CONCRETE_MODEL;
}

const RESERVED = new Set([
  "confidence",
  "probabilities",
  "usage",
  "model",
  "answers",
  "state",
  "questions",
  "error",
  "type",
  "quota",
]);

/** Jev documents no format for question ids or choice labels, so any printable key is accepted. */
const CONTROL_RE = /[\u0000-\u001f\u007f]/;

function isKey(value: string, max: number): boolean {
  return value.length > 0 && value.length <= max && !CONTROL_RE.test(value);
}

/** Jev answers with jev-* aliases use Jev's normalized confidence (docs.typesafe.ai/confidence). */
export function usesJevConfidence(model: string): boolean {
  return /^jev-/.test(model);
}

export const LIMITS = {
  questions: 64,
  /** Total choice options + score levels + noul pairs per call; each is one cross-encoder pass. */
  alternatives: 1024,
  choiceOptions: 255,
  scoreLevels: 10,
  keyChars: 128,
  stateChars: 8000,
  instructionChars: 4000,
  descriptionChars: 1000,
  allowEmptyState: false,
};

export type Limits = { readonly [K in keyof typeof LIMITS]: (typeof LIMITS)[K] };

/**
 * The decider-pro-1.0.0 pin is a long-context LLM sidecar, so it takes the text the Decision Index sends: an empty
 * state (everything in the question) and long states, instructions and option descriptions. Counts stay the same.
 */
export const PRO_LIMITS: Limits = {
  ...LIMITS,
  stateChars: 200_000,
  instructionChars: 100_000,
  descriptionChars: 8_000,
  allowEmptyState: true,
};

export function limitsFor(model: string): Limits {
  return resolveModel(model) === PRO_MODEL ? PRO_LIMITS : LIMITS;
}

export type Json =
  | null
  | string
  | number
  | boolean
  | Json[]
  | { [key: string]: Json };

export type ChoiceAnswer = {
  type: "choice";
  choice: string;
  confidence: number;
  probabilities: Record<string, number>;
};

export type ScoreAnswer = {
  type: "score";
  score: number;
  confidence: number;
  legend: Record<string, Json>;
  probabilities: Record<string, number>;
};

export type NoulAnswer = {
  type: "noul";
  noul: number;
};

export type Answer = ChoiceAnswer | ScoreAnswer | NoulAnswer;

export type SystemOneResponse = {
  model: string;
  answers: Record<string, Answer>;
  usage: { input_tokens: number; output_tokens: number };
};

export type NormalizedQuestion =
  | {
      id: string;
      type: "choice";
      instructions: string;
      options: { key: string; description: string }[];
    }
  | {
      id: string;
      type: "score";
      instructions: string;
      levels: string[];
      /** The raw criteria entries, kept only when a level is structured JSON; echoed in the legend. */
      legend?: Json[];
    }
  | {
      id: string;
      type: "noul";
      instructions: string;
      yes: string;
      no: string;
    };

export type DecisionRequest = {
  model: string;
  state: Json;
  stateText: string;
  questions: NormalizedQuestion[];
};

export type WireError = {
  error: { type: string; message: string; request_id: string };
};

export function requestId(): string {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return `req_${Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")}`;
}

export function renderValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function isJson(value: unknown): value is Json {
  if (value === null) return true;
  const t = typeof value;
  if (t === "string" || t === "number" || t === "boolean") {
    return t !== "number" || Number.isFinite(value as number);
  }
  if (Array.isArray(value)) return value.every(isJson);
  if (t === "object") {
    return Object.values(value as object).every(isJson);
  }
  return false;
}

function bad(message: string): { ok: false; message: string } {
  return { ok: false, message };
}

export function tryParse(
  input: unknown,
): { ok: true; request: DecisionRequest } | { ok: false; message: string } {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return bad("Body must be a JSON object with state and questions.");
  }
  const body = input as Record<string, unknown>;

  let model = "decider-latest";
  if (body.model != null) {
    if (typeof body.model !== "string" || !body.model.trim()) {
      return bad("model must be a string.");
    }
    model = body.model.trim();
    const known = MODEL_ALIASES.some((alias) => alias === model);
    if (!known) {
      return bad(
        `Unknown model "${model}". Use ${MODEL_ALIASES.join(", ")}. Aliases answer as ${CONCRETE_MODEL} (or ${PREVIOUS_MODEL} / ${PRO_MODEL} / ${LEXICAL_MODEL} when pinned).`,
      );
    }
  }

  const limits = limitsFor(model);
  if (!("state" in body)) return bad("state is required.");
  const state = coerceState(body.state);
  if (!isJson(state)) return bad("state must be JSON: a string, object, or array.");
  const stateText = typeof state === "string" ? state : JSON.stringify(state);
  if (!stateText.trim() && !limits.allowEmptyState) return bad("state is empty.");
  if (stateText.length > limits.stateChars) {
    return bad(`state is ${stateText.length} characters. The limit is ${limits.stateChars}.`);
  }

  if (!body.questions || typeof body.questions !== "object" || Array.isArray(body.questions)) {
    return bad("questions must be an object keyed by question id.");
  }
  const entries = Object.entries(body.questions as Record<string, unknown>);
  if (entries.length === 0) return bad("Ask at least one question.");
  if (entries.length > LIMITS.questions) {
    return bad(`At most ${LIMITS.questions} questions per call.`);
  }

  const questions: NormalizedQuestion[] = [];
  let alternatives = 0;
  for (const [id, raw] of entries) {
    if (!isKey(id, LIMITS.keyChars) || RESERVED.has(id)) {
      return bad(
        `Question id "${id}" must be 1–${LIMITS.keyChars} characters without control characters, and not a reserved word (${[...RESERVED].join(", ")}).`,
      );
    }
    const parsed = parseQuestion(id, raw, limits);
    if (!parsed.ok) return parsed;
    const question = parsed.question;
    alternatives +=
      question.type === "choice" ? question.options.length : question.type === "score" ? question.levels.length : 2;
    if (alternatives > LIMITS.alternatives) {
      return bad(
        `This call asks for more than ${LIMITS.alternatives} alternatives in total (choice options + score levels + 2 per noul). Split it into smaller calls.`,
      );
    }
    questions.push(question);
  }

  return { ok: true, request: { model, state, stateText, questions } };
}

function coerceState(value: unknown): unknown {
  if (typeof value !== "string") return value;
  const trimmed = value.trim();
  if (
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      return JSON.parse(trimmed) as unknown;
    } catch {
      return value;
    }
  }
  return value;
}

function parseQuestion(
  id: string,
  raw: unknown,
  limits: Limits,
): { ok: true; question: NormalizedQuestion } | { ok: false; message: string } {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return bad(`Question "${id}" must be an object.`);
  }
  const q = raw as Record<string, unknown>;
  const type = q.type;
  if (type !== "choice" && type !== "score" && type !== "noul") {
    return bad(`Question "${id}" type must be choice, score, or noul.`);
  }
  const instructions = renderValue(q.instructions).trim();
  if (instructions.length > limits.instructionChars) {
    return bad(`Question "${id}" instructions are too long.`);
  }

  if (type === "noul") {
    const criteria = q.criteria;
    let yes = "";
    let no = "";
    if (criteria != null) {
      if (!criteria || typeof criteria !== "object" || Array.isArray(criteria)) {
        return bad(`Noul "${id}" criteria must be { "true": "...", "false": "..." }.`);
      }
      const c = criteria as Record<string, unknown>;
      yes = renderValue(c.true).trim().slice(0, limits.descriptionChars);
      no = renderValue(c.false).trim().slice(0, limits.descriptionChars);
    }
    if (!instructions && !yes && !no) {
      return bad(`Noul "${id}" needs instructions or criteria.`);
    }
    return { ok: true, question: { id, type, instructions, yes, no } };
  }

  if (type === "score") {
    const levels = readLevels(id, q.criteria, limits);
    if (!levels.ok) return levels;
    const question: NormalizedQuestion = { id, type, instructions, levels: levels.levels };
    if (levels.legend) question.legend = levels.legend;
    return { ok: true, question };
  }

  const options = readOptions(id, q, limits);
  if (!options.ok) return options;
  return { ok: true, question: { id, type, instructions, options: options.options } };
}

function readLevels(
  id: string,
  criteria: unknown,
  limits: Limits,
): { ok: true; levels: string[]; legend?: Json[] } | { ok: false; message: string } {
  let list: unknown[] = [];
  if (Array.isArray(criteria)) list = criteria;
  else if (criteria && typeof criteria === "object") {
    list = Object.keys(criteria)
      .sort((a, b) => Number(a) - Number(b))
      .map((key) => (criteria as Record<string, unknown>)[key]);
  } else {
    return bad(`Score "${id}" criteria must be an ordered list of 1–${LIMITS.scoreLevels} levels.`);
  }
  // Level i is always index i, as in Jev; blank levels keep their slot.
  const levels = list.map((item) => renderValue(item).trim());
  if (levels.length < 1 || levels.length > LIMITS.scoreLevels) {
    return bad(`Score "${id}" needs 1–${LIMITS.scoreLevels} levels.`);
  }
  if (levels.every((level) => !level)) {
    return bad(`Score "${id}" levels are all empty.`);
  }
  if (levels.some((level) => level.length > limits.descriptionChars)) {
    return bad(`Score "${id}" has a level that is too long.`);
  }
  const structured = list.some((item) => item !== null && typeof item === "object");
  return structured ? { ok: true, levels, legend: list.map((item) => (item ?? "") as Json) } : { ok: true, levels };
}

function readOptions(
  id: string,
  q: Record<string, unknown>,
  limits: Limits,
):
  | { ok: true; options: { key: string; description: string }[] }
  | { ok: false; message: string } {
  if (Array.isArray(q.options)) {
    const options = q.options.map((item) => {
      const description = renderValue(item).trim();
      const key = slug(description);
      return { key, description };
    });
    return checkOptions(id, options, limits);
  }
  const criteria = q.criteria;
  if (!criteria || typeof criteria !== "object" || Array.isArray(criteria)) {
    return bad(`Choice "${id}" needs criteria: { label: "what this option means" }.`);
  }
  const options = Object.entries(criteria as Record<string, unknown>).map(([key, value]) => ({
    key,
    description: value == null ? "" : renderValue(value).trim(),
  }));
  return checkOptions(id, options, limits);
}

function checkOptions(
  id: string,
  options: { key: string; description: string }[],
  limits: Limits,
):
  | { ok: true; options: { key: string; description: string }[] }
  | { ok: false; message: string } {
  if (options.length < 1 || options.length > LIMITS.choiceOptions) {
    return bad(`Choice "${id}" needs 1–${LIMITS.choiceOptions} options.`);
  }
  const seen = new Set<string>();
  for (const option of options) {
    if (!isKey(option.key, LIMITS.keyChars)) {
      return bad(`Choice "${id}" option "${option.key}" must be 1–${LIMITS.keyChars} characters without control characters.`);
    }
    if (seen.has(option.key)) return bad(`Choice "${id}" repeats option "${option.key}".`);
    seen.add(option.key);
    if (option.description.length > limits.descriptionChars) {
      return bad(`Choice "${id}" option "${option.key}" description is too long.`);
    }
  }
  return { ok: true, options };
}

function slug(text: string): string {
  const base = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 40);
  return base || "option";
}

export function distribute(weights: number[]): number[] {
  const n = weights.length;
  if (n === 0) return [];
  const safe = weights.map((w) => (Number.isFinite(w) && w > 0 ? w : 0));
  const sum = safe.reduce((a, b) => a + b, 0);
  const raw = sum <= 0 ? safe.map(() => 1 / n) : safe.map((w) => w / sum);
  const rounded = raw.map((p) => Math.round(p * 10000) / 10000);
  const drift = Math.round((1 - rounded.reduce((a, b) => a + b, 0)) * 10000) / 10000;
  let idx = 0;
  for (let i = 1; i < rounded.length; i++) {
    if (rounded[i] > rounded[idx]) idx = i;
  }
  rounded[idx] = Math.round((rounded[idx] + drift) * 10000) / 10000;
  if (rounded[idx] < 0) rounded[idx] = 0;
  return rounded;
}

/** Share of the mass on the winning option. Keel's decider-* confidence; Jev normalizes instead (see below). */
export function confidenceFrom(probs: number[]): number {
  if (probs.length === 0) return 0;
  const top = Math.max(...probs);
  return Math.round(Math.min(1, Math.max(0, top)) * 1000) / 1000;
}

function round3(x: number): number {
  return Math.round(Math.min(1, Math.max(0, x)) * 1000) / 1000;
}

/** Jev choice confidence: (p_max − 1/n) / (1 − 1/n). 0 on a uniform split. https://docs.typesafe.ai/confidence */
export function jevChoiceConfidence(probs: number[]): number {
  const n = probs.length;
  if (n === 0) return 0;
  if (n === 1) return 1;
  return round3((Math.max(...probs) - 1 / n) / (1 - 1 / n));
}

/**
 * Jev score confidence: 1 − (mean |i − mode| under p) / (that spread under a uniform p), floored at 0.
 * https://docs.typesafe.ai/confidence
 */
export function jevScoreConfidence(probs: number[]): number {
  const n = probs.length;
  if (n === 0) return 0;
  if (n === 1) return 1;
  const mode = argmax(probs);
  const spread = probs.reduce((sum, p, i) => sum + p * Math.abs(i - mode), 0);
  const centre = (n - 1) / 2;
  let uniform = 0;
  for (let i = 0; i < n; i++) uniform += Math.abs(i - centre);
  uniform /= n;
  return round3(1 - spread / uniform);
}

export function argmax(probs: number[]): number {
  let best = 0;
  for (let i = 1; i < probs.length; i++) {
    if (probs[i] > probs[best]) best = i;
  }
  return best;
}

export type WeightBag = Record<string, Record<string, number>>;

export function projectWeights(
  request: DecisionRequest,
  weights: WeightBag,
): Record<string, Answer> {
  const answers: Record<string, Answer> = {};
  for (const question of request.questions) {
    const bag = weights[question.id] ?? {};
    if (question.type === "noul") {
      const yes = Number(bag.yes);
      const noul = Number.isFinite(yes) ? Math.min(100, Math.max(0, yes)) / 100 : 0.5;
      answers[question.id] = { type: "noul", noul: Math.round(noul * 10000) / 10000 };
      continue;
    }
    if (question.type === "choice") {
      const keys = question.options.map((option) => option.key);
      const probs = distribute(keys.map((key) => Number(bag[key])));
      const winner = keys[argmax(probs)] ?? keys[0];
      const probabilities: Record<string, number> = {};
      keys.forEach((key, i) => {
        probabilities[key] = probs[i] ?? 0;
      });
      answers[question.id] = {
        type: "choice",
        choice: winner,
        confidence: usesJevConfidence(request.model) ? jevChoiceConfidence(probs) : confidenceFrom(probs),
        probabilities,
      };
      continue;
    }
    const probs = distribute(question.levels.map((_, i) => Number(bag[String(i)])));
    let expected = 0;
    const probabilities: Record<string, number> = {};
    const legend: Record<string, Json> = {};
    question.levels.forEach((level, i) => {
      const p = probs[i] ?? 0;
      expected += i * p;
      probabilities[String(i)] = p;
      legend[String(i)] = question.legend?.[i] ?? level;
    });
    answers[question.id] = {
      type: "score",
      score: Math.round(expected * 100) / 100,
      confidence: usesJevConfidence(request.model) ? jevScoreConfidence(probs) : confidenceFrom(probs),
      legend,
      probabilities,
    };
  }
  return answers;
}

export function jsonSchemaFor(request: DecisionRequest): Record<string, unknown> {
  const properties: Record<string, unknown> = {};
  const required: string[] = [];
  for (const question of request.questions) {
    required.push(question.id);
    if (question.type === "noul") {
      properties[question.id] = {
        type: "object",
        additionalProperties: false,
        required: ["yes"],
        properties: { yes: { type: "integer", minimum: 0, maximum: 100 } },
      };
    } else if (question.type === "choice") {
      const optionProps: Record<string, unknown> = {};
      const optionRequired: string[] = [];
      for (const option of question.options) {
        optionRequired.push(option.key);
        optionProps[option.key] = { type: "integer", minimum: 0, maximum: 100 };
      }
      properties[question.id] = {
        type: "object",
        additionalProperties: false,
        required: optionRequired,
        properties: optionProps,
      };
    } else {
      const levelProps: Record<string, unknown> = {};
      const levelRequired: string[] = [];
      question.levels.forEach((_, i) => {
        levelRequired.push(String(i));
        levelProps[String(i)] = { type: "integer", minimum: 0, maximum: 100 };
      });
      properties[question.id] = {
        type: "object",
        additionalProperties: false,
        required: levelRequired,
        properties: levelProps,
      };
    }
  }
  return {
    type: "object",
    additionalProperties: false,
    required: ["weights"],
    properties: {
      weights: {
        type: "object",
        additionalProperties: false,
        required,
        properties,
      },
    },
  };
}

export function promptFor(request: DecisionRequest): string {
  const lines: string[] = [
    "STATE (the only evidence — do not invent facts beyond it):",
    request.stateText,
    "",
    "QUESTIONS (judge each one independently; do not let one answer change another):",
  ];
  for (const question of request.questions) {
    lines.push("");
    lines.push(`## ${question.id} (${question.type})`);
    lines.push(question.instructions);
    if (question.type === "choice") {
      lines.push("Put an integer weight 0–100 on every option. Split weight when the state is ambiguous.");
      for (const option of question.options) {
        lines.push(`- ${option.key}: ${option.description || "(no extra description)"}`);
      }
    } else if (question.type === "score") {
      lines.push(
        "These levels are ordered from 0 upward. Put integer weights 0–100 on every level. If the state sits between two levels, split weight across those neighbors — do not collapse to a single level unless it clearly fits.",
      );
      question.levels.forEach((level, i) => {
        lines.push(`- ${i}: ${level}`);
      });
    } else {
      lines.push(
        'Weight "yes" from 0 to 100: your probability that the instructions are true, as a percent. 50 means you cannot tell.',
      );
      if (question.yes) lines.push(`True means: ${question.yes}`);
      if (question.no) lines.push(`False means: ${question.no}`);
    }
  }
  return lines.join("\n");
}

export const SYSTEM_PROMPT = [
  "You are Decider, a calibrated decision model. You do not write prose, advice, or explanations.",
  "You assign probability weights. A tie is equal weight. 0 and 100 are for cases the state makes unambiguous.",
  "Backtick paths such as `customer.plan` refer to fields inside STATE.",
  "Never add options. Never drop an option. Never use outside knowledge to override the state.",
  "Return only the JSON object of weights.",
].join(" ");

export type GuardSettings = {
  noul: number;
  confidence: number;
};

export function branchSnippet(
  request: DecisionRequest,
  answers: Record<string, Answer>,
  guards: GuardSettings,
): { typescript: string; elixir: string } {
  const lines: string[] = [
    "const reply = await keel.ask(state);",
    "",
  ];
  const elixir: string[] = [];
  for (const question of request.questions) {
    const answer = answers[question.id];
    if (!answer) continue;
    if (answer.type === "noul") {
      lines.push(
        `if (reply.${question.id} > ${guards.noul.toFixed(2)}) return ${JSON.stringify([question.id])};`,
      );
      elixir.push(
        `def handle_answer(%{${question.id}: p}, from, s) when p > ${guards.noul.toFixed(2)}, do: done(from, [:${question.id}], s)`,
      );
    }
  }
  const choice = request.questions.find((q) => q.type === "choice");
  const score = request.questions.find((q) => q.type === "score");
  if (choice) {
    const scoreAnswer = score ? answers[score.id] : undefined;
    const mid =
      scoreAnswer && scoreAnswer.type === "score"
        ? Math.max(0, Math.round((scoreAnswer.score - 0.4) * 10) / 10)
        : 0;
    const scoreClause = score ? ` && reply.${score.id} >= ${mid.toFixed(1)}` : "";
    lines.push(
      `if (reply.${choice.id} && reply.confidence.${choice.id} >= ${guards.confidence.toFixed(2)}${scoreClause}) {`,
      `  return [reply.${choice.id}${score ? ', "priority:high"' : ""}];`,
      "}",
      `return [reply.${choice.id}, "needs-review"];`,
    );
    elixir.push(
      `def handle_answer(%{${choice.id}: k, confidence: %{${choice.id}: c}}${score ? `, ${score.id}: sev` : ""}, from, s)`,
      `    when c >= ${guards.confidence.toFixed(2)}${score ? ` and sev >= ${mid}` : ""},`,
      `    do: done(from, [k${score ? ', :"priority:high"' : ""}], s)`,
      `def handle_answer(%{${choice.id}: k}, from, s), do: done(from, [k, :"needs-review"], s)`,
    );
  }
  return { typescript: lines.join("\n"), elixir: elixir.join("\n") };
}
