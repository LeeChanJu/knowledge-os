# System Atlas continuation

The user approved continuation after reviewing M2. The existing IA is preserved.
This increment groups Runtime expansion (M3), Engineering branches (M4), and
bilingual navigation/drift validation (M5). It does not extend Knowledge OS runtime.

## Delivered scope

- Six Runtime journeys, each with its full backbone on entry. Read has 8 stages,
  ingestion 9, provenance 4, remember 5, correction 4, external action 5.
- The original 10-stage Engineering backbone remains visible. Detailed paths bind
  concrete invariants to code, regressions and existing verification records.
- 116 nodes and 145 edges. Educational prose: 232 node Markdown files plus 12
  journey comprehension files. No educational database or runtime dependency.
- Journey selection and cross-axis links preserve hash navigation, selected ancestors
  and the return journey. Collapse, search, language changes and old URLs coexist.
- Separate current/target/human/deferred explanations prevent end-to-end automation
  or third-party capabilities from being presented as existing product behavior.

## Evidence and preserved boundaries

Accepted ADR 0001, contract registry 1.37.0, current architecture inventory, source
and migration references, existing regression selectors, and curated verification
records supply implementation evidence. Source inspection included ontology scalar
validation, graph split_text, temporal helpers, Notion executor, recovery functions,
core constraints and deletion-replay fixtures. Earlier operational ledger entries
are historical, not fresh verification. F1/F2 remain scoped; F3–F8 and the release
gate remain open. This task executes documentation tests only, not production/DB
regressions. No production files, contract, migration, verification record or DB
were changed.

## Review routes

- `/#/ko-KR/runtime?journey=ingest`
- `/#/en/runtime?journey=act&node=act-execute`
- `/#/ko-KR/engineering?node=executor-proof`
- `/#/en/engineering?node=backup-read`
- `/#/en/engineering?node=release-accept`

## Limits

A scoped result is not full subsystem verification. The history branch does not
claim fresh temporal execution. Generic source automation, SAP execution, production
semantic population and host-loss recovery are not promised. The preserved 77-page
catalog records reclassification without destructive retirement or rewritten bodies.
A real beginner's comprehension still needs user review; automated tests establish
navigation and reference integrity, not educational effectiveness.

## Validation

- Atlas schema/reference/drift regressions: 13 passed.
- Full browser suite: 22 passed, including all six journeys in both languages,
  cross-axis returns, original M2 route, branch collapse, history, mobile, glossary,
  old documents and Architecture navigation. Local documentation requests only.
- `explorer:check` passed against current local evidence `7fd035395c2e`.
- Publication source synchronization and TypeScript/Vite build passed against the
  public evidence baseline `5275071c977d`; public verification records are preserved.
- Screenshots: `test-results/atlas-release.png`, `atlas-ingest-mobile.png`, and
  `atlas-expanded-{ko-KR,en}.png` (the latter captures the language-switch result).
- Changes are confined to `architecture-explorer/`. No database regression runs.
