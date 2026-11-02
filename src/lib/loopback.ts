/** Hostname part of a Host header value ("[::1]:8080" -> "::1", "localhost:8080" -> "localhost"). */
export function hostnameOf(hostHeader: string | null | undefined): string {
  const value = (hostHeader ?? "").trim().toLowerCase();
  if (value.startsWith("[")) {
    const end = value.indexOf("]");
    return end > 0 ? value.slice(1, end) : "";
  }
  const colon = value.indexOf(":");
  return colon === -1 ? value : value.slice(0, colon);
}

/**
 * True when the Host header names this machine's loopback interface. A Host check (rather than
 * the peer address) also defeats DNS rebinding, where a web page reaches the local port under
 * its own domain name.
 */
export function isLoopbackHost(hostHeader: string | null | undefined): boolean {
  const name = hostnameOf(hostHeader);
  if (name === "localhost" || name === "::1") return true;
  return /^127(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}$/.test(name);
}

export const SERVER_FN_BASE = "/_serverFn";

/** Server functions are the UI's private RPC (they include `getCopilotSetup`, which returns the bearer). */
export function isServerFnPath(pathname: string): boolean {
  return pathname === SERVER_FN_BASE || pathname.startsWith(`${SERVER_FN_BASE}/`);
}
