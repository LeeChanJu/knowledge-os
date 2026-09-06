import { execFileSync } from "node:child_process";
import {
  mkdtempSync,
  rmSync,
  writeFileSync,
  symlinkSync,
  realpathSync,
  existsSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export function checkStaged(root) {
  const temporary = mkdtempSync(join(tmpdir(), "architecture-index-"));
  try {
    execFileSync("git", [
      "-C",
      root,
      "checkout-index",
      "--all",
      `--prefix=${temporary}/`,
    ]);
    const gitDir = execFileSync(
      "git",
      ["-C", root, "rev-parse", "--absolute-git-dir"],
      { encoding: "utf8" },
    ).trim();
    writeFileSync(join(temporary, ".git"), `gitdir: ${gitDir}\n`);
    symlinkSync(
      resolve(root, "architecture-explorer/node_modules"),
      join(temporary, "architecture-explorer/node_modules"),
      "dir",
    );
    execFileSync(
      process.execPath,
      [join(temporary, "architecture-explorer/scripts/explorer.mjs"), "check"],
      {
        cwd: temporary,
        stdio: "pipe",
        env: {
          ...process.env,
          ...(process.env.PYTHON
            ? {}
            : existsSync(join(root, ".venv/bin/python"))
              ? { PYTHON: join(root, ".venv/bin/python") }
              : {}),
        },
      },
    );
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
}
if (
  process.argv[1] &&
  realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  try {
    const root = execFileSync("git", ["rev-parse", "--show-toplevel"], {
      encoding: "utf8",
    }).trim();
    checkStaged(root);
    console.log("Architecture Explorer: staged evidence is synchronized.");
  } catch (e) {
    console.error(e.stderr?.toString() || e.message);
    console.error(
      "Commit stopped: staged Explorer evidence is stale or unavailable. Run npm --prefix architecture-explorer run explorer:sync, review the result, and stage the matching metadata. No files were rewritten or staged by this hook.",
    );
    process.exitCode = 1;
  }
}
