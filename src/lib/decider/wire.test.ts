import assert from "node:assert/strict";
import test from "node:test";
import {
  argmax,
  confidenceFrom,
  distribute,
  jevChoiceConfidence,
  jevScoreConfidence,
  projectWeights,
  resolveModel,
  tryParse,
  wantsLexical,
  type DecisionRequest,
} from "./wire.ts";

test("distribute renormalizes and sums to 1", () => {
  const probs = distribute([50, 50, 0]);
  const sum = probs.reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(sum - 1) < 1e-9);
  assert.equal(probs[0], probs[1]);
  assert.equal(probs[2], 0);
});

test("uniform split is not a confident call", () => {
  const probs = distribute([0, 0, 0, 0]);
  assert.ok(Math.abs(probs.reduce((a, b) => a + b, 0) - 1) < 1e-9);
  assert.ok(confidenceFrom(probs) <= 0.26);
});

test("confidence is 1 on a certain choice", () => {
  assert.equal(confidenceFrom([1, 0, 0]), 1);
});

test("argmax is stable on a tie", () => {
  assert.equal(argmax([0.4, 0.4, 0.2]), 0);
});

test("parses the three primitives and jev model alias", () => {
  const parsed = tryParse({
    model: "jev-latest",
    state: { message: "Charged twice. Cancel Friday if this is not refunded." },
    questions: {
      kind: {
        type: "choice",
        instructions: "What kind of issue?",
        criteria: { billing: "Money", technical: "Broken product", other: null },
      },
      severity: {
        type: "score",
        instructions: "How severe?",
        criteria: ["Cosmetic", "Workaround", "Blocks", "Data loss"],
      },
      security: { type: "noul", instructions: "Is this a vulnerability?" },
    },
  });
  assert.equal(parsed.ok, true);
  if (!parsed.ok) return;
  assert.equal(parsed.request.questions.length, 3);
  assert.equal(parsed.request.model, "jev-latest");
});

test("rejects reserved question ids and unknown models", () => {
  assert.equal(tryParse({ state: "x", questions: { confidence: { type: "noul", instructions: "Y?" } } }).ok, false);
  assert.equal(
    tryParse({ model: "gpt-4", state: "x", questions: { a: { type: "noul", instructions: "Y?" } } }).ok,
    false,
  );
});

test("score expected value sits between neighboring levels", () => {
  const request: DecisionRequest = {
    model: "decider-latest",
    state: "x",
    stateText: "x",
    questions: [
      {
        id: "severity",
        type: "score",
        instructions: "How severe?",
        levels: ["Cosmetic", "Workaround", "Blocks", "Data loss"],
      },
    ],
  };
  const answers = projectWeights(request, { severity: { "0": 0, "1": 20, "2": 60, "3": 20 } });
  const answer = answers.severity;
  assert.ok(answer && answer.type === "score");
  if (!answer || answer.type !== "score") return;
  assert.ok(answer.score > 1.5 && answer.score < 2.5);
  assert.equal(answer.legend["2"], "Blocks");
  const sum = Object.values(answer.probabilities).reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(sum - 1) < 1e-9);
});

test("choice winner follows the heaviest option", () => {
  const request: DecisionRequest = {
    model: "decider-latest",
    state: "x",
    stateText: "x",
    questions: [
      {
        id: "kind",
        type: "choice",
        instructions: "Kind?",
        options: [
          { key: "billing", description: "Money" },
          { key: "technical", description: "Broken" },
        ],
      },
    ],
  };
  const answers = projectWeights(request, { kind: { billing: 80, technical: 20 } });
  const answer = answers.kind;
  assert.ok(answer && answer.type === "choice" && answer.choice === "billing");
});

// Jev parity: https://docs.typesafe.ai/confidence, https://api.typesafe.ai/openapi.json

test("Jev confidence formulas match the documented examples", () => {
  assert.equal(jevChoiceConfidence([0.6, 0.3, 0.1]), 0.4);
  assert.equal(jevChoiceConfidence([0.6, 0.2, 0.2]), 0.4);
  assert.equal(jevChoiceConfidence([0.25, 0.25, 0.25, 0.25]), 0);
  assert.equal(jevChoiceConfidence([1]), 1);
  assert.equal(jevScoreConfidence([0, 0.57, 0.43]), 0.355);
  assert.equal(jevScoreConfidence([0, 0.5, 0.5]), 0.25);
  assert.equal(jevScoreConfidence([0.5, 0, 0.5]), 0);
  assert.equal(jevScoreConfidence([0, 0, 1, 0]), 1);
});

test("jev-* models answer with Jev confidence; decider-* keeps top probability", () => {
  const body = (model: string) => ({
    model,
    state: "x",
    questions: {
      kind: { type: "choice", instructions: "Kind?", criteria: { a: "", b: "", c: "" } },
      sev: { type: "score", instructions: "How bad?", criteria: ["low", "mid", "high"] },
    },
  });
  const weights = { kind: { a: 60, b: 30, c: 10 }, sev: { "0": 0, "1": 57, "2": 43 } };
  for (const [model, choice, score] of [
    ["jev-latest", 0.4, 0.355],
    ["decider-latest", 0.6, 0.57],
  ] as const) {
    const parsed = tryParse(body(model));
    assert.ok(parsed.ok);
    if (!parsed.ok) return;
    const answers = projectWeights(parsed.request, weights);
    assert.equal(answers.kind?.type === "choice" && answers.kind.confidence, choice);
    assert.equal(answers.sev?.type === "score" && answers.sev.confidence, score);
  }
});

test("accepts Jev-shaped questions Keel used to reject", () => {
  const options = Object.fromEntries(Array.from({ length: 255 }, (_, i) => [`Option ${i} (EU)`, null]));
  const questions: Record<string, unknown> = {
    "which team?": { type: "choice", criteria: options },
    only: { type: "choice", instructions: null, criteria: { "Ship it": "Only path" } },
    "1st": { type: "noul", criteria: { true: "Refund allowed", false: "Not allowed" } },
  };
  for (let i = 0; i < 20; i++) questions[`q${i}`] = { type: "noul", instructions: `Is ${i} even?` };
  const parsed = tryParse({ model: "jev-1.14.0", state: "x", questions });
  assert.ok(parsed.ok, parsed.ok ? "" : parsed.message);
  if (!parsed.ok) return;
  assert.equal(parsed.request.questions.length, 23);
  const answers = projectWeights(parsed.request, {});
  assert.equal(answers.only?.type === "choice" && answers.only.confidence, 1);
});

test("score levels keep their positions and echo structured criteria", () => {
  const parsed = tryParse({
    state: "x",
    questions: { sev: { type: "score", instructions: "How bad?", criteria: ["low", null, { label: "high", sla: "1h" }] } },
  });
  assert.ok(parsed.ok);
  if (!parsed.ok) return;
  const q = parsed.request.questions[0];
  assert.ok(q?.type === "score");
  if (q?.type !== "score") return;
  assert.equal(q.levels.length, 3);
  assert.equal(q.levels[1], "");
  const answer = projectWeights(parsed.request, { sev: { "0": 0, "1": 0, "2": 100 } }).sev;
  assert.ok(answer?.type === "score");
  if (answer?.type !== "score") return;
  assert.equal(answer.score, 2);
  assert.deepEqual(answer.legend["2"], { label: "high", sla: "1h" });
});

test("still rejects unusable questions", () => {
  const ask = (questions: Record<string, unknown>) => tryParse({ state: "x", questions }).ok;
  assert.equal(ask({ a: { type: "noul" } }), false);
  assert.equal(ask({ a: { type: "choice", criteria: {} } }), false);
  assert.equal(ask({ a: { type: "score", criteria: Array(11).fill("x") } }), false);
  assert.equal(ask({ "a\nb": { type: "noul", instructions: "Y?" } }), false);
  const many = Object.fromEntries(
    Array.from({ length: 5 }, (_, i) => [`q${i}`, { type: "choice", criteria: Object.fromEntries(Array.from({ length: 255 }, (_, j) => [`o${j}`, null])) }]),
  );
  assert.equal(ask(many), false);
});

test("Microsoft-Decision-1 model names resolve to Keel's neural model", () => {
  for (const model of [
    "microsoft-decision-1",
    "Microsoft-Decision-1",
    "microsoft/microsoft-decision-1",
    "microsoft/microsoft-decision-1-20261009",
  ]) {
    const parsed = tryParse({ model, state: "x", questions: { a: { type: "noul", instructions: "Y?" } } });
    assert.ok(parsed.ok, model);
    if (!parsed.ok) return;
    assert.equal(wantsLexical(parsed.request.model), false);
    assert.equal(resolveModel(parsed.request.model), "decider-3.0.0");
  }
  assert.equal(tryParse({ model: "my-foundry-deployment", state: "x", questions: { a: { type: "noul", instructions: "Y?" } } }).ok, false);
});

test("aliases resolve to decider-3.0.0; decider-2.0.0 and decider-1.x stay pinnable", () => {
  for (const model of ["decider-latest", "decider-3.0.0", "jev-latest", "jev-1.13.0", "decider-preview"]) {
    assert.equal(resolveModel(model), "decider-3.0.0", model);
  }
  assert.equal(resolveModel("decider-2.0.0"), "decider-2.0.0");
  assert.equal(resolveModel("decider-pro-1.0.0"), "decider-pro-1.0.0");
  assert.equal(resolveModel("decider-1.2.0"), "decider-1.2.0");
  for (const model of ["decider-3.0.0", "decider-2.0.0"]) {
    assert.ok(tryParse({ model, state: "x", questions: { a: { type: "noul", instructions: "Y?" } } }).ok, model);
  }
});

test("the Keel-Pro pin takes an empty state and long text; other models keep the default limits", () => {
  const long = "x".repeat(20_000);
  const ask = (model: string, state: unknown, instructions: string, description = "yes") =>
    tryParse({ model, state, questions: { a: { type: "choice", instructions, criteria: { y: description, n: "no" } } } }).ok;
  for (const [state, instructions, description] of [["", "Pick", "yes"], [long, "Pick", "yes"], ["s", long, "yes"], ["s", "Pick", "d".repeat(1500)]]) {
    assert.equal(ask("decider-pro-1.0.0", state, instructions, description), true);
    assert.equal(ask("decider-3.0.0", state, instructions, description), false);
  }
  assert.equal(ask("decider-pro-1.0.0", "x".repeat(200_001), "Pick"), false);
});
