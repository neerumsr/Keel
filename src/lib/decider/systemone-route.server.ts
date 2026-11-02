/** The System One POST handler, shared by /api/v1/systemone and the Foundry-style /providers/microsoft/v1/systemone. */
import { authorizeDecision } from "./auth.server.ts";

type Run = (body: unknown) => Promise<{ status: number; body: unknown }>;

const NO_STORE = { "Cache-Control": "no-store" };

async function defaultRun(body: unknown) {
  const { execute } = await import("./judge.server");
  return execute(body);
}

export async function handleSystemOne(request: Request, run: Run = defaultRun): Promise<Response> {
  if (!authorizeDecision(request.headers)) {
    return Response.json(
      {
        error: {
          type: "unauthorized",
          message: "Send Authorization: Bearer <key> (or api-key: <key>) with the Copilot key from the Keel Copilot tab.",
          request_id: "req_unauthorized",
        },
      },
      { status: 401, headers: NO_STORE },
    );
  }
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json(
      { error: { type: "invalid_request", message: "Body must be JSON.", request_id: "req_json" } },
      { status: 400, headers: NO_STORE },
    );
  }
  const result = await run(body);
  return Response.json(result.body, { status: result.status, headers: NO_STORE });
}
