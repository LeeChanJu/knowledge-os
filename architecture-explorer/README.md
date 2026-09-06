# Knowledge OS Architecture Explorer

A removable, read-only **developer documentation application**. It explains this repository; it is not the deferred product graph UI, a source of canonical truth, or a runtime dependency of `knowledge_os`.

The browser loads static generated metadata. It never calls Knowledge OS, Neo4j, or a source provider. The static inspector never imports production Python, loads `.env`, reads private `data/` backups, or executes migrations/tests against a database. Only the Explorer's generated documentation is written by synchronization.

## Run locally

Use Node **20.20.1** (or a supported newer Node) and Python **3.12**. The scanner uses the existing repository `.venv/bin/python` when available, otherwise `python3`. Set `PYTHON` to an absolute Python 3.12 executable to override. Pinning the Python minor version keeps AST fingerprints comparable across machines. No production package installation is required for the Explorer.

```bash
cd architecture-explorer
npm ci
npm run explorer:check
npm run dev -- --host 127.0.0.1
```

Open [the local Explorer](http://127.0.0.1:5173). Vite is bound to loopback and restricted to this directory. After intentional documentation changes:

```bash
npm run explorer:sync
npm run explorer:check
npm test
npm run build
```

`sync` is not required for a fresh synchronized checkout. Both `vite` startup and `vite build` independently run the check. A stale model cannot build. `npm run preview` serves the already checked static build on port 4173; it makes no assertion about later repository changes.

For browser validation:

```bash
npx playwright install chromium
npm run test:browser
```

For the Python inspector, using the existing repository development environment:

```bash
../.venv/bin/python -m pytest -q -p no:cacheprovider -c /dev/null tests/test_inspector.py
../.venv/bin/ruff check scripts/inspect_repository.py tests/test_inspector.py
```

## Explore progressively

The overview shows major architectural concepts. Choose a node on the canvas or in the keyboard-accessible list to select it, reveal its direct neighborhood, highlight incoming/outgoing relationships, and open its details. Expansion is one hop, not recursive. Reference and finding nodes remain hidden initially.

Search covers hidden components and exact repository paths, within the active filters. Selecting a result expands its neighborhood. Filters restrict both visible nodes and search results; they do not imply that other repository components do not exist. A selected detail may remain open while filters hide its node. Reset clears selection, expansions, search, and filters.

The detail panel distinguishes responsibility, inputs, outputs, ownership, invariants, contracts, evidence, verification, issues, and intentional deferrals. Evidence references navigate to internal documentation details with path, qualified symbol/signature, declared fields/decorators, contract values, or migration objects. They do not expose arbitrary files. Hash links support direct navigation and browser back/forward. A reference's presence is not a passing test.

## Documentation model

| File | Ownership and purpose |
| --- | --- |
| `data/schema.json` | Versioned JSON Schema for curated architecture, verification and renderable metadata. |
| `data/curated.json` | Human-reviewed purpose, rationale, ownership, invariants, references, graph relationships, domains, and overview positions. |
| `data/verification.json` | **Explicit curated verification authority**: scoped claims, states, resolution requirements, provenance, authority snapshots and accepted dependency fingerprints. |
| `data/evidence.json` | Generated inventory of interfaces, test selectors, configuration, documentation hashes, migration objects and evidence revision. |
| `data/architecture.json` | Generated UI projection joining curated semantics, verification claims and validated references. |

The graph has its own documentation categories and relationships. These are not changes to `config/ontology.yaml`. Six contract nodes explain Source, Evidence, Knowledge, Governance, Retrieval and Action. The major domain groups are source systems, evidence lineage, governance, canonical knowledge, retrieval, service/adapters and operations/assurance; repository references have a separate navigation group.

All overview components have explicit evidence. Source Registry is a graph concept, parsing/chunking are existing functions, and Entity Resolution is limited to workspace/type/case-folded-name identity at approval. Extraction context is implemented; automated providers are deferred. Semantic/vector contract support is distinguished from inactive production vector population. MCP supports governed requests as well as reads, but cannot approve or execute. SQLite is an existing operations store, not another knowledge database.

### Implementation states

Exactly four states are used:

- **VERIFIED:** a narrowly scoped accepted verification record with executable test references, recorded outcome, authority, revision, and dependency fingerprints.
- **IMPLEMENTED:** implementation or reference exists; no blanket claim of successfully verified behavior.
- **KNOWN ISSUE:** an unresolved finding or unexecuted acceptance gate affects this scope.
- **DEFERRED:** a deliberately inactive future capability.

F1 and F2 import the explicit “corrected and verified” decision in `AGENT.md` / `AGENTS.md` and link their regression/remediation tests. Their correction revisions are `a2b36ea` and `f3bcaa1`; **Git history and commit messages are not verification authority**. The repository instruction does not contain raw execution transcripts or test counts; this limitation is visible. This task does not rerun or invent production verification.

F3–F8 remain open. F3's metadata-hash subcase overlaps the F1 correction, but the whole F3 finding is not thereby closed. The v0.1 acceptance gate remains unexecuted. The older conformance ledger's `PROVEN` snapshots do not automatically map to VERIFIED. Knowledge records' runtime `VERIFIED` label is unrelated to these implementation states.

### Synchronization and explicit reconciliation

`npm run explorer:sync` reads authoritative inputs, validates the schema and references, and writes **only** `data/evidence.json` and `data/architecture.json`. It never edits curated states, closes findings, refreshes accepted verification fingerprints, runs production tests, or stages files. Stale verification blocks sync before either generated file is written.

`npm run explorer:check` independently computes the expected projection in memory and exits nonzero for stale/missing generated files, malformed schemas, broken file/symbol/test/heading/migration/contract references, unrepresented numbered findings, changed status authorities, new/changed evaluation evidence documents, or stale reviewed verification dependencies. It never writes files or uses timestamps as freshness evidence.

When a check fails:

1. Read the named reference, finding, or authority mismatch. Correct broken references only after reviewing the actual repository change.
2. If an authority, verified implementation, or reviewed finding changed, explicitly reconcile `verification.json`. Preserve the prior claim's recorded scope and limitations. Record new executed evidence and its environment before retaining VERIFIED, or explicitly change the state and explain why. Changing a hash alone is not proof.
3. For issue resolution, review all related regressions and record the accepted result, sources, revision, executable tests and dependency coverage. Do not remove the finding to hide it. New `test_fN_*` tests require a corresponding curated finding.
4. Run sync, review the generated diff, run check and tests, and stage the intended curated/generated files together.

The initial F1/F2 dependency coverage conservatively pins all production modules, existing tests, config, migrations and dependency declarations. A normalized executable change anywhere in that coverage requires review. This favors false-positive review over a stale VERIFIED claim, without introducing a dependency-analysis framework. Open findings also pin their reviewed implementation/test scope, so a possible fix cannot silently remain represented as an unchanged open finding.

Python interfaces are generated using the standard-library AST. Bodies, line offsets and large excerpts are not copied to generated evidence. Comment, whitespace and docstring-only changes do not alter interfaces or normalized behavior hashes. Internal body changes outside reviewed/verified coverage need no prose updates. Model fields, decorators (including REST/MCP surfaces and parametrized tests), signatures, file inventories, config and migrations remain checked. Human review supplies rationale; AST inspection never invents it.

### Revision and freshness

Generated metadata contains the last relevant evidence commit and a deterministic SHA-256 of the current evidence inventory. The revision algorithm skips Explorer-only commits and Python changes that preserve the documented interfaces and reviewed semantic fingerprints; it does not trust a previously generated SHA. No generation timestamp or machine path is persisted. A commit that changes relevant evidence can advance the baseline SHA; run sync again after that commit and commit the generated metadata in an Explorer-only follow-up before pushing. That follow-up does not advance the baseline. Uncommitted relevant changes can be synchronized, but the baseline remains a historical commit; the content digest identifies the actual projected inputs.

The UI separately displays the evidence baseline, actual checkout SHA, tracked dirty indicator and schema version. “CHECKED SNAPSHOT” means check passed when the dev server started or the static build was made. It is not a live freshness guarantee. Restart after changes. There is no watcher service or database-backed freshness mechanism.

## Local hook and CI

The optional hook validates an exported **staged index**, not the working tree. It cannot hide stale staged metadata behind unstaged synchronized output. It creates and removes a temporary export, uses installed Explorer dependencies, and never stages or rewrites repository files.

From the repository root, activate once:

```bash
git config --local core.hooksPath architecture-explorer/hooks
```

This replaces the local hooksPath setting; integrate with an existing hook setup if one is already in use. It is not activated automatically by this implementation. Install the Explorer dependencies before using it.

The sole addition outside this directory is `.github/workflows/architecture-explorer.yml`. It checks a clean full-history checkout on relevant pushes/PRs, installs only Explorer/tool-test dependencies, runs the non-mutating drift/reference gate, tests, build and Chromium control tests. No production service credentials or Neo4j access are required. Local hooks can be bypassed; CI is the enforcement check. Requiring that check for merges is a repository settings decision outside this task.

## Evidence and known gaps

The model derives from the accepted stable-context ADR, registry `1.37.0`, ontology `1.0.0`, nine migrations, source modules, REST/MCP definitions, six existing Python test modules, operations/policy documentation, evaluation snapshots and current repository remediation instructions.

Remaining documentation limits:

- Existing historical evaluation records are not fresh production test executions.
- F1/F2 verification is attributed to the explicit remediation decision; raw execution logs are not supplied by that instruction.
- F3–F8 and release acceptance remain open. This application does not remediate them.
- No fuzzy entity-resolution service, automated extraction provider, or active production embedding provider is claimed.
- Provider ACL parity, host-loss recovery, off-device retention and additional-customer operational validation remain bounded by their repository evidence.
- Static analysis checks declared interfaces and references, not semantic correctness of every architectural explanation. Architecture changes still need human review.

## Removal

Disable the optional hook (or restore the previous hooksPath), remove `architecture-explorer/`, and remove its dedicated workflow. If the hook was configured using the command above:

```bash
git config --local --unset core.hooksPath
```

No Knowledge OS source, production configuration, existing tests, contracts or migrations depend on the Explorer. No persisted data needs migration or correction.

## GitHub Pages deployment

The existing workflow deploys **only `architecture-explorer/dist`** to [GitHub Pages](https://leechanju.github.io/knowledge-os/) after drift validation, tests, browser checks and the build all pass. Deployment runs on the repository's default branch, including an explicit workflow dispatch; pull requests validate without publishing. No runtime API, Neo4j connection, credential, authentication service or production deployment is introduced.

This GitHub repository is a public snapshot mirror with its own Git history. Its source tree was confirmed identical to the local source tree before the Explorer was added. Historical correction IDs such as F1's `a2b36ea` and F2's `f3bcaa1` refer to the original source history; the public mirror need not contain those objects. Their curated `revisionScope` makes that provenance explicit. The check still requires the recorded remediation authority, executable references and exact accepted dependency fingerprints; a Git message or missing historical object does not supply proof. Repository-scoped revision claims continue to require a resolvable commit.

Generated metadata is synchronized against the history of the checkout being published. The public evidence baseline can therefore differ from the local baseline while documenting identical source content. No local/private history is pushed to make the histories match.
