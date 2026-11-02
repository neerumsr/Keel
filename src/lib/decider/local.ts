import type { DecisionRequest, NormalizedQuestion, WeightBag } from "./wire";

/**
 * In-process System One judge. No network call.
 * Each option is a dot product of what the state activates and what the option
 * text is about, plus direct word overlap. Weights are unnormalized; the wire
 * layer turns them into probabilities.
 */

type Token = { stem: string; negated: boolean };

const NEGATIONS = new Set([
  "not",
  "no",
  "never",
  "without",
  "none",
  "dont",
  "doesnt",
  "isnt",
  "wont",
  "cant",
]);

const RAW_FEATURES: Record<string, string[]> = {
  money: ["charge", "billing", "invoice", "refund", "payment", "paid", "subscription", "seat", "money", "price", "fee", "duplicate", "billed"],
  defect: ["broken", "error", "crash", "blank", "white", "fail", "exception", "bug", "timeout", "outage", "down", "failing"],
  access: ["login", "password", "reset", "permission", "locked", "account", "session", "signin"],
  security: ["script", "inject", "injection", "xss", "token", "secret", "vulnerability", "untrusted", "markup", "payload", "sanitize", "credential", "unauthorized", "leaked", "auth", "middleware", "security"],
  unsafe: ["trust", "trusted", "trusts", "supplied", "bypass", "rewrite"],
  integration: ["stripe", "connect", "webhook", "integration", "api"],
  leave: ["cancel", "churn", "leave", "losing", "friday"],
  blocked: ["cannot", "unable", "blocked", "timeout", "failing"],
  mild: ["typo", "spelling", "readme", "cosmetic", "heading", "docs", "documentation"],
  anger: ["furious", "angry", "losing", "threatening"],
  extreme: ["secret", "exposure", "rce", "leak", "leaked"],
};

const FEATURES: Record<string, Set<string>> = Object.fromEntries(
  Object.entries(RAW_FEATURES).map(([name, words]) => [name, new Set(words.map(stem))]),
);

function stem(word: string): string {
  let value = word;
  if (value.length > 5 && value.endsWith("ing")) value = value.slice(0, -3);
  else if (value.length > 4 && value.endsWith("ed")) value = value.slice(0, -2);
  else if (value.length > 4 && value.endsWith("es")) value = value.slice(0, -2);
  else if (value.length > 3 && value.endsWith("s") && !value.endsWith("ss")) value = value.slice(0, -1);
  return value;
}

export function tokenize(text: string): Token[] {
  const raw = text
    .toLowerCase()
    .replace(/'/g, "")
    .split(/[^a-z0-9]+/)
    .filter((part) => part.length > 1);
  const stems = raw.map(stem);
  return stems.map((value, index) => {
    let negated = false;
    for (let i = Math.max(0, index - 3); i < index; i++) {
      if (NEGATIONS.has(stems[i] ?? "")) negated = true;
    }
    return { stem: value, negated };
  });
}

function activation(tokens: Token[]): Map<string, number> {
  const counts = new Map<string, number>();
  const seen = new Set<string>();
  for (const token of tokens) {
    if (token.negated || seen.has(token.stem)) continue;
    seen.add(token.stem);
    for (const [name, terms] of Object.entries(FEATURES)) {
      if (!terms.has(token.stem)) continue;
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
  }
  if (tokens.some((token, i) => token.stem === "time" && tokens[i + 1]?.stem === "out" && !token.negated)) {
    counts.set("defect", (counts.get("defect") ?? 0) + 1);
    counts.set("blocked", (counts.get("blocked") ?? 0) + 1);
  }
  const act = new Map<string, number>();
  for (const [name, count] of counts) act.set(name, Math.min(1, count / 2));
  return act;
}

function affinity(tokens: Token[], feature: string): number {
  const terms = FEATURES[feature];
  if (!terms) return 0;
  let hits = 0;
  const seen = new Set<string>();
  for (const token of tokens) {
    if (token.negated || seen.has(token.stem) || !terms.has(token.stem)) continue;
    seen.add(token.stem);
    hits++;
  }
  return hits === 0 ? 0 : Math.min(1, hits / 2);
}

function lexical(state: Token[], option: Token[]): number {
  const wanted = new Set(option.filter((token) => !token.negated && token.stem.length > 2).map((token) => token.stem));
  if (wanted.size === 0) return 0;
  let hits = 0;
  const seen = new Set<string>();
  for (const token of state) {
    if (token.negated || seen.has(token.stem) || !wanted.has(token.stem)) continue;
    seen.add(token.stem);
    hits++;
  }
  return Math.min(1, hits / Math.min(4, wanted.size));
}

function dot(act: Map<string, number>, text: Token[]): number {
  let sum = 0;
  for (const [name, value] of act) sum += value * affinity(text, name);
  return sum;
}

function negatedOverlap(state: Token[], text: Token[]): number {
  const wanted = new Set(text.map((token) => token.stem));
  let hits = 0;
  const seen = new Set<string>();
  for (const token of state) {
    if (!token.negated || seen.has(token.stem) || !wanted.has(token.stem)) continue;
    seen.add(token.stem);
    hits++;
  }
  return Math.min(1, hits);
}

function softmaxWeights(scores: number[]): number[] {
  const max = Math.max(...scores);
  const min = Math.min(...scores);
  if (max < 0.12 || max - min < 0.06) return scores.map(() => 1);
  const temp = 0.42;
  return scores.map((score) => Math.exp((score - max) / temp) * 100);
}

function choiceWeights(question: Extract<NormalizedQuestion, { type: "choice" }>, state: Token[], act: Map<string, number>, stateText: string): Record<string, number> {
  const concrete = /\/[\w.-]+\.[a-z]{1,4}/i.test(stateText) && /\b(add|fix|update|remove|change)\b/i.test(stateText);
  const danger = Math.max(act.get("unsafe") ?? 0, act.get("extreme") ?? 0);
  const destructive = /\b(delete|drop|wipe)\b/i.test(stateText) && /\b(production|database|tables)\b/i.test(stateText);
  const scores = question.options.map((option) => {
    const text = tokenize(`${option.key} ${option.description}`);
    let score = dot(act, text) * 1.15 + lexical(state, text) * 1.35;
    if (concrete && (option.key === "edit" || /\b(implement|specified)\b/.test(`${option.key} ${option.description}`))) {
      score += 0.85;
    }
    if (/\b(where|which)\b/i.test(stateText) && /missing|ask/.test(`${option.key} ${option.description}`)) score += 0.45;
    if ((danger >= 0.5 || destructive) && option.key === "stop") score += 1.15;
    if ((danger >= 0.5 || destructive) && option.key === "edit") score -= 1.05;
    return score;
  });
  const weights = softmaxWeights(scores);
  const bag: Record<string, number> = {};
  question.options.forEach((option, i) => {
    bag[option.key] = Math.round(weights[i] ?? 1);
  });
  return bag;
}

function scoreWeights(question: Extract<NormalizedQuestion, { type: "score" }>, state: Token[], act: Map<string, number>): Record<string, number> {
  const n = question.levels.length;
  const extreme = act.get("extreme") ?? 0;
  const high = Math.max(act.get("leave") ?? 0, act.get("security") ?? 0, act.get("unsafe") ?? 0);
  const mid = Math.max(act.get("blocked") ?? 0, act.get("defect") ?? 0, act.get("anger") ?? 0);
  const low = act.get("mild") ?? 0;
  const mass = extreme + high + mid + low;
  const S = mass === 0 ? 0.35 : (extreme * 1 + high * 0.74 + mid * 0.48 + low * 0.05) / mass;
  const scores = question.levels.map((level, i) => {
    const t = n === 1 ? 0 : i / (n - 1);
    const bump = Math.exp(-((t - S) ** 2) / (2 * 0.2 ** 2));
    const text = tokenize(level);
    return bump * 0.55 + dot(act, text) * 1.25 + lexical(state, text);
  });
  const weights = softmaxWeights(scores);
  const bag: Record<string, number> = {};
  question.levels.forEach((_, i) => {
    bag[String(i)] = Math.round(weights[i] ?? 1);
  });
  return bag;
}

function noulWeight(question: Extract<NormalizedQuestion, { type: "noul" }>, state: Token[], act: Map<string, number>): number {
  const yesText = tokenize(`${question.instructions} ${question.yes}`);
  const noText = tokenize(question.no);
  const yes = dot(act, yesText) + lexical(state, yesText);
  const denial = negatedOverlap(state, yesText);
  let no = lexical(state, noText) + denial * 1.35;
  const asksSecurity = /vulnerab|injection|secret|unauthorized|trust/.test(
    `${question.instructions} ${question.yes}`,
  );
  const hot = Math.max(act.get("security") ?? 0, act.get("unsafe") ?? 0, act.get("extreme") ?? 0);
  if (asksSecurity && hot === 0) no += 1.1;
  if (yes + no < 0.18) return 50;
  const p = 1 / (1 + Math.exp(-(yes - no) / 0.38));
  return Math.round(Math.min(1, Math.max(0, p)) * 100);
}

export function localWeights(request: DecisionRequest): WeightBag {
  const state = tokenize(request.stateText);
  const act = activation(state);
  const bag: WeightBag = {};
  for (const question of request.questions) {
    if (question.type === "choice") bag[question.id] = choiceWeights(question, state, act, request.stateText);
    else if (question.type === "score") bag[question.id] = scoreWeights(question, state, act);
    else bag[question.id] = { yes: noulWeight(question, state, act) };
  }
  return bag;
}
