#!/usr/bin/env node
/**
 * Download open base weights from Hugging Face (MIT license). One-time; the
 * decision path never touches the network.
 *
 *   npm run model:fetch            -> models/keel-base  (zero-shot ONNX fallback, ~13 MB)
 *   npm run model:fetch -- --train -> models/base-xd6   (PyTorch weights to fine-tune Keel)
 *
 * The trained Keel-3 model (models/keel-3, decider-3.0.0) is produced by `npm run model:export`;
 * Keel-2 (models/keel-2, decider-2.0.0) stays on disk for clients that pin it.
 */
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";

const REPO = "MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33";
const train = process.argv.includes("--train");
const dest = path.resolve(train ? "models/base-xd6" : "models/keel-base");
const tokenizer = ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"];
const files = train ? [...tokenizer, "model.safetensors"] : [...tokenizer, "onnx/model_quantized.onnx"];

for (const file of files) {
  const out = path.join(dest, file);
  if (existsSync(out)) {
    console.log(`have ${file}`);
    continue;
  }
  mkdirSync(path.dirname(out), { recursive: true });
  const url = `https://huggingface.co/${REPO}/resolve/main/${file}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${url}`);
  writeFileSync(out, Buffer.from(await response.arrayBuffer()));
  console.log(`got  ${file}`);
}

if (!train) {
  const config = {
    id: "decider-2.0.0-zeroshot",
    base: REPO,
    hypothesisVersion: 1,
    maxLength: 256,
    threads: 4,
    onnx: "onnx/model_quantized.onnx",
    temperature: { choice: 1, score: 1, noul: 1 },
    abstain: { threshold: 0.35, floor: 0 },
    lexicalBlend: { choice: 0.5, score: 0.5, noul: 0.5 },
    scoreSmoothing: 0,
    noulBias: 0,
  };
  writeFileSync(path.join(dest, "keel.json"), JSON.stringify(config, null, 2));
}
console.log(`ready: ${dest}`);
