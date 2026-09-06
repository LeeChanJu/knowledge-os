import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtempSync,
  cpSync,
  rmSync,
  readFileSync,
  writeFileSync,
  symlinkSync,
  renameSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { execFileSync } from "node:child_process";
import { run, generate, canonical, defaultRoot } from "../scripts/explorer.mjs";
import { checkStaged } from "../scripts/check-staged.mjs";
let root;
const git = (...args) =>
  execFileSync("git", ["-C", root, ...args], {
    encoding: "utf8",
    stdio: "pipe",
  });
const file = (p) => join(root, p);
const change = (p, fn) =>
  writeFileSync(file(p), fn(readFileSync(file(p), "utf8")));
const alterJson = (p, fn) =>
  change(p, (s) => {
    const o = JSON.parse(s);
    fn(o);
    return canonical(o);
  });
const curated = "architecture-explorer/data/curated.json";
const verification = "architecture-explorer/data/verification.json";
const generated = "architecture-explorer/data/architecture.json";
beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "kos-explorer-test-"));
  execFileSync("git", ["init", "--quiet", root], { stdio: "pipe" });
  const objectDir = execFileSync(
    "git",
    ["-C", defaultRoot, "rev-parse", "--git-path", "objects"],
    { encoding: "utf8" },
  ).trim();
  writeFileSync(
    file(".git/objects/info/alternates"),
    resolve(defaultRoot, objectDir) + "\n",
  );
  const head = execFileSync("git", ["-C", defaultRoot, "rev-parse", "HEAD"], {
    encoding: "utf8",
  }).trim();
  git("reset", "--hard", head);
  cpSync(
    resolve(defaultRoot, "architecture-explorer"),
    file("architecture-explorer"),
    {
      recursive: true,
      filter: (p) =>
        !/(?:^|\/)(node_modules|dist|test-results|playwright-report|__pycache__)(?:\/|$)/.test(
          p,
        ),
    },
  );
  symlinkSync(
    resolve(defaultRoot, "architecture-explorer/node_modules"),
    file("architecture-explorer/node_modules"),
    "dir",
  );
  git("config", "user.email", "explorer-fixture@example.invalid");
  git("config", "user.name", "Explorer fixture");
  git("config", "core.hooksPath", "/dev/null");
});
afterEach(() => rmSync(root, { recursive: true, force: true }));
function stageCommit() {
  // A clean checkout already contains the Explorer; make a real documentation change.
  writeFileSync(file("architecture-explorer/fixture-note.md"), "Explorer-only fixture revision.\n");
  git("add", "architecture-explorer");
  git("commit", "--quiet", "-m", "Explorer fixture");
}
test("sync twice produces identical bytes; check never writes; only generated artifacts change", () => {
  const initialDiff = git("diff", "--name-only");
  const before = readFileSync(file(curated), "utf8"),
    states = readFileSync(file(verification), "utf8");
  run("sync", root);
  const once = readFileSync(file(generated), "utf8");
  run("sync", root);
  run("check", root);
  assert.equal(readFileSync(file(generated), "utf8"), once);
  assert.equal(readFileSync(file(curated), "utf8"), before);
  assert.equal(readFileSync(file(verification), "utf8"), states);
  assert.equal(git("diff", "--name-only"), initialDiff);
});
test("tampered generated metadata fails independently and check leaves tampering untouched", () => {
  run("sync", root);
  change(generated, (s) => s.replace("Source Registry", "Fake Registry"));
  const before = readFileSync(file(generated), "utf8");
  assert.throws(() => run("check", root), /Generated metadata stale/);
  assert.equal(readFileSync(file(generated), "utf8"), before);
});
test("removed or renamed implementation file fails even after sync", () => {
  renameSync(
    file("src/knowledge_os/graph.py"),
    file("src/knowledge_os/graph_renamed.py"),
  );
  assert.throws(() => run("sync", root), /Missing repository reference/);
});
test("renamed symbol, renamed test and absent documentation heading fail references", () => {
  alterJson(curated, (m) => {
    m.nodes[0].references.push({
      path: "src/knowledge_os/graph.py",
      symbol: "GraphStore.removed_method",
    });
  });
  assert.throws(() => generate(root), /Missing symbol\/test/);
  alterJson(curated, (m) => {
    m.nodes[0].references.pop();
    m.nodes[0].references.push({
      path: "tests/test_contracts.py",
      symbol: "test_no_longer_present",
    });
  });
  assert.throws(() => generate(root), /Missing symbol\/test/);
  alterJson(curated, (m) => {
    m.nodes[0].references.pop();
    m.nodes[0].references.push({
      path: "README.md",
      anchor: "nonexistent-heading",
    });
  });
  assert.throws(() => generate(root), /Missing documentation heading/);
});
test("removed migration and changed contract invalidate pinned verification", () => {
  rmSync(file("migrations/002_chunk_vector.cypher"));
  assert.throws(() => run("check", root), /Missing repository reference/);
});
test("contract version changes require explicit verification reconciliation", () => {
  change("config/contracts.yaml", (s) => s.replace("source-v12", "source-v13"));
  const before = readFileSync(file(verification), "utf8");
  assert.throws(() => run("sync", root), /stale VERIFIED evidence/);
  assert.equal(readFileSync(file(verification), "utf8"), before);
});
test("behavior change invalidates VERIFIED evidence; sync cannot refresh fingerprints", () => {
  change(
    "src/knowledge_os/ids.py",
    (s) =>
      s.replace("def stable_id(", "def stable_id(") +
      "\nBEHAVIOR_CHANGE = True\n",
  );
  const before = readFileSync(file(verification), "utf8");
  assert.throws(() => run("check", root), /F1: stale VERIFIED/);
  assert.throws(() => run("sync", root), /stale VERIFIED/);
  assert.equal(readFileSync(file(verification), "utf8"), before);
});
test("reviewed issue changes still fail with VERIFIED claims explicitly downgraded", () => {
  alterJson(verification, (v) =>
    v.claims
      .filter((c) => c.status === "VERIFIED")
      .forEach((c) => {
        c.status = "IMPLEMENTED";
        c.dependencies = {};
      }),
  );
  change(
    "src/knowledge_os/ontology.py",
    (s) => s + "\nPREDICATE_VALIDATION_CHANGED = True\n",
  );
  assert.throws(() => run("sync", root), /F5: reviewed issue evidence changed/);
});
test("formatting and comments do not alter symbol interfaces or behavior fingerprints", () => {
  run("sync", root);
  const before = readFileSync(file(generated), "utf8");
  change(
    "src/knowledge_os/graph.py",
    (s) => "# Harmless internal commentary.\n\n" + s,
  );
  run("check", root);
  assert.equal(readFileSync(file(generated), "utf8"), before);
  git("add", "src/knowledge_os/graph.py");
  git("commit", "--quiet", "-m", "Comment-only fixture change");
  run("check", root);
  assert.equal(readFileSync(file(generated), "utf8"), before);
});
test("status authority changes cannot silently leave resolved issue displayed as open", () => {
  change("AGENT.md", (s) =>
    s.replace(
      "Remaining audit findings must be resolved",
      "F3 is corrected and verified.\n\nRemaining audit findings must be resolved",
    ),
  );
  assert.throws(() => run("sync", root), /Verification authority changed/);
});
test("new regression finding must be curated, not silently ignored", () => {
  // Keep broad verified coverage unchanged so this tests the inventory guard itself.
  writeFileSync(
    file("tests/test_new_finding.py"),
    "def test_f9_new_requirement():\n    assert True\n",
  );
  assert.throws(() => run("sync", root), /Unmapped remediation finding F9/);
});
test("duplicate IDs, unsupported VERIFIED nodes and unsafe references fail", () => {
  alterJson(curated, (m) => m.nodes.push(m.nodes[0]));
  assert.throws(() => generate(root), /Duplicate architecture node/);
  alterJson(curated, (m) => {
    m.nodes.pop();
    m.nodes[0].status = "VERIFIED";
  });
  assert.throws(() => generate(root), /unsupported VERIFIED/);
  alterJson(curated, (m) => {
    m.nodes[0].status = "IMPLEMENTED";
    m.nodes[0].references.push({ path: "../outside" });
  });
  assert.throws(() => generate(root), /Unsafe reference/);
});
test("Explorer-only commits do not cause self-referential SHA regeneration", () => {
  run("sync", root);
  const before = readFileSync(file(generated), "utf8");
  stageCommit();
  run("check", root);
  assert.equal(readFileSync(file(generated), "utf8"), before);
});
test("staged check sees old generated metadata despite synchronized working tree", () => {
  run("sync", root);
  stageCommit();
  alterJson(
    curated,
    (m) => (m.nodes[0].position.x += 10),
  );
  git("add", curated);
  run("sync", root);
  assert.throws(
    () => checkStaged(root),
    (e) => /Generated metadata stale/.test(e.stderr?.toString() || ""),
  );
  git("add", "architecture-explorer/data");
  checkStaged(root);
});
test("staged check ignores unrelated unstaged working changes and never stages them", () => {
  run("sync", root);
  stageCommit();
  change("config/contracts.yaml", (s) =>
    s.replace("source-v12", "source-v999"),
  );
  const index = git("write-tree");
  checkStaged(root);
  assert.equal(git("write-tree"), index);
  assert.match(
    readFileSync(file("config/contracts.yaml"), "utf8"),
    /source-v999/,
  );
});

test("new or amended evaluation records require curated reconciliation", () => {
  writeFileSync(
    file("docs/evaluations/new-remediation.md"),
    "# New remediation evidence\n\nA new record must be reviewed.\n",
  );
  assert.throws(
    () => run("sync", root),
    /Verification evidence document inventory changed/,
  );
});

test("direct Vite build rejects stale generated metadata", () => {
  run("sync", root);
  change(generated, (s) => s.replace("Source Registry", "Stale display"));
  assert.throws(
    () =>
      execFileSync(
        process.execPath,
        [file("architecture-explorer/node_modules/vite/bin/vite.js"), "build"],
        {
          cwd: file("architecture-explorer"),
          stdio: "pipe",
          env: {
            ...process.env,
            PYTHON: process.env.PYTHON || execFileSync(
              "python3",
              ["-c", "import sys;print(sys.executable)"],
              { encoding: "utf8" },
            ).trim(),
          },
        },
      ),
    (e) => /Generated metadata stale/.test(e.stderr?.toString() || ""),
  );
});
