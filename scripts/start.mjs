// Runs the production build (`npm run build`) on loopback unless KEEL_HOST opts in.
import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const entry = fileURLToPath(new URL("../.output/server/index.mjs", import.meta.url));
if (!existsSync(entry)) {
  console.error("No build found. Run `npm run build` first.");
  process.exit(1);
}
process.env.HOST = process.env.KEEL_HOST?.trim() || "127.0.0.1";
process.env.PORT ||= "8080";
await import(pathToFileURL(entry).href);
