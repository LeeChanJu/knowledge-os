# Authorized Entity discovery — 2026-09-05

## Measured retrieval gap

Entity and neighbor reads required a stable Entity ID, but no Knowledge Service operation could
discover that ID from a name. Agents could search evidence text, yet graph navigation still depended
on an out-of-band identifier or adapter-specific nested Assertion response.

## Minimum extension

Retrieval-v10 adds `GET /v1/entities/search` and MCP `search_entities` over the existing Neo4j
`entity_name_fulltext` index. Candidate Entities are workspace-scoped and become visible only when at
least one related temporal Assertion has its complete evidence set authorized through every current
DocumentVersion ACL. Results return stable IDs, bounded metadata, accessible Assertion counts, and a
workspace/access-bound retrieval trace. Optional `as_of` uses the established temporal contract.

No index, database, graph framework, or canonical mutation path is added.

## Verification

Contract tests cover MCP mapping and fixed access/as-of injection; the complete suite passed with 91
tests.

An isolated live Neo4j fixture in `it-entity-search-v1` promoted one evidence-backed `USES`
Assertion between `Knowledge OS` and `Neo4j`. The punctuation-bearing query `Neo4j)` returned only
the `Neo4j` Entity with one accessible Assertion under `retrieval-v10`. A denied principal returned
zero results, and the exclusive `valid_to` boundary returned zero. The trace recorded
`entity-fulltext-v1`, was readable under the authorized access fingerprint, and was hidden under the
denied fingerprint. Exact workspace cleanup removed all 10 fixture nodes and left zero workspace
nodes; the operations database was temporary.
