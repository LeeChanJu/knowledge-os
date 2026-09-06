import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import Ajv from "ajv";
export const stable = (value) =>
  JSON.stringify(value, (_, v) =>
    v && typeof v === "object" && !Array.isArray(v)
      ? Object.fromEntries(
          Object.entries(v).sort(([a], [b]) => a.localeCompare(b, "en")),
        )
      : v,
  );
export const digest = (value) =>
  createHash("sha256").update(stable(value)).digest("hex");
export function checkContent(root, architecture) {
  const dir = resolve(root, "architecture-explorer/content");
  const read = (p) => JSON.parse(readFileSync(resolve(dir, p), "utf8"));
  const manifest = read("manifest.json");
  const schema = read("schema.json");
  const validate = new Ajv({ strict: false }).compile(schema);
  for (const p of manifest.pages) {
    if (!/^[a-z0-9-]+$/.test(p.id))
      throw Error(`Unsafe documentation route: ${p.id}`);
    if (
      stable(p.sectionIds) !==
      stable([
        "one-sentence",
        "plain-language",
        "example",
        "in-knowledge-os",
        "why",
        "related",
        "technical",
        "implementation",
      ])
    )
      throw Error(`Invalid teaching sections: ${p.id}`);
    if (new Set(p.stepIds).size !== p.stepIds.length)
      throw Error(`Duplicate diagram steps: ${p.id}`);
  }
  const ids = new Set(manifest.pages.map((p) => p.id));
  if (ids.size !== manifest.pages.length)
    throw Error("Duplicate documentation page");
  const nodes = new Map(architecture.nodes.map((n) => [n.id, n]));
  const claims = new Set(architecture.verification.map((c) => c.id));
  const all = {};
  for (const lang of ["en", "ko-KR"]) {
    const files = readdirSync(resolve(dir, lang))
      .filter((p) => p.endsWith(".json"))
      .sort();
    if (stable(files) !== stable([...ids].map((id) => id + ".json").sort()))
      throw Error(`Missing or stale translation pages: ${lang}`);
    all[lang] = {};
    for (const p of manifest.pages) {
      const d = read(`${lang}/${p.id}.json`);
      if (!validate(d))
        throw Error(
          `Documentation schema ${lang}/${p.id}: ${JSON.stringify(validate.errors)}`,
        );
      if (
        d.id !== p.id ||
        stable(d.sections.map((s) => s.id)) !== stable(p.sectionIds) ||
        stable(d.steps.map((s) => s.id)) !== stable(p.stepIds)
      )
        throw Error(`Localized structure mismatch: ${lang}/${p.id}`);
      for (const id of [
        ...p.nodeIds,
        ...p.referenceIds,
        ...d.steps.map((s) => s.nodeId),
      ])
        if (!nodes.has(id))
          throw Error(
            `Broken documentation architecture reference: ${p.id} -> ${id}`,
          );
      for (const id of p.referenceIds)
        if (!nodes.get(id).resource)
          throw Error(`Not a repository reference: ${id}`);
      for (const id of p.claimIds)
        if (!claims.has(id))
          throw Error(`Broken verification reference: ${id}`);
      for (const id of p.relatedPageIds)
        if (!ids.has(id)) throw Error(`Broken localized route: ${id}`);
      all[lang][p.id] = d;
    }
  }
  for (const id of ids)
    for (const lang of ["en", "ko-KR"]) {
      const peer = { ...all[lang === "en" ? "ko-KR" : "en"][id] };
      delete peer.reviewedPeerDigest;
      if (all[lang][id].reviewedPeerDigest !== digest(peer))
        throw Error(`Stale translation review: ${lang}/${id}`);
      if (
        stable(all.en[id].steps.map((s) => s.nodeId)) !==
        stable(all["ko-KR"][id].steps.map((s) => s.nodeId))
      )
        throw Error(`Localized diagram reference mismatch: ${id}`);
    }
  for (const id of manifest.learningPath)
    if (!ids.has(id)) throw Error(`Broken learning path: ${id}`);
  const locales = Object.fromEntries(
    ["en", "ko-KR"].map((l) => [l, read(`locales/${l}.json`)]),
  );
  const sourceDir = resolve(root, "architecture-explorer/src");
  for (const file of readdirSync(sourceDir, { recursive: true }).filter(p => /\.(tsx?|mjs)$/.test(p))) {
    const source = readFileSync(resolve(sourceDir, file), "utf8");
    for (const match of source.matchAll(/\bt\(\s*(["'])((?:\\.|[^\\])*?)\1\s*,?\s*\)/g)) {
      const key = match[2].replace(/\\(["'\\])/g, "$1");
      if (!locales.en[key] || !locales["ko-KR"][key]) throw Error(`Missing UI translation for source key: ${key}`);
    }
  }
  if (
    stable(Object.keys(locales.en).sort()) !==
    stable(Object.keys(locales["ko-KR"]).sort())
  )
    throw Error("Missing UI translation");
  if (
    Object.values(locales["ko-KR"]).some(
      (v) => typeof v !== "string" || !v.trim(),
    )
  )
    throw Error("Empty UI translation");
  const links = read("github.json");
  if (links.repository !== "https://github.com/LeeChanJu/knowledge-os")
    throw Error("Unexpected GitHub repository");
  if (!/^[a-f0-9]{40}$/.test(links.revision))
    throw Error("Invalid public evidence revision");
  for (const [id, record] of Object.entries(links.references)) {
    const r = nodes.get(id)?.resource;
    if (
      !r ||
      r.path !== record.path ||
      (r.fingerprint || "") !== record.fingerprint
    )
      throw Error(`Stale GitHub evidence reference: ${id}`);
    const bytes = execFileSync("git", ["show", `${links.revision}:${r.path}`], {
      cwd: root,
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (createHash("sha256").update(bytes).digest("hex") !== record.fileDigest)
      throw Error(`Invalid pinned GitHub source: ${id}`);
  }
  for (const n of architecture.nodes.filter((n) => n.resource))
    if (!links.references[n.id])
      throw Error(`Missing GitHub reference: ${n.id}`);
  const architectureText = {
    en: read("architecture/en.json"),
    "ko-KR": read("architecture/ko-KR.json"),
  };
  const claimText = {
    en: read("architecture/claims-en.json"),
    "ko-KR": read("architecture/claims-ko-KR.json"),
  };
  const review = read("architecture/review.json");
  const curated = JSON.parse(
    readFileSync(
      resolve(root, "architecture-explorer/data/curated.json"),
      "utf8",
    ),
  );
  for (const lang of ["en", "ko-KR"]) {
    if (
      stable(Object.keys(architectureText[lang]).sort()) !==
      stable(curated.nodes.map((n) => n.id).sort())
    )
      throw Error(`Missing or stale architecture translation: ${lang}`);
    if (
      stable(Object.keys(claimText[lang]).sort()) !== stable([...claims].sort())
    )
      throw Error(`Missing claim translation: ${lang}`);
    for (const n of curated.nodes) {
      const tr = architectureText[lang][n.id];
      for (const field of [
        "name",
        "description",
        "responsibilities",
        "inputs",
        "outputs",
        "owns",
        "invariants",
        "gaps",
        "deferrals",
      ]) {
        if (
          !(field in tr) ||
          typeof tr[field] !== typeof n[field] ||
          (Array.isArray(n[field]) && n[field].length !== tr[field].length)
        )
          throw Error(
            `Architecture translation structure: ${lang}/${n.id}/${field}`,
          );
        if (lang === "en" && stable(tr[field]) !== stable(n[field]))
          throw Error(`Stale English architecture source: ${n.id}/${field}`);
      }
    }
    for (const c of architecture.verification)
      for (const field of Object.keys(claimText.en[c.id]))
        if (lang === "en" && claimText.en[c.id][field] !== c[field])
          throw Error(`Stale claim translation: ${c.id}`);
    if (
      review[lang] !==
      digest({
        architecture: architectureText[lang],
        claims: claimText[lang],
        ui: locales[lang],
      })
    )
      throw Error(`Translation review required: ${lang}`);
  }
  for (const e of architecture.edges)
    if (!locales.en[e.label] || !locales["ko-KR"][e.label])
      throw Error(`Missing relationship translation: ${e.label}`);
  return {
    schemaVersion: manifest.schemaVersion,
    manifest,
    documents: all,
    locales,
    github: links,
    architecture: architectureText,
    claims: claimText,
  };
}
