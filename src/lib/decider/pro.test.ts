import assert from "node:assert/strict";
import test from "node:test";
import { isLoopbackUrl, proWeights } from "./pro.server.ts";
import { tryParse, type DecisionRequest } from "./wire.ts";

function request(): DecisionRequest {
  const parsed = tryParse({
    model: "decider-pro-1.0.0",
    state: { diff: "rename a variable" },
    questions: {
      act: { type: "choice", instructions: "Next step?", criteria: { edit: "Edit", ask: "Ask" } },
      risky: { type: "noul", instructions: "Is it risky?" },
    },
  });
  assert.ok(parsed.ok);
  return parsed.request;
}

function fakeFetch(status: number, body: unknown, seen: unknown[] = []): typeof fetch {
  return (async (url: string, init: RequestInit) => {
    seen.push({ url, body: JSON.parse(String(init.body)) });
    return new Response(JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
}

test("only loopback sidecar URLs are allowed", () => {
  assert.ok(isLoopbackUrl("http://127.0.0.1:8090"));
  assert.ok(isLoopbackUrl("http://localhost:8090"));
  assert.ok(isLoopbackUrl("http://[::1]:8090"));
  assert.ok(!isLoopbackUrl("http://10.0.0.5:8090"));
  assert.ok(!isLoopbackUrl("https://example.com"));
  assert.ok(!isLoopbackUrl("not a url"));
});

test("proWeights posts state and normalized questions, returns the weight bag", async () => {
  const seen: { url: string; body: { state: unknown; questions: { id: string }[] } }[] = [];
  const weights = { act: { edit: 80, ask: 20 }, risky: { yes: 10 } };
  const got = await proWeights(request(), fakeFetch(200, { model: "decider-pro-1.0.0", weights }, seen));
  assert.deepEqual(got, weights);
  assert.equal(seen[0]!.url, "http://127.0.0.1:8090/v1/weights");
  assert.deepEqual(seen[0]!.body.state, { diff: "rename a variable" });
  assert.deepEqual(
    seen[0]!.body.questions.map((q) => q.id),
    ["act", "risky"],
  );
});

test("proWeights returns null on sidecar errors, missing questions, or a non-loopback URL", async () => {
  assert.equal(await proWeights(request(), fakeFetch(500, {})), null);
  assert.equal(await proWeights(request(), fakeFetch(200, { weights: { act: { edit: 1 } } })), null);
  const down = (async () => {
    throw new TypeError("fetch failed");
  }) as unknown as typeof fetch;
  assert.equal(await proWeights(request(), down), null);
  const prev = process.env.KEEL_PRO_URL;
  process.env.KEEL_PRO_URL = "http://10.1.2.3:8090";
  try {
    let called = false;
    const spy = (async () => {
      called = true;
      return new Response("{}");
    }) as unknown as typeof fetch;
    assert.equal(await proWeights(request(), spy), null);
    assert.equal(called, false);
  } finally {
    if (prev === undefined) delete process.env.KEEL_PRO_URL;
    else process.env.KEEL_PRO_URL = prev;
  }
});
