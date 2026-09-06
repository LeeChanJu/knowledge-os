import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtempSync,
  cpSync,
  readFileSync,
  writeFileSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { checkContent, digest } from "../scripts/check-content.mjs";
import { defaultRoot } from "../scripts/explorer.mjs";
import { execFileSync } from "node:child_process";
let root;
const architecture = JSON.parse(
  readFileSync(new URL("../data/architecture.json", import.meta.url)),
);
const file = (p) => resolve(root, "architecture-explorer", p);
const alter = (p, fn) => {
  const v = JSON.parse(readFileSync(file(p)));
  fn(v);
  writeFileSync(file(p), JSON.stringify(v));
};
beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "kos-content-"));
  cpSync(resolve(defaultRoot, "architecture-explorer/src"), file("src"), { recursive: true });
  cpSync(
    resolve(defaultRoot, "architecture-explorer/content"),
    file("content"),
    { recursive: true },
  );
  cpSync(resolve(defaultRoot, "architecture-explorer/data"), file("data"), {
    recursive: true,
  });
  const dir = execFileSync("git", ["rev-parse", "--absolute-git-dir"], {
    cwd: defaultRoot,
    encoding: "utf8",
  }).trim();
  writeFileSync(join(root, ".git"), "gitdir: " + dir + "\n");
});
afterEach(() => rmSync(root, { recursive: true, force: true }));
test("all 77 pages have paired structure and deterministic checked projection", () => {
  const one = checkContent(root, architecture);
  const two = checkContent(root, architecture);
  assert.deepEqual(one, two);
  assert.equal(one.manifest.pages.length, 77);
  assert.equal(one.manifest.learningPath.length, 10);
  assert.equal(
    one.manifest.pages.filter((p) => p.kind === "walkthrough").length,
    6,
  );
});
test("missing page, stale file and missing section cannot pass as translated", () => {
  rmSync(file("content/ko-KR/ontology.json"));
  assert.throws(
    () => checkContent(root, architecture),
    /Missing or stale translation/,
  );
});
test("changed English prose requires explicit Korean review without writing either language", () => {
  alter(
    "content/en/ontology.json",
    (v) => (v.sections[1].body += " Clarification."),
  );
  const before = readFileSync(file("content/en/ontology.json"));
  assert.throws(
    () => checkContent(root, architecture),
    /Stale translation review/,
  );
  assert.deepEqual(readFileSync(file("content/en/ontology.json")), before);
});
test("one-language-only section and broken concept route fail", () => {
  alter("content/ko-KR/ontology.json", (v) => v.sections.pop());
  assert.throws(() => checkContent(root, architecture), /schema/);
});
test("broken localized related routes fail", () => {
  alter("content/manifest.json", (v) =>
    v.pages[0].relatedPageIds.push("not-real"),
  );
  assert.throws(
    () => checkContent(root, architecture),
    /Broken localized route/,
  );
});
test("deleted implementation or verification references fail", () => {
  alter("content/manifest.json", (v) =>
    v.pages[0].referenceIds.push("ref:removed"),
  );
  assert.throws(
    () => checkContent(root, architecture),
    /Broken documentation architecture/,
  );
});
test("changed graph explanation invalidates its curated translation", () => {
  alter(
    "data/curated.json",
    (v) => (v.nodes[0].description += " Changed architecture."),
  );
  assert.throws(
    () => checkContent(root, architecture),
    /Stale English architecture source/,
  );
});
test("localized diagram cannot point to a different component", () => {
  alter(
    "content/ko-KR/new-document.json",
    (v) => (v.steps[0].nodeId = "ontology"),
  );
  assert.throws(
    () => checkContent(root, architecture),
    /Localized diagram reference mismatch|Stale translation/,
  );
});
test("UI missing translations fail", () => {
  alter("content/locales/ko-KR.json", (v) => delete v.Learn);
  assert.throws(
    () => checkContent(root, architecture),
    /Missing UI translation/,
  );
});
test("a new UI string missing from both catalogs fails at check time", () => {
  writeFileSync(file("src/new-label.ts"), 't("Untranslated new control");');
  assert.throws(() => checkContent(root, architecture), /Missing UI translation for source key/);
});
test("pinned GitHub link cannot silently acquire another path or fingerprint", () => {
  alter(
    "content/github.json",
    (v) => (Object.values(v.references)[0].path = "README.md"),
  );
  assert.throws(
    () => checkContent(root, architecture),
    /Stale GitHub evidence reference/,
  );
});
test("translation digest ignores object key order but includes actual text", () => {
  assert.equal(digest({ a: 1, b: 2 }), digest({ b: 2, a: 1 }));
  assert.notEqual(digest({ a: "text" }), digest({ a: "changed" }));
});
