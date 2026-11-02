#!/usr/bin/env node
// Smoke test: spawn mcp/keel-mcp-server.mjs over stdio, list tools, call keel_status and keel_decide.
// Needs a running Keel (KEEL_URL) and KEEL_TOKEN in the environment. Exit code 0 = pass.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { fileURLToPath } from "node:url";

const serverPath = fileURLToPath(new URL("./keel-mcp-server.mjs", import.meta.url));
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverPath],
  env: { ...process.env },
});
const client = new Client({ name: "keel-smoke", version: "1.0.0" });
await client.connect(transport);

const fail = (msg) => {
  console.error(`FAIL: ${msg}`);
  process.exitCode = 1;
};

const { tools } = await client.listTools();
const names = tools.map((t) => t.name).sort();
console.log("tools/list:", names.join(", "));
for (const n of ["keel_decide", "keel_status", "keel_switch"]) if (!names.includes(n)) fail(`missing tool ${n}`);
console.log("instructions:", (client.getInstructions() ?? "").slice(0, 80) + "…");

const status = await client.callTool({ name: "keel_status", arguments: {} });
console.log("keel_status:", status.content[0].text.replace(/\s+/g, " "));
if (status.isError) fail("keel_status errored");

const decide = await client.callTool({
  name: "keel_decide",
  arguments: {
    state: "User: the checkout page charges my card twice when I press Pay. Lost $80.",
    questions: {
      kind: { type: "choice", instructions: "Route the ticket.", criteria: { billing: "money/charges", bug: "software defect", account: "login/profile" } },
      severity: { type: "score", instructions: "How bad is it?", criteria: ["cosmetic", "workaround exists", "blocks the task", "data or money loss"] },
      security: { type: "noul", instructions: "Is this a security incident?" },
    },
  },
});
const text = decide.content[0].text;
console.log("keel_decide:", text.replace(/\s+/g, " ").slice(0, 600));
if (decide.isError) fail("keel_decide errored");
else {
  const answers = JSON.parse(text).answers;
  if (!answers?.kind?.choice || typeof answers?.severity?.score !== "number" || typeof answers?.security?.noul !== "number") {
    fail("keel_decide answers malformed");
  }
}

await client.close();
console.log(process.exitCode ? "SMOKE FAILED" : "SMOKE OK");
