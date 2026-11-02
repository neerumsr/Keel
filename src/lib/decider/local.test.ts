import assert from "node:assert/strict";
import test from "node:test";
import { PRESETS, draftToBody } from "./presets.ts";
import { SUITE } from "./suite.ts";
import { localWeights } from "./local.ts";
import { projectWeights, tryParse } from "./wire.ts";

function decide(body: unknown) {
  const parsed = tryParse(body);
  assert.equal(parsed.ok, true);
  if (!parsed.ok) throw new Error("parse");
  const started = performance.now();
  const answers = projectWeights(parsed.request, localWeights(parsed.request));
  return { answers, ms: performance.now() - started };
}

test("triage prefers billing, high severity, not a vulnerability", () => {
  const { answers } = decide(draftToBody(PRESETS[0]!));
  const kind = answers.kind;
  const severity = answers.severity;
  const security = answers.security;
  assert.equal(kind?.type, "choice");
  assert.equal(severity?.type, "score");
  assert.equal(security?.type, "noul");
  if (kind?.type !== "choice" || severity?.type !== "score" || security?.type !== "noul") return;
  assert.equal(kind.choice, "billing");
  assert.ok(kind.confidence >= 0.4, `confidence ${kind.confidence}`);
  assert.ok(severity.score >= 2.2, `severity ${severity.score}`);
  assert.ok(security.noul <= 0.3, `security ${security.noul}`);
});

test("refund policy blocks a refund that the customer still asked for", () => {
  const { answers } = decide(draftToBody(PRESETS[1]!));
  const refund = answers.refund;
  assert.equal(refund?.type, "noul");
  if (refund?.type !== "noul") return;
  assert.ok(refund.noul < 0.5, `refund ${refund.noul}`);
});

test("unsafe auth diff is blocked and wants a test", () => {
  const { answers } = decide(draftToBody(PRESETS[2]!));
  const verdict = answers.verdict;
  const risk = answers.risk;
  const tests = answers.needs_tests;
  assert.equal(verdict?.type, "choice");
  assert.equal(risk?.type, "score");
  assert.equal(tests?.type, "noul");
  if (verdict?.type !== "choice" || risk?.type !== "score" || tests?.type !== "noul") return;
  assert.equal(verdict.choice, "block");
  assert.ok(risk.score >= 2, `risk ${risk.score}`);
  assert.ok(tests.noul >= 0.6, `tests ${tests.noul}`);
});

test("a specified logout edit is an edit, not a stop", () => {
  const { answers } = decide(draftToBody(PRESETS[3]!));
  const action = answers.action;
  assert.equal(action?.type, "choice");
  if (action?.type !== "choice") return;
  assert.equal(action.choice, "edit");
});

test("password reset is an account issue", () => {
  const { answers } = decide({
    state: "Reset email never arrives. Cannot sign in.",
    questions: {
      kind: {
        type: "choice",
        instructions: "What kind of issue?",
        criteria: { billing: "Money", bug: "Broken product", account: "Login, password, permissions" },
      },
    },
  });
  const kind = answers.kind;
  assert.equal(kind?.type, "choice");
  if (kind?.type !== "choice") return;
  assert.equal(kind.choice, "account");
});

test("an empty greeting is not a confident call", () => {
  const { answers } = decide({
    state: "Hello there",
    questions: {
      kind: {
        type: "choice",
        instructions: "What kind of issue?",
        criteria: { billing: "Money and invoices", bug: "Broken product", account: "Login" },
      },
    },
  });
  const kind = answers.kind;
  assert.equal(kind?.type, "choice");
  if (kind?.type !== "choice") return;
  assert.ok(kind.confidence <= 0.5, `confidence ${kind.confidence}`);
});

test("fifty local cases stay inside a few milliseconds", () => {
  for (const item of SUITE) {
    const { answers, ms } = decide(item.body);
    assert.ok(ms < 30, `${item.name} took ${ms}ms`);
    const route = answers.route;
    const risk = answers.risk;
    assert.equal(route?.type, "choice");
    assert.equal(risk?.type, "score");
    if (route?.type !== "choice") continue;
    const sum = Object.values(route.probabilities).reduce((a, b) => a + b, 0);
    assert.ok(Math.abs(sum - 1) < 1e-6);
  }
});
