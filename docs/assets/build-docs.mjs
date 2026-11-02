// Generates docs/use-cases.md from docs/assets/use-cases.data.mjs.
// Run: node docs/assets/build-docs.mjs   (then: node docs/build-html.mjs)
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { groups, useCases } from "./use-cases.data.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, "..", "use-cases.md");

const typeName = { choice: "choice", score: "score", noul: "yes/no (noul)" };
const L = [];
L.push("# 50 use cases");
L.push("");
L.push("Fifty decisions that agents and apps make all day, each written as a complete System One request you can paste into `curl`. Every one of them is something a small local model can answer in milliseconds, so the LLM never sees it, or sees only the hard cases.");
L.push("");
L.push("Every use case maps to cases tagged `uc:<slug>` in the blind test suite (`src/lib/decider/eval-blind.ts`, `eval-blind-b.ts`), which no model was trained on. The list comes from `artifacts/parity/use-cases.md`; the source of this page is `docs/assets/use-cases.data.mjs`.");
L.push("");
L.push("## Read this first");
L.push("");
L.push("- **Measured savings, by workload.** On the held-out suites at confidence gate τ = 0.6, putting the Keel-3 RC in front of a dedicated LLM decision call cut visible LLM tokens by <!-- num:tok.k3.wl.gating -->100%<!-- /num --> for edit/ask/stop gating, <!-- num:tok.k3.wl.guardrail -->100%<!-- /num --> for guardrail yes/no questions, <!-- num:tok.k3.wl.routing -->80.1%<!-- /num --> for routing and triage, <!-- num:tok.k3.wl.moderation -->60.2%<!-- /num --> for moderation and <!-- num:tok.k3.wl.severity -->39%<!-- /num --> for severity scoring. The sample per workload is small (5 to 53 cases). See [Token savings](token-savings.md).");
L.push("- **The per-use-case token figures below are planning estimates, not measurements.** Each is the prompt plus answer an agent would otherwise send to an LLM for that one decision: a compact rubric of 150–300 tokens, the typical state, and 30–80 output tokens, with no chain of thought.");
L.push("- **Safety-critical use cases need a gate.** Where a wrong answer is harmful (marked *safety-critical*), act on Keel's answer only above a confidence threshold, and send everything else to an LLM or a human. Keel can tighten a gate; never let it alone approve a destructive action. See [Concepts](concepts.md#the-τ-gate-keel-first-llm-fallback).");
L.push("- Run any example against your local Keel with the key from [Quickstart, step 2](quickstart.md#2-get-your-local-key):");
L.push("");
L.push("```bash");
L.push("curl -s http://localhost:8080/api/v1/systemone -H \"Authorization: Bearer $KEEL_TOKEN\" \\");
L.push("  -H \"Content-Type: application/json\" -d @request.json");
L.push("```");
L.push("");
L.push("## Contents");
L.push("");
L.push("| Group | Use cases |");
L.push("|---|---|");
let n = 0;
const numbering = new Map();
for (const [g, name] of groups) {
  const items = useCases.filter((u) => u.g === g);
  const links = items.map((u) => {
    n += 1;
    numbering.set(u.slug, n);
    return `[${n}. ${u.title}](#${anchor(n, u.title)})`;
  });
  L.push(`| **${g}. ${name}** | ${links.join(" · ")} |`);
}
L.push("");

const safety = new Set(["coding-gate", "shell-guard", "ci-failure", "license", "incident-severity", "paging", "moderation", "pii", "secret", "prompt-injection", "jailbreak", "phishing", "data-class", "handoff", "refund", "answer-grading", "memory"]);

for (const [g, name, blurb] of groups) {
  L.push(`## ${g}. ${name}`);
  L.push("");
  L.push(blurb);
  L.push("");
  for (const u of useCases.filter((x) => x.g === g)) {
    const i = numbering.get(u.slug);
    L.push(`### ${i}. ${u.title}`);
    L.push("");
    const types = [...new Set(Object.values(u.q).map((q) => typeName[q.type]))].join(", ");
    L.push(`**Who:** ${u.who} **Type:** ${types}. **Blind-suite tag:** \`uc:${u.slug}\`${safety.has(u.slug) ? ". **Safety-critical.**" : "."}`);
    L.push("");
    L.push("```json");
    L.push(JSON.stringify({ model: "decider-latest", state: u.state, questions: u.q }, null, 2));
    L.push("```");
    L.push("");
    L.push(`**Act on it:** ${u.act}`);
    L.push("");
    L.push(`**LLM tokens avoided per decision (estimate):** ${u.tokens}.`);
    L.push("");
  }
}

L.push("## Writing your own");
L.push("");
L.push("- Put the facts in `state` and the rubric in `instructions` and `criteria`. Never put secrets in `state`.");
L.push("- Keep choice options mutually exclusive, and describe each one in a few concrete words. The descriptions become part of the hypothesis the model reads.");
L.push("- Order score levels from low to high. The answer is the expected level index and can be fractional.");
L.push("- Keep the deciding fact near the start of `state`. Keel reads about 256 tokens per (state, option) pair.");
L.push("- If your decision family is not covered well, fine-tune on it. See [Training guide](training-guide.md).");
L.push("");

function anchor(i, title) {
  return `${i}-${title}`.toLowerCase().replace(/[^\p{L}\p{N} -]/gu, "").trim().replace(/ /g, "-");
}

writeFileSync(out, L.join("\n"), "utf8");
console.log(`wrote ${out} (${useCases.length} use cases)`);
