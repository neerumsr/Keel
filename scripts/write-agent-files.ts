/**
 * Write the Copilot agent files for local use (origin http://localhost:8080).
 *
 *   node --experimental-strip-types scripts/write-agent-files.ts [--repo <path>] [--no-user]
 *
 *   node --experimental-strip-types scripts/write-agent-files.ts [--repo-key]   (embed the real bearer in repo files)
 *
 * Writes <repo>/.github/agents/keel.agent.md and <repo>/.github/copilot-instructions.md with a
 * <KEEL_TOKEN> placeholder (safe to commit), plus ~/.copilot/agents/keel.agent.md and the Keel block
 * of ~/.copilot/copilot-instructions.md with the real bearer. The bearer is derived from KEEL_SECRET
 * or the per-install secret in ~/.keel/secret, same as the running server.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { agentFile, instructionsFile } from "../src/lib/decider/agent-files.ts";
import { copilotKey } from "../src/lib/decider/auth.server.ts";

const args = process.argv.slice(2);
const repoFlag = args.indexOf("--repo");
const repo = path.resolve(repoFlag >= 0 ? args[repoFlag + 1]! : process.cwd());
const origin = process.env.KEEL_ORIGIN ?? "http://localhost:8080";
const key = copilotKey()!;

// Repo files are committed, so they carry a placeholder unless --repo-key is passed.
// User-level files (~/.copilot) carry the real per-install bearer.
const repoKey = args.includes("--repo-key") ? key : "<KEEL_TOKEN>";
const marker = "<!-- keel:start -->";

function write(file: string, text: string) {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, text);
  console.log(`wrote ${file}`);
}

function mergeInstructions(file: string, instructions: string) {
  const block = `${marker}\n${instructions}<!-- keel:end -->\n`;
  if (!existsSync(file)) return write(file, block);
  const current = readFileSync(file, "utf8");
  write(
    file,
    current.includes(marker)
      ? current.replace(/<!-- keel:start -->[\s\S]*?<!-- keel:end -->\n?/, block)
      : `${current.trimEnd()}\n\n${block}`,
  );
}

write(path.join(repo, ".github", "agents", "keel.agent.md"), agentFile(origin, repoKey));
mergeInstructions(path.join(repo, ".github", "copilot-instructions.md"), instructionsFile(origin, repoKey));

if (!args.includes("--no-user")) {
  const home = path.join(os.homedir(), ".copilot");
  write(path.join(home, "agents", "keel.agent.md"), agentFile(origin, key));
  mergeInstructions(path.join(home, "copilot-instructions.md"), instructionsFile(origin, key));
}
