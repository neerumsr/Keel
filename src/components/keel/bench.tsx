import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import { Results } from "@/components/keel/results";
import { runDecision } from "@/lib/decider/decide.functions";
import { PRESETS, draftToBody, emptyQuestion, type Draft, type DraftQuestion } from "@/lib/decider/presets";
import { tryParse, type SystemOneResponse } from "@/lib/decider/wire";

const DRAFT_KEY = "keel-draft";

export function Bench() {
  const [draft, setDraft] = useState<Draft>(PRESETS[0]!);
  const [ready, setReady] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SystemOneResponse | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [snapshot, setSnapshot] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(DRAFT_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as Partial<Draft>;
        if (parsed.questions?.length && typeof parsed.state === "string") {
          setDraft({
            name: parsed.name || "Custom",
            state: parsed.state,
            questions: parsed.questions.map((question, index) => ({
              ...emptyQuestion(index + 1),
              ...question,
              uid: question.uid || `restored-${index}`,
            })),
          });
        }
      }
    } catch {
      /* keep the triage preset */
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch {
      /* private mode */
    }
  }, [draft, ready]);

  async function decide() {
    const body = draftToBody(draft);
    const parsed = tryParse(body);
    if (!parsed.ok) {
      setError(parsed.message);
      setResponse(null);
      setLatencyMs(null);
      setSnapshot(null);
      return;
    }
    setPending(true);
    setError(null);
    try {
      const result = await runDecision({ data: body });
      if (!result.ok) {
        setResponse(null);
        setLatencyMs(null);
        setSnapshot(null);
        setError(result.body.error.message);
      } else {
        setResponse(result.body);
        setLatencyMs(result.latency_ms);
        setSnapshot(JSON.stringify(body));
      }
    } catch {
      setError("The decision call did not complete.");
      setResponse(null);
      setLatencyMs(null);
      setSnapshot(null);
    } finally {
      setPending(false);
    }
  }

  const stale = snapshot != null && snapshot !== JSON.stringify(draftToBody(draft));

  return (
    <div className="grid min-w-0 gap-6 lg:grid-cols-2">
      <section className="flex min-w-0 flex-col gap-5">
        <div>
          <p className="text-xs font-medium tracking-wide text-copper uppercase">Bench</p>
          <h1 className="mt-1 font-serif text-3xl tracking-tight text-balance">
            Ask typed questions of one state.
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-pretty text-muted">
            Choice picks a label. Score sits on a ladder and may land between rungs. Noul is the
            probability the statement is true. They are judged together, in parallel, and the answer
            is something your code can branch on.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.name}
              type="button"
              onClick={() => {
                setDraft(preset);
                setResponse(null);
                setLatencyMs(null);
                setSnapshot(null);
                setError(null);
              }}
              className={
                "min-h-11 rounded-md border px-3 text-sm " +
                (draft.name === preset.name
                  ? "border-ink bg-ink text-paper"
                  : "border-line bg-sheet text-ink")
              }
            >
              {preset.name}
            </button>
          ))}
        </div>

        <label className="block">
          <span className="text-sm font-medium">State</span>
          <textarea
            value={draft.state}
            onChange={(event) => setDraft({ ...draft, name: "Custom", state: event.target.value })}
            spellCheck={false}
            className="mt-2 min-h-40 w-full resize-y rounded-md border border-line bg-sheet p-3 font-mono text-sm leading-relaxed text-ink"
          />
        </label>

        <div className="flex flex-col gap-3">
          {draft.questions.map((question, index) => (
            <QuestionCard
              key={question.uid || `q-${index}`}
              question={question}
              canRemove={draft.questions.length > 1}
              onChange={(next) => {
                const questions = draft.questions.slice();
                questions[index] = next;
                setDraft({ ...draft, name: "Custom", questions });
              }}
              onRemove={() => {
                const questions = draft.questions.filter((_, i) => i !== index);
                setDraft({ ...draft, name: "Custom", questions });
              }}
              onMove={(dir) => {
                const target = index + dir;
                if (target < 0 || target >= draft.questions.length) return;
                const questions = draft.questions.slice();
                const item = questions[index];
                if (!item) return;
                questions.splice(index, 1);
                questions.splice(target, 0, item);
                setDraft({ ...draft, name: "Custom", questions });
              }}
            />
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() =>
              setDraft({
                ...draft,
                name: "Custom",
                questions: [...draft.questions, emptyQuestion(draft.questions.length + 1)],
              })
            }
            disabled={draft.questions.length >= 8}
            className="inline-flex min-h-11 items-center gap-2 rounded-md border border-line bg-sheet px-3 text-sm disabled:opacity-40"
          >
            <Plus className="size-4" aria-hidden="true" />
            Add question
          </button>
          <button
            type="button"
            onClick={() => void decide()}
            disabled={pending}
            className="inline-flex min-h-11 items-center rounded-md bg-copper px-4 text-sm font-medium text-paper disabled:opacity-60"
          >
            {pending ? "Judging…" : "Decide"}
          </button>
        </div>
        <p className="text-xs leading-relaxed text-muted">
          Judged on this machine. No API key and no network call. Eight questions maximum. The model
          only sees the state you write here.
        </p>
      </section>

      <Results
        draft={draft}
        response={response}
        latencyMs={latencyMs}
        snapshot={snapshot}
        stale={stale}
        error={error}
        pending={pending}
        onDecide={() => void decide()}
      />
    </div>
  );
}

function QuestionCard({
  question,
  canRemove,
  onChange,
  onRemove,
  onMove,
}: {
  question: DraftQuestion;
  canRemove: boolean;
  onChange: (next: DraftQuestion) => void;
  onRemove: () => void;
  onMove: (dir: -1 | 1) => void;
}) {
  return (
    <article className="min-w-0 rounded-md border border-line bg-sheet p-3">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1">
          <label className="min-w-0 flex-1">
            <span className="sr-only">Question id</span>
            <input
              value={question.id}
              onChange={(event) => onChange({ ...question, id: event.target.value.trim() })}
              className="w-full min-w-0 rounded-sm border border-line bg-paper px-2 py-2 font-mono text-sm"
              aria-label="Question id"
            />
          </label>
          <button
            type="button"
            className="inline-flex size-11 shrink-0 items-center justify-center"
            onClick={() => onMove(-1)}
            aria-label="Move question up"
          >
            <ChevronUp className="size-4" aria-hidden="true" />
          </button>
          <button
            type="button"
            className="inline-flex size-11 shrink-0 items-center justify-center"
            onClick={() => onMove(1)}
            aria-label="Move question down"
          >
            <ChevronDown className="size-4" aria-hidden="true" />
          </button>
          {canRemove ? (
            <button
              type="button"
              className="inline-flex size-11 shrink-0 items-center justify-center text-copper"
              onClick={onRemove}
              aria-label="Remove question"
            >
              <Trash2 className="size-4" aria-hidden="true" />
            </button>
          ) : null}
        </div>
        <TypeSwitch value={question.type} onChange={(type) => onChange({ ...question, type })} />
      </div>
      <label className="mt-3 block">
        <span className="text-xs text-muted">Instructions</span>
        <textarea
          value={question.instructions}
          onChange={(event) => onChange({ ...question, instructions: event.target.value })}
          className="mt-1 min-h-16 w-full resize-y rounded-sm border border-line bg-paper px-2 py-2 text-sm"
        />
      </label>
      {question.type === "choice" ? <OptionEditor question={question} onChange={onChange} /> : null}
      {question.type === "score" ? <LevelEditor question={question} onChange={onChange} /> : null}
      {question.type === "noul" ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <Field label="True means" value={question.yes} onChange={(yes) => onChange({ ...question, yes })} />
          <Field label="False means" value={question.no} onChange={(no) => onChange({ ...question, no })} />
        </div>
      ) : null}
    </article>
  );
}

function TypeSwitch({
  value,
  onChange,
}: {
  value: DraftQuestion["type"];
  onChange: (type: DraftQuestion["type"]) => void;
}) {
  const types: DraftQuestion["type"][] = ["choice", "score", "noul"];
  return (
    <div className="flex rounded-sm border border-line p-0.5" role="group" aria-label="Question type">
      {types.map((type) => (
        <button
          key={type}
          type="button"
          aria-pressed={value === type}
          onClick={() => onChange(type)}
          className={
            "min-h-10 rounded-sm px-2 text-xs font-medium " +
            (value === type ? "bg-copper-soft text-copper" : "text-muted")
          }
        >
          {type}
        </button>
      ))}
    </div>
  );
}

function OptionEditor({
  question,
  onChange,
}: {
  question: DraftQuestion;
  onChange: (next: DraftQuestion) => void;
}) {
  function update(index: number, patch: Partial<DraftQuestion["options"][number]>) {
    const options = question.options.slice();
    const current = options[index];
    if (!current) return;
    options[index] = { ...current, ...patch };
    onChange({ ...question, options });
  }
  return (
    <div className="mt-3 flex flex-col gap-2">
      {question.options.map((option, index) => (
        <div key={`${question.uid}-opt-${index}`} className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            value={option.key}
            aria-label={`Option ${index + 1} key`}
            onChange={(event) => update(index, { key: event.target.value.trim() })}
            className="w-full min-w-0 rounded-sm border border-line bg-paper px-2 py-2 font-mono text-xs sm:w-28 sm:shrink-0"
          />
          <input
            value={option.description}
            aria-label={`Option ${option.key || index + 1} description`}
            onChange={(event) => update(index, { description: event.target.value })}
            className="w-full min-w-0 flex-1 rounded-sm border border-line bg-paper px-2 py-2 text-sm"
          />
          <button
            type="button"
            aria-label={`Remove option ${option.key || index + 1}`}
            disabled={question.options.length <= 2}
            onClick={() =>
              onChange({ ...question, options: question.options.filter((_, i) => i !== index) })
            }
            className="inline-flex size-11 shrink-0 items-center justify-center disabled:opacity-30"
          >
            <Trash2 className="size-4" aria-hidden="true" />
          </button>
        </div>
      ))}
      <button
        type="button"
        disabled={question.options.length >= 12}
        onClick={() =>
          onChange({
            ...question,
            options: [
              ...question.options,
              { key: `option_${question.options.length + 1}`, description: "" },
            ],
          })
        }
        className="self-start py-2 text-sm text-copper disabled:opacity-40"
      >
        Add option
      </button>
    </div>
  );
}

function LevelEditor({
  question,
  onChange,
}: {
  question: DraftQuestion;
  onChange: (next: DraftQuestion) => void;
}) {
  return (
    <div className="mt-3 flex flex-col gap-2">
      <p className="text-xs text-muted">
        Ordered from 0. The score is the expected rung, so it can fall between these.
      </p>
      {question.levels.map((level, index) => (
        <div key={`${question.uid}-lvl-${index}`} className="flex items-center gap-2">
          <span className="w-6 shrink-0 font-mono text-xs text-muted tabular-nums">{index}</span>
          <input
            value={level}
            aria-label={`Level ${index}`}
            onChange={(event) => {
              const levels = question.levels.slice();
              levels[index] = event.target.value;
              onChange({ ...question, levels });
            }}
            className="min-w-0 flex-1 rounded-sm border border-line bg-paper px-2 py-2 text-sm"
          />
          <button
            type="button"
            aria-label={`Remove level ${index}`}
            disabled={question.levels.length <= 2}
            onClick={() =>
              onChange({ ...question, levels: question.levels.filter((_, i) => i !== index) })
            }
            className="inline-flex size-11 shrink-0 items-center justify-center disabled:opacity-30"
          >
            <Trash2 className="size-4" aria-hidden="true" />
          </button>
        </div>
      ))}
      <button
        type="button"
        disabled={question.levels.length >= 10}
        onClick={() => onChange({ ...question, levels: [...question.levels, ""] })}
        className="self-start py-2 text-sm text-copper disabled:opacity-40"
      >
        Add level
      </button>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs text-muted">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-sm border border-line bg-paper px-2 py-2 text-sm"
      />
    </label>
  );
}
