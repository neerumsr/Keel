import { readdirSync } from "node:fs";
import { join } from "node:path";
import type { Plugin } from "vite";
import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { nitro } from "nitro/vite";
import { isMigrationFile } from "./scripts/migration-plan.mjs";

/** The files `src/lib/db.ts` globs — same directory, same non-recursive scope. */
function hasGlobbedMigrations(root: string): boolean {
  try {
    return readdirSync(join(root, "migrations")).some(isMigrationFile);
  } catch {
    return false;
  }
}

/**
 * Finish PGLite bootstrap during dev-server setup (before traffic). Vite awaits
 * async `configureServer` hooks. Production: `src/lib/db` kicks `ensureDbReady`
 * on import.
 *
 * Vite awaiting the hook puts this on time-to-first-render, so an app with no
 * migrations — no schema to apply — skips it entirely rather than paying for a
 * PGLite instance it never queries.
 */
function pgliteBootstrapPlugin(): Plugin {
  return {
    name: "keel:pglite-bootstrap",
    apply: "serve",
    async configureServer(server) {
      if (!hasGlobbedMigrations(server.config.root)) return;
      try {
        const mod = (await server.ssrLoadModule("/src/lib/db.ts")) as {
          ensureDbReady?: () => Promise<void>;
        };
        if (typeof mod.ensureDbReady === "function") {
          await mod.ensureDbReady();
        }
      } catch (err) {
        console.error("[keel] DB bootstrap failed:", err);
        throw err;
      }
    },
  };
}

// Loopback by default: the dev server hands the local bearer to the UI, so it
// must not be reachable from the network. Set KEEL_HOST (e.g. 0.0.0.0) to opt in.
const host = process.env.KEEL_HOST?.trim() || "127.0.0.1";

export default defineConfig(({ command, isPreview }) => ({
  server: {
    host,
    port: 8080,
    strictPort: true,
  },
  preview: {
    host,
    port: 8081,
    strictPort: true,
  },
  resolve: { tsconfigPaths: true },
  // Keel-2 runs a native ONNX runtime in-process; never bundle it.
  ssr: { external: ["onnxruntime-node", "@huggingface/transformers"] },
  plugins: [
    pgliteBootstrapPlugin(),
    tailwindcss(),
    tanstackStart(),
    // Standalone Node server for `npm run build && npm start` (.output/server/index.mjs).
    // PGlite loads its WASM/data files from its own package directory, so keep it external.
    ...(command === "build" || isPreview
      ? [nitro({ preset: "node-server", traceDeps: ["@electric-sql/pglite*"] })]
      : []),
    viteReact(),
  ],
}));