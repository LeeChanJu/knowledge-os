import {
  readFileSync,
  writeFileSync,
  existsSync,
  readdirSync,
  realpathSync,
} from "node:fs";
import { resolve, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import Ajv from "ajv";
import { parse as yaml } from "yaml";

export const defaultRoot = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../..",
);
export const canonical = (value) => JSON.stringify(value, null, 2) + "\n";
export const hash = (value) => createHash("sha256").update(value).digest("hex");
const python = () =>
  process.env.PYTHON ||
  (existsSync(resolve(defaultRoot, ".venv/bin/python"))
    ? resolve(defaultRoot, ".venv/bin/python")
    : "python3");
const git = (root, ...args) =>
  execFileSync("git", ["-C", root, ...args], { encoding: "utf8" }).trim();
const read = (root, path) => readFileSync(safePath(root, path), "utf8");
const json = (root, path) => JSON.parse(read(root, path));
export function safePath(root, path) {
  const full = resolve(root, path);
  if (
    path.includes("\\") ||
    path.startsWith("/") ||
    relative(root, full).startsWith("..")
  )
    throw Error(`Unsafe reference: ${path}`);
  if (!existsSync(full)) throw Error(`Missing repository reference: ${path}`);
  if (relative(realpathSync(root), realpathSync(full)).startsWith(".."))
    throw Error(`Reference escapes repository: ${path}`);
  return full;
}
function walk(root, dir, extensions) {
  if (!existsSync(resolve(root, dir))) return [];
  return readdirSync(resolve(root, dir), { withFileTypes: true })
    .flatMap((entry) => {
      if (
        entry.name.startsWith(".") ||
        entry.name === "__pycache__" ||
        entry.name.endsWith(".egg-info")
      )
        return [];
      const path = `${dir}/${entry.name}`;
      return entry.isDirectory()
        ? walk(root, path, extensions)
        : extensions.some((ext) => path.endsWith(ext))
          ? [path]
          : [];
    })
    .sort();
}
export function section(text, anchor) {
  if (!anchor) return text;
  const lines = text.split("\n");
  const slug = (s) =>
    s
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, "")
      .trim()
      .replace(/\s+/g, "-");
  const start = lines.findIndex(
    (line) => /^#+ /.test(line) && slug(line.replace(/^#+ /, "")) === anchor,
  );
  if (start < 0) throw Error(`Missing documentation heading: ${anchor}`);
  const level = lines[start].match(/^#+/)[0].length;
  let end = start + 1;
  while (end < lines.length && !new RegExp(`^#{1,${level}} `).test(lines[end]))
    end++;
  return lines.slice(start, end).join("\n").trim();
}
export function scan(root) {
  const pythonPaths = [
    ...walk(root, "src/knowledge_os", [".py"]),
    ...walk(root, "tests", [".py"]),
  ].sort();
  const inspection = JSON.parse(
    execFileSync(
      python(),
      [
        resolve(
          defaultRoot,
          "architecture-explorer/scripts/inspect_repository.py",
        ),
        root,
      ],
      {
        input: JSON.stringify(pythonPaths),
        encoding: "utf8",
        maxBuffer: 16 * 1024 * 1024,
      },
    ),
  );
  const documents = [
    "README.md",
    ...["AGENT.md", "AGENTS.md"].filter((p) => existsSync(resolve(root, p))),
    ...walk(root, "docs", [".md"]),
    ...walk(root, "prompts", [".md"]),
  ];
  const configs = [
    ...walk(root, "config", [".yaml", ".yml"]),
    ...walk(root, "examples", [".json"]),
    "pyproject.toml",
    "uv.lock",
  ];
  const migrations = walk(root, "migrations", [".cypher"]);
  const files = {};
  for (const path of [
    ...new Set([...pythonPaths, ...documents, ...configs, ...migrations]),
  ].sort()) {
    const content = read(root, path);
    if (path.endsWith(".py")) {
      // No line offsets, function bodies, or excerpts: formatting does not churn the model.
      files[path] = { kind: "python", symbols: inspection[path].symbols };
    } else {
      const kind = migrations.includes(path)
        ? "migration"
        : documents.includes(path)
          ? "document"
          : "configuration";
      files[path] = { kind, fingerprint: hash(content) };
      if (kind === "migration")
        files[path].objects = [
          ...content.matchAll(
            /(?:CREATE|DROP)\s+(?:CONSTRAINT|(?:FULLTEXT |VECTOR )?INDEX)\s+(\w+)/g,
          ),
        ].map((m) => m[1]);
      if (path.endsWith(".yaml") || path.endsWith(".yml"))
        files[path].value = yaml(content);
    }
  }
  return {
    files,
    inspection,
    contracts: yaml(read(root, "config/contracts.yaml")),
  };
}
function validateSchema(root, value, definition) {
  const schema = json(root, "architecture-explorer/data/schema.json");
  const ajv = new Ajv({ allErrors: true });
  const validate = ajv.compile({ ...schema, $ref: `#/$defs/${definition}` });
  if (!validate(value))
    throw Error(`${definition} schema: ${ajv.errorsText(validate.errors)}`);
}
export function resolveReference(root, ref, repository) {
  safePath(root, ref.path);
  const file = repository.files[ref.path];
  if (!file)
    throw Error(`Reference outside documented evidence inventory: ${ref.path}`);
  if (ref.symbol) {
    const symbol = file.symbols?.find((s) => s.symbol === ref.symbol);
    if (!symbol) throw Error(`Missing symbol/test: ${ref.path}::${ref.symbol}`);
    if (ref.kind === "test" && symbol.kind !== "test")
      throw Error(`Not an executable test: ${ref.path}::${ref.symbol}`);
    return { id: `ref:${ref.path}::${ref.symbol}`, ...ref, ...symbol };
  }
  const extra = ref.anchor
    ? { fingerprint: hash(section(read(root, ref.path), ref.anchor)) }
    : {};
  return {
    id: `ref:${ref.path}${ref.anchor ? "#" + ref.anchor : ""}`,
    ...ref,
    ...file,
    ...extra,
    symbols: undefined,
    value: file.value,
  };
}
export function dependencyFingerprint(root, path, repository) {
  safePath(root, path);
  return (
    repository.inspection[path]?.semanticFingerprint || hash(read(root, path))
  );
}
export function validateVerification(root, verification, repository, nodeIds) {
  const evaluationFiles = Object.fromEntries(
    Object.entries(repository.files)
      .filter(([path]) => path.startsWith("docs/evaluations/"))
      .map(([path, record]) => [path, record.fingerprint]),
  );
  if (
    canonical(evaluationFiles) !==
    canonical(verification.reviewedEvaluationDocuments)
  )
    throw Error(
      "Verification evidence document inventory changed. Explicitly reconcile data/verification.json before synchronization.",
    );
  for (const authority of verification.authorities) {
    const current = hash(section(read(root, authority.path), authority.anchor));
    if (current !== authority.fingerprint)
      throw Error(
        `Verification authority changed: ${authority.path}#${authority.anchor || ""}. Explicitly reconcile data/verification.json; sync cannot decide issue status.`,
      );
  }
  const ids = new Set();
  for (const claim of verification.claims) {
    if (ids.has(claim.id))
      throw Error(`Duplicate verification ID: ${claim.id}`);
    ids.add(claim.id);
    for (const id of claim.affects)
      if (!nodeIds.has(id))
        throw Error(`${claim.id}: missing affected component ${id}`);
    for (const test of claim.tests)
      resolveReference(root, { ...test, kind: "test" }, repository);
    for (const source of claim.sources)
      resolveReference(root, source, repository);
    if (claim.status === "VERIFIED") {
      if (
        !claim.tests.length ||
        !claim.sources.length ||
        !claim.recordedOutcome ||
        !claim.environment ||
        !claim.revision ||
        !Object.keys(claim.dependencies).length
      )
        throw Error(
          `${claim.id}: VERIFIED needs executable references, recorded outcome, authority, revision and dependency coverage.`,
        );
      if (!/^[0-9a-f]{40}$/.test(claim.revision))
        throw Error(`${claim.id}: invalid verification revision`);
      if (claim.revisionScope === "repository") {
        git(root, "cat-file", "-e", `${claim.revision}^{commit}`);
      } else if (claim.revisionScope !== "original-source-history") {
        throw Error(`${claim.id}: declare the provenance of the verification revision.`);
      }
      // The revision locates code; the curated record and its authorities establish the claim.
      for (const test of claim.tests)
        if (!(test.path in claim.dependencies))
          throw Error(
            `${claim.id}: test not covered by verification fingerprint: ${test.path}`,
          );
      for (const [path, expected] of Object.entries(claim.dependencies)) {
        if (dependencyFingerprint(root, path, repository) !== expected)
          throw Error(
            `${claim.id}: stale VERIFIED evidence in ${path}. Explicit reconciliation or new executed evidence is required; sync never changes verification states.`,
          );
      }
    }
    if (claim.status !== "VERIFIED")
      for (const [path, expected] of Object.entries(claim.dependencies)) {
        if (dependencyFingerprint(root, path, repository) !== expected)
          throw Error(
            `${claim.id}: reviewed issue evidence changed in ${path}. Explicitly reconcile the finding; sync cannot decide whether it is resolved.`,
          );
      }
    if (claim.status === "KNOWN ISSUE" && !claim.resolutionRequired)
      throw Error(`${claim.id}: open finding needs resolution criteria`);
  }
  // Repository remediation regressions cannot silently disappear from the issue ledger.
  const findingIds = new Set(
    Object.values(repository.files)
      .flatMap((f) => f.symbols || [])
      .flatMap((s) => {
        const m = s.kind === "test" && s.symbol.match(/^test_f(\d+)_/);
        return m ? ["F" + m[1]] : [];
      }),
  );
  for (const id of findingIds)
    if (!ids.has(id))
      throw Error(
        `Unmapped remediation finding ${id}; explicitly update verification.json.`,
      );
}
export function evidenceRevision(root, paths, verifiedPaths) {
  let cursor = "HEAD";
  while (true) {
    const revision = git(
      root,
      "log",
      "-1",
      "--format=%H",
      cursor,
      "--",
      ...paths,
    );
    if (!revision) break;
    cursor = revision + "^";
    const changes = git(
      root,
      "diff-tree",
      "--root",
      "--no-commit-id",
      "--name-status",
      "-r",
      revision,
      "--",
      ...paths,
    )
      .split("\n")
      .filter(Boolean)
      .map((line) => line.split("\t"));
    if (!changes.length) continue;
    if (
      changes.some(([status, path]) => status !== "M" || !path.endsWith(".py"))
    )
      return revision;
    const contents = {};
    for (const [, path] of changes) {
      contents["before:" + path] = git(root, "show", `${revision}^:${path}`);
      contents["after:" + path] = git(root, "show", `${revision}:${path}`);
    }
    const parsed = JSON.parse(
      execFileSync(
        python(),
        [
          resolve(
            defaultRoot,
            "architecture-explorer/scripts/inspect_repository.py",
          ),
          root,
          "--contents",
        ],
        {
          input: JSON.stringify(contents),
          encoding: "utf8",
          maxBuffer: 16 * 1024 * 1024,
        },
      ),
    );
    for (const [, path] of changes) {
      const a = parsed["before:" + path],
        b = parsed["after:" + path];
      if (
        canonical(a.symbols) !== canonical(b.symbols) ||
        (verifiedPaths.has(path) &&
          a.semanticFingerprint !== b.semanticFingerprint)
      )
        return revision;
    }
  }
  throw Error(
    "Cannot identify evidence revision from Git history; use a full checkout.",
  );
}
export function generate(root = defaultRoot) {
  const curated = json(root, "architecture-explorer/data/curated.json");
  const verification = json(
    root,
    "architecture-explorer/data/verification.json",
  );
  validateSchema(root, curated, "curated");
  validateSchema(root, verification, "verification");
  const nodeIds = new Set(curated.nodes.map((n) => n.id));
  if (nodeIds.size !== curated.nodes.length)
    throw Error("Duplicate architecture node ID");
  const domainIds = new Set(curated.domains.map((d) => d.id));
  for (const n of curated.nodes)
    if (!domainIds.has(n.domain)) throw Error(`Missing domain ${n.domain}`);
  const repository = scan(root);
  validateVerification(root, verification, repository, nodeIds);
  const resources = new Map();
  const refId = (ref) => {
    const resource = resolveReference(root, ref, repository);
    resources.set(resource.id, resource);
    return resource.id;
  };
  const edges = [];
  const edgeIds = new Set();
  const edge = (source, target, label, refs, overview = false) => {
    const id = `${source}~${label}~${target}`;
    if (edgeIds.has(id)) throw Error(`Duplicate relationship ${id}`);
    edgeIds.add(id);
    edges.push({ id, source, target, label, references: refs, overview });
  };
  const claimsById = new Map(verification.claims.map((c) => [c.id, c]));
  const nodes = curated.nodes.map((node) => {
    for (const contract of node.contracts)
      if (!repository.contracts.contracts[contract])
        throw Error(`Unknown contract ${contract}`);
    const refs = node.references.map(refId);
    const relatedClaims = verification.claims.filter((c) =>
      c.affects.includes(node.id),
    );
    const direct = node.verification ? claimsById.get(node.verification) : null;
    if (node.verification && !direct)
      throw Error(`Unknown verification ${node.verification}`);
    if (node.status === "VERIFIED" && direct?.status !== "VERIFIED")
      throw Error(`${node.id}: unsupported VERIFIED state`);
    const status =
      direct?.status ||
      (relatedClaims.some((c) => c.status === "KNOWN ISSUE")
        ? "KNOWN ISSUE"
        : node.status);
    return {
      ...node,
      status,
      references: refs,
      knownIssues: relatedClaims
        .filter((c) => c.status === "KNOWN ISSUE")
        .map((c) => c.id),
    };
  });
  for (const link of curated.edges) {
    if (!nodeIds.has(link.source) || !nodeIds.has(link.target))
      throw Error(`Broken relationship ${link.source} -> ${link.target}`);
    edge(
      link.source,
      link.target,
      link.label,
      link.references.map(refId),
      link.overview,
    );
  }
  for (const node of nodes) {
    for (const id of node.references) edge(node.id, id, "documented by", [id]);
    for (const name of node.contracts)
      if (node.id !== `contract-${name}`)
        edge(node.id, `contract-${name}`, "bounded by", []);
  }
  for (const claim of verification.claims) {
    const references = [
      ...claim.sources,
      ...claim.tests.map((t) => ({ ...t, kind: "test" })),
    ].map(refId);
    nodes.push({
      id: claim.id,
      name: `${claim.id} · ${claim.title}`,
      category: "finding",
      domain: "operations",
      overview: false,
      description: claim.scope,
      responsibilities: [
        claim.status === "VERIFIED"
          ? "Preserve the accepted verification scope and its dependency coverage without turning it into a subsystem-wide claim."
          : "Keep this finding visible until its resolution criteria are met.",
      ],
      inputs: [],
      outputs: [],
      owns: ["Documentation of the claim; no runtime data."],
      invariants: [
        claim.resolutionRequired ||
          "Verification applies only to the declared scope and pinned dependencies.",
      ],
      gaps: [claim.limitations],
      deferrals: [],
      contracts: [],
      references,
      status: claim.status,
      knownIssues: claim.status === "KNOWN ISSUE" ? [claim.id] : [],
      verification: claim.id,
    });
    for (const id of claim.affects)
      edge(
        id,
        claim.id,
        claim.status === "VERIFIED" ? "verified scope" : "has finding",
        references,
      );
    for (const ref of references) edge(claim.id, ref, "supported by", [ref]);
  }
  for (const r of resources.values())
    nodes.push({
      id: r.id,
      name: r.symbol || r.path.split("/").at(-1),
      category:
        r.kind === "test"
          ? "test"
          : r.kind === "document"
            ? "document"
            : "reference",
      domain: "references",
      overview: false,
      description: r.symbol ? `${r.kind} in ${r.path}` : r.path,
      responsibilities: [],
      inputs: [],
      outputs: [],
      owns: [],
      invariants: [],
      gaps: [
        "A reference identifies evidence; its existence is not proof of successful execution.",
      ],
      deferrals: [],
      contracts: [],
      references: [],
      status: "IMPLEMENTED",
      knownIssues: [],
      resource: r,
    });
  const allIds = new Set(nodes.map((n) => n.id));
  for (const e of edges)
    if (!allIds.has(e.source) || !allIds.has(e.target))
      throw Error(`Dangling relationship ${e.id}`);
  if (allIds.size !== nodes.length) throw Error("Duplicate node/reference ID");
  const inventory = {
    schemaVersion: curated.schemaVersion,
    files: repository.files,
  };
  const evidenceDigest = hash(canonical(inventory));
  // Use the latest commit touching authoritative inputs, not HEAD: Explorer-only commits do not churn evidence.
  const paths = Object.keys(repository.files);
  const pinnedPaths = new Set(
    verification.claims.flatMap((c) => Object.keys(c.dependencies)),
  );
  const baselineRevision = evidenceRevision(root, paths, pinnedPaths);
  if (!baselineRevision)
    throw Error("Cannot identify evidence revision from Git history");
  const evidence = { ...inventory, evidenceDigest, baselineRevision };
  const architecture = {
    schemaVersion: curated.schemaVersion,
    evidenceDigest,
    baselineRevision,
    domains: curated.domains,
    notes: curated.notes,
    nodes: nodes.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)),
    edges: edges.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)),
    verification: verification.claims,
  };
  validateSchema(root, architecture, "architecture");
  return { evidence, architecture };
}
export function run(mode = "check", root = defaultRoot) {
  if (!["check", "sync"].includes(mode)) throw Error(`Unknown command ${mode}`);
  const generated = generate(root);
  const stale = [];
  for (const [name, value] of Object.entries(generated)) {
    const path = resolve(root, `architecture-explorer/data/${name}.json`);
    const expected = canonical(value);
    if (!existsSync(path) || readFileSync(path, "utf8") !== expected) {
      stale.push(name);
      if (mode === "sync") writeFileSync(path, expected);
    }
  }
  if (mode === "check" && stale.length)
    throw Error(
      `Generated metadata stale: ${stale.join(", ")}. Run cd architecture-explorer && npm run explorer:sync, review and stage the generated files.`,
    );
  return generated;
}
if (
  process.argv[1] &&
  realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  try {
    const { architecture: a } = run(process.argv[2] || "check");
    console.log(
      `Explorer ${process.argv[2] || "check"} passed: ${a.nodes.length} nodes, ${a.edges.length} edges. Evidence ${a.baselineRevision.slice(0, 12)}.`,
    );
  } catch (error) {
    console.error(`Architecture Explorer: ${error.message}`);
    process.exitCode = 1;
  }
}
