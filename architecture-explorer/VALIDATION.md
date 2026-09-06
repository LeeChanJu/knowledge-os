# First-milestone delivery report

Evidence baseline: `4a0493a8fd25ff7c91d8332344cbd4b991146f26`. This report concerns the Explorer only, not Knowledge OS release acceptance.

## Delivered model

- **29 overview nodes / 38 overview relationships.**
- **214 total nodes / 372 total relationships**, progressively revealed.
- 45 curated architectural nodes, 160 validated repository-reference nodes, and 9 finding/gate nodes.
- 124 repository evidence files; 30 Python modules with 521 generated qualified symbol/signature/test records; nine migration files.
- Seven architectural domain groups: source systems, evidence lineage, governance, canonical knowledge, retrieval, service/adapters, operations/assurance. Repository references are an eighth navigation group.
- Six stable contract nodes: Source, Evidence, Knowledge, Governance, Retrieval, Action.

The overview contains every requested concept and the existing SQLite operations store. Source Registry is the existing Source concept, not an invented service. Direct `HAS_DOCUMENT`, `HAS_VERSION`, `HAS_CHUNK`, and `EVIDENCE_FOR` links preserve the evidence chain. Proposal and Approval remain separate expansion nodes with explicit promotion relationships.

## Verification performed

- Deterministic sync/check and schema/reference validation passed. Repeated sync produces identical bytes; check does not write.
- **22 Node tests passed.** The suite covers graph expansion/filtering/routing, lineage, generated-file tampering, removed files/migrations, missing symbols/tests/headings, contract drift, reviewed verification invalidation, comments/formatting, issue/evaluation authority changes, new findings, bad IDs/paths, revision stability, staged-versus-working-tree differences, and a direct Vite build rejecting stale metadata.
- **3 Python inspector pytest tests** and Ruff passed.
- TypeScript checking and the Vite build passed. Metadata and Cytoscape are separate static chunks.
- **2 Chromium browser scenarios passed** (27 tests total). The main scenario exercises canvas selection, progressive expansion, detail/evidence tabs, internal file references, browser back/forward, zoom, fit, pan, reset after expansion and panning, hidden-node search, search clearing/no results, domain and every state filter, empty-map recovery, finding/proof details, themes and theme persistence. The second covers unknown/direct hash links and a narrow viewport.
- Browser request capture found no requests outside the local Explorer origin. No Knowledge OS API, provider, or Neo4j request occurred.
- Dark overview, expanded finding, and light overview screenshots were inspected. A position-object mutation/reset defect found during visual QA was corrected and covered by repeated canvas selection after reset.
- Production source, existing tests, ADRs, contracts, migrations, configuration, AGENT.md and AGENTS.md have no tracked diff. No root index changes were staged by this task.

The GitHub Actions workflow is supplied but has not run on GitHub in this task. Its commands were exercised locally. The optional local hook is supplied and tested with isolated Git index exports; activation remains the documented one-time developer command.

## Evidence and limits

The accepted stable-context ADR, contract registry 1.37.0, ontology 1.0.0, migrations 001–009, GraphStore/models, source adapters, REST/MCP surfaces, operations/recovery modules, existing unit/real-Neo4j regression definitions, current repository instructions and evaluation records ground the model.

F1/F2 VERIFIED are scoped imports of the explicit repository remediation decision, linked to executable regression evidence. Their correction commits locate code; Git messages do not prove verification. Raw execution transcripts are not supplied by the repository instruction. This task did not rerun production tests or renew production verification.

F3–F8 and the v0.1 acceptance gate remain open. F3's partial overlap with F1 is explicit. Production embedding activation, automated extraction, fuzzy entity disambiguation, full provider ACL parity, host-loss/off-device recovery and additional-customer operational validation are not invented or represented as proven.

## Files added

Everything below is under `architecture-explorer/`, except the one approved workflow:

- `.gitignore`, `README.md`, `VALIDATION.md`
- `package.json`, `package-lock.json`, `index.html`, `tsconfig.json`, `vite.config.ts`, `playwright.config.ts`
- `data/schema.json`, `data/curated.json`, `data/verification.json`, `data/evidence.json`, `data/architecture.json`
- `scripts/inspect_repository.py`, `scripts/explorer.mjs`, `scripts/check-staged.mjs`, `hooks/pre-commit`
- `src/main.tsx`, `src/App.tsx`, `src/Graph.tsx`, `src/model.ts`, `src/graph-state.mjs`, `src/style.css`
- `tests/graph-state.test.mjs`, `tests/synchronization.test.mjs`, `tests/test_inspector.py`, `tests/browser/explorer.spec.ts`
- Repository root: `.github/workflows/architecture-explorer.yml`

Build output, dependencies, test artifacts, and browser screenshots remain ignored. No production configuration, service or database was added.

## Run

```bash
cd architecture-explorer
npm ci
npm run explorer:check
npm run dev -- --host 127.0.0.1
```

Open [the local Explorer](http://127.0.0.1:5173). See [README](README.md) for synchronization, explicit verification reconciliation, optional hook activation, CI, and removal.
