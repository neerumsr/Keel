# Plugging Keel into coding agents

Owner: msd1-3. Verified against vendor docs fetched 2026-10. Each section links its source.

## Recommendation: ship an MCP server

All five target clients (Copilot CLI, VS Code Copilot, Claude Code, Codex CLI, Cursor) support **local stdio MCP servers**. MCP is the only mechanism they all share.

The alternative is "call the HTTP API with curl from instructions", which is what `.github/agents/keel.agent.md` does today. It works but has drawbacks:
- the bearer has to appear in prompt text;
- the agent needs shell permission;
- the request JSON is hand-written, with no schema.

An MCP server fixes all three:
- it exposes typed tools with input schemas;
- the token stays in the server's environment;
- the client's normal tool-approval UI applies.

**Decision:** ship `mcp/keel-mcp-server.mjs`. It is implemented and smoke-tested. Keep the agent files and instructions as the "when to call Keel" policy layer.

| Tool | Maps to | Notes |
|---|---|---|
| `keel_status` | `GET /api/v1/status` | Public; call before the first decision |
| `keel_decide` | `POST /api/v1/systemone` | `state`, `questions` (1–8), optional `model` (default `decider-latest`) |
| `keel_switch` | `POST /api/v1/switch` | `{enabled}`; only when the user says "Keel on/off" |

Environment:
- `KEEL_URL` (default `http://localhost:8080`)
- `KEEL_TOKEN` (the bearer; required for decide and switch)
- `KEEL_TIMEOUT_MS` (default 15000)

Errors come back as `isError: true` with the HTTP status and a hint (0 = unreachable or config, 400, 401, 409 = switch off with no model call made, 429). The server also sends MCP `instructions`; Codex reads them, and the first 512 characters are self-contained.

Prerequisites:
- Node 22.
- `npm install` in the Keel repo, which provides `@modelcontextprotocol/sdk` and `zod`.
- Keel running (`npm run dev`).

Use the **absolute path** to the server file. Its imports resolve from the repo's `node_modules`, so any working directory works.

**Never commit the token.** Every snippet below references the `KEEL_TOKEN` environment variable instead of a literal value.

Smoke test (it spawns the server and runs `tools/list`, `keel_status` and `keel_decide`):

```powershell
$env:KEEL_TOKEN = '<your local bearer>'; node mcp/smoke.mjs   # prints SMOKE OK
```

Result on 2026-10 against `decider-2.0.0`: tools `keel_decide, keel_status, keel_switch`. A double-charge ticket returned `billing` (0.75), severity 2.53 of 0–3, and security noul 0.12. With no token, the server returned a clean config error.

In the snippets, `C:\path\to\Keel` stands for your clone (on macOS or Linux, `/path/to/Keel`).

---

## (a) GitHub Copilot CLI

Docs: [Add MCP servers to Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers), [custom agents for CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli), [VS Code MCP config reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) (this reference also defines the portable `mcpServers` format the CLI reads).

**Command line:**

```shell
copilot mcp add keel --env KEEL_TOKEN=${KEEL_TOKEN} -- node C:\path\to\Keel\mcp\keel-mcp-server.mjs
```

Or run `/mcp add` inside an interactive session.

**User config file** `~/.copilot/mcp-config.json` (or `$COPILOT_HOME/mcp-config.json`). Only `PATH` is inherited from the parent environment; pass every other variable in `env`, where `${NAME}` is expanded:

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

**Per-repo config:** `.mcp.json` at the repo root uses the same `mcpServers` shape and takes precedence. `.github/mcp.json` is also read.

**Policy layer:**
- `~/.copilot/agents/keel.agent.md` (user) or `.github/agents/keel.agent.md` (repo). Both already exist; the user copy wins on an ID clash. Select one with `/agent` or `copilot --agent keel`.
- Custom instructions: `~/.copilot/copilot-instructions.md`, `.github/copilot-instructions.md`, `AGENTS.md`, or `.github/instructions/**/*.instructions.md`.

**Suggested instruction once MCP is installed** (it replaces the curl block and keeps the token out of the prompt):

```markdown
# Keel decisions
When a task needs a typed branch (route, severity, edit/ask/stop) call the `keel_status` tool once; if enabled,
call `keel_decide` instead of guessing. Low confidence or noul near 0.5 → ask or escalate. "Keel on/off" → `keel_switch`.
```

## (b) VS Code Copilot agent mode

Docs: [Add MCP servers](https://code.visualstudio.com/docs/agent-customization/mcp-servers), [MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

Use either format.

**VS Code format.** The file is `.vscode/mcp.json` (workspace) or your profile `mcp.json`. It has a top-level `servers` key, uses `${env:NAME}` references, and accepts `${workspaceFolder}`:

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

If you'd rather be prompted for the token than read it from the environment, use `inputs`:

```json
{
  "inputs": [{ "type": "promptString", "id": "keel-token", "description": "Keel bearer", "password": true }],
  "servers": { "keel": { "type": "stdio", "command": "node",
    "args": ["${workspaceFolder}/mcp/keel-mcp-server.mjs"], "env": { "KEEL_TOKEN": "${input:keel-token}" } } }
}
```

VS Code does not forward servers that use `${input:...}` to Copilot harness sessions; use the env form for those.

**Portable format.** The file is `.mcp.json` at the workspace root with a top-level `mcpServers` key and `${KEEL_TOKEN}` references. It is the same file as Copilot CLI's per-repo config, so one file serves both clients.

**Policy layer:**
- `.github/agents/keel.agent.md` (custom agent, already present)
- `.github/copilot-instructions.md`
- `AGENTS.md`

You can also add the server through the Command Palette with **MCP: Add Server → Command (stdio)**.

## (c) Claude Code

Docs: [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp), [hooks guide](https://code.claude.com/docs/en/hooks-guide), [hooks reference](https://code.claude.com/docs/reference/hooks#pretooluse).

```shell
claude mcp add --env KEEL_TOKEN=$KEEL_TOKEN --transport stdio keel -- node /path/to/Keel/mcp/keel-mcp-server.mjs
# add --scope project to write .mcp.json, or --scope user for ~/.claude.json
```

Notes from the docs:
- Place an option such as `--transport stdio` between `--env` and the server name.
- Everything after `--` is passed to the server untouched.

**Project `.mcp.json`** (an entry without `type` is treated as stdio; `${VAR}` expansion is supported):

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

The tools appear as `mcp__keel__keel_decide`, `mcp__keel__keel_status` and `mcp__keel__keel_switch`.

**Policy layer:** put the "Keel decisions" paragraph above in `CLAUDE.md`, the project root file that Claude Code loads.

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

**Optional hook (pattern only, not shipped).** A `PreToolUse` command hook can POST the pending tool call to Keel as a `noul` ("is this destructive?") and return `{"permissionDecision": "ask"}` above a threshold. This is the strongest "Keel as gatekeeper" integration, but it puts Keel on every tool call. Treat it as opt-in.

## (d) OpenAI Codex CLI

Docs: [Codex MCP](https://developers.openai.com/codex/mcp), which redirects to the ChatGPT learn docs for the CLI surface.

```shell
codex mcp add keel --env KEEL_TOKEN=$KEEL_TOKEN -- node /path/to/Keel/mcp/keel-mcp-server.mjs
```

**`~/.codex/config.toml`** (or project `.codex/config.toml`, which applies to trusted projects only):

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

**Policy layer:** `AGENTS.md`. The repo already has one; add the "Keel decisions" paragraph. Codex also reads the server's MCP `instructions`.

## (e) Cursor

Docs: [Cursor MCP](https://cursor.com/docs/mcp).

Cursor reads `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global), with a top-level `mcpServers` key and `${env:NAME}` interpolation:

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

**Policy layer:** a project rule in `.cursor/rules/keel.mdc` (`alwaysApply: true`) or `AGENTS.md` containing the "Keel decisions" paragraph. We did not re-fetch the rules docs this session; check them at https://cursor.com/docs/context/rules.

---

## Variable syntax cheat sheet

| Client | File | Root key | Env reference |
|---|---|---|---|
| Copilot CLI | `~/.copilot/mcp-config.json`, `.mcp.json`, `.github/mcp.json` | `mcpServers` | `${NAME}` |
| VS Code | `.vscode/mcp.json` / profile | `servers` | `${env:NAME}`, `${input:id}` |
| VS Code (portable) | `.mcp.json` | `mcpServers` | `${NAME}`, `${NAME:-default}` |
| Claude Code | `.mcp.json`, `~/.claude.json` | `mcpServers` | `${NAME}`, `${NAME:-default}` |
| Codex CLI | `~/.codex/config.toml`, `.codex/config.toml` | `[mcp_servers.<name>]` | `env_vars = [...]` forwards |
| Cursor | `.cursor/mcp.json`, `~/.cursor/mcp.json` | `mcpServers` | `${env:NAME}` |

**One file, three clients:** a repo-root `.mcp.json` with `mcpServers` and `${KEEL_TOKEN}` is read by Copilot CLI, VS Code (portable format) and Claude Code. Ship that as the docs-phase default, plus `.vscode/mcp.json`, `.cursor/mcp.json` and a Codex TOML snippet.

## Follow-ups (not done)

- Add `"bin": {"keel-mcp": "mcp/keel-mcp-server.mjs"}` to `package.json` so `npx keel-mcp` works after the open-source publish.
- Optionally add `KEEL_AUTH_HEADER` so the same server can point at Jev or MSD1. MSD1 uses `api-key` and the path `/providers/microsoft/v1/systemone`.
