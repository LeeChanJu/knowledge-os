# Local MCP adapter — 2026-09-05

## Measured gap

Google Drive evidence, retrieval, ontology, prompts, and graph reads were available through REST,
but Codex and Claude Code had no MCP server to consume those stable contracts. Direct Neo4j access
would have exposed Cypher and database credentials and duplicated authorization logic in each
agent host.

## Minimal adapter

The `knowledge-os-mcp` stdio process uses the official MCP Python SDK v2 and calls only Knowledge
Service routes. It exposes six read-only tools. The host fixes workspace and a comma-separated set
of source principals at process launch. Tool schemas do not contain principal, workspace, Cypher,
approval, ingestion, or execution arguments. `MCP_BASE_URL` is optional and reserved for an
explicitly supervised separated service.

The official SDK is the only new protocol dependency. No server port, queue, database, agent
framework, authorization engine, or second business-logic layer was introduced. The same FastAPI
routes remain authoritative and the MCP process can be replaced without changing graph contracts.

## Verification

- The official SDK in-memory client completed capability negotiation and listed exactly the six
  expected tools.
- Schema inspection confirmed a 100-ID maximum Evidence request and no create, approve, or execute
  tool.
- Unit tests confirmed that workspace and sorted/deduplicated principals come only from server
  environment.
- A real uvicorn Knowledge Service and separately launched stdio MCP child completed
  `search_knowledge` followed by `get_evidence` against the live private Google Drive Source.
- The chain returned two search results under retrieval-v4 and exactly two provenance-bearing
  Evidence records. The validation summary omitted Chunk text.
- Ruff passed and all 54 unit tests passed.

This proves the local read path `Google Drive -> Neo4j Knowledge Service -> MCP -> host SDK`. It
does not yet prove host UI registration, Notion ingestion, governed MCP mutations, or semantic
retrieval quality.

## Host registration evidence

The server was subsequently registered as `knowledge-os` in both installed hosts using the same
absolute stdio command and the source-derived `google-drive:me` principal:

- Codex reports the global server enabled with stdio transport and redacts its three environment
  values in diagnostic output.
- Claude Code reports the project-local server connected with stdio transport.
- The local Knowledge Service returned a healthy response at registration time.
- Pre-existing direct Neo4j MCP registrations were retained rather than silently removed. The new
  governed adapter can coexist until measured usage supports an explicit migration decision.

This closes host registration for the current machine. The REST service is not yet installed as a
login-time process. The later host-owned lifecycle change below removes that requirement. A host
that was already running may still need a new session to discover a changed server registration.

## Rejected launchd experiment

A user LaunchAgent was tested as the smallest native login-time supervisor. launchd registered the
exact label and attempted restarts, but macOS denied the background process access to
`.venv/pyvenv.cfg` because this repository lives under the protected `Documents` directory. The
process exited before Python startup and never bound the service port.

Granting broad filesystem privacy access or copying runtime configuration and operational data to
a second location would weaken the minimum-access and single-source boundaries. The experiment was
therefore rejected: the exact launchd label was booted out, both generated plist files were removed,
and the already verified manual service command was restored.

The resulting evidence justified a smaller extension instead of a new deployment foundation: the
MCP host now owns the existing FastAPI application's lifecycle and calls its routes through ASGI in
process. `MCP_BASE_URL` remains an explicit option for a future supervised separated service. This
closes the reboot/startup gap without a LaunchAgent, a second data location, or duplicated service
logic.

## Host-owned lifecycle verification

- Port 8000 had no listener before, during, or after the test.
- A real stdio child entered the FastAPI lifecycle, verified and migrated the live Neo4j database,
  and completed ontology, search, and exact Evidence calls through in-process ASGI.
- A checked-in golden question returned two authorized search results; the Evidence bundle returned
  exactly the same two Chunk IDs with Source, DocumentVersion, historical authorization, and current
  authorization metadata. No personal Chunk text was emitted in the validation summary.
- Codex global and Claude Code project-local registrations were updated to remove
  `MCP_BASE_URL`; both retain only the exact `personal` workspace and `google-drive:me` principal.
- Unit coverage now proves that the default URL is absent and that requests use ASGI transport.
