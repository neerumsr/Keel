/** Fifty fixed cases. No user text — safe to run as a latency comparison. */

export type SuiteCase = {
  id: number;
  name: string;
  body: {
    model: "decider-latest";
    state: string;
    questions: Record<string, unknown>;
  };
};

const SITUATIONS: { name: string; state: string }[] = [
  { name: "Double charge", state: "Charged twice for September. Will cancel Friday if not refunded." },
  { name: "Password reset", state: "Reset email never arrives. Cannot sign in." },
  { name: "Blank page", state: "Settings page is white after the last deploy. No error text." },
  { name: "SQL in name", state: "A profile name field echoes untrusted markup back into the admin list." },
  { name: "Docs typo", state: "README has a spelling mistake in one heading. No code change." },
  { name: "Missing spec", state: "Add logout. The user did not say where, and there are three settings pages." },
  { name: "Rewrite auth", state: "Replace the session helper so a client-supplied user id is trusted." },
  { name: "Calm refund", state: "Policy: duplicates are refunded. Customer: please refund the duplicate, thanks." },
  { name: "Angry no refund", state: "Policy: integration help is not a refund. Customer demands money back because Stripe will not connect." },
  { name: "Invoice seats", state: "Invoice lists two seats. Only one person can sign in." },
];

export const SUITE: SuiteCase[] = Array.from({ length: 50 }, (_, index) => {
  const seed = SITUATIONS[index % SITUATIONS.length]!;
  const state = `${seed.state} Case ${index + 1}.`;
  return {
    id: index + 1,
    name: `${index + 1}. ${seed.name}`,
    body: {
      model: "decider-latest",
      state,
      questions: {
        route: {
          type: "choice",
          instructions: "Which path fits this case?",
          criteria: {
            billing: "Money, invoices, refunds",
            bug: "Something is broken",
            account: "Login or permissions",
            technical: "Integration or outage",
            security: "Vulnerability or injection",
            edit: "Safe, specified change",
            ask: "A missing fact would change the action",
            stop: "Unsafe or out of scope",
          },
        },
        risk: {
          type: "score",
          instructions: "How risky is acting on this immediately?",
          criteria: ["Cosmetic", "Local and reversible", "Behavior change", "Data, auth, or secrets"],
        },
      },
    },
  };
});

export function summarize(samples: number[]): { n: number; median: number; p95: number; max: number; mean: number } {
  if (samples.length === 0) return { n: 0, median: 0, p95: 0, max: 0, mean: 0 };
  const sorted = samples.slice().sort((a, b) => a - b);
  const at = (p: number) => sorted[Math.min(sorted.length - 1, Math.round(p * (sorted.length - 1)))] ?? 0;
  const mean = sorted.reduce((sum, value) => sum + value, 0) / sorted.length;
  return { n: sorted.length, median: at(0.5), p95: at(0.95), max: sorted[sorted.length - 1] ?? 0, mean };
}
