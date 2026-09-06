# Canonical Assertion stable-ID read — 2026-09-05

## Measured contract gap

Entity reads embedded related Assertions, but the Knowledge Service had no way to resolve a
canonical Assertion directly from its stable ID. Consumers therefore depended on knowing an Entity
and parsing an adapter-specific nested response, unlike Decision and Event primitives.

## Minimum extension

Knowledge-v5 adds `GET /v1/assertions/{assertion_id}` and the read-only MCP `get_assertion` adapter.
The response returns the Assertion, subject, optional object, immutable evidence authorization,
current authorization, and Approval history. Optional `as_of` filtering uses the existing half-open
validity contract. The entire read fails closed unless every supporting Chunk remains authorized
through its Document's current version.

No canonical write, approval capability, graph framework, or storage change is introduced.

## Verification

Contract tests cover MCP discovery, fixed identity injection, and REST/as-of mapping; the complete
suite passed with 88 tests.

An isolated live Neo4j fixture in workspace `it-assertion-read-v1` traversed Source, Document,
DocumentVersion, Chunk, Proposal, Approval, Assertion, and two Entities. The authorized read returned
subject `Knowledge OS`, object `Neo4j`, one evidence record, and one Approval. A different principal
received no result, and the Assertion was absent at its exclusive `valid_to` boundary. Exact
workspace cleanup removed all 10 fixture nodes and left zero workspace nodes. Two earlier fail-closed
fixture attempts (invalid script field and invalid ontology type) also executed their `finally`
cleanup and left zero isolated primitives. The operations database was temporary in all attempts.
