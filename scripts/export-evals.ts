/** Export eval suites as JSON for the Python trainer (dedup + labeled-50 as training rows). */
import { mkdirSync, writeFileSync } from "node:fs";
import { EVAL_CASES } from "../src/lib/decider/eval-set.ts";
import { HOLDOUT_CASES } from "../src/lib/decider/eval-holdout.ts";
import { HOLDOUT_B_CASES } from "../src/lib/decider/eval-holdout-b.ts";
import { OPEN_CASES } from "../src/lib/decider/eval-open.ts";
import { hypotheses } from "../src/lib/decider/hypothesis.ts";
import { tryParse } from "../src/lib/decider/wire.ts";

mkdirSync("training/data", { recursive: true });
writeFileSync(
  "training/data/evals.json",
  JSON.stringify({ labeled: EVAL_CASES, holdout: HOLDOUT_CASES, holdoutB: HOLDOUT_B_CASES, open: OPEN_CASES }, null, 1),
);

// Fixtures so training/keel/test_hypothesis.py can prove the Python spec matches.
const fixtures = [...EVAL_CASES, ...OPEN_CASES, ...HOLDOUT_B_CASES].slice(0, 260).flatMap((item) => {
  const parsed = tryParse({ state: item.state, questions: item.questions });
  if (!parsed.ok) return [];
  return parsed.request.questions.map((question) => ({
    state: item.state,
    stateText: parsed.request.stateText,
    question: (item.questions as Record<string, unknown>)[question.id],
    hypotheses: hypotheses(question),
  }));
});
mkdirSync("artifacts", { recursive: true });
writeFileSync("artifacts/hypothesis-fixtures.json", JSON.stringify(fixtures, null, 1));
console.log(`exported ${EVAL_CASES.length}+${HOLDOUT_CASES.length}+${HOLDOUT_B_CASES.length}+${OPEN_CASES.length} cases, ${fixtures.length} hypothesis fixtures`);
