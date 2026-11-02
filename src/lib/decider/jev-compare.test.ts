import assert from "node:assert/strict";
import { test } from "node:test";
import { EVAL_CASES } from "./eval-set.ts";
import { compare, compareMarkdown } from "./jev-compare.ts";
import { localWeights } from "./local.ts";
import { projectWeights, tryParse } from "./wire.ts";

const suites = [{ name: "labeled-5", cases: EVAL_CASES.slice(0, 5) }];

test("no key: nothing is sent and every Jev field is null", async () => {
  let calls = 0;
  const fake = (async () => {
    calls++;
    throw new Error("must not be called");
  }) as unknown as typeof fetch;
  const report = await compare(suites, localWeights, "decider-1.2.0", undefined, fake);
  assert.equal(calls, 0);
  assert.equal(report.jevCompared, false);
  assert.match(report.jevReason ?? "", /TYPESAFE_API_KEY/);
  assert.equal(report.accuracy.jev, null);
  assert.equal(report.latencyMs.jev.median, null);
  assert.ok(report.rows.every((r) => r.jev.answers === null && r.jev.choiceOk === null));
  assert.match(compareMarkdown(report), /not\*\* measured/);
});

test("401 stops after the first call", async () => {
  let calls = 0;
  const fake = (async () => {
    calls++;
    return new Response("bad key", { status: 401 });
  }) as unknown as typeof fetch;
  const report = await compare(suites, localWeights, "decider-1.2.0", "k", fake);
  assert.equal(calls, 1);
  assert.equal(report.jevCompared, false);
  assert.match(report.jevReason ?? "", /401/);
});

test("a Jev that echoes Keel agrees fully", async () => {
  const fake = (async (_url: string, init: RequestInit) => {
    const parsed = tryParse({ ...JSON.parse(String(init.body)), model: "decider-latest" });
    if (!parsed.ok) throw new Error(parsed.message);
    const answers = projectWeights(parsed.request, localWeights(parsed.request));
    return Response.json({ model: "jev-1.13.0", answers });
  }) as unknown as typeof fetch;
  const report = await compare(suites, localWeights, "decider-1.2.0", "k", fake);
  assert.equal(report.jevCompared, true);
  assert.equal(report.agreement.choice ?? 1, 1);
  assert.equal(report.agreement.scoreMae ?? 0, 0);
  assert.equal(report.accuracy.jev?.choice, report.accuracy.keel.choice);
});
