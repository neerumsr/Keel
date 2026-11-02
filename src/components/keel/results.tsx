import { useState } from "react";
import { draftToBody, type Draft } from "@/lib/decider/presets";
import {
  branchSnippet,
  tryParse,
  type Answer,
  type GuardSettings,
  type SystemOneResponse,
} from "@/lib/decider/wire";

export function Results({
  draft,
  response,
  latencyMs,
  snapshot,
  stale,
  error,
  pending,
  onDecide,
}: {
  draft: Draft;
  response: SystemOneResponse | null;
  latencyMs: number | null;
  snapshot: string | null;
  stale: boolean;
  error: string | null;
  pending: boolean;
  onDecide: () => void;
}) {
  const [guards, setGuards] = useState<GuardSettings>({ noul: 0.5, confidence: 0.6 });
  const [snippet, setSnippet] = useState<"typescript" | "elixir">("typescript");

  const frozen = snapshot ? tryParse(JSON.parse(snapshot) as unknown) : null;
  const branch =
    response && frozen?.ok ? branchSnippet(frozen.request, response.answers, guards) : null;

  return (
    <aside className="min-w-0 lg:sticky lg:top-4 lg:self-start">
      <div className="rounded-md border border-line bg-sheet">
        <div className="flex items-baseline justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="font-serif text-xl">Answer</h2>
          {response ? (
            <p className="font-mono text-xs text-muted tabular-nums">
              {response.model}
              {latencyMs != null ? ` · ${(latencyMs / 1000).toFixed(1)}s` : ""}
              {" · "}
              {response.usage.input_tokens === 0 && response.usage.output_tokens === 0
                ? "local"
                : `${response.usage.input_tokens}+${response.usage.output_tokens} tok`}
            </p>
          ) : null}
        </div>

        <div className="flex flex-col gap-4 p-4">
          {pending ? <Waiting count={draft.questions.length} /> : null}
          {error ? (
            <p className="rounded-sm bg-copper-soft px-3 py-2 text-sm text-copper" role="alert">
              {error}
            </p>
          ) : null}
          {stale && response ? (
            <p className="text-xs text-muted">The bench changed after this answer. Decide again to refresh it.</p>
          ) : null}
          {!pending && !error && !response ? (
            <div className="py-6">
              <p className="text-sm leading-relaxed text-muted">
                Decisions land here. Nothing is called until you press Decide. A noul near 0.5 is a
                coin flip — branch on the probability, don’t pretend it was a boolean.
              </p>
            </div>
          ) : null}

          {response && frozen?.ok
            ? frozen.request.questions.map((question) => {
                const answer = response.answers[question.id];
                if (!answer) return null;
                return <AnswerBlock key={question.id} id={question.id} answer={answer} />;
              })
            : null}

          {branch ? (
            <div className="border-t border-line pt-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-medium">Guard</h3>
                <div className="flex rounded-sm border border-line p-0.5">
                  {(["typescript", "elixir"] as const).map((kind) => (
                    <button
                      key={kind}
                      type="button"
                      aria-pressed={snippet === kind}
                      onClick={() => setSnippet(kind)}
                      className={
                        "min-h-10 rounded-sm px-2 text-xs " +
                        (snippet === kind ? "bg-ink text-paper" : "text-muted")
                      }
                    >
                      {kind === "typescript" ? "TypeScript" : "Elixir"}
                    </button>
                  ))}
                </div>
              </div>
              <p className="mt-1 text-xs text-muted">
                Thresholds stay in your code. Moving them does not call the model again.
              </p>
              <label className="mt-3 block text-xs text-muted">
                Noul above {guards.noul.toFixed(2)}
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={guards.noul}
                  onChange={(event) => setGuards({ ...guards, noul: Number(event.target.value) })}
                  className="mt-1 w-full accent-copper"
                />
              </label>
              <label className="mt-2 block text-xs text-muted">
                Choice confidence at least {guards.confidence.toFixed(2)}
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={guards.confidence}
                  onChange={(event) =>
                    setGuards({ ...guards, confidence: Number(event.target.value) })
                  }
                  className="mt-1 w-full accent-copper"
                />
              </label>
              <pre className="mt-3 overflow-x-auto rounded-sm bg-paper p-3 font-mono text-xs leading-relaxed text-ink">
                {snippet === "typescript" ? branch.typescript : branch.elixir}
              </pre>
            </div>
          ) : null}
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-paper p-3 lg:hidden">
        <button
          type="button"
          onClick={onDecide}
          disabled={pending}
          className="flex min-h-12 w-full items-center justify-center rounded-md bg-copper text-sm font-medium text-paper disabled:opacity-60"
        >
          {pending ? "Judging…" : `Decide · ${draft.questions.length} questions`}
        </button>
      </div>
    </aside>
  );
}

function Waiting({ count }: { count: number }) {
  return (
    <div>
      <p className="text-sm">
        Judging {count} {count === 1 ? "question" : "questions"}.
      </p>
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-line">
        <div className="keel-wait h-full w-1/3 bg-copper" />
      </div>
    </div>
  );
}

function AnswerBlock({ id, answer }: { id: string; answer: Answer }) {
  if (answer.type === "noul") {
    const pct = Math.round(answer.noul * 1000) / 10;
    return (
      <section>
        <Header id={id} type="noul" />
        <p className="mt-1 font-serif text-3xl tabular-nums">{answer.noul.toFixed(2)}</p>
        <p className="text-xs text-muted">P(yes). No confidence field — the probability is the answer.</p>
        <Bar label="yes" value={answer.noul} note={`${pct}%`} />
      </section>
    );
  }

  if (answer.type === "choice") {
    return (
      <section>
        <Header id={id} type="choice" />
        <p className="mt-1 font-serif text-3xl">{answer.choice}</p>
        <p className="text-xs text-muted tabular-nums">confidence {answer.confidence.toFixed(2)}</p>
        <div className="mt-2 flex flex-col gap-2">
          {Object.entries(answer.probabilities).map(([key, value]) => (
            <Bar key={key} label={key} value={value} note={value.toFixed(2)} hot={key === answer.choice} />
          ))}
        </div>
      </section>
    );
  }

  const nearest = String(Math.round(answer.score));
  return (
    <section>
      <Header id={id} type="score" />
      <p className="mt-1 font-serif text-3xl tabular-nums">{answer.score.toFixed(2)}</p>
      <p className="text-xs text-muted">
        nearest rung {nearest}
        {answer.legend[nearest] ? ` · ${answer.legend[nearest]}` : ""} · confidence{" "}
        <span className="tabular-nums">{answer.confidence.toFixed(2)}</span>
      </p>
      <div className="mt-2 flex flex-col gap-2">
        {Object.entries(answer.probabilities).map(([key, value]) => (
          <Bar
            key={key}
            label={`${key} ${answer.legend[key] ?? ""}`}
            value={value}
            note={value.toFixed(2)}
          />
        ))}
      </div>
    </section>
  );
}

function Header({ id, type }: { id: string; type: string }) {
  return (
    <div className="flex items-center gap-2">
      <h3 className="font-mono text-sm">{id}</h3>
      <span className="rounded-sm bg-copper-soft px-1.5 py-0.5 text-xs text-copper">{type}</span>
    </div>
  );
}

function Bar({
  label,
  value,
  note,
  hot,
}: {
  label: string;
  value: number;
  note: string;
  hot?: boolean;
}) {
  const width = `${Math.max(0, Math.min(100, value * 100))}%`;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 text-xs">
        <span className={hot ? "font-medium text-ink" : "text-muted"}>{label}</span>
        <span className="font-mono text-muted tabular-nums">{note}</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-line">
        <div className={"h-full rounded-full " + (hot ? "bg-copper" : "bg-ink")} style={{ width }} />
      </div>
    </div>
  );
}
