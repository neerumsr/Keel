import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/v1/systemone")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { handleSystemOne } = await import("@/lib/decider/systemone-route.server");
        return handleSystemOne(request);
      },
    },
  },
});