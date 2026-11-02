import { createFileRoute } from "@tanstack/react-router";
import { MODEL_ALIASES, resolveModel } from "@/lib/decider/wire";

export const Route = createFileRoute("/api/v1/models")({
  server: {
    handlers: {
      GET: async () => {
        return Response.json(
          {
            object: "list",
            data: MODEL_ALIASES.map((id) => ({
              id,
              object: "model",
              owned_by: "keel",
              resolves_to: resolveModel(id),
            })),
          },
          { headers: { "Cache-Control": "no-store" } },
        );
      },
    },
  },
});
