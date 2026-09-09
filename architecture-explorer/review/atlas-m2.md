# System Atlas — M1 / M2 review

Scope: the approved dual-roadmap IA, without expanding into M3. Runtime's eight-step
read/query backbone and Engineering's ten-step backbone are complete on entry.
A persistent topology distinguishes external originals, observation/ingestion,
Knowledge OS, Neo4j, the adapter and the user/assistant request-response path.

The implemented detailed branch is:

Question/read → return support → check evidence → the document as it was → why
preserve versions → Engineering's preservation rule → storage implementation →
metadata integrity regression → scoped executed evidence → original question flow.

The map is React controls with SVG directional connectors, not a new graph engine.
The existing Cytoscape Architecture remains separate. Opening a branch retains the
backbone's layout; the active ancestor path remains in a persistent strip. A new
backbone selection changes the active branch lane, rather than recursively opening
every subtree. Closing the drawer does not collapse the map. Explicit collapse,
search, zoom, fit, drag/scroll pan, keyboard focus and browser history are supported.

## Routes

- `/#/ko-KR` and `/#/en`: two-question Atlas entry.
- `/#/{language}/runtime`: read/query roadmap, no drawer initially.
- `/#/{language}/engineering`: full engineering backbone, no drawer initially.
- Query parameters `node`, `root`, `open`, `returnTo` preserve spatial context.
- The `atlas` query on Reference/Architecture links preserves return to the exact
  selected roadmap stage, including through subsequent graph node selections.
- Existing Learn and Reference routes retain their content. The approved 77-page
  reclassification is recorded in `content/atlas/catalog.json`; planned merges and
  redirects are not destructive changes in M2.

## Repository evidence

Current local source HEAD: `2a730fff3fe29bebc9b0d00acf724cc7cc0d2672`.
The Atlas references the checked existing architecture inventory and curated
verification records. F1 is exposed after the plain-language integrity explanation,
not as a navigation root. Rules link ADR 0001 and registry 1.37.0; storage links
`GraphStore._write_version` and `source_metadata_fingerprint`; regression links name
exact F1 selectors and `tests/test_metadata_correction.py`. Execution details use
the existing F1 record and its Korean translation. Code/test existence is not proof.
Current local evidence and the publicly available GitHub snapshot are distinguished.
No claim state, production file, migration, runtime test or database is changed.

## Data and checks

`content/atlas/model.json` has 28 nodes, 35 directed relationships, complete 8/10
backbones and explicit cross-axis mappings. `schema.json` rejects a node-provided
verification status: the only authority remains `data/verification.json`.
Educational prose is in 56 small Korean/English Markdown files. `review.json`
pins reviewed metadata/prose; `catalog.json` preserves all 77 legacy body hashes.

`check-atlas.mjs`, integrated into `explorer:check` and therefore the existing hook
and CI, rejects missing backbones, renamed references, branch cycles, unreachable
cross-axis targets, lost legacy content, missing translations and stale review
hashes. It performs no imports or execution of production modules and never changes
verification states. Eight new metadata regression tests cover these failures.

## Review / remaining scope

Review the required round trip in both languages before M3. Source ingestion,
conversational write, correction and external-action deep journeys have not been
expanded as Atlas experiences. Most Engineering steps provide only orientation and
links to the existing Architecture; their detailed branches remain later work.
No new F1/F2 or temporal verification is claimed, and no database test was executed
for this documentation change. The one-minute beginner comprehension criterion
still needs a real reader's review.

Screenshots from browser tests: `test-results/atlas-{ko-KR|en}-runtime.png`,
`atlas-{ko-KR|en}-engineering.png`, `atlas-mobile.png`, `atlas-light.png`.
This milestone is local review only; GitHub Pages has not been updated for M2.

## Completed UI and build checks

- Browser suite: 18 passed, including both languages of the exact requested round
  trip, all legacy pages, Architecture controls and the existing hover regressions.
- Following the final breadcrumb/input/detail refinements, all four Atlas browser
  tests passed again. Browser requests stayed on the local documentation origin.
- Atlas metadata regression tests: 8 passed.
- `npm run explorer:check`: passed against local evidence baseline `7fd035395c2e`.
- Final TypeScript/Vite build: passed. The existing static bundle size advisory
  remains (about 1.17 MB before gzip); this is not a build failure.
- `git diff --check`: passed; no changed paths outside the Explorer.

- Full Explorer unit/synchronization suite: 59 passed, 0 failed/skipped. This includes
  temporary Git/index exports and non-mutating checks; production modules were not
  run as a database regression suite. Final Atlas metadata checks: 8 passed.
