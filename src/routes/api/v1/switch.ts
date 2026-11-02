import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/v1/switch")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { authorizeBearer } = await import("@/lib/decider/auth.server");
        if (!authorizeBearer(request.headers.get("authorization"))) {
          return Response.json(
            { error: { type: "unauthorized", message: "Bearer required." } },
            { status: 401, headers: { "Cache-Control": "no-store" } },
          );
        }
        let body: unknown;
        try {
          body = await request.json();
        } catch {
          return Response.json(
            { error: { type: "invalid_request", message: "Body must be JSON." } },
            { status: 400 },
          );
        }
        const enabled = (body as { enabled?: unknown }).enabled;
        if (typeof enabled !== "boolean") {
          return Response.json(
            { error: { type: "invalid_request", message: 'Send {"enabled": true} or {"enabled": false}.' } },
            { status: 400 },
          );
        }
        const { writeEnabled } = await import("@/lib/decider/switch.server");
        const next = await writeEnabled(enabled);
        return Response.json({ enabled: next }, { headers: { "Cache-Control": "no-store" } });
      },
    },
  },
});
