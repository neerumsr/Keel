# Integrations

Copy-paste setup for GitHub Copilot CLI, VS Code, Claude Code, OpenAI Codex CLI, Cursor, the Jev and Microsoft-Decision-1 SDKs, and plain HTTP.

## How agents use Keel

Every coding agent below supports local **MCP** (Model Context Protocol) servers over stdio. Keel ships one, `mcp/keel-mcp-server.mjs`, so a single server works in every client. The agent sees three typed tools, the key stays in the server's environment instead of the prompt, and the client's normal tool-approval UI applies.

<!-- diagram:agents-mcp -->

There are two layers:

1. **The MCP server** gives the agent the tools.
2. **A policy paragraph** (in an agent file, `AGENTS.md`, `CLAUDE.md` or a rule) tells it *when* to use them.

| Tool | Calls | Use |
|---|---|---|
| `keel_status` | `GET /api/v1/status` | Once, before the first decision. If Keel is off, do not call `keel_decide`. |
| `keel_decide` | `POST /api/v1/systemone` | `state`, `questions` (1–8), optional `model` (default `decider-latest`) |
| `keel_switch` | `POST /api/v1/switch` | Only when the user says "Keel on" or "Keel off" |

## Before you start

1. Clone Keel, run `npm install` (it provides `@modelcontextprotocol/sdk` and `zod`), and start it with `npm run dev`. You need Node 22.
2. Put your key in the `KEEL_TOKEN` environment variable: `export KEEL_TOKEN=$(npm run -s keel:token)` (PowerShell: `$env:KEEL_TOKEN = npm run -s keel:token`). The key is unique to your install; see [Quickstart, step 2](quickstart.md#2-get-your-local-key).
3. Run the smoke test. It starts the server and calls all three tools:

```bash
node mcp/smoke.mjs
# tools/list: keel_decide, keel_status, keel_switch
# keel_status: { "enabled": true, "model": "decider-3.0.0", ... }
# keel_decide: { "model": "decider-3.0.0", "answers": { "kind": { "type": "choice", "choice": "billing", ... } } }
# SMOKE OK
```

Server environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `KEEL_URL` | `http://localhost:8080` | Where Keel is running |
| `KEEL_TOKEN` | none | The key. Required for `keel_decide` and `keel_switch`. |
| `KEEL_TIMEOUT_MS` | `15000` | Per-request timeout |

Always use the **absolute path** to the server file. In the snippets, `/path/to/Keel` stands for your clone (`C:\path\to\Keel` on Windows). **Never commit the key.** Every snippet below references `KEEL_TOKEN` from the environment.

Errors come back to the agent as tool errors with the HTTP status and a hint: 0 means Keel is unreachable or misconfigured, 401 a wrong key, 409 that Keel is switched off (no model ran), and 429 the rate limit.

## The policy paragraph

Paste this into whichever instruction file your client reads. It is short on purpose.

```markdown
# Keel decisions
When a task needs a typed branch (route, severity, edit/ask/stop) call the `keel_status` tool once; if enabled,
call `keel_decide` instead of guessing. Low confidence or noul near 0.5 → ask or escalate. "Keel on/off" → `keel_switch`.
```

## GitHub Copilot CLI

**Add the server** from the command line:

```shell
copilot mcp add keel --env KEEL_TOKEN=${KEEL_TOKEN} -- node /path/to/Keel/mcp/keel-mcp-server.mjs
```

Or run `/mcp add` in an interactive session, or edit `~/.copilot/mcp-config.json`. Only `PATH` is inherited from your shell, so pass every other variable in `env`:

```json
{
  "mcpServers": {
    "keel": {
      "type": "local",
      "command": "node",
      "args": ["C:\\path\\to\\Keel\\mcp\\keel-mcp-server.mjs"],
      "env": { "KEEL_URL": "http://localhost:8080", "KEEL_TOKEN": "${KEEL_TOKEN}" },
      "tools": ["*"]
    }
  }
}
```

A repo-root `.mcp.json` with the same `mcpServers` shape takes precedence, and `.github/mcp.json` is also read.

**Add the policy.** Keel ships a custom agent at `.github/agents/keel.agent.md`. Run `npm run keel:agents` to install it in `~/.copilot/agents/` with your token filled in, then select it with `/agent` or `copilot --agent keel`. You can also paste the policy paragraph into `.github/copilot-instructions.md`, `AGENTS.md` or `~/.copilot/copilot-instructions.md`.

`npm run keel:agents` regenerates these files for your current origin. The repo copies, `.github/agents/keel.agent.md` and `.github/copilot-instructions.md`, get a `<KEEL_TOKEN>` placeholder and are safe to commit. The real token goes only to your user-level files, `~/.copilot/agents/keel.agent.md` and the Keel block of `~/.copilot/copilot-instructions.md`, so the agent works everywhere without the key entering the repo. `--repo-key` embeds the real token in the repo copies too; never commit that. The generated files call the HTTP API with curl. Once MCP is installed, prefer the MCP policy paragraph, which keeps the key out of the prompt.

Docs: [Add MCP servers to Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers), [Custom agents for Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli).

## VS Code Copilot agent mode

**Add the server** in `.vscode/mcp.json` (workspace) or your profile's `mcp.json`. VS Code uses a `servers` key and `${env:NAME}` references:

```json
{
  "servers": {
    "keel": {
      "type": "stdio",
      "command": "node",
      "args": ["${workspaceFolder}/mcp/keel-mcp-server.mjs"],
      "env": { "KEEL_URL": "http://localhost:8080", "KEEL_TOKEN": "${env:KEEL_TOKEN}" }
    }
  }
}
```

To be prompted for the key instead of reading it from the environment, use `inputs`:

```json
{
  "inputs": [{ "type": "promptString", "id": "keel-token", "description": "Keel key", "password": true }],
  "servers": { "keel": { "type": "stdio", "command": "node",
    "args": ["${workspaceFolder}/mcp/keel-mcp-server.mjs"], "env": { "KEEL_TOKEN": "${input:keel-token}" } } }
}
```

VS Code does not forward `${input:...}` servers to Copilot harness sessions, so use the env form there. You can also add the server with **MCP: Add Server → Command (stdio)** in the Command Palette.

**Add the policy.** VS Code picks up `.github/agents/keel.agent.md` as a custom agent, plus `.github/copilot-instructions.md` and `AGENTS.md`.

Docs: [Add MCP servers in VS Code](https://code.visualstudio.com/docs/agent-customization/mcp-servers), [MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

## One file for three clients

A repo-root `.mcp.json` is read by Copilot CLI, VS Code (portable format) and Claude Code:

```json
{
  "mcpServers": {
    "keel": {
      "command": "node",
      "args": ["/path/to/Keel/mcp/keel-mcp-server.mjs"],
      "env": { "KEEL_TOKEN": "${KEEL_TOKEN}", "KEEL_URL": "${KEEL_URL:-http://localhost:8080}" }
    }
  }
}
```

## Claude Code

**Add the server:**

```shell
claude mcp add --env KEEL_TOKEN=$KEEL_TOKEN --transport stdio keel -- node /path/to/Keel/mcp/keel-mcp-server.mjs
# add --scope project to write .mcp.json, or --scope user for ~/.claude.json
```

Put options such as `--transport stdio` between `--env` and the server name. Everything after `--` is passed to the server untouched. The tools appear as `mcp__keel__keel_decide`, `mcp__keel__keel_status` and `mcp__keel__keel_switch`.

**Add the policy** by pasting the policy paragraph into `CLAUDE.md` at the project root.

**Optional subagent** at `.claude/agents/keel.md`:

```markdown
---
name: keel
description: Routes ambiguous typed judgments (route, severity, edit/ask/stop) through the local Keel decision model.
tools: mcp__keel__keel_status, mcp__keel__keel_decide
---
Call keel_status once. If enabled, express the decision as System One questions and call keel_decide.
Report the choice, confidence and probabilities. Below 0.6 confidence, recommend asking the user.
```

**Optional gatekeeper hook (a pattern, not shipped).** A `PreToolUse` command hook can send each pending tool call to Keel as a noul ("is this destructive?") and return `{"permissionDecision": "ask"}` above a threshold. This is the strongest integration, but it puts Keel on every tool call, so treat it as opt-in.

Docs: [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Hooks guide](https://code.claude.com/docs/en/hooks-guide).

## OpenAI Codex CLI

**Add the server:**

```shell
codex mcp add keel --env KEEL_TOKEN=$KEEL_TOKEN -- node /path/to/Keel/mcp/keel-mcp-server.mjs
```

Or edit `~/.codex/config.toml`. A project `.codex/config.toml` also works, for trusted projects only:

```toml
[mcp_servers.keel]
command = "node"
args = ["/path/to/Keel/mcp/keel-mcp-server.mjs"]
env_vars = ["KEEL_TOKEN"]            # forward from the parent env; no literal secret in the file
env = { KEEL_URL = "http://localhost:8080" }
startup_timeout_sec = 10
tool_timeout_sec = 30
enabled_tools = ["keel_status", "keel_decide", "keel_switch"]
```

**Add the policy** by pasting the policy paragraph into `AGENTS.md`. Codex also reads the instructions the MCP server sends at start-up.

Docs: [Codex MCP](https://developers.openai.com/codex/mcp).

## Cursor

**Add the server** in `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "keel": {
      "command": "node",
      "args": ["/path/to/Keel/mcp/keel-mcp-server.mjs"],
      "env": { "KEEL_URL": "http://localhost:8080", "KEEL_TOKEN": "${env:KEEL_TOKEN}" }
    }
  }
}
```

**Add the policy** as a project rule in `.cursor/rules/keel.mdc`:

```markdown
---
description: Use the local Keel decision model for typed branches
alwaysApply: true
---
# Keel decisions
When a task needs a typed branch (route, severity, edit/ask/stop) call the `keel_status` tool once; if enabled,
call `keel_decide` instead of guessing. Low confidence or noul near 0.5 → ask or escalate. "Keel on/off" → `keel_switch`.
```

`AGENTS.md` works as well. Docs: [Cursor MCP](https://cursor.com/docs/mcp), [Cursor rules](https://cursor.com/docs/context/rules).

## Variable syntax cheat sheet

| Client | File | Root key | Env reference |
|---|---|---|---|
| Copilot CLI | `~/.copilot/mcp-config.json`, `.mcp.json`, `.github/mcp.json` | `mcpServers` | `${NAME}` |
| VS Code | `.vscode/mcp.json`, profile `mcp.json` | `servers` | `${env:NAME}`, `${input:id}` |
| VS Code (portable) | `.mcp.json` | `mcpServers` | `${NAME}`, `${NAME:-default}` |
| Claude Code | `.mcp.json`, `~/.claude.json` | `mcpServers` | `${NAME}`, `${NAME:-default}` |
| Codex CLI | `~/.codex/config.toml`, `.codex/config.toml` | `[mcp_servers.<name>]` | `env_vars = [...]` |
| Cursor | `.cursor/mcp.json`, `~/.cursor/mcp.json` | `mcpServers` | `${env:NAME}` |

## TypeSafe Jev SDKs

Point the SDK at Keel's `/api` prefix and turn compression off. Keel does not decode compressed bodies yet.

```bash
export TYPESAFE_API_KEY=$KEEL_TOKEN
export TYPESAFE_BASE_URL=http://localhost:8080/api
```

```python
from typesafe_sdk import TypeSafeClient, Choice
with TypeSafeClient(compression=False) as client:
    r = client.system_one(state="I was charged twice.", questions={
        "team": Choice(instructions="Which team?", criteria={"Billing": "Payments", "Tech Support": "Bugs"})})
```

```ts
import { TypeSafeClient, choice } from "@typesafe-ai/sdk";
const client = new TypeSafeClient({ baseURL: "http://localhost:8080/api", apiKey: process.env.KEEL_TOKEN, compression: false });
```

Verified with `typesafe-sdk` 0.7.5 and `@typesafe-ai/sdk` 0.7.0. `models.list()` does not parse Keel's model list yet.

## Microsoft-Decision-1 clients

Swap the Foundry endpoint for Keel and send the Keel key as `api-key`:

```text
https://<resource>.services.ai.azure.com/providers/microsoft/v1/systemone
→ http://localhost:8080/providers/microsoft/v1/systemone
```

Use `"model": "microsoft-decision-1"` or omit it. OpenRouter clients set their base URL to `http://localhost:8080/api` and keep `microsoft/microsoft-decision-1`.

## Plain HTTP and LangChain-style tools

Any framework that can make an HTTP call can use Keel. Wrap it as a tool with a narrow schema, so the LLM only fills in the state:

```python
import os, requests

KEEL = "http://localhost:8080/api/v1/systemone"
HEADERS = {"Authorization": f"Bearer {os.environ['KEEL_TOKEN']}"}

def route_ticket(ticket: str) -> str:
    """Route a support ticket to billing, tech or sales. Returns the team, or 'unsure'."""
    body = {"state": ticket, "questions": {"team": {"type": "choice",
            "instructions": "Which team should handle this ticket?",
            "criteria": {"billing": "Payments, refunds, invoices", "tech": "Bugs and outages", "sales": "New purchases"}}}}
    a = requests.post(KEEL, json=body, headers=HEADERS, timeout=5).json()["answers"]["team"]
    return a["choice"] if a["confidence"] >= 0.6 else "unsure"
```

Register `route_ticket` with your framework's tool decorator (for example LangChain's `@tool`), or call it directly in code before invoking the LLM. Calling it in code is cheaper: the LLM never sees the decision at all. See [Token savings](token-savings.md).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Tool error with status 0 | Keel is not running, or `KEEL_URL` is wrong | Start `npm run dev`. Check `curl http://localhost:8080/api/v1/status`. The server binds `127.0.0.1`, so a client in a container or on another machine cannot reach it unless you set `KEEL_HOST`. |
| 401 | `KEEL_TOKEN` is missing or stale (the secret was rotated, `KEEL_SECRET` changed, or another user account has its own `~/.keel/secret`) | Run `npm run -s keel:token` again and rerun `npm run keel:agents`. Restart the client so it picks up the new environment. |
| 409 | Keel is switched off | Say "Keel on", or `POST /api/v1/switch` with `{"enabled": true}` |
| 400 "Body must be JSON" from a Jev SDK | The SDK compressed the body | Pass `compression=False` |
| The server does not appear in the client | Relative path, or the wrong root key for that client | Use an absolute path and check the cheat sheet |
| The agent never calls Keel | No policy paragraph | Add it to the instruction file your client reads |
