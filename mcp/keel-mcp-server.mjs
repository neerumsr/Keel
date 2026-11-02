#!/usr/bin/env node
// Keel MCP server (stdio). Bridges any MCP client to the local Keel HTTP API.
// Env: KEEL_URL (default http://localhost:8080), KEEL_TOKEN (bearer for /systemone and /switch),
//      KEEL_TIMEOUT_MS (default 15000).
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const KEEL_URL = (process.env.KEEL_URL || "http://localhost:8080").replace(/\/+$/, "");
const KEEL_TOKEN = process.env.KEEL_TOKEN || "";
const TIMEOUT_MS = Number(process.env.KEEL_TIMEOUT_MS || 15000);

const INSTRUCTIONS = [
  "Keel is a local decision model (System One wire). Call keel_status once before the first decision;",
  "if enabled is false, do not call keel_decide. Use keel_decide for typed branches: route work (choice),",
  "rate severity/risk (score, ordered levels low→high), or yes/no gates (noul = P(yes); you pick the threshold).",
  "Read answers.<id>.choice/.confidence/.probabilities, .score, or .noul. Treat low confidence as 'ask or escalate'.",
  "Never put secrets in state. keel_switch turns the shared switch on/off only when the user asks.",
].join(" ");

async function keel(path, { method = "GET", body, auth = false } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    if (!KEEL_TOKEN) {
      return { ok: false, status: 0, data: { error: { type: "config", message: "KEEL_TOKEN is not set in the MCP server environment." } } };
    }
    headers.Authorization = `Bearer ${KEEL_TOKEN}`;
  }
  try {
    const res = await fetch(`${KEEL_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { raw: text.slice(0, 2000) };
    }
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: { error: { type: "unreachable", message: `Keel at ${KEEL_URL} is unreachable: ${err?.message ?? err}` } },
    };
  }
}

const HINTS = {
  0: "Start the Keel app (npm run dev) or fix KEEL_URL / KEEL_TOKEN.",
  400: "Request rejected; the message names the bad field. Fix the questions/criteria and retry.",
  401: "Bearer missing or wrong; set KEEL_TOKEN for this MCP server.",
  409: "Keel is switched off. No model call was made; decide without Keel or ask the user.",
  429: "Rate limited (120 req/60s). Back off and retry later.",
  503: "decider-pro-1.0.0 needs the Keel-Pro sidecar (serve/keel_pro_server.py). Retry with decider-latest or start the sidecar.",
};

function toResult({ ok, status, data }) {
  const payload = ok ? data : { status, ...data, hint: HINTS[status] ?? "Unexpected Keel error." };
  return {
    content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
    isError: !ok,
  };
}

const question = z.object({
  type: z.enum(["choice", "score", "noul"]),
  instructions: z.string().max(1200).optional().describe("What to decide, in plain words."),
  criteria: z
    .union([z.record(z.string(), z.string().nullable()), z.array(z.string())])
    .optional()
    .describe("choice: {label: meaning} (2-12). score: ordered levels low→high (2-10). noul: optional {true, false}."),
});

const server = new McpServer({ name: "keel", version: "1.0.0" }, { instructions: INSTRUCTIONS });

server.registerTool(
  "keel_status",
  {
    title: "Keel status",
    description: "Check whether the shared Keel switch is on and which model is serving. Call before the first decision.",
    inputSchema: {},
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  async () => toResult(await keel("/api/v1/status")),
);

server.registerTool(
  "keel_decide",
  {
    title: "Keel decide",
    description:
      "Ask Keel (local, calibrated, single-pass) one to eight typed questions about a state. Returns per-question " +
      "choice+confidence+probabilities, score (expected level) + probabilities, or noul = P(yes). Fails with 409 if the switch is off.",
    inputSchema: {
      state: z
        .union([z.string(), z.record(z.string(), z.unknown())])
        .describe("Facts to decide on (string or JSON object, ≤ 8000 chars). No secrets."),
      questions: z.record(z.string(), question).describe("Map of question id → question. 1-8 questions."),
      model: z.string().optional().describe("Model alias; default decider-latest (Keel-Lite). decider-pro-1.0.0 pins Keel-Pro when its sidecar runs."),
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  async ({ state, questions, model }) =>
    toResult(
      await keel("/api/v1/systemone", {
        method: "POST",
        auth: true,
        body: { model: model ?? "decider-latest", state, questions },
      }),
    ),
);

server.registerTool(
  "keel_switch",
  {
    title: "Keel switch",
    description: 'Turn the shared Keel switch on or off ("Keel on" / "Keel off"). Only when the user asks.',
    inputSchema: { enabled: z.boolean() },
    annotations: { readOnlyHint: false, idempotentHint: true, openWorldHint: false },
  },
  async ({ enabled }) => toResult(await keel("/api/v1/switch", { method: "POST", auth: true, body: { enabled } })),
);

await server.connect(new StdioServerTransport());
