import assert from "node:assert/strict";
import { test } from "node:test";
import { isLoopbackHost, isServerFnPath } from "./loopback.ts";

test("loopback Host headers are accepted", () => {
  for (const host of ["localhost", "localhost:8080", "127.0.0.1:8080", "127.1.2.3", "[::1]:8080", "LOCALHOST:8080"]) {
    assert.equal(isLoopbackHost(host), true, host);
  }
});

test("network, rebinding and malformed Host headers are rejected", () => {
  for (const host of [
    "192.0.2.20:8080",
    "0.0.0.0:8080",
    "evil.example:8080",
    "localhost.evil.example",
    "127.0.0.1.evil.example",
    "127.0.0.256",
    "[::ffff:192.0.2.20]:8080",
    "",
    null,
    undefined,
  ]) {
    assert.equal(isLoopbackHost(host), false, String(host));
  }
});

test("only server-function paths are guarded", () => {
  assert.equal(isServerFnPath("/_serverFn/abc"), true);
  assert.equal(isServerFnPath("/_serverFnX"), false);
  assert.equal(isServerFnPath("/api/v1/status"), false);
});
