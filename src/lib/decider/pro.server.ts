/** Keel-Pro client: asks the loopback sidecar (serve/keel_pro_server.py) for option weights. Server-only. */
import type { DecisionRequest, WeightBag } from "./wire";

const DEFAULT_URL = "http://127.0.0.1:8090";
const TIMEOUT_MS = 30_000;

export function proSidecarUrl(): string {
  return (process.env.KEEL_PRO_URL || DEFAULT_URL).replace(/\/+$/, "");
}

/** The sidecar is a local process; refuse anything that would send decision state off the machine. */
export function isLoopbackUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname.replace(/^\[|\]$/g, "");
    return host === "127.0.0.1" || host === "localhost" || host === "::1";
  } catch {
    return false;
  }
}

/** Weights from Keel-Pro, or null when the sidecar is not configured, not running, or answers badly. */
export async function proWeights(
  request: DecisionRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<WeightBag | null> {
  const base = proSidecarUrl();
  if (!isLoopbackUrl(base)) return null;
  try {
    const res = await fetchImpl(`${base}/v1/weights`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state: request.state, questions: request.questions }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { weights?: unknown };
    const weights = body.weights;
    if (!weights || typeof weights !== "object" || Array.isArray(weights)) return null;
    for (const question of request.questions) {
      const bag = (weights as Record<string, unknown>)[question.id];
      if (!bag || typeof bag !== "object") return null;
    }
    return weights as WeightBag;
  } catch {
    return null;
  }
}
