# Capability Learn IA delivery

## Scope

The latest user request explicitly authorized implementation of the IA attachment,
including reclassification of the existing 77 pages. The attachment's older
plan-only wording was superseded. All work remains isolated in the Explorer.
No production behavior, migration, contract or verification state was changed for
this IA task. Earlier working-tree changes from the flagship milestone remain.

## What changed

- The glossary hover link has a safe pointer corridor and delayed outside dismissal.
  A browser regression failed on the original gap crossing and passed after the fix.
  Selecting the learning link closes the popover, so it cannot obstruct the destination.
- Learn starts at one complete mental model and branches into six capabilities.
  Google Drive / Notion / Files and their original documents remain outside Knowledge OS.
- There are six bilingual capability journeys, 26 stages, twelve new Markdown files,
  inline concept explanations and optional detailed references. Each journey has two
  substantive answer/reveal comprehension checks and four explicit capability boundaries.
- All 77 legacy page bodies are preserved: 1 flow entry, 34 deep dives, 19 explanations,
  23 references. All 76 non-entry old Learn paths have aliases. The old full Start Here
  is also retained at `reference/deep-dives/start-here`.
- A persistent position trail carries capability and stage through explanations,
  generated implementation evidence and graph navigation; language changes and browser
  back/forward retain it. Learn, Explore and Reference have distinct jobs.

## Structure

`content/ia/` contains navigation, classifications, stage references and reviewed
bilingual fingerprints. `content/journeys/{ko-KR,en}/` contains educational prose.
`data/verification.json` remains the curated verification authority;
`data/evidence.json` remains generated repository evidence. None of these is a new
runtime ontology or knowledge database.

The complete old-to-new route table is in `learn-ia-audit.md`. README documents the
six route slugs, content structure, validation and local run commands.

## Evidence and limits

Journey evidence IDs point into the existing checked architecture inventory:
source/evidence lineage, graph storage, retrieval, ontology, proposal/approval,
correction, action adapters, matching tests, contracts and ADRs. The UI opens exact
repository references and existing pinned GitHub links. A code location is not a
new successful execution. Current behavior, human authorization and deferred scope
remain separate from target conversations. Relevant F1–F8/release-gate records are
linked from capability boundaries, as applicable; this milestone does not rerun or
reclassify production verification.

Remaining editorial work: some preserved reference bodies still have their older
presentation style; non-destructive merges and executable how-to guides require
separate evidence-preserving work. A real beginner still needs to assess the
one-minute comprehension criterion. Browser tests do not establish that outcome.

## Local routes and screenshots

Use `http://127.0.0.1:5177/#/ko-KR/learn/start-here` for the running development
server, or the port printed by `npm run dev -- --host 127.0.0.1`. Replace `ko-KR`
with `en` for English. Journey slugs: `remember`, `find`, `relationships`, `sources`,
`correct`, `act`.

Browser runs save `test-results/ia-{language}-home.png`,
`ia-{language}-{journey}.png` and `ia-{language}-mobile.png`. These generated review
screenshots are ignored by Git. This task updates the local app; it does not publish
a new GitHub Pages snapshot.

## Validation results

- `npm test`: 48 passed, 0 failed/skipped (includes deterministic synchronization,
  stale verification, renamed references, authority changes, revision handling,
  temporary staged-index exports and non-mutating checks).
- After the last guard additions, focused IA and graph suites: 14 passed,
  including three new checks beyond that full run. Final capability-to-finding
  reference checks: 6 passed.
- Full browser suite: 13 passed. Following the final map-route correction,
  all four IA browser tests passed again, including the newly added map/primer
  regression. Both hover regressions also passed after the popup-close fix.
  Combined coverage is 14 distinct browser tests. Both language paths visit every
  capability stage. Captured browser requests stayed on the local documentation app.
- `npm run explorer:check`: passed, 214 architecture nodes / 372 edges.
- Final `npm run build`: passed with checked metadata; Vite reports the existing
  large static bundle advisory (about 1.1 MB before gzip). No build failure.
- CUA visual review: Korean/English entry, concept branch, dark/light reading.
  Playwright screenshots additionally cover desktop and 390 px mobile views.
- `git diff --check`: passed. Git status contains no changes outside
  `architecture-explorer/`; no production regression/database suite was run for
  this documentation-navigation change.

## Added files for this IA task

- `src/docs/Term.tsx`, `src/docs/LearnIA.tsx`, `src/docs/ia.ts`
- `content/ia/catalog.json`, `content/ia/journeys.json`, `content/ia/review.json`
- `content/journeys/en/{remember,find,relationships,sources,correct,act}.md`
- `content/journeys/ko-KR/{remember,find,relationships,sources,correct,act}.md`
- `scripts/check-ia.mjs`, `tests/ia.test.mjs`
- `tests/browser/ia.spec.ts`, `tests/browser/hover.spec.ts`
- `review/learn-ia-audit.md`, `review/learn-ia-delivery.md`

Existing Explorer routing, shared map, flagship/reference wrappers, graph hash
handling, stylesheet, content checker, README and relevant Explorer tests were
updated to integrate them. The previous flagship work was not discarded.
