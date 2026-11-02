import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { reportMarkdown, runEval } from "./eval.ts";

const ARTIFACTS = path.resolve(import.meta.dirname, "../../../artifacts");

test("fifty labeled cases compare Keel on with Keel off", () => {
  const report = runEval();
  mkdirSync(ARTIFACTS, { recursive: true });
  writeFileSync(path.join(ARTIFACTS, "keel-on-off-report.json"), JSON.stringify(report, null, 2));
  writeFileSync(path.join(ARTIFACTS, "keel-on-off-report.md"), reportMarkdown(report));

  assert.equal(report.cases, 50);
  assert.equal(report.jevCompared, false);
  assert.equal(report.keelOn.latencyMs.n, 50);
  assert.ok(report.keelOn.latencyMs.p95 < 20, `p95 ${report.keelOn.latencyMs.p95}ms`);
  assert.ok(report.keelOn.choice.scored >= 30);
  assert.ok(report.regression.verdict === "no_regression" || report.regression.verdict === "regression");
});
