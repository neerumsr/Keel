import { createFileRoute } from "@tanstack/react-router";

/** Microsoft Foundry path for Microsoft-Decision-1; same handler as /api/v1/systemone. */
export const Route = createFileRoute("/providers/microsoft/v1/systemone")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { handleSystemOne } = await import("@/lib/decider/systemone-route.server");
        return handleSystemOne(request);
      },
    },
  },
});