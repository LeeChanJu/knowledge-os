# North Star conformance ledger

- Evidence snapshot: 2026-09-06
- Contract registry at this evidence snapshot: `1.37.0`
- Status vocabulary: `PROVEN`, `PARTIAL`, `GATED`, `DEFERRED`

This ledger prevents implementation activity from being mistaken for completion. `PROVEN` requires
current code plus executed evidence at the scope claimed. `PARTIAL` means the stable contract exists
but a named operational scope is not yet demonstrated. `GATED` requires an external credential,
human decision, or authorized System-of-Record capability. `DEFERRED` is intentionally outside the
minimum sufficient system until measurements require it.

The governing rule remains:

> Do not redesign working foundations without evidence. Extend stable contracts rather than
> replacing the architecture.

## Requirement ledger

| North Star requirement | Status | Current authoritative evidence | Remaining proof or gate |
|---|---|---|---|
| Sources remain Systems of Record | PROVEN | Filesystem, Notion ingestion, and Google Drive source adapters are read-only; source bodies enter Neo4j through manifest-v2. A separately authenticated official Notion MCP performed one explicitly user-approved source mutation and the read-only connector subsequently versioned it; the MCP did not make canonical graph knowledge. The governed executor then performed one owner-approved, claim-bound Notion creation through the source API, after which the read-only connector versioned the result as source evidence. | Direct hosted-MCP writes remain outside Knowledge OS Action governance and must stay user-explicit. The internal connection now has read, insert, and update capability, but Knowledge OS can use writes only through a separately approved bounded Action and executor policy. |
| Neo4j is the System of Context | PROVEN | Source lineage, semantic primitives, full-text index, and the 1,536-dimensional vector index use the local Neo4j instance. SQLite is limited to operations evidence. Doctor passes 40 checks. | None for the current local deployment. |
| Provenance, versions, temporal validity, and decision history | PROVEN | `Source -> Document -> DocumentVersion -> Chunk`, immutable authorization snapshots, temporal canonical models, content-addressed Proposals, and immutable Approval history are implemented and tested. A real Codex MCP search-to-Evidence chain returned the new Notion Chunk's exact DocumentVersion, Source ID/type/URI, and both historical and current ACL snapshots. | Continue adding read-only invariants when measured corruption modes appear. |
| Stable knowledge primitives | PROVEN | Constraints and contracts exist for Source, Document, DocumentVersion, Chunk, Entity, Assertion, Event, Decision, Action, Proposal, and Approval. Human approval promoted two personal Decisions and four evidence-linked Assertions across five Entities; Doctor found zero integrity violations. | Add records only when real evidence or governed capabilities require them. |
| Extracted knowledge cannot silently become canonical | PROVEN | MCP can create and inspect Proposals but exposes no approval/rejection tool. Human review requires a separately configured actor and explicit `--yes`; all three approved personal Proposals retain their Approval traces. | Zero personal Proposals are pending at this snapshot. Future extraction remains proposal-first. |
| Deterministic, idempotent, deduplicated, recoverable ingestion | PROVEN | Stable IDs, compare-and-set versions/cursors, atomic manifest-v2, tombstones, state-after-commit, exact replay tests, and verified cross-store recovery sets are present. The latest post-Action recovery set was restored to a separate database, exactly matched all manifest topology plus Action/Execution state, passed all 40 Doctor checks and the authorization suite, and was removed without touching the active database. Source-v11 also refuses an empty first connector inventory over existing active Documents, closing a wrong-account checkpoint risk measured against the live Drive API. | Provider-authenticated personal refreshes are separate source gates below. Host-loss recovery and off-device retention remain outside the local same-DBMS proof. |
| Google Drive personal ingestion | PROVEN | Dedicated authorized-user ADC refreshes without persisted access tokens. A provider-authenticated 12-file snapshot promoted source-v11 versions; the next run had 12 unchanged items and no new Chunks or tombstones, and the stable third replay reused the exact sync-run/checkpoint with manifest-level `unchanged=true`. Source-v12 narrows every refreshed access token to `drive.readonly`; live token introspection proved the unrelated scopes were absent. Google Auth Platform now declares that exact scope. | The owner accepted Testing mode with manual reauthorization after seven-day expiry. Unattended credential durability is intentionally not claimed for the personal deployment. |
| Notion ingestion | PROVEN | The page-tree connector handles pagination, nested blocks, data sources, deterministic content, completeness failure, and connection identity. Its owner-only `0600` token remains outside Git. After the hosted-MCP and governed Action creations, the connector versioned each new child and changed parent through manifest-v2. After approved test cleanup, it created a new parent version and tombstoned only the governed test Document while retaining history. The immediate replay created zero Chunks; the stable third refresh returned no records and reused the exact sync-run, checkpoint Event, and cursor. | Expand the explicitly shared corpus only as desired. Human/group ACL parity remains an explicit source-API limitation. Insert/update capability is governed separately from the read-only ingestion process. |
| Meeting ingestion | PROVEN | VTT/SRT use the proven filesystem manifest path, retain transcript cues verbatim, and pass deterministic fixture ingestion tests. Notion-native meeting pages use the proven generic page-tree path without a meeting-specific architecture. A read-only discovery found no real personal transcript in the currently authorized corpus. | Functional support is complete. Validate additional exporter formats only when a real source requires them; do not manufacture personal meeting knowledge from fixtures. |
| Keyword retrieval | PROVEN | Personal and held-out golden-question suites execute against Neo4j full-text search with access filtering, literal query handling, trace IDs, and versioned ranking evidence. | Improve ranking only when a versioned suite demonstrates a regression or material quality gap. |
| Semantic and hybrid retrieval | PROVEN | Neo4j vector storage, immutable embedding provenance, semantic/hybrid contracts, model isolation, capability discovery, MCP projection, and fixture execution are tested. A versioned Korean cross-lingual development suite measured BGE-M3 at 1.0 recall/0.95 MRR dense and 1.0/1.0 hybrid. Multilingual-E5-large won development but lost held-out recall, so neither candidate replaced the working keyword baseline. | Functional support is complete. The personal corpus intentionally has 0/82 current Chunks embedded and reports semantic availability false until a provider passes fresh acceptance evidence; do not change the 1,536-dimensional index merely to make the flag true. |
| Graph retrieval | PROVEN | Traced authorized Entity discovery plus Entity, neighbor, canonical Assertion, Decision, and semantic Event Knowledge Service/MCP contracts exist; temporal reads support as-of filtering. A real MCP client in the `google-drive:me` context discovered Knowledge OS, its four approved neighbors, and a `VERIFIED` evidence-backed Decision with one Approval; an unauthorized principal received zero discovery results and 404 for the known Decision ID. | Extend only with approved evidence-backed knowledge. |
| Stable Knowledge Service and replaceable adapters | PROVEN | REST is the stable service contract; MCP is a bounded adapter used by Codex and Claude Code without Cypher credentials or direct canonical mutation. Host registrations now carry the exact Google Drive and Notion source principals. A fresh Codex MCP client retrieved both authorized Notion Chunks through Knowledge Service, while a one-run unauthorized principal received zero results. Source-v12 exposes authorized Source/Document provenance and checkpoint discovery without bulk body reads while keeping narrowed OAuth refresh inside the source adapter. | A2A and custom UI remain replaceable future adapters; absence does not justify changing service contracts. |
| Source authorization and future workspace isolation | PROVEN | Current DocumentVersion ACL controls evidence reads and governance; traces, feedback, and evaluations carry workspace/access fingerprints. Cross-workspace and cross-principal tests fail closed. After the Notion credential gained insert/update capability, a live Knowledge Service regression still returned the governed page only to the exact source principal while an unrelated Notion principal received zero results. | A full ReBAC engine is deferred until actual group/workspace requirements exceed source ACL snapshots. |
| Telemetry, traces, evaluation, feedback, and errors | PROVEN | The existing local SQLite store contains bounded adapter telemetry, retrieval traces, evaluations, audit records, errors, and tenant-scoped feedback/evaluation provenance. | Do not add an observability stack without measured operational insufficiency. |
| Git-versioned contracts, ontology, migrations, prompts, and code | PROVEN | Contract registry, ontology, checksum-protected Neo4j migrations, immutable prompt versions, tests, and evaluation records are committed. Doctor compares the migration ledger with Git. | SQLite schema evolution is code-controlled and recovery-protected; introduce a separate migration framework only if measured evolution complexity requires it. |
| Governed, auditable Actions | PROVEN | Action request, review, capability principals, type-specific policy mapping, atomic claim lease, stable external idempotency key, and immutable execution evidence contracts exist. Knowledge OS MCP cannot approve or execute Actions. One live owner-approved Notion creation produced one completed Claim and one successful Execution; its terminal replay stopped before provider access. The unapproved compensation first stopped before policy validation, then executed exactly once after a separate explicit owner approval. Read-only re-ingestion tombstoned the page and retained its version history. | Each future capability and concrete mutation still requires its own bounded policy, authorized API, and approval boundary. |
| Minimum sufficient engineering | PROVEN | The system remains Neo4j plus local SQLite and uses no extra vector DB, queue, orchestrator, authorization engine, or observability platform. | Any replacement requires evidence listed in `config/contracts.yaml`. |
| Reusable customer-specific Context Graph | PROVEN | Workspace-scoped graph queries, source ACL enforcement, access-bound operations evidence, and isolated customer fixtures demonstrate that the same Source, Evidence, Knowledge, Governance, Retrieval, and Action contracts can be reused without architectural redesign. | A real second customer or SAP delivery deployment is future operational validation, not a prerequisite for the current reusable architecture. Record it when such a corpus is authorized. |

## Current data evidence

- Personal workspace: one Google Drive Source plus one checkpointed Notion Source, 14 active
  Documents, 14 current DocumentVersions, and 82 active Chunks. Google Drive contributes 12/12/80;
  Notion contributes 2/2/2. The graph retains 15 Documents, 30 DocumentVersions, and 166 Chunks
  including the tombstoned test history.
- Personal governance: zero pending Proposals, three approved Proposals, five Approvals, five
  Entities, four Assertions, two Decisions, two approved and successful Actions, two completed
  execution Claims, and two successful Executions.
- Semantic readiness: 0 of 82 current Chunks embedded; vector index online at 1,536 dimensions with cosine
  similarity.
- Graph readiness: five accessible personal Entities and `graph_available=true`; every record was
  promoted through explicit evidence review and immutable Approval history.
- Operational evidence at this snapshot: 455 telemetry rows, 221 retrieval traces, 164 evaluations,
  38 audit rows, three recorded errors, and zero durable feedback rows.
- Integrity: 111 tests passed; Doctor passed 40 checks; broad topology audit found zero isolated
  stable primitives.
- Latest verified recovery set: `20260905T191640Z-6a16d7ff`, captured from clean commit `f0ec6d5`
  after the approved compensation and stable tombstone replay;
  artifact hashes, SQLite integrity, and Neo4j archive consistency passed. Its manifest pins contract
  registry `1.37.0`, all nine applied migrations, 15 retained Documents, 30 DocumentVersions, 166
  retained Chunks, both successful Actions and Executions, and the 455/221/164
  telemetry/retrieval/evaluation snapshot. The preceding post-Action set was restored in an isolated
  drill that exactly matched its manifest, passed Doctor 40/40 plus the authorization suite, and was
  removed without touching the active database. The latest set changed data state rather than
  schema or recovery machinery, so archive verification was repeated without another restore drill.

Counts are evidence snapshots, not architectural constants. Re-run the source queries and Doctor
before using them for a later decision.

## Operational follow-ups and completed gates

1. **Human governance gate — completed 2026-09-06:** the user explicitly approved all three
   evidence-reviewed Proposals; the graph now retains three Approvals and the promoted records.
2. **Semantic provider activation — deferred by evidence:** select one reproducible document/query embedding runtime and exact
   model version. Populate only authorized current Chunks, then compare semantic and hybrid results
   against the checked-in held-out suite before changing retrieval foundations. BGE-M3 revision
   `5617a9f...` plus its title-composition and query-instruction variants did not justify replacing
   the current baseline. A new Korean cross-lingual development suite exposed the real bilingual
   keyword gap; E5 won that development comparison but its one-time held-out run lost recall despite
   higher hybrid MRR. The original held-out suite is now spent. Continue candidate work only on the
   development suites until a new human-reviewed holdout or materially new corpus exists. Semantic
   retrieval support is implemented and tested; provider population is intentionally inactive rather
   than a missing architectural capability.
3. **Google Drive source gate — completed 2026-09-06:** dedicated refresh-capable ADC, complete
   12-file provider snapshot, unchanged content replay, and exact manifest/checkpoint replay are
   proven, and the console declares only the required Drive scope. The owner selected personal
   Testing mode with manual seven-day reauthorization; do not introduce domain/branding work unless
   unattended operation becomes a measured requirement.
4. **Notion source gate — completed 2026-09-06:** the existing internal connection was used for a
   live refresh of the explicitly shared root. The first run observed one unchanged page and
   committed the provider cursor without a content change; the immediate replay reused the same
   sync-run identity with `unchanged=true` and zero records. Content update and insert capabilities
   were initially disabled, and the same provider replay passed again with only content-read
   authorization. The token is retained in an owner-only local file outside Git, and the installed
   connector replayed successfully without process credential variables. Do not claim human ACL
   parity or expand page access without an explicit sharing decision. An explicitly approved
   official Notion MCP write and a later governed Action each created one child page; the read-only
   connector imported them and their parent changes. The owner then explicitly enabled content
   insert/update for the governed Action path, without changing the ingestion process into a writer.
   The immediate replay reused all three DocumentVersion IDs and created zero Chunks; the stable
   third replay reused the exact sync-run, checkpoint Event, and cursor with no records.
5. **Action execution gate — live creation accepted 2026-09-06:** the owner approved
   `notion-create-page-policy-v1` and one concrete disposable page creation. A separate executor
   enforces `human:owner` review,
   `connector:notion` execution, the one shared root, bounded plain-text parameters, one call per new
   claim, fail-closed ambiguous outcomes, and a separately approved `in_trash` compensation Action.
   MCP maps exact Action types to policies and still cannot approve or execute. Fake-transport tests,
   the 111-test suite, installed-wheel check, and Doctor 40/40 pass. The live Action produced exactly
   one completed claim and one successful execution; a later execution attempt stopped before
   provider access and left those counts unchanged. Read-only re-ingestion preserved Notion
   provenance and ACL metadata, and the immediate replay created zero Chunks. The owner explicitly
   enabled Content Insert and Content Update on the internal connection for this governed path.
   The target-bound archive compensation first failed closed while unapproved, then executed once
   after a separate explicit owner approval. Re-ingestion tombstoned the test page, retained its
   historical version and Chunk, and reached exact stable replay. The earlier direct hosted-MCP test
   is not retroactively represented as governed.
6. **Customer/SAP operational validation — future:** when a separately scoped real corpus is
   authorized, ingest it and run authorization plus retrieval evaluations before claiming that
   specific deployment is production-ready. The current contract reuse claim is limited to the
   tested architecture and does not claim an existing customer deployment.

These gates do not authorize credentials, Proposal decisions, external mutations, or new platform
dependencies. Until a gate is supplied, safe work should improve evidence, integrity checks, and
existing contracts rather than simulate completion.
