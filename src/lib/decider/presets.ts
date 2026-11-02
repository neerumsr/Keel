export type DraftOption = { key: string; description: string };

export type DraftQuestion = {
  uid: string;
  id: string;
  type: "choice" | "score" | "noul";
  instructions: string;
  options: DraftOption[];
  levels: string[];
  yes: string;
  no: string;
};

export type Draft = {
  name: string;
  state: string;
  questions: DraftQuestion[];
};

export function emptyQuestion(index: number): DraftQuestion {
  return {
    uid: `q-${index}-${Math.random().toString(36).slice(2, 8)}`,
    id: `question_${index}`,
    type: "choice",
    instructions: "",
    options: [
      { key: "yes", description: "" },
      { key: "no", description: "" },
    ],
    levels: ["Low", "High"],
    yes: "",
    no: "",
  };
}

function q(
  uid: string,
  id: string,
  type: DraftQuestion["type"],
  instructions: string,
  extra: Partial<Pick<DraftQuestion, "options" | "levels" | "yes" | "no">> = {},
): DraftQuestion {
  return {
    uid,
    id,
    type,
    instructions,
    options: extra.options ?? [],
    levels: extra.levels ?? [],
    yes: extra.yes ?? "",
    no: extra.no ?? "",
  };
}

export const PRESETS: Draft[] = [
  {
    name: "Triage",
    state: [
      "{",
      '  "title": "Checkout charges the card twice",',
      '  "body": "Customer was charged twice for September and says they will cancel Friday unless it is refunded. Login also times out on the invoice page.",',
      '  "plan": "team",',
      '  "labels": ["billing", "urgent"]',
      "}",
    ].join("\n"),
    questions: [
      q("triage-kind", "kind", "choice", "What kind of issue is this?", {
        options: [
          { key: "billing", description: "Charges, invoices, refunds, seats" },
          { key: "bug", description: "Something in the product is broken" },
          { key: "account", description: "Login, permissions, or profile" },
        ],
      }),
      q("triage-severity", "severity", "score", "How severe is this for the customer?", {
        levels: ["Cosmetic", "Workaround exists", "Blocks the task", "Data loss or about to churn"],
      }),
      q("triage-security", "security", "noul", "Does this describe a vulnerability?", {
        yes: "Unauthorized access, injection, leaked secrets, or a trust-boundary bug",
        no: "Ordinary product or billing trouble",
      }),
    ],
  },
  {
    name: "Refund",
    state: [
      "Customer: I've been trying to connect Stripe for 3 days and it keeps failing. I'm losing sales. I want the last invoice refunded.",
      "Policy: Duplicate charges are refunded in full. Integration help is not a refund. Refunds after 30 days need a manager.",
    ].join("\n\n"),
    questions: [
      q("refund-dept", "department", "choice", "Which team should handle the message?", {
        options: [
          { key: "billing", description: "Charges, invoices, refunds, subscriptions" },
          { key: "technical", description: "Bugs, integrations, outages" },
          { key: "account", description: "Login, profile, permissions" },
        ],
      }),
      q(
        "refund-yes",
        "refund",
        "noul",
        "Does the customer explicitly ask for money back, and does policy allow it?",
        {
          yes: "They ask for a refund and the policy covers this case",
          no: "They want help, or the policy does not cover a refund",
        },
      ),
      q("refund-heat", "frustration", "score", "How frustrated does the customer appear?", {
        levels: [
          "Calm and matter-of-fact",
          "Frustrated but civil",
          "Very angry, or threatening to leave",
        ],
      }),
    ],
  },
  {
    name: "Pull request",
    state: [
      "diff: auth middleware now trusts a client-supplied user id when the session cookie is missing.",
      "tests: none added.",
      "author: a new contributor.",
    ].join("\n"),
    questions: [
      q("pr-verdict", "verdict", "choice", "What should the reviewer do with this change?", {
        options: [
          { key: "approve", description: "Safe to merge as written" },
          { key: "request_changes", description: "Needs a specific fix first" },
          { key: "block", description: "Security or data-loss risk; do not merge" },
        ],
      }),
      q("pr-risk", "risk", "score", "How risky is this diff?", {
        levels: ["Comment or docs", "Local behavior", "Auth, billing, or data", "Remote code or secret exposure"],
      }),
      q("pr-tests", "needs_tests", "noul", "Does this change need a test before merge?", {
        yes: "Behavior, auth, or data handling changed and tests do not cover it",
        no: "No behavior change, or tests already cover it",
      }),
    ],
  },
  {
    name: "Copilot step",
    state: [
      "Task: add a logout button to the settings page.",
      "Repo notes: settings is src/routes/settings.tsx. Session helpers live in src/lib/auth and must not be rewritten.",
      "The user did not mention design changes.",
    ].join("\n"),
    questions: [
      q("step-action", "action", "choice", "What should the coding agent do next?", {
        options: [
          { key: "edit", description: "The change is specified enough to implement" },
          { key: "ask", description: "A missing fact would change the edit" },
          { key: "stop", description: "Unsafe, out of scope, or would rewrite protected code" },
        ],
      }),
      q("step-risk", "risk", "score", "How risky is proceeding with an edit?", {
        levels: ["Cosmetic", "Local and reversible", "Behavior change", "Data, auth, or secrets"],
      }),
      q("step-tests", "tests", "noul", "Should the agent add or update a test for this step?", {
        yes: "The edit changes behavior a test could lock",
        no: "Copy, comments, or a change that existing tests already cover",
      }),
    ],
  },
];

export function draftToBody(draft: Draft): unknown {
  const questions: Record<string, unknown> = {};
  for (const question of draft.questions) {
    if (question.type === "choice") {
      const criteria: Record<string, string | null> = {};
      for (const option of question.options) {
        criteria[option.key] = option.description.trim() ? option.description.trim() : null;
      }
      questions[question.id] = {
        type: "choice",
        instructions: question.instructions.trim(),
        criteria,
      };
    } else if (question.type === "score") {
      questions[question.id] = {
        type: "score",
        instructions: question.instructions.trim(),
        criteria: question.levels.map((level) => level.trim()).filter(Boolean),
      };
    } else {
      const criteria: Record<string, string> = {};
      if (question.yes.trim()) criteria.true = question.yes.trim();
      if (question.no.trim()) criteria.false = question.no.trim();
      questions[question.id] = {
        type: "noul",
        instructions: question.instructions.trim(),
        ...(Object.keys(criteria).length ? { criteria } : {}),
      };
    }
  }
  let state: unknown = draft.state;
  const trimmed = draft.state.trim();
  if (
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      state = JSON.parse(trimmed) as unknown;
    } catch {
      state = draft.state;
    }
  }
  return { model: "decider-latest", state, questions };
}
