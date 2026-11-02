import { useState } from "react";
import { runDecision, setKeelEnabled } from "@/lib/decider/decide.functions";
import { SUITE, summarize } from "@/lib/decider/suite";

type Row = { id: number; name: string; ms: number; note: string };

export function Compare() {
  const [mode, setMode] = useState<"on" | "off" | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [done, setDone] = useState<"on" | "off" | null>(null);
  const [onStats, setOnStats] = useState<ReturnType<typeof summarize> | null>(null);
  const [offStats, setOffStats] = useState<ReturnType<typeof summarize> | null>(null);

  const running = mode != null && done !== mode;
  const stats = summarize(rows.map((row) => row.ms));

  async function run(next: "on" | "off") {
    setMode(next);
    setDone(null);
    setRows([]);
    const collected: Row[] = [];
    if (next === "on") {
      await setKeelEnabled({ data: { enabled: true } });
      window.dispatchEvent(new CustomEvent("keel-switch", { detail: true }));
    }
    for (const item of SUITE) {
      const started = performance.now();
      if (next === "off") {
        const ms = Math.round(performance.now() - started);
        collected.push({ id: item.id, name: item.name, ms, note: "skipped — Keel off, no model call" });
      } else {
        try {
          const result = await runDecision({ data: item.body });
          const ms = result.ok ? result.latency_ms : Math.round(performance.now() - started);
          const note = result.ok
            ? winner(result.body.answers)
            : result.body.error.message;
          collected.push({ id: item.id, name: item.name, ms, note });
        } catch {
          collected.push({
            id: item.id,
            name: item.name,
            ms: Math.round(performance.now() - started),
            note: "call failed",
          });
        }
      }
      setRows(collected.slice());
    }
    const summary = summarize(collected.map((row) => row.ms));
    if (next === "on") setOnStats(summary);
    else setOffStats(summary);
    setDone(next);
    setMode(null);
  }

  const added =
    onStats && offStats ? Math.max(0, Math.round(onStats.median - offStats.median)) : null;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <div>
        <p className="text-xs font-medium tracking-wide text-copper uppercase">Compare</p>
        <h1 className="mt-1 font-serif text-3xl tracking-tight text-balance">Fifty cases, Keel on and off.</h1>
        <p className="mt-2 text-sm leading-relaxed text-pretty text-muted">
          Off does not run the model, which is what Copilot should do after you say “Keel off”. On
          runs the local model once per case. The gap is the time Keel adds. This is not a comparison
          with TypeSafe Jev, and it does not measure whether Copilot’s edits get worse.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={running}
          onClick={() => void run("on")}
          className="min-h-11 rounded-md bg-ink px-4 text-sm font-medium text-paper disabled:opacity-50"
        >
          {mode === "on" ? `On ${rows.length}/50` : "Run 50 with Keel on"}
        </button>
        <button
          type="button"
          disabled={running}
          onClick={() => void run("off")}
          className="min-h-11 rounded-md border border-line bg-sheet px-4 text-sm disabled:opacity-50"
        >
          {mode === "off" ? `Off ${rows.length}/50` : "Run 50 with Keel off"}
        </button>
      </div>
      <p className="text-xs text-muted">
        The on run turns the switch on. Both runs stay on this machine. The off run leaves the
        switch as it is and does not run the model.
      </p>
      {onStats || offStats ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="On, median" value={onStats ? seconds(onStats.median) : "—"} />
          <Stat label="Off, median" value={offStats ? seconds(offStats.median) : "—"} />
          <Stat label="Added by Keel" value={added == null ? "—" : seconds(added)} />
        </div>
      ) : null}
      {rows.length > 0 ? (
        <div className="overflow-hidden rounded-md border border-line bg-sheet">
          <p className="border-b border-line px-3 py-2 font-mono text-xs text-muted tabular-nums">
            {done ? "done" : "running"} · median {seconds(stats.median)} · p95 {seconds(stats.p95)} · max{" "}
            {seconds(stats.max)}
          </p>
          <ul className="max-h-96 overflow-auto">
            {rows.map((row) => (
              <li key={row.id} className="flex gap-3 border-b border-line px-3 py-2 text-sm last:border-0">
                <span className="w-16 shrink-0 font-mono text-xs text-muted tabular-nums">{seconds(row.ms)}</span>
                <span className="min-w-0">
                  <span className="font-medium">{row.name}</span>
                  <span className="mt-0.5 block truncate text-xs text-muted">{row.note}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-md border border-line bg-sheet p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 font-serif text-2xl tabular-nums">{value}</p>
    </article>
  );
}

function seconds(ms: number): string {
  return `${(ms / 1000).toFixed(2)}s`;
}

function winner(answers: Record<string, { type: string; choice?: string; score?: number; noul?: number }>): string {
  const route = answers.route;
  if (route?.type === "choice" && route.choice) return `route ${route.choice}`;
  return "answered";
}
