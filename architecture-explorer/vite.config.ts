import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { run, defaultRoot } from "./scripts/explorer.mjs";

export default defineConfig(() => {
  // Every entry point, including direct `vite build`, must pass the read-only gate.
  run("check");
  const checkoutRevision = execFileSync("git", ["rev-parse", "HEAD"], {
    cwd: defaultRoot,
    encoding: "utf8",
  }).trim();
  const dirty =
    execFileSync("git", ["status", "--porcelain", "--untracked-files=no"], {
      cwd: defaultRoot,
      encoding: "utf8",
    }).trim().length > 0;
  return {
    base: "./",
    plugins: [react()],
    define: {
      __BUILD_INFO__: JSON.stringify({
        checkoutRevision,
        dirty,
        state: "CHECKED SNAPSHOT",
      }),
    },
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      fs: {
        strict: true,
        allow: [resolve(defaultRoot, "architecture-explorer")],
      },
    },
    preview: { host: "127.0.0.1", port: 4173, strictPort: true },
  };
});
