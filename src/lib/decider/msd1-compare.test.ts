import assert from "node:assert/strict";
import { test } from "node:test";
import { EVAL_CASES } from "./eval-set.ts";
import { localWeights } from "./local.ts";
import {
  compareMsd1,
  msd1Markdown,
  normalizeMsd1Answers,
  OPENROUTER_MSD1_MODEL,
  OPENROUTER_SYSTEMONE_URL,
  resolveMsd1Config,
  toMsd1Body,
} from "./msd1-compare.ts";
import { projectWeights, tryParse, type DecisionRequest } from "./wire.ts";

const parse = (body: unknown): DecisionRequest => {
  const parsed = tryParse(body);
  if (!parsed.ok) throw new Error(parsed.message);
  return parsed.request;
};

const mixed = parse({
  state: { message: "Checkout is down again.", contacts: 3 },
  questions: {
    team: { type: "choice", instructions: "Which team?", criteria: { billing: "Charges", engineering: "Bugs", support: null } },
    severity: { type: "score", instructions: "How severe?", criteria: ["Cosmetic", "Minor", "Major", "Critical"] },
    repeat: { type: "noul", instructions: "Contacted before?" },
    gated: { type: "noul", instructions: "Refund promised?", criteria: { true: "Commits money", false: "No commitment" } },
  },
});

const suites = [{ name: "labeled-5", cases: EVAL_CASES.slice(0, 5) }];

test("resolve: no credential means no config and a reason", () => {
  const r = resolveMsd1Config({});
  assert.equal(r.ok, false);
  assert.match(r.ok ? "" : r.reason, /OPENROUTER_API_KEY/);
});

test("resolve: OpenRouter and Foundry shapes", () => {
  const or = resolveMsd1Config({ OPENROUTER_API_KEY: "k" });
  assert.ok(or.ok);
  assert.equal(or.config.url, OPENROUTER_SYSTEMONE_URL);
  assert.equal(or.config.model, OPENROUTER_MSD1_MODEL);

  const fk = resolveMsd1Config({ OPENROUTER_API_KEY: "k", AZURE_AI_ENDPOINT: "https://x.services.ai.azure.com/", AZURE_AI_DEPLOYMENT: "d1", AZURE_AI_API_KEY: "a" });
  assert.ok(fk.ok);
  assert.equal(fk.config.url, "https://x.services.ai.azure.com/providers/microsoft/v1/systemone");
  assert.equal(fk.config.model, "d1");
  assert.deepEqual(Object.keys(fk.config.headers), ["api-key"]);

  const ft = resolveMsd1Config({ MSD1_FOUNDRY_ENDPOINT: "https://x", MSD1_FOUNDRY_DEPLOYMENT: "d1" }, "tok");
  assert.ok(ft.ok);
  assert.equal(ft.config.auth, "entra-token");

  const noAuth = resolveMsd1Config({ MSD1_FOUNDRY_ENDPOINT: "https://x", MSD1_FOUNDRY_DEPLOYMENT: "d1" });
  assert.equal(noAuth.ok, false);
  assert.equal(resolveMsd1Config({ MSD1_PROVIDER: "openrouter", AZURE_AI_ENDPOINT: "https://x" }).ok, false);
});

test("request projection keeps the System One shape", () => {
  const body = toMsd1Body(mixed, "dep");
  assert.equal(body.model, "dep");
  assert.deepEqual(body.state, { message: "Checkout is down again.", contacts: 3 });
  assert.deepEqual(body.questions.team, { type: "choice", instructions: "Which team?", criteria: { billing: "Charges", engineering: "Bugs", support: null } });
  assert.deepEqual(body.questions.severity!.criteria, ["Cosmetic", "Minor", "Major", "Critical"]);
  assert.equal("criteria" in body.questions.repeat!, false);
  assert.deepEqual(body.questions.gated!.criteria, { true: "Commits money", false: "No commitment" });
});

test("response normalization keeps vendor numbers and derives only what is missing", () => {
  const { answers, issues } = normalizeMsd1Answers(mixed, {
    team: { type: "choice", choice: "engineering", confidence: 0.8, probabilities: { billing: 0.05, engineering: 0.8, support: 0.15 } },
    severity: { type: "score", probabilities: { "0": 0, "1": 0.1, "2": 0.3, "3": 0.6 } },
    repeat: { type: "noul", noul: 0.91 },
    gated: { probability: 0.2 },
  });
  assert.deepEqual(answers.team, { type: "choice", choice: "engineering", confidence: 0.8, probabilities: { billing: 0.05, engineering: 0.8, support: 0.15 } });
  assert.equal(answers.severity?.type === "score" && answers.severity.score, 2.5);
  assert.equal(answers.severity?.type === "score" && answers.severity.confidence, 0.6);
  assert.equal(answers.severity?.type === "score" && answers.severity.legend["3"], "Critical");
  assert.deepEqual(answers.repeat, { type: "noul", noul: 0.91 });
  assert.deepEqual(answers.gated, { type: "noul", noul: 0.2 });
  assert.ok(issues.some((i) => /score derived/.test(i)));
  assert.ok(issues.some((i) => /from "probability"/.test(i)));
});

test("response normalization drops what it cannot read instead of guessing", () => {
  const { answers, issues } = normalizeMsd1Answers(mixed, {
    team: { type: "choice", choice: "sales", confidence: 0.9 },
    severity: { type: "noul", noul: 0.5 },
    repeat: { type: "noul", noul: 1.7 },
  });
  assert.deepEqual(answers, {});
  assert.ok(issues.some((i) => /"sales" is not an option/.test(i)));
  assert.ok(issues.some((i) => /type noul != score/.test(i)));
  assert.ok(issues.some((i) => /gated: missing/.test(i)));
});

test("no credential: nothing is sent and every MSD1 field is null", async () => {
  let calls = 0;
  const fake = (async () => {
    calls++;
    throw new Error("must not be called");
  }) as unknown as typeof fetch;
  const report = await compareMsd1(suites, localWeights, "decider-1.2.0", resolveMsd1Config({}), fake);
  assert.equal(calls, 0);
  assert.equal(report.msd1Compared, false);
  assert.equal(report.msd1Calls, 0);
  assert.equal(report.accuracy.msd1, null);
  assert.equal(report.latencyMs.msd1.median, null);
  assert.ok(report.rows.every((r) => r.msd1.answers === null && r.msd1.choiceOk === null && r.msd1.safetyMiss === null));
  assert.match(msd1Markdown(report), /not\*\* measured/);
});

test("401 stops after the first call; call budget is enforced", async () => {
  let calls = 0;
  const reject = (async () => {
    calls++;
    return new Response("bad key", { status: 401 });
  }) as unknown as typeof fetch;
  const r1 = await compareMsd1(suites, localWeights, "decider-1.2.0", resolveMsd1Config({ OPENROUTER_API_KEY: "k" }), reject);
  assert.equal(calls, 1);
  assert.equal(r1.msd1Compared, false);
  assert.match(r1.msd1Reason ?? "", /401/);

  const echo = (async (_url: string, init: RequestInit) => {
    const body = JSON.parse(String(init.body));
    assert.equal(body.model, OPENROUTER_MSD1_MODEL);
    const request = parse({ ...body, model: "decider-latest" });
    return Response.json({ model: "microsoft/microsoft-decision-1-20261009", answers: projectWeights(request, localWeights(request)), usage: { input_tokens: 100, output_tokens: 0, cost: 0.0000042 } });
  }) as unknown as typeof fetch;
  const r2 = await compareMsd1(suites, localWeights, "decider-1.2.0", resolveMsd1Config({ OPENROUTER_API_KEY: "k" }), echo, 3);
  assert.equal(r2.msd1Calls, 3);
  assert.equal(r2.rows.filter((r) => r.msd1.answers).length, 3);
  assert.match(r2.rows[4]!.msd1.error ?? "", /budget/);
  assert.equal(r2.msd1Compared, true);
  assert.equal(r2.agreement.choice ?? 1, 1);
  assert.equal(r2.msd1InputTokens, 300);
  assert.equal(r2.msd1ServedModel, "microsoft/microsoft-decision-1-20261009");
  assert.equal(r2.accuracyOnAnswered?.msd1.choice, r2.accuracyOnAnswered?.keel.choice);
});
