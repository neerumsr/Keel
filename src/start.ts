import { createMiddleware, createStart } from "@tanstack/react-start";
import { isLoopbackHost, isServerFnPath } from "@/lib/loopback";

/**
 * Server functions (UI RPC, including `getCopilotSetup`, which returns the local bearer) answer
 * only requests addressed to a loopback Host, even when KEEL_HOST exposes the server on the
 * network. The bearer-protected `/api/v1/*` routes are unaffected.
 */
const loopbackServerFns = createMiddleware({ type: "request" }).server(({ request, next }) => {
  if (isServerFnPath(new URL(request.url).pathname) && !isLoopbackHost(request.headers.get("host"))) {
    return new Response("Forbidden: Keel's UI functions only answer on localhost.", {
      status: 403,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  return next();
});

export const startInstance = createStart(() => ({
  requestMiddleware: [loopbackServerFns],
}));
