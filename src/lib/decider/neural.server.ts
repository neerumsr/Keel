/**
 * Keel neural judge. In-process ONNX cross-encoder; no network, ever.
 * Loads models/keel-3 (Keel-3, default), models/keel-2 (pinned decider-2.0.0, and
 * the default when keel-3 is absent) or models/keel-base (zero-shot) from disk.
 * The lexical judge in local.ts is fused in as a prior and is the fallback
 * when no model directory is present.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { hypotheses } from "./hypothesis.ts";
import { localWeights } from "./local.ts";
import { distribute, type DecisionRequest, type WeightBag } from "./wire.ts";

export type KeelConfig = {
  id: string;
  base: string;
  hypothesisVersion: number;
  maxLength: number;
  threads: number;
  onnx: string;
  temperature: { choice: number; score: number; noul: number };
  /** Blend toward uniform when no hypothesis is entailed (max sigmoid below threshold). */
  abstain: { threshold: number; floor: number };
  /** Weight of the lexical judge's log-probabilities added to neural logits. */
  lexicalBlend: { choice: number; score: number; noul: number };
  /** Share of each score level's mass spread to its neighbors (ordinal smoothing). */
  scoreSmoothing: number;
  noulBias: number;
  trainedOn?: string;
};

const DEFAULTS: KeelConfig = {
  id: "decider-3.0.0",
  base: "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33",
  hypothesisVersion: 1,
  maxLength: 256,
  threads: 4,
  onnx: "onnx/model_quantized.onnx",
  temperature: { choice: 1, score: 1, noul: 1 },
  abstain: { threshold: 0.35, floor: 0 },
  lexicalBlend: { choice: 0, score: 0, noul: 0 },
  scoreSmoothing: 0,
  noulBias: 0,
};

type Tokenizer = (
  text: string[],
  options: { text_pair: string[]; padding: boolean; truncation: boolean; max_length: number; return_tensor: false },
) => { input_ids: number[][]; attention_mask: number[][]; token_type_ids?: number[][] };

type OrtTensor = { data: Float32Array | ArrayLike<number>; dims: readonly number[] };
type Session = { inputNames: readonly string[]; run(feeds: Record<string, unknown>): Promise<Record<string, OrtTensor>> };
type TensorCtor = new (type: "int64", data: BigInt64Array, dims: number[]) => unknown;

type Loaded = { dir: string; config: KeelConfig; tokenizer: Tokenizer; session: Session; Tensor: TensorCtor };

let loading: Promise<Loaded | null> | null = null;
let loadError: string | null = null;

// A dir counts only with its weights: models/keel-3/onnx is not in git, so a fresh clone falls back to keel-2.
const hasModel = (dir: string) =>
  existsSync(path.join(dir, "tokenizer.json")) &&
  existsSync(path.join(dir, "config.json")) &&
  existsSync(path.join(dir, readConfig(dir).onnx));

export function modelDir(): string | null {
  const candidates = [
    process.env.KEEL_MODEL_DIR,
    path.resolve(process.cwd(), "models", "keel-3"),
    path.resolve(process.cwd(), "models", "keel-2"),
    path.resolve(process.cwd(), "models", "keel-base"),
  ].filter((value): value is string => Boolean(value));
  for (const dir of candidates) {
    if (hasModel(dir)) return dir;
  }
  return null;
}

/** Directory of the pinned Keel-2 weights (model "decider-2.0.0"), or null when not on disk. */
export function previousModelDir(): string | null {
  const dir = process.env.KEEL2_MODEL_DIR ?? path.resolve(process.cwd(), "models", "keel-2");
  return hasModel(dir) ? dir : null;
}

export function readConfig(dir: string): KeelConfig {
  const file = path.join(dir, "keel.json");
  if (!existsSync(file)) return { ...DEFAULTS };
  const raw = JSON.parse(readFileSync(file, "utf8")) as Partial<KeelConfig>;
  return {
    ...DEFAULTS,
    ...raw,
    temperature: { ...DEFAULTS.temperature, ...raw.temperature },
    abstain: { ...DEFAULTS.abstain, ...raw.abstain },
    lexicalBlend: { ...DEFAULTS.lexicalBlend, ...raw.lexicalBlend },
  };
}

async function load(dirOverride?: string): Promise<Loaded | null> {
  const dir = dirOverride ?? modelDir();
  if (!dir) {
    loadError = "No model directory. Run `npm run model:fetch` or train one (training/README.md).";
    return null;
  }
  try {
    const config = readConfig(dir);
    const transformers = await import("@huggingface/transformers");
    transformers.env.allowRemoteModels = false;
    transformers.env.allowLocalModels = true;
    transformers.env.localModelPath = path.dirname(dir) + path.sep;
    const tokenizer = (await transformers.AutoTokenizer.from_pretrained(path.basename(dir))) as unknown as Tokenizer;
    const ort = await import("onnxruntime-node");
    const session = (await ort.InferenceSession.create(path.join(dir, config.onnx), {
      intraOpNumThreads: config.threads,
      interOpNumThreads: 1,
      executionMode: "sequential",
      graphOptimizationLevel: "all",
    })) as unknown as Session;
    loadError = null;
    return { dir, config, tokenizer, session, Tensor: ort.Tensor as unknown as TensorCtor };
  } catch (error) {
    loadError = error instanceof Error ? error.message : String(error);
    return null;
  }
}

const byDir = new Map<string, Promise<Loaded | null>>();

export function loadModel(dirOverride?: string): Promise<Loaded | null> {
  if (dirOverride) {
    let pending = byDir.get(dirOverride);
    if (!pending) {
      pending = load(dirOverride);
      byDir.set(dirOverride, pending);
    }
    return pending;
  }
  if (!loading) loading = load();
  return loading;
}

export async function neuralStatus(): Promise<{ loaded: boolean; id: string | null; dir: string | null; error: string | null }> {
  const model = await loadModel();
  return { loaded: model != null, id: model?.config.id ?? null, dir: model?.dir ?? null, error: loadError };
}

/** Entailment margin per pair: logit(entailment) - logit(not_entailment). */
async function margins(model: Loaded, premises: string[], hyps: string[]): Promise<number[]> {
  const encoded = model.tokenizer(premises, {
    text_pair: hyps,
    padding: true,
    truncation: true,
    max_length: model.config.maxLength,
    return_tensor: false,
  });
  const rows = encoded.input_ids.length;
  const cols = encoded.input_ids[0]?.length ?? 0;
  const flat = (matrix: number[][] | undefined) => {
    const data = new BigInt64Array(rows * cols);
    if (!matrix) return data;
    for (let r = 0; r < rows; r++) {
      const row = matrix[r]!;
      for (let c = 0; c < cols; c++) data[r * cols + c] = BigInt(row[c] ?? 0);
    }
    return data;
  };
  const sources: Record<string, number[][] | undefined> = {
    input_ids: encoded.input_ids,
    attention_mask: encoded.attention_mask,
    token_type_ids: encoded.token_type_ids,
  };
  const feeds: Record<string, unknown> = {};
  for (const name of model.session.inputNames) {
    feeds[name] = new model.Tensor("int64", flat(sources[name]), [rows, cols]);
  }
  const out = await model.session.run(feeds);
  const logits = out.logits!.data as Float32Array;
  const result: number[] = [];
  for (let r = 0; r < rows; r++) result.push((logits[r * 2] ?? 0) - (logits[r * 2 + 1] ?? 0));
  return result;
}

function softmax(values: number[]): number[] {
  const max = Math.max(...values);
  const exps = values.map((value) => Math.exp(value - max));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map((value) => value / sum);
}

const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));

function lexLogits(bag: Record<string, number> | undefined, keys: string[]): number[] {
  const probs = distribute(keys.map((key) => Number(bag?.[key] ?? 1)));
  return probs.map((p) => Math.log(Math.max(p, 1e-4)));
}

export function groupProbabilities(
  config: KeelConfig,
  type: "choice" | "score",
  raw: number[],
  lexical: number[],
): number[] {
  const temp = config.temperature[type];
  const blend = config.lexicalBlend[type];
  let probs = softmax(raw.map((m, i) => m / temp + blend * (lexical[i] ?? 0)));
  if (type === "score" && config.scoreSmoothing > 0 && probs.length > 2) {
    const a = config.scoreSmoothing;
    probs = probs.map((p, i) => {
      const left = probs[i - 1];
      const right = probs[i + 1];
      const neighbors = (left ?? 0) + (right ?? 0);
      const share = left == null || right == null ? a / 2 : a;
      return p * (1 - share) + (a / 2) * neighbors;
    });
  }
  const top = Math.max(...raw.map(sigmoid));
  if (config.abstain.threshold > 0 && top < config.abstain.threshold) {
    const keep = config.abstain.floor + (1 - config.abstain.floor) * (top / config.abstain.threshold);
    probs = probs.map((p) => keep * p + (1 - keep) / probs.length);
  }
  return probs;
}

export async function neuralWeights(request: DecisionRequest, dirOverride?: string): Promise<WeightBag | null> {
  const model = await loadModel(dirOverride);
  if (!model) return null;
  const premises: string[] = [];
  const hyps: string[] = [];
  const spans: { start: number; end: number }[] = [];
  for (const question of request.questions) {
    const list = hypotheses(question);
    spans.push({ start: hyps.length, end: hyps.length + list.length });
    for (const hyp of list) {
      premises.push(request.stateText);
      hyps.push(hyp);
    }
  }
  const all = await margins(model, premises, hyps);
  const lexical = localWeights(request);
  const bag: WeightBag = {};
  request.questions.forEach((question, qi) => {
    const span = spans[qi]!;
    const raw = all.slice(span.start, span.end);
    if (question.type === "noul") {
      const lex = Number(lexical[question.id]?.yes ?? 50) / 100;
      const lexLogit = Math.log(Math.max(lex, 1e-3) / Math.max(1 - lex, 1e-3));
      const z = (raw[0]! - raw[1]!) / model.config.temperature.noul + model.config.noulBias + model.config.lexicalBlend.noul * lexLogit;
      bag[question.id] = { yes: sigmoid(z) * 100 };
      return;
    }
    const keys = question.type === "choice" ? question.options.map((o) => o.key) : question.levels.map((_, i) => String(i));
    const probs = groupProbabilities(model.config, question.type, raw, lexLogits(lexical[question.id], keys));
    const weights: Record<string, number> = {};
    keys.forEach((key, i) => {
      weights[key] = (probs[i] ?? 0) * 1_000_000;
    });
    bag[question.id] = weights;
  });
  return bag;
}

/** Raw margins, for calibration scripts. */
export async function rawMargins(request: DecisionRequest, dirOverride?: string): Promise<{ id: string; margins: number[] }[] | null> {
  const model = await loadModel(dirOverride);
  if (!model) return null;
  const out: { id: string; margins: number[] }[] = [];
  for (const question of request.questions) {
    const list = hypotheses(question);
    out.push({ id: question.id, margins: await margins(model, list.map(() => request.stateText), list) });
  }
  return out;
}
