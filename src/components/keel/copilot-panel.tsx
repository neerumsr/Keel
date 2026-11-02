import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { agentFile, instructionsFile } from "@/lib/decider/agent-files";
import { getCopilotSetup } from "@/lib/decider/decide.functions";

export function CopilotPanel() {
  const [setup, setSetup] = useState<{ key: string | null; model: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getCopilotSetup()
      .then((value) => {
        if (!cancelled) setSetup({ key: value.key, model: value.model });
      })
      .catch(() => {
        if (!cancelled) setError("Could not prepare the Copilot key.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const origin = typeof window === "undefined" ? "" : window.location.origin;
  const key = setup?.key ?? "";
  const agent = key ? agentFile(origin, key) : "";
  const instructions = key ? instructionsFile(origin, key) : "";

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <p className="text-xs font-medium tracking-wide text-copper uppercase">Copilot</p>
        <h1 className="mt-1 font-serif text-3xl tracking-tight text-balance">
          The same decision, inside VS Code and the Copilot CLI.
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-pretty text-muted">
          Keel is a local decision model. It speaks the same wire as TypeSafe Jev
          (<span className="font-mono text-xs">POST /api/v1/systemone</span>) and returns{" "}
          <span className="font-mono text-xs">{setup?.model ?? "decider-3.0.0"}</span>.{" "}
          <span className="font-mono text-xs">jev-latest</span> is an alias. Nothing here calls an API
          or needs an xAI key.
        </p>
      </div>

      {error ? (
        <p className="rounded-sm bg-copper-soft px-3 py-2 text-sm text-copper" role="alert">
          {error}
        </p>
      ) : null}

      {!setup && !error ? <p className="text-sm text-muted">Preparing the Copilot key…</p> : null}

      {setup && !setup.key ? (
        <p className="rounded-sm bg-copper-soft px-3 py-2 text-sm text-copper" role="status">
          Decisions are unavailable in this environment, so there is no key to give Copilot.
        </p>
      ) : null}

      {key ? (
        <>
          <CopyBlock
            title="VS Code"
            path=".github/agents/keel.agent.md"
            detail="Also picked up by Copilot on GitHub. In chat, choose the Keel agent before an ambiguous edit."
            text={agent}
          />
          <CopyBlock
            title="Copilot CLI"
            path="~/.copilot/agents/keel.agent.md"
            detail="Same file, user scope. In the CLI, run /agent and select Keel. A repo copy at .github/agents/ works too."
            text={agent}
          />
          <CopyBlock
            title="Always on"
            path=".github/copilot-instructions.md"
            detail="Short instructions so every Copilot session in the repo knows when to call Keel."
            text={instructions}
          />
          <section className="rounded-md border border-line bg-sheet p-4">
            <h2 className="font-serif text-xl">In VS Code</h2>
            <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-muted">
              <li>On your machine, in this project: <span className="font-mono text-xs text-ink">npm install</span> then <span className="font-mono text-xs text-ink">npm run dev</span>. It listens on port 8080. No API key.</li>
              <li>Open http://localhost:8080, copy the files, and save them in the repo you have open as <span className="font-mono text-xs text-ink">.github/agents/keel.agent.md</span> and <span className="font-mono text-xs text-ink">.github/copilot-instructions.md</span>.</li>
              <li>In Copilot chat or the CLI, choose the Keel agent. Say “Keel off” or “Keel on”. That hits the switch on your machine.</li>
            </ol>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              Keel is not a VS Code extension. Run this app on your machine and point Copilot at it.
              There is no API key. The bearer below only proves the request came from your Copilot
              config. Set KEEL_SECRET in the environment if you want a different one.
            </p>
            <p className="mt-3 text-xs leading-relaxed text-muted">
              From the project directory: npm install, then npm run dev. The app listens on port 8080.
              Copy the files again after that so the address is http://localhost:8080.
            </p>
            <code className="mt-3 block overflow-x-auto rounded-sm bg-paper p-3 font-mono text-xs break-all">
              Authorization: Bearer {key}
            </code>
          </section>
        </>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-3">
        <Fact title="Choice" body="Returns the winning key, a probability for every key, and a confidence." />
        <Fact title="Score" body="Returns an expected rung. 2.4 means between level 2 and level 3." />
        <Fact title="Noul" body="Returns P(yes) only. You pick the threshold. Near 0.5, don’t act." />
      </section>
    </div>
  );
}

function Fact({ title, body }: { title: string; body: string }) {
  return (
    <article className="rounded-md border border-line bg-sheet p-3">
      <h2 className="font-serif text-lg">{title}</h2>
      <p className="mt-1 text-sm leading-relaxed text-muted">{body}</p>
    </article>
  );
}

function CopyBlock({
  title,
  path,
  detail,
  text,
}: {
  title: string;
  path: string;
  detail: string;
  text: string;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <section className="rounded-md border border-line bg-sheet">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <h2 className="font-serif text-xl">{title}</h2>
          <p className="mt-1 font-mono text-xs text-copper">{path}</p>
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-muted">{detail}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            void navigator.clipboard.writeText(text).then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1600);
            });
          }}
          className="inline-flex min-h-11 items-center gap-2 rounded-md border border-line bg-paper px-3 text-sm"
        >
          {copied ? <Check className="size-4" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
          {copied ? "Copied" : "Copy file"}
        </button>
      </div>
      <pre className="max-h-72 overflow-auto p-4 font-mono text-xs leading-relaxed text-ink">{text}</pre>
    </section>
  );
}
