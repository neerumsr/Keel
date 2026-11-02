import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/v1/status")({
  server: {
    handlers: {
      GET: async () => {
        const { readEnabled } = await import("@/lib/decider/switch.server");
        const { CONCRETE_MODEL, LEXICAL_MODEL } = await import("@/lib/decider/wire");
        const { neuralStatus } = await import("@/lib/decider/neural.server");
        const enabled = await readEnabled();
        const neural = await neuralStatus();
        return Response.json(
          {
            enabled,
            model: neural.loaded ? (neural.id ?? CONCRETE_MODEL) : LEXICAL_MODEL,
            engine: neural.loaded ? "neural" : "lexical",
            neural: { loaded: neural.loaded, id: neural.id, error: neural.error },
            fallback: LEXICAL_MODEL,
          },
          { headers: { "Cache-Control": "no-store" } },
        );
      },
    },
  },
});
