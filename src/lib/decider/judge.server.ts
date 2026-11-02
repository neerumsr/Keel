import { localWeights } from "./local";
import {
  CONCRETE_MODEL,
  LEXICAL_MODEL,
  PREVIOUS_MODEL,
  PRO_MODEL,
  resolveModel,
  wantsLexical,
  type WeightBag,
  projectWeights,
  requestId,
  tryParse,
  type SystemOneResponse,
  type WireError,
} from "./wire";

export type ExecuteResult =
  | { ok: true; status: 200; latency_ms: number; body: SystemOneResponse }
  | { ok: false; status: number; body: WireError };

const hits: number[] = [];
const WINDOW_MS = 60_000;

/** Decisions per minute; KEEL_RATE_PER_MINUTE overrides the default 120 (0 turns the limit off, e.g. for benchmark runs). */
export function ratePerMinute(env: Record<string, string | undefined> = process.env): number {
  const raw = env.KEEL_RATE_PER_MINUTE;
  if (raw === undefined || raw.trim() === "") return 120;
  const n = Number(raw);
  return Number.isInteger(n) && n >= 0 ? n : 120;
}

function takeSlot(): boolean {
  const max = ratePerMinute();
  if (max === 0) return true;
  const now = Date.now();
  while (hits.length > 0 && hits[0]! < now - WINDOW_MS) hits.shift();
  if (hits.length >= max) return false;
  hits.push(now);
  return true;
}

function fail(status: number, type: string, message: string): ExecuteResult {
  return { ok: false, status, body: { error: { type, message, request_id: requestId() } } };
}

export async function execute(input: unknown): Promise<ExecuteResult> {
  const parsed = tryParse(input);
  if (!parsed.ok) return fail(400, "invalid_request", parsed.message);

  const { readEnabled } = await import("./switch.server");
  if (!(await readEnabled())) {
    return fail(409, "disabled", "Keel is off. No model call was made.");
  }
  if (!takeSlot()) {
    return fail(429, "rate_limited", "Too many decisions this minute. Try again shortly.");
  }

  const started = performance.now();
  let weights: WeightBag | null = null;
  let model = LEXICAL_MODEL;
  if (resolveModel(parsed.request.model) === PRO_MODEL) {
    // An explicit Keel-Pro pin never falls back silently: the answer would carry another model's numbers.
    const { proWeights } = await import("./pro.server");
    weights = await proWeights(parsed.request);
    if (!weights) {
      return fail(503, "model_unavailable", `${PRO_MODEL} needs the Keel-Pro sidecar (serve/keel_pro_server.py, see artifacts/parity/pro/SERVE.md). No decision was made.`);
    }
    model = PRO_MODEL;
  } else if (!wantsLexical(parsed.request.model) && process.env.KEEL_ENGINE !== "lexical") {
    const { neuralWeights, loadModel, previousModelDir } = await import("./neural.server");
    // A decider-2.0.0 pin answers from models/keel-2 when it is on disk; otherwise the default model answers.
    const dir = resolveModel(parsed.request.model) === PREVIOUS_MODEL ? (previousModelDir() ?? undefined) : undefined;
    weights = await neuralWeights(parsed.request, dir).catch(() => null);
    if (weights) model = (await loadModel(dir))?.config.id ?? CONCRETE_MODEL;
  }
  const answers = projectWeights(parsed.request, weights ?? localWeights(parsed.request));
  return {
    ok: true,
    status: 200,
    latency_ms: Math.round((performance.now() - started) * 100) / 100,
    body: {
      model,
      answers,
      usage: { input_tokens: 0, output_tokens: 0 },
    },
  };
}
