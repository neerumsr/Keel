import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { authorizeBearer, copilotKey } from "./auth.server.ts";
import { handleSystemOne } from "./systemone-route.server.ts";

const key = copilotKey()!;
const echo = async (body: unknown) => ({ status: 200, body: { echoed: body } });

function post(headers: Record<string, string>, body = '{"state":"x"}'): Request {
  return new Request("http://keel.test/api/v1/systemone", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body,
  });
}

test("decision calls accept Bearer or a Foundry-style api-key header", async () => {
  assert.equal((await handleSystemOne(post({ authorization: `Bearer ${key}` }), echo)).status, 200);
  const viaApiKey = await handleSystemOne(post({ "api-key": key }), echo);
  assert.equal(viaApiKey.status, 200);
  assert.deepEqual(await viaApiKey.json(), { echoed: { state: "x" } });
});

test("wrong, missing, or malformed keys are rejected before the body is read", async () => {
  let ran = false;
  const spy = async () => {
    ran = true;
    return { status: 200, body: {} };
  };
  const cases: Record<string, string>[] = [{}, { "api-key": "nope" }, { "api-key": `${key}x` }, { authorization: key }, { authorization: "Bearer nope" }];
  for (const headers of cases) {
    assert.equal((await handleSystemOne(post(headers), spy)).status, 401);
  }
  assert.equal(ran, false);
  // The switch stays Bearer-only.
  assert.equal(authorizeBearer(null), false);
});

test("bad JSON is a 400 after auth", async () => {
  assert.equal((await handleSystemOne(post({ "api-key": key }, "{"), echo)).status, 400);
});

test("Foundry path /providers/microsoft/v1/systemone uses the same handler", () => {
  const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
  const foundry = read("../../routes/providers/microsoft/v1/systemone.ts");
  const api = read("../../routes/api/v1/systemone.ts");
  assert.match(foundry, /createFileRoute\("\/providers\/microsoft\/v1\/systemone"\)/);
  for (const source of [foundry, api]) {
    assert.match(source, /import\("@\/lib\/decider\/systemone-route\.server"\)/);
    assert.match(source, /handleSystemOne\(request\)/);
  }
});
