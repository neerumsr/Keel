import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Bench } from "@/components/keel/bench";
import { Compare } from "@/components/keel/compare";
import { CopilotPanel } from "@/components/keel/copilot-panel";
import { KeelSwitch } from "@/components/keel/switch";

export const Route = createFileRoute("/")({
  component: Home,
});

type Tab = "bench" | "compare" | "copilot";

function Home() {
  const [tab, setTab] = useState<Tab>("bench");

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-paper">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Mark />
            <div>
              <p className="font-serif text-xl leading-none tracking-tight">Keel</p>
              <p className="mt-1 text-xs text-muted">Decision model · System One wire</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <KeelSwitch />
            <nav className="flex rounded-md border border-line bg-sheet p-1" aria-label="Sections">
              <TabButton current={tab} id="bench" onSelect={setTab}>
                Bench
              </TabButton>
              <TabButton current={tab} id="compare" onSelect={setTab}>
                Compare
              </TabButton>
              <TabButton current={tab} id="copilot" onSelect={setTab}>
                Copilot
              </TabButton>
            </nav>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 pb-28 sm:px-6 lg:pb-10">
        {tab === "bench" ? <Bench /> : null}
        {tab === "compare" ? <Compare /> : null}
        {tab === "copilot" ? <CopilotPanel /> : null}
      </main>
    </div>
  );
}

function TabButton({
  current,
  id,
  onSelect,
  children,
}: {
  current: Tab;
  id: Tab;
  onSelect: (id: Tab) => void;
  children: string;
}) {
  const selected = current === id;
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(id)}
      className={
        "min-h-11 rounded-sm px-3 text-sm font-medium " +
        (selected ? "bg-ink text-paper" : "text-ink")
      }
    >
      {children}
    </button>
  );
}

function Mark() {
  return (
    <svg viewBox="0 0 24 24" className="size-9 shrink-0" aria-hidden="true">
      <rect width="24" height="24" rx="4" className="fill-ink" />
      <path
        d="M6.5 17V7h2.3l3.2 6.1L15.2 7H17.5v10h-2v-6.1L12.2 17h-1.1L8.5 10.9V17H6.5z"
        className="fill-paper"
      />
    </svg>
  );
}
