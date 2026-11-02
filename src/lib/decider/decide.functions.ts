import { createServerFn } from "@tanstack/react-start";
import { CONCRETE_MODEL } from "./wire";

export const runDecision = createServerFn({ method: "POST" })
  .validator((data: unknown) => data)
  .handler(async ({ data }) => {
    const { execute } = await import("./judge.server");
    return execute(data);
  });

export const getKeelEnabled = createServerFn({ method: "GET" }).handler(async () => {
  const { readEnabled } = await import("./switch.server");
  return { enabled: await readEnabled() };
});

export const setKeelEnabled = createServerFn({ method: "POST" })
  .validator((data: unknown) => {
    const enabled = (data as { enabled?: unknown } | null)?.enabled;
    if (typeof enabled !== "boolean") throw new Error("enabled must be true or false");
    return { enabled };
  })
  .handler(async ({ data }) => {
    const { writeEnabled } = await import("./switch.server");
    return { enabled: await writeEnabled(data.enabled) };
  });

export const getCopilotSetup = createServerFn({ method: "GET" }).handler(async () => {
  const { copilotKey } = await import("./auth.server");
  return {
    key: copilotKey(),
    model: CONCRETE_MODEL,
    aliases: ["decider-latest", "jev-latest"],
    path: "/api/v1/systemone",
    modelsPath: "/api/v1/models",
  };
});

