# ADR 0001: Stable Context Contracts

- Status: accepted
- Date: 2026-09-02

## Decision

The Knowledge OS is a local-first System of Context. Notion, Google Drive, files,
meeting systems, and future connectors remain Systems of Record. Neo4j is the
semantic context graph; SQLite is limited to local operations, audit, telemetry,
feedback, errors, and evaluations.

The stable boundaries are Source, Evidence, Knowledge, Governance, Retrieval, and
Action. REST is the first adapter. MCP, A2A, user interfaces, LLM providers, agent
frameworks, embedding providers, and connector implementations may change without
changing these boundaries.

Extracted assertions, events, and decisions enter the canonical graph only through Proposal
and Approval. Proposals carry explicit evidence lineage and are reviewable only when every
supporting source authorization permits access. Actions remain `NOT_EXECUTED` after approval until
an independently authorized connector executes them against a System-of-Record API and records
the result. Source versions, authorization snapshots, evidence, temporal validity, supersession,
and decision traces are never discarded.

Governance state transitions require an adapter-derived access context. The reviewer must be an
authenticated principal in that context and must be authorized to read every supporting evidence
Chunk. Identity authentication remains an adapter concern; the Knowledge Service enforces the
workspace and evidence policy consistently regardless of REST, MCP, or future transports.
Approval and rejection revalidate the exact payload-to-`SUPPORTED_BY` evidence set, active
Document lifecycle, and current DocumentVersion authorization inside the write transaction.
Evidence Documents are locked in deterministic order before that check, closing the race with
concurrent ACL updates, new source versions, and tombstones while retaining historical Chunks as
provenance.
The Proposal itself is revision-locked before its status transition, so concurrent approve/reject
requests produce exactly one immutable Approval outcome.

Governed supersession is a single-successor state transition, not an unconstrained graph edge.
Targets must be current, verified records in the proposal workspace when proposed and again when
approved. The approval transaction atomically claims the target, so concurrent approvals cannot
create two canonical successors. Assertion corrections preserve the subject and predicate while
allowing their object or value and evidence to change.

Historical authorization snapshots are provenance, not permanent grants. Reads and governance
mutations evaluate the latest DocumentVersion authorization for each evidence document while
returning the original evidence snapshot separately. A source-side revocation therefore closes
access without rewriting or discarding historical evidence.

The Source and Evidence read contract exposes authorized source catalogs, document summaries,
immutable version history, and opt-in Chunk bodies. It reads the existing Neo4j lineage directly;
source systems remain authoritative and no document repository or duplicate content store is
introduced.

Keyword retrieval treats adapter input as literal natural-language terms, never as Lucene query
syntax. Reserved punctuation and operator-shaped words cannot alter the query structure or cause a
parser failure; the original query remains unchanged in the access-bound trace.

Actions carry immutable workspace, policy-version, reviewer-principal, and executor-principal
snapshots. Only a designated authenticated reviewer can approve or reject, and only a designated
authenticated connector can append execution evidence. Recording evidence never performs the
external operation; authenticated System-of-Record adapters remain the sole execution boundary.
Action creation, decision, and execution evidence use the Action node as their transaction
serialization boundary. Concurrent idempotent creation resolves to one Action, approve/reject
produces one decision, and execution retries cannot append evidence after the first recorded
success. Policy version and executor capability are revalidated inside the write transaction.

Action-v3 extends that boundary with a pre-execution claim. An authorized connector must
atomically claim an approved Action before invoking a System of Record. One bounded lease is live
at a time, and all attempts receive the same Action/policy-derived external idempotency key. Result
evidence must close the current claim with the same capability, policy, authorization reference,
claim id, and external key. This prevents concurrent compliant connectors from independently
beginning a mutation. It does not claim exactly-once behavior from an external API that ignores
idempotency. Lease expiry never grants takeover: the current claim must first be reconciled against
the System of Record and closed with immutable result evidence.

Replaceable embedding adapters may annotate only current active evidence that their authenticated
access context can read. Model/version metadata remains explicit, and historical or revoked Chunks
cannot be mutated through the embedding contract.

Each Source is bound on first ingestion to a stable connector instance identifier. The same
binding is enforced for item ingestion, tombstones, and cursor checkpoints, including idempotent
paths. Parser and chunker versions describe processing, not connector identity. Legacy unbound
Sources may be claimed once; connector handover is deliberately explicit and audited rather than
being inferred from a new caller.

Source-v3 makes connector-neutral manifest ingestion atomic without changing Neo4j as the storage
boundary. The Source node serializes a complete manifest transaction containing all upserts,
tombstones, and its checkpoint. A noninitial run must compare-and-set the prior cursor before any
document write. Completion Events bind source, sync-run ID, cursor, and a content-free canonical
manifest hash; replay with altered input fails closed. Manifest-v1 input remains readable while
manifest-v2 advertises these stronger semantics to new connectors.

## Highest-order change-control rule

> Do not redesign working foundations without evidence. Extend stable contracts
> rather than replacing the architecture.

A replacement requires measured evidence of a correctness, quality, performance,
security, authorization, or source-contract limitation. Novelty, preference, and
framework popularity are not sufficient evidence.

## Consequences

- Additive contracts and numbered migrations are preferred.
- Applied migrations are checksum-protected and never edited.
- A new database, queue, vector store, orchestration platform, observability stack,
  authorization engine, or custom abstraction requires a recorded evidence-backed
  decision.
- Contract versions live in `config/contracts.yaml`; ontology versions live in
  `config/ontology.yaml`.
- Source-v4, Governance-v4, and Action-v4 reject timezone-naive external timestamps and normalize
  accepted offsets to UTC before persistence and deterministic identity computation.
- Source-v5 requires document-version compare-and-set for direct update/deletion mutations while
  preserving the existing Source-level cursor lock as the atomic manifest serialization boundary.
- Governance-v5 content-addresses Proposal identity and binds it to a persisted payload hash, so
  adapter retries cannot multiply review items or canonical promotions.
- Action-v5 requires a workspace/requester-scoped idempotency key at capability creation and binds
  it to one payload before any approval or execution claim can exist.
- Governance-v6 and Action-v6 bind creation actors and workspaces to authenticated access contexts;
  Proposal creation additionally enforces current source ACLs before entering the review queue.
- Governance-v8 makes Approval ownership an explicit integrity invariant: every Approval must have
  exactly one incoming `HAS_APPROVAL` relationship from a Proposal or governed Action.
- Source-v6 preserves title and source URI metadata on new DocumentVersions and rejects metadata
  drift hidden behind a reused source revision.
- Source-v8 makes operational Event ownership explicit: every non-semantic Event must have exactly
  one incoming `HAS_EVENT` relationship from its Source or Document provenance parent.
- Source-v9 projects authorized Source and Document catalogs through MCP while keeping bulk Chunk
  bodies behind the bounded Evidence contract.
- Knowledge-v2 exposes optional timezone-aware as-of filtering over existing Assertion, Decision,
  and semantic Event timestamps without replacing the graph read contracts.
- Knowledge-v3 exposes deterministic ontology and checksum-verified prompt content through
  read-only service endpoints, allowing extraction adapters to remain replaceable while all
  candidate writes continue through governed Proposal contracts.
- Knowledge-v4 projects authorized canonical Decision and semantic Event reads through MCP using
  the existing evidence and optional as-of contracts, without exposing Proposal approval.
- Knowledge-v5 gives canonical Assertions their own authorized stable-ID read contract, returning
  subject/object Entities and requiring all supporting evidence to remain currently accessible.
- Evidence-v2 provides an all-or-nothing authorized bundle of exact Chunks and immutable source
  provenance for MCP and extraction adapters without exposing Neo4j or Cypher as the service
  boundary.
- Retrieval-v6 projects authorized trace reads and bounded feedback through MCP using host-fixed
  access and actor identity; feedback remains operational evidence and cannot promote knowledge.
- Retrieval-v7 binds the persisted feedback actor to the request's authenticated access principals,
  preventing an adapter from attributing quality evidence to an unrelated identity.
- Retrieval-v8 scopes evaluations by workspace and access fingerprint, deriving linked provenance
  from the retrieval trace and refusing mismatched or unattributed new records.
- Retrieval-v9 scopes feedback rows with the same trace-derived workspace and access fingerprint;
  the Doctor detects missing operational provenance without silently repairing it.
- Retrieval-v10 adds traced Entity discovery over Neo4j's existing full-text index. A result requires
  at least one related Assertion whose complete evidence remains authorized at read time.
- Retrieval-v11 distinguishes graph contract support from authorized data readiness by reporting
  accessible Entity count and graph availability under the same complete-evidence rule.
- The initial MCP adapter is a read-only stdio projection of REST Knowledge Service contracts.
  Host configuration fixes workspace and source principals; models cannot supply identities or
  access direct Neo4j credentials.
- Dynamic MCP and human-review identifiers are encoded as single URL path segments before transport;
  adapter input cannot use slash traversal to select a different Knowledge Service endpoint.
- Architectural changes should cite retrieval traces, evaluations, errors, feedback,
  performance measurements, or an explicit external requirement.
- Adapter telemetry is intentionally bounded and content-free. REST records route templates,
  status classes, latency, and opaque correlation IDs; unexpected exception text and request
  bodies never enter the operations store. Domain traces and adapter traces remain distinct.
- Versioned retrieval suites use the stable Retrieval contract and existing SQLite operations
  store to provide reproducible recall and ranking evidence; they do not introduce a framework or
  separate evaluation platform.
- Retrieval policy cases keep expected-empty authorization outcomes separate from recall metrics
  and fail the suite on any leaked result.
- Retrieval-v3 preserves the Neo4j full-text candidate source and authorization predicate, then
  applies a bounded, explainable title-token score and two-chunks-per-document early diversity pass.
  The ranker version is stored in each keyword/hybrid trace; deferred chunks are appended rather
  than discarded.
- Retrieval-v4 preserves that retrieval path and makes embedding writes immutable and idempotent:
  the vector, model, and model version are fingerprinted, exact retries are accepted, and a
  different payload is rejected until an explicit versioned re-embedding contract exists.
- Read-only readiness checks verify graph lineage and ownership invariants, migration checksums,
  index state, and SQLite integrity. Detection is separated from repair so corruption cannot be
  silently normalized or historical evidence rewritten.
- Retrieval traces exposed through adapters are bound to a canonical workspace/principal-set
  fingerprint. Trace reads and linked feedback/evaluations require the same access context, while
  raw principal sets are excluded from operational trace metadata.
