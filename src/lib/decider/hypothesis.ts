/**
 * Keel-2 hypothesis spec. Every question becomes a group of (state, hypothesis)
 * pairs; the cross-encoder scores each pair and the group is normalized.
 * The Python trainer (training/keel/hypothesis.py) implements the same strings;
 * training/keel/test_hypothesis.py checks them against artifacts/hypothesis-fixtures.json.
 */
import type { NormalizedQuestion } from "./wire.ts";

export const HYPOTHESIS_VERSION = 1;

export function humanKey(key: string): string {
  return key.replace(/[_:-]+/g, " ").trim();
}

function join(instructions: string, answer: string, detail: string): string {
  const head = `${instructions.trim()} Answer: ${answer.trim()}.`;
  const tail = detail.trim();
  return tail ? `${head} ${tail}` : head;
}

/** Hypotheses in option order. Noul is always [yes, no]. */
export function hypotheses(question: NormalizedQuestion): string[] {
  if (question.type === "choice") {
    return question.options.map((option) => join(question.instructions, humanKey(option.key), option.description));
  }
  if (question.type === "score") {
    return question.levels.map((level) => join(question.instructions, level, ""));
  }
  return [join(question.instructions, "yes", question.yes), join(question.instructions, "no", question.no)];
}
