import assert from "node:assert/strict";
import { test } from "node:test";
import { EVAL_CASES } from "./eval-set.ts";
import { prepare } from "./eval.ts";
import { loadModel, modelDir, neuralWeights, previousModelDir } from "./neural.server.ts";
import { projectWeights } from "./wire.ts";

const dir = modelDir();

test("neural judge returns a well-formed answer for every labeled case", { skip: dir ? false : "no model on disk (npm run model:fetch)" }, async () => {
  const model = await loadModel();
  assert.ok(model, "model loads");
  for (const item of EVAL_CASES) {
    const request = prepare(item);
    const bag = await neuralWeights(request);
    assert.ok(bag);
    const answers = projectWeights(request, bag);
    for (const [id, answer] of Object.entries(answers)) {
      if (answer.type === "choice") {
        const sum = Object.values(answer.probabilities).reduce((a, b) => a + b, 0);
        assert.ok(Math.abs(sum - 1) < 0.01, `case ${item.id} ${id} sums to ${sum}`);
        assert.ok(answer.confidence >= 0 && answer.confidence <= 1);
      } else if (answer.type === "score") {
        assert.ok(answer.score >= 0);
      } else {
        assert.ok(answer.noul >= 0 && answer.noul <= 1);
      }
    }
  }
});

test("neural judge is deterministic", { skip: dir ? false : "no model on disk" }, async () => {
  const request = prepare(EVAL_CASES[0]!);
  const a = projectWeights(request, (await neuralWeights(request))!);
  const b = projectWeights(request, (await neuralWeights(request))!);
  assert.deepEqual(a, b);
});

const previous = previousModelDir();
test("the decider-2.0.0 pin loads Keel-2 next to the default model", { skip: previous ? false : "models/keel-2 not on disk" }, async () => {
  const model = await loadModel(previous!);
  assert.equal(model?.config.id, "decider-2.0.0");
  const request = prepare(EVAL_CASES[0]!);
  assert.ok(await neuralWeights(request, previous!));
});
