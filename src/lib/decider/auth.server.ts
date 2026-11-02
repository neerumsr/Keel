import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const PURPOSE = "keel-local-decider-v1";

/** Per-install secret file: KEEL_SECRET_FILE, else ~/.keel/secret. */
export function secretFilePath(): string {
  return process.env.KEEL_SECRET_FILE?.trim() || path.join(os.homedir(), ".keel", "secret");
}

let cachedFileSecret: string | null = null;

/** KEEL_SECRET wins; otherwise a random secret generated once per install and kept outside the repo. */
function localSecret(): string {
  const fromEnv = process.env.KEEL_SECRET?.trim();
  if (fromEnv) return fromEnv;
  if (cachedFileSecret) return cachedFileSecret;
  const file = secretFilePath();
  if (existsSync(file)) {
    const stored = readFileSync(file, "utf8").trim();
    if (stored) return (cachedFileSecret = stored);
  }
  const fresh = randomBytes(32).toString("base64url");
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, `${fresh}\n`, { mode: 0o600 });
  try {
    chmodSync(file, 0o600);
  } catch {
    // Best effort on filesystems without POSIX modes.
  }
  return (cachedFileSecret = fresh);
}

/** Local bearer for agents, derived from the per-install secret. Never an API key. */
export function copilotKey(): string | null {
  return createHmac("sha256", localSecret()).update(PURPOSE).digest("base64url").slice(0, 40);
}

function matchesKey(token: string): boolean {
  const expected = copilotKey();
  if (!expected || !token) return false;
  const got = Buffer.from(token);
  const want = Buffer.from(expected);
  if (got.length !== want.length) return false;
  return timingSafeEqual(got, want);
}

export function authorizeBearer(header: string | null): boolean {
  if (!header) return false;
  const match = /^Bearer\s+(\S+)\s*$/i.exec(header);
  return match ? matchesKey(match[1]!) : false;
}

/**
 * Decision calls only: Bearer, or the same key in an `api-key` header (Microsoft Foundry key auth).
 * The switch stays Bearer-only.
 */
export function authorizeDecision(headers: Headers): boolean {
  if (authorizeBearer(headers.get("authorization"))) return true;
  const apiKey = headers.get("api-key")?.trim();
  return apiKey ? matchesKey(apiKey) : false;
}
