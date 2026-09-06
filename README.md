# Knowledge OS

Architecture Freeze v1 - 2026-09-02

The versioned architecture decision and stable contract registry are in
[`docs/architecture/0001-stable-context-contracts.md`](docs/architecture/0001-stable-context-contracts.md)
and [`config/contracts.yaml`](config/contracts.yaml).
The requirement-by-requirement evidence ledger and remaining completion gates are maintained in
[`docs/architecture/north-star-conformance.md`](docs/architecture/north-star-conformance.md).
Provider-neutral extraction prompts and their checksums are registered in
[`config/prompts.yaml`](config/prompts.yaml); changing prompt content requires a new version.
`GET /v1/ontology` and `GET /v1/prompts/{name}` expose the exact versioned extraction context to
replaceable adapters without coupling them to repository paths. Prompt output can only enter the
graph through governed Proposal endpoints.
MCP `get_contracts` exposes the same Git-controlled contract registry and highest-order change rule,
so agents negotiate current boundaries rather than assuming them.
MCP also exposes bounded Source and Document catalog reads, including connector/checkpoint status,
current authorization, and immutable version metadata. It never exposes bulk document bodies through
the catalog path; agents resolve exact authorized evidence through the existing Evidence contract.
Canonical Assertion, Decision, and semantic Event records are likewise readable by stable ID
through REST and MCP with the same source authorization and optional as-of semantics; approval
remains outside the agent adapter.
`POST /v1/evidence/bundle` resolves a bounded set of exact Chunk IDs with their immutable
DocumentVersion and Source provenance. It returns the bundle only when every requested Chunk is in
the workspace, its Document remains active, and the caller can read the Document's latest ACL
snapshot; missing and unauthorized inputs fail closed with the same response.

This Knowledge OS is a customer-specific System of Context, not a replacement for
Systems of Record. It compounds semantic knowledge, evidence, decision history,
and feedback into a governed Context Graph consumable by agents.

Storage, retrieval, model, visualization, and agent protocols are replaceable
implementations behind stable contracts. Operational actions must execute through
authenticated, authorized, and auditable APIs or tools with policy and human approval
boundaries.

## Frozen boundaries

- Source of truth: Notion, Google Drive, files, and other original systems
- Evidence lineage: `Source -> Document -> DocumentVersion -> Chunk -> Assertion`
- Semantic layer: canonical `Entity`, temporal `Assertion`, `Event`, and `Decision`
- Governance: `Proposal -> Approval -> canonical graph`
- Knowledge store: Neo4j Desktop 2 local instance (`sap-ax-kg`) running Neo4j
  2026.07.1, with graph + vector index + full-text index
- Operations/evaluation store: SQLite
- Stable service boundary: REST now; MCP and A2A remain adapters
- Deferred until measured: external vector DB, ReBAC engine, action execution, custom UI

## Run locally

```bash
cp .env.example .env
uv sync --extra dev --no-editable
PYTHONPATH=src uv run --no-sync python -m knowledge_os.migrate
uv run --no-sync uvicorn knowledge_os.api:app --app-dir src --reload
```

Because the environment intentionally uses a non-editable local wheel, rebuild it after changing
Python source or entry points:

```bash
uv sync --reinstall-package knowledge-os --extra dev --extra connectors --no-editable
```

Relative `OPS_DB_PATH`, `ONTOLOGY_PATH`, `CONTRACTS_PATH`, `PROMPTS_PATH`, and
`MIGRATIONS_PATH` values are resolved from the process working directory. A wheel may run outside
the repository only when these paths are supplied as absolute environment values pointing to the
same Git-controlled deployment configuration. Configuration and migrations are not copied into
the wheel as a second source of truth.

Before running migrations, start `sap-ax-kg` from Neo4j Desktop and put that
instance's password in `.env`. The application connects to the Desktop instance
at `bolt://localhost:7687`; Docker is not used by this project.

Open API docs at <http://localhost:8000/docs>. Use Query and Bloom from Neo4j
Desktop for database inspection and visualization.

`GET /health` is a lightweight connectivity probe. `GET /health/readiness` and the local command
below perform read-only integrity checks and return a non-success status when an invariant fails:

```bash
knowledge-os-doctor
```

The doctor checks document/current-version cardinality, version and Chunk parentage, lifecycle
flags, Source connector binding and Workspace ownership, supersession cycles, Proposal and
canonical evidence workspace boundaries, Action
workspace ownership, applied migration checksums, Neo4j index state, and SQLite integrity. It
reports bounded sample IDs but never repairs or deletes data automatically.

Filesystem, Notion, and Google Drive CLI runs record success/failure timing through the existing
SQLite operations store. Connector failure records contain stable adapter context and a correlated
error ID, but deliberately exclude credentials, source identifiers, paths, and content.

## Backup and recovery

`knowledge-os-recovery create` produces one local recovery set containing an official Neo4j
Enterprise full backup, an online SQLite backup, stable-contract versions, the Git revision and
dirty flag, capture-window timestamps, and SHA-256 evidence for both artifacts. It does not stop
Neo4j or mutate the graph. `verify` checks every hash, runs SQLite's integrity check, and runs
Neo4j's offline archive consistency checker in a temporary directory.

```bash
knowledge-os-recovery create \
  --neo4j-admin /path/to/dbms/bin/neo4j-admin \
  --java-home /path/to/desktop/runtime/Contents/Home
knowledge-os-recovery verify data/backups/BACKUP_ID \
  --neo4j-admin /path/to/dbms/bin/neo4j-admin \
  --java-home /path/to/desktop/runtime/Contents/Home
```

Recovery sets live below ignored `data/backups/` by default because they contain private source
content and authorization history. Copy them to separately protected local storage according to
the threat model; never commit them. A recovery set is a bounded cross-store capture window, not
a distributed transaction. See
[`docs/operations/backup-and-restore.md`](docs/operations/backup-and-restore.md) for the restore
procedure, success criteria, and limitations.

## First working flow

1. `POST /v1/ingestion/text` records a versioned document and deterministic chunks.
   The first write binds its Source to `connector_id`; later ingestion, tombstones, and checkpoints
   must present the same stable connector instance identifier.
2. Re-ingesting identical content, source revision, processing contract, and authorization
   snapshot is a no-op.
3. Changed content, source version, authorization, or processing configuration creates a new
   immutable `DocumentVersion`; every version retains its source ACL snapshot.
   If a source returns to an earlier state, its connector must supply a distinct `source_version`
   or `source_updated_at`; otherwise ingestion rejects the ambiguous history instead of creating
   a false `SUPERSEDES` cycle.
4. `POST /v1/proposals` stores proposed assertions without contaminating canonical knowledge.
5. `POST /v1/proposals/{id}/approve` validates ontology version, temporal bounds,
   evidence existence, and supersession eligibility before atomically writing assertions and
   entities. A governed record can have only one approved successor; assertion corrections retain
   the same subject and predicate.
6. Both approval and rejection produce an immutable governance decision node and audit entry.
7. Source, document-version, entity, evidence, keyword, and graph-neighbor APIs read the graph.

`POST /v1/decisions/proposals` records a proposed human or organizational Decision with evidence,
temporal validity, participants, ontology version, and optional supersession. It becomes a
canonical `Decision` only through the existing proposal approval endpoint. Decision reads retain
their complete evidence and authorization context; later decisions supersede rather than overwrite.

`POST /v1/events/proposals` does the same for real-world semantic Events, keeping them distinct
from operational sync and deletion events through `event_class=SEMANTIC`. Occurrence intervals,
participants, correction history, and evidence remain preserved; corrections create a new Event
that supersedes the earlier one rather than replacing it. `GET /v1/events/{event_id}` applies the
same workspace and source-derived authorization policy as other knowledge reads. The registered
event extraction prompt can only produce a proposal—never a canonical Event.

Proposal creation validates every evidence reference inside the proposal workspace and records
explicit `Proposal-[:SUPPORTED_BY]->Chunk` lineage in the same transaction. `GET /v1/proposals`
is the review inbox for assertion, decision, and event proposals, with status/type filters;
`GET /v1/proposals/{proposal_id}` returns the review payload, evidence authorization snapshots,
and approvals. A proposal is returned only when the caller can read every supporting Chunk, which
prevents a mixed-ACL proposal from leaking inaccessible claims. Legacy proposals without provable
evidence linkage fail closed; migration 005 reconstructs linkage for already-promoted knowledge.
Approval and rejection requests carry the same explicit access context. The reviewer identity must
be one of the authenticated principals, and every supporting Chunk must be readable before the
state transition can occur. REST, MCP, or another edge adapter is responsible for deriving those
principals from its authenticated session; caller-supplied display names alone never authorize a
governance mutation.
Governance-v5 makes Proposal identity content-addressed across assertion, Decision, and Event
payloads. Exact retries, including concurrent adapter retries, resolve to one Proposal and return
its current lifecycle state; the persisted SHA-256 binds that identity to the canonical payload.
An already approved or rejected payload is never silently reopened as a new review item.
Governance-v6 binds the declared creator to the authenticated access context and verifies every
supporting document's current source-derived ACL during Proposal creation. The graph stores only a
canonical access fingerprint and principal count, not the raw principal set.

Source identity is scoped by workspace, source type, and opaque external ID. Connectors may attach
`sync_cursor` and `sync_run_id` to observed items, but item ingestion never advances the committed
source checkpoint. After every item in a run succeeds, `POST /v1/ingestion/checkpoints` atomically
commits the cursor with an optional compare-and-set precondition and records a completion `Event`.
This prevents a crash in the middle of a multi-item pull from skipping unprocessed records on
restart. Explicitly empty runs are supported without inventing document writes.
The authorized Source read contract exposes its bound connector identity for diagnosis and audit.
`POST /v1/ingestion/tombstone` records an idempotent
source-deletion `Event`, deactivates current chunks, and marks dependent assertions' evidence as
deleted without erasing history or silently changing canonical assertion status.

Connector implementations can submit the same versioned JSON contract through
`POST /v1/ingestion/manifests` or the local `knowledge-os-ingest` command. A manifest may mix
upserts and tombstones. Manifest-v2 acquires the existing Source as its serialization boundary and
commits every DocumentVersion, tombstone Event, and the source checkpoint in one Neo4j
transaction. After initial sync, `expected_previous_cursor` is mandatory; stale or concurrent runs
fail before any document write. Each `sync_run_id` is bound to the manifest's canonical hash and
cursor, and duplicate operations for one external document are rejected during validation.
Records are canonically ordered by external document ID before hashing and execution, so provider
listing order cannot change the run identity.
Retrying the identical completed manifest returns unchanged. Manifest-v1 remains read-compatible
and receives the same atomic server behavior. The example in
`examples/sync-manifest-v2.json` is intentionally provider-neutral: Notion, Google Drive,
meeting exporters, filesystem readers, and future adapters translate source APIs into this
contract rather than coupling the graph to their SDKs.
Source-v4 requires every externally supplied timestamp to carry a timezone and normalizes it to
UTC before identity, version, or checkpoint computation. Governance-v4 and Action-v4 apply the
same rule to observed/valid/decision/event and execution timestamps, preventing local-machine
timezone assumptions from changing provenance or temporal ordering.
Source-v5 adds document-level compare-and-set to the direct text and tombstone endpoints. Changing
or deleting an existing document requires its current `DocumentVersion.id`; the transaction
rechecks that exact ID before changing `CURRENT_VERSION` or lifecycle state. Identical ingestion
retries remain idempotent without a precondition. Atomic manifests derive this precondition inside
their existing Source lock, so connector manifests do not gain another field or round trip.
Source-v6 snapshots title and source URI identity on every new DocumentVersion and binds them with
a canonical metadata hash. Reusing one content/source/processing revision with different metadata
is rejected instead of returning a false unchanged result. Connectors use a new source version or
timestamp for a genuine rename or move, preserving both metadata states in version history.
Source-v7 keeps the Source collection URI separate from an optional per-document source URI. This
allows a Drive folder, filesystem root, or Notion tree to remain the stable Source while each
DocumentVersion retains the exact file or page link used as evidence. Older requests that omit the
new field retain Source-v6 behavior.

`GET /v1/sources` and `GET /v1/documents` provide an authorization-filtered evidence catalog;
their identifier endpoints expose source sync metadata and immutable DocumentVersion history.
Document detail omits Chunk bodies by default and returns them only with `include_chunks=true`.
Access is always evaluated against the latest version, including when an authorized caller asks to
inspect older versions, so history browsing cannot bypass a later source-side revocation. Source
list responses deliberately omit the mutable source-level owner/ACL cache: document-version
authorization is the enforcement boundary.

Proposal, Assertion, Entity, Event, and Decision identity and ownership are also workspace-scoped.
Proposal creation and approval verify that every evidence Chunk belongs to the Proposal workspace;
cross-workspace evidence and supersession are rejected before canonical promotion. Identical names
may therefore resolve independently in customer-specific Context Graphs without contaminating one
another.
Approval and rejection repeat the lifecycle and current-ACL check inside their write transaction
after locking the evidence Documents, and require the payload evidence IDs to exactly match the
persisted `SUPPORTED_BY` lineage. Concurrent revocation, tombstone, or version changes therefore
resolve at one explicit transaction boundary instead of leaving a stale authorization window.
Knowledge-v2 adds an optional timezone-aware `as_of` to Entity, neighbor, Decision, and semantic
Event reads. Assertion and Decision intervals use half-open `[valid_from, valid_to)` semantics;
Events are visible once `occurred_at <= as_of`, including completed historical events. Omitting
`as_of` preserves the existing explicit historical-read behavior rather than silently changing
stable consumers.
Governance-v7 adds date-precision Decisions without weakening the existing instant contract.
`decided_at` remains the timezone-aware instant input. When evidence supplies only a calendar day,
`decided_on` preserves that exact source value, records `decided_at_precision=DAY`, and derives a
UTC day boundary solely for deterministic comparison. Callers must supply exactly one temporal
form and may not silently invent an instant. The versioned decision extraction prompt enforces the
same rule.

REST knowledge reads require an access context: a `workspace_id` plus one or more source-system
principal identifiers. Access is decided from the evidence document's latest authorization
snapshot: it must be `PUBLIC`, owned by one of those principals, or contain one in its ACL. The
historical evidence snapshot remains unchanged and is returned separately from the current policy
snapshot, so provenance is preserved without allowing revoked access to survive through an older
version. Keyword, semantic, hybrid, proposal, entity, neighbor, event, and decision reads apply the
same rule, and workspace boundaries remain absolute even for public content. The default local
principal is `local-user`; adapters should pass the authenticated user's stable source principals
explicitly. This is intentionally a small, source-derived policy boundary, not a new authorization
database or premature ReBAC engine.

Atomic knowledge payloads such as Decision and Event are returned only when every supporting
evidence document is currently readable. Entity and neighbor reads filter at the individual
Assertion level. This prevents a permitted evidence fragment from revealing a statement synthesized
from other evidence whose access has been revoked.

For local documents, `knowledge-os-ingest-files ROOT --state data/files-state.json` converts a
deterministic directory snapshot into manifest v2, submits it, and atomically updates local state
only after checkpoint commit. It handles UTF-8 text, Markdown, reStructuredText, PDF, and DOCX;
install `uv sync --extra connectors` for PDF/DOCX parsing. WebVTT and SRT meeting transcripts are
also retained verbatim, including timestamps and speaker labels. Use
`--source-type meeting_transcripts` to identify that Source without adding a meeting-specific graph
path. Missing files become tombstones on the next successful snapshot. A crash before state update
safely replays the same deterministic run. A successful follow-up snapshot receives a distinct,
deterministic run ID bound to both its previous and new cursor, so it cannot collide with the
initial manifest even when the content cursor is unchanged.

For Google Drive, `knowledge-os-ingest-google-drive --folder FOLDER_ID --state
data/google-drive-state.json` reads one complete authorized folder snapshot through the official
API and submits it through the same manifest-v2 boundary. It preserves file IDs, revisions,
per-file links, effective permissions, and deletion evidence without writing to Drive. See
[`docs/operations/google-drive.md`](docs/operations/google-drive.md) for credential and parser
boundaries.

For Notion, `knowledge-os-ingest-notion` traverses one explicitly shared root page, nested child
pages, and child data-source rows through the read-only API, translates the snapshot into the same
atomic manifest-v2, and updates local state only after graph commit. The source principal is
derived from Notion's
`/users/me` connection ID rather than supplied by the operator. This first adapter intentionally
does not pretend that connection visibility is a complete copy of Notion's human ACL model, and it
marks unsupported block and property types instead of silently dropping them. See
[`docs/operations/notion-connector.md`](docs/operations/notion-connector.md).

## Governed actions

`POST /v1/actions` records an idempotent action request and its policy version. Approval and
rejection endpoints append governance decisions, but deliberately do not execute anything:
`execution_status` remains `NOT_EXECUTED`. A future connector may execute only an approved action
through an authorized System-of-Record API and must append its result and audit evidence.
Until a separately governed automatic-approval policy exists, external Actions fail closed when
submitted with `approval_required=false`.
Each Action freezes separate `review_principals` and `execution_principals` alongside its workspace
and policy version. Reads require the requester, an authorized reviewer, or an authorized connector;
approval requires a designated reviewer, and execution evidence requires a designated connector
whose identity is present in the adapter-derived access context. Migration 006 scopes legacy
Actions and leaves their executor list empty so undeclared historical capabilities fail closed.
`POST /v1/actions/{action_id}/execution-claims` must be called before any external mutation. It
atomically reserves the approved Action for one authorized connector with a bounded lease and
returns an Action-stable external idempotency key. Competing connectors fail closed; an idempotent
retry returns the original live claim. An expired lease also fails closed until its external result
is reconciled as FAILED or SUCCEEDED—it never silently authorizes a takeover. Connectors must pass
the returned key through an external API's native idempotency facility whenever one exists.
`POST /v1/actions/{action_id}/executions` never performs that external call. It accepts immutable
result evidence only for the Action's current claim and requires matching connector identity,
external API, authorization reference, policy version, claim id, external idempotency key, and
external request metadata. Failed attempts require structured error evidence; retries cannot
rewrite an earlier attempt.
Action-v5 requires an explicit Action creation `idempotency_key`. The key is scoped by workspace
and requester and remains bound to one canonical payload; retries return the existing lifecycle
state, while reuse for different parameters fails closed. Identical payloads may still be requested
again intentionally, but only under a new explicit key.
Action-v6 also requires `requested_by` and workspace to match the authenticated creation context;
its fingerprint and principal count are retained as bounded request provenance.
Action creation, approve/reject, claims, and execution evidence writes serialize on the Action
node. Concurrent use of one idempotency key resolves to one record, concurrent decisions yield one
Approval, only one live claim can authorize an external call, and only one successful execution
can be recorded. Capability, claim, and policy checks repeat inside the write transaction rather
than trusting an earlier read. A lease plus stable key closes in-process concurrency; exactly-once
external mutation still depends on the System of Record honoring that key.

The first concrete executor adapter covers governed Notion child-page creation plus a separately
approved trash-only compensation Action. MCP remains request-only; a human reviews the Action with
`knowledge-os-review`, and the separate `knowledge-os-execute-notion-action ACTION_ID --yes` process
claims and records the external attempt. Exact target, parameters, type-specific policy mapping,
and ambiguous-outcome behavior are documented in
[`docs/operations/notion-actions.md`](docs/operations/notion-actions.md). No live write is implied by
the presence of this executable.

## Evidence-driven operations

Keyword retrieval returns a durable `trace_id`. `/v1/traces/{trace_id}` exposes the measured
query contract, result identifiers, latency, and configuration version; `/v1/feedback` and
`/v1/evaluations` attach human feedback and evaluation outcomes to that trace. Unexpected
retrieval failures are recorded in the same local SQLite operations store with an `error_id`.
Knowledge results carry both the originating `DocumentVersion` authorization snapshot and, where
they differ, the current snapshot used for enforcement. Replaceable adapters therefore receive
provenance and the effective source-derived policy without changing the knowledge contract.

The REST adapter records one bounded telemetry row for every request using only method, route
template, status class, status code, generated request ID, adapter-contract version, and latency.
It distinguishes success, denial, not-found, conflict, other client errors, and server errors.
Unexpected failures receive a correlated `error_id`; the response and SQLite record expose a
generic message rather than exception text or request content. Retrieval failure records likewise
retain a query hash and workspace identifier instead of the raw failed query. Domain-level
telemetry remains separate, so adapter availability and ingestion/retrieval behavior can be
measured independently without another observability system.

Every adapter-visible retrieval trace is bound to the canonical fingerprint of its workspace and
principal set. Trace lookup and trace-linked feedback or evaluation require the same access
context; mismatches and legacy unbound traces fail closed with no existence disclosure. SQLite
stores the fingerprint and principal count in trace context, not the raw principal set. As with
knowledge reads, the edge adapter remains responsible for deriving principals from authentication.
The MCP adapter projects this existing boundary through `get_retrieval_trace` and
`record_retrieval_feedback`. The server supplies the fixed access context and actor, allowing agents
to close the retrieval-quality feedback loop without receiving canonical or source mutation rights.
Retrieval-v7 also binds every feedback actor to that request's authenticated principal set. A
single principal is derived automatically; multi-principal contexts must name one member explicitly.
Retrieval-v8 persists the workspace and access fingerprint on every new evaluation row. Trace-linked
evaluations derive and verify both values from the immutable retrieval trace; existing linked rows
are backfilled from that trace when the local operations schema opens.
Retrieval-v9 applies the same trace-derived workspace and access provenance to feedback rows, keeping
human and agent quality signals tenant-scoped without duplicating raw principal sets.

`POST /v1/retrieval/query` is the stable keyword, semantic, and hybrid retrieval contract.
Keyword input is converted to literal Unicode terms before it reaches Neo4j full-text search, so
slashes, parentheses, operators, wildcards, and other Lucene syntax in ordinary questions cannot
change query structure or trigger parser errors. Retrieval-v3 oversamples bounded Neo4j candidates,
adds an explainable title-token signal, and places at most two chunks from one document in the
early result pass before appending deferred chunks. Results expose lexical score and title overlap,
and traces record `lexical-title-diversity-v1`; the full-text index and authorization predicate are
unchanged. Traces retain the original user query.
Embeddings are supplied by replaceable adapters and stored on evidence chunks through
`PUT /v1/chunks/{chunk_id}/embedding` with their model and version. Hybrid ranking uses reciprocal
rank fusion; neither the contract nor canonical knowledge depends on an embedding provider or
retrieval framework. Neo4j remains the only graph, keyword, and vector retrieval store.
Embedding writes carry an explicit adapter access context: `created_by` must be an authenticated
principal, and the target must be an accessible active Chunk in the document's current version.
Historical or revoked evidence cannot be modified through the embedding endpoint.
Retrieval-v4 also fingerprints the vector, model, and model version. A byte-equivalent retry is
idempotent, while any replacement fails closed so an adapter cannot silently erase embedding
provenance. A future model change therefore requires an explicit versioned re-embedding contract.
The vector index includes active/model/version filter properties and uses Neo4j's current
`SEARCH` clause, so model isolation occurs inside the ANN search rather than by post-filtering.

`GET /v1/entities/search` and MCP `search_entities` provide traced graph discovery over the existing
Neo4j Entity full-text index. An Entity is visible only through at least one Assertion whose complete
evidence set remains authorized; stable IDs feed the existing Entity, Assertion, and neighbor reads.
Retrieval capability discovery reports both `accessible_entities` and `graph_available`, preventing
contract support from being mistaken for populated graph context.

Versioned retrieval suites turn those traces into reproducible quality evidence. Copy
`examples/retrieval-eval-suite-v1.json`, replace its expected stable IDs with known-good Chunk or
Document IDs, and keep the resulting customer-specific suite in Git. Each case embeds the existing
`RetrievalQuery`, including workspace access, retrieval mode, and optional versioned embedding.

```bash
knowledge-os-evaluate path/to/retrieval-eval-suite.json
```

The checked-in `examples/personal-google-drive-retrieval-eval-v1.json` is the first executable
personal-corpus baseline. Its measured 2026-09-05 result and explicit limits are recorded in
`docs/evaluations/2026-09-05-personal-keyword-baseline.md`; this evidence supports retaining the
current Neo4j keyword foundation rather than redesigning retrieval prematurely.

`examples/personal-golden-questions-retrieval-v1.json` is the harder question-form regression
suite. Evaluation-only `excluded_document_ids` prevents its source question table from contaminating
the score; exclusions never alter production retrieval. The measured result and remaining ranking
gap are recorded in `docs/evaluations/2026-09-05-held-out-golden-questions.md`.

`examples/personal-authorization-retrieval-v1.json` adds policy cases through
`expected_no_results`. Policy pass rate is reported separately from positive recall and every
negative case must pass. The first measured source/workspace denial result is recorded in
`docs/evaluations/2026-09-05-source-authorization.md`.

The runner records every case against its retrieval `trace_id`, computes recall@k and reciprocal
rank for positive cases, reports no-result policy pass rate separately, and reports the canonical
suite SHA-256 fingerprint. It exits nonzero when mean recall is below `minimum_mean_recall` or any
policy case fails. This supplies a small local regression gate before retrieval architecture,
chunking, prompts, authorization, or embedding configuration are changed; it adds no evaluation
service or store.

Schema migrations are applied once and recorded in Neo4j with their Git-controlled checksum.
Never edit an applied migration; append a new numbered migration instead.

Embedding and LLM extraction are adapter slots, not hard-coded dependencies. Until a
provider is configured, ingestion still creates the complete evidence and version chain.

## MCP adapter

`knowledge-os-mcp` is a local stdio adapter for Codex, Claude Code, and other MCP hosts. By default
the host-owned process runs the same Knowledge Service ASGI application in-process, so no separate
port or daemon is required. It never imports the Neo4j driver or accepts Cypher. The tool surface
supports governed reads plus content-addressed assertion, Decision, and Event Proposal creation
and review-required Action requests.
It deliberately exposes no approval, rejection, canonical promotion, ingestion, Action execution,
or external-system mutation. Workspace, source principals, creating actor, Action reviewers,
executors, and policy version are fixed by launch-time environment rather than model-controlled
arguments. See
[`docs/operations/mcp-adapter.md`](docs/operations/mcp-adapter.md) for startup and registration.
The adapter retains `search_knowledge` for simple keyword use and exposes the same provider-neutral
keyword/semantic/hybrid `RetrievalQuery` through `retrieve_knowledge`; query vectors and their exact
model/version remain the caller adapter's responsibility.
Retrieval-v5 adds an authorization-filtered capability read so adapters can distinguish an online
empty vector index from a usable embedded corpus. It exposes counts and model/version metadata only
for active evidence currently readable by the configured principals; unauthorized workspaces or
sources report zero rather than leaking corpus readiness.

## Human review CLI

`knowledge-os-review` is the minimum local review surface over the same Knowledge Service routes.
It lists authorized Proposals and Actions, shows exact Evidence or Action policy/target/history,
and permits an explicit human approve or reject decision only with `--yes`. Reviewer workspace,
principals, and actor come from launch-time `REVIEW_*` settings, never model arguments. Proposal
approval can promote canonical knowledge; Action approval changes lifecycle state but cannot
execute an external operation. MCP and source connectors still cannot approve. See
[`docs/operations/human-review.md`](docs/operations/human-review.md).
