# Local MCP adapter

The MCP process is a replaceable adapter, not the System of Context. In the local-first default it
owns the same FastAPI Knowledge Service lifecycle in-process. This removes a separate port and
login-time daemon without bypassing or duplicating any Knowledge Service route, authorization, or
telemetry contract.

Register the installed stdio command with absolute paths. Use the exact comma-separated principals
retained from each source system; do not grant display names, wildcards, or broader workspace roles.
A personal installation consuming both proven sources uses
`google-drive:me,notion:connection:<connection-id>`:

```bash
codex mcp add knowledge-os \
  --env MCP_WORKSPACE_ID=personal \
  --env MCP_PRINCIPALS=google-drive:me,notion:connection:<connection-id> \
  --env MCP_ACTION_REVIEW_PRINCIPALS=google-drive:me \
  --env MCP_ACTION_EXECUTION_PRINCIPALS=local-connector \
  -- /absolute/path/to/neo4j/.venv/bin/knowledge-os-mcp

claude mcp add --scope local knowledge-os \
  -e MCP_WORKSPACE_ID=personal \
  -e MCP_PRINCIPALS=google-drive:me,notion:connection:<connection-id> \
  -e MCP_ACTION_REVIEW_PRINCIPALS=google-drive:me \
  -e MCP_ACTION_EXECUTION_PRINCIPALS=local-connector \
  -- /absolute/path/to/neo4j/.venv/bin/knowledge-os-mcp
```

Confirm the registered server with `codex mcp get knowledge-os` or `/mcp` inside Claude Code.
The stdio process should be silent while waiting for a host; stdout is reserved for MCP protocol
frames. Service diagnostics belong on stderr.

The registration persists and each MCP host starts and stops its own governed service lifecycle.
No listener on port 8000 is required. For an intentionally separated deployment, set
`MCP_BASE_URL` to its supervised Knowledge Service URL; that is an explicit override, not the local
default.

This checkout uses a non-editable wheel. After changing MCP or Knowledge Service Python code,
explicitly rebuild the installed package before restarting a host; an ordinary `uv sync` can retain
the already installed local version:

```bash
uv sync --reinstall-package knowledge-os --extra dev --extra connectors --no-editable
```

Do not install a LaunchAgent that runs this checkout in place while it remains under macOS
`Documents`: background launchd execution was measured to fail at Python startup under TCC. The
host-owned default makes that workaround unnecessary. A future separated deployment still requires
one deliberate application-data location and migration plan.

Available tools:

- `search_knowledge`
- `search_entities`
- `retrieve_knowledge`
- `get_retrieval_capabilities`
- `get_retrieval_trace`
- `record_retrieval_feedback`
- `list_sources`
- `get_source`
- `list_documents`
- `get_document`
- `get_evidence`
- `get_entity`
- `get_neighbors`
- `get_assertion`
- `get_decision`
- `get_event`
- `get_ontology`
- `get_contracts`
- `get_extraction_prompt`
- `propose_assertions`
- `propose_decision`
- `propose_event`
- `list_proposals`
- `get_proposal`
- `request_action`
- `list_actions`
- `get_action`

Proposal tools inject the configured workspace, complete principal set, and creating actor. When
there is exactly one principal it is the actor. With multiple principals, registration must set
`MCP_ACTOR` to one member of `MCP_PRINCIPALS`; missing or foreign actors fail closed. The model
cannot supply these identity fields.

`search_knowledge` is the keyword convenience tool. `retrieve_knowledge` maps directly to the
stable retrieval contract and accepts `keyword`, `semantic`, or `hybrid`. Semantic and hybrid calls
must receive a query embedding plus the exact model and version from a replaceable adapter. The MCP
server does not invent vectors or select a provider, and Neo4j filters candidates to matching
model/version and the fixed source-derived access context.
Call `get_retrieval_capabilities` before semantic work. It reports only currently authorized active
Chunk counts and embedding model/version groups, plus the configured vector dimension. A model is
not usable merely because an index exists; `semantic_available` is true only when at least one
authorized embedded Chunk exists. Retrieval-v11 applies the same distinction to graph discovery:
`accessible_entities` counts only Entities backed by at least one completely authorized Assertion,
and `graph_available` is false when that count is zero.

`search_entities` is the graph-discovery entrypoint. It uses Neo4j's existing Entity full-text index
and returns stable Entity IDs only when at least one related Assertion is fully authorized through
all of its current source evidence. Results include a retrieval-v10 trace and optional `as_of`
filtering; `get_entity` and `get_neighbors` then resolve the selected graph context.

Retrieval calls return a `trace_id`. `get_retrieval_trace` reads its result identifiers, latency,
mode, and version only when the trace belongs to the MCP server's fixed workspace and principal
fingerprint. `record_retrieval_feedback` attaches a `-1`, `0`, or `1` rating and/or a bounded comment
under the configured MCP actor. It cannot change a Chunk, canonical knowledge, or a source system.

Source-v9 projects the existing authorized Source and Document catalogs through MCP. Source reads
include connector and checkpoint status; Document reads include current authorization and immutable
version metadata. `get_document` deliberately fixes `include_chunks=false`; exact bodies remain
available through bounded search results and `get_evidence` rather than an unbounded catalog read.

Knowledge-v5 projects canonical Assertion, Decision, and semantic Event reads by stable ID. All use
the fixed MCP access context, preserve their supporting evidence, and accept the existing optional
`as_of` instant. Assertion reads also return subject and optional object Entities. The adapter still
cannot approve the Proposal that creates any canonical record.

`get_contracts` exposes the current Source, Evidence, Knowledge, Governance, Retrieval, and Action
versions plus the evidence-backed change-control rule. Agents can negotiate current behavior rather
than inferring a version from tool names or documentation. It exposes Git-controlled configuration,
not runtime secrets or cross-workspace readiness samples.

Action requests also inject the configured reviewer, executor, and policy identities. Both
`MCP_ACTION_REVIEW_PRINCIPALS` and `MCP_ACTION_EXECUTION_PRINCIPALS` must be configured before the
tool can create an Action; otherwise it fails closed. The model supplies only the requested
capability, target, parameters, reason, and idempotency key. Every request is forced to require
approval. Configure an execution principal only for a connector that will separately authenticate
to the Knowledge Service; merely naming it here does not grant MCP an execution capability.

There are deliberately no proposal approval or rejection, canonical promotion, Action execution,
ingestion, or external-system mutation tools. A Proposal remains review-only until a separately
authenticated human review surface calls the existing governance decision contract.

All model-supplied stable IDs are encoded as one URL path segment before the internal or separated
HTTP transport sees them. Embedded slashes and percent escapes cannot traverse to another endpoint.
