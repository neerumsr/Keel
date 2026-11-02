import { useEffect, useState } from "react";
import { getKeelEnabled, setKeelEnabled } from "@/lib/decider/decide.functions";

export function KeelSwitch() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void getKeelEnabled()
      .then((value) => {
        if (!cancelled) setEnabled(value.enabled);
      })
      .catch(() => {
        if (!cancelled) setEnabled(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onFlip = (event: Event) => {
      const detail = (event as CustomEvent<boolean>).detail;
      if (typeof detail === "boolean") setEnabled(detail);
    };
    window.addEventListener("keel-switch", onFlip);
    return () => window.removeEventListener("keel-switch", onFlip);
  }, []);

  async function flip(next: boolean) {
    setBusy(true);
    try {
      const value = await setKeelEnabled({ data: { enabled: next } });
      setEnabled(value.enabled);
      window.dispatchEvent(new CustomEvent("keel-switch", { detail: value.enabled }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-1 rounded-md border border-line bg-sheet p-1" role="group" aria-label="Keel switch">
      <button
        type="button"
        aria-pressed={enabled === true}
        disabled={busy || enabled == null}
        onClick={() => void flip(true)}
        className={
          "min-h-11 rounded-sm px-3 text-sm font-medium " +
          (enabled === true ? "bg-ink text-paper" : "text-muted")
        }
      >
        Keel on
      </button>
      <button
        type="button"
        aria-pressed={enabled === false}
        disabled={busy || enabled == null}
        onClick={() => void flip(false)}
        className={
          "min-h-11 rounded-sm px-3 text-sm font-medium " +
          (enabled === false ? "bg-copper text-paper" : "text-muted")
        }
      >
        Keel off
      </button>
    </div>
  );
}
