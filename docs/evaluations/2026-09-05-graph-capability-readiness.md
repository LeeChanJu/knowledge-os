# Graph capability readiness — 2026-09-05

## Measured capability gap

Retrieval capability discovery listed `graph` as a supported mode but reported readiness only for
semantic embeddings. An agent could not distinguish a working graph contract from a workspace with
no authorized canonical Entities, which is currently the truthful state of the personal graph.

## Minimum extension

Retrieval-v11 adds `accessible_entities` and `graph_available`. An Entity counts only when at least
one related Assertion has every evidence Chunk authorized through the current DocumentVersion ACL.
No names, IDs, raw ACLs, or inaccessible counts are exposed. The query reuses Neo4j and the same
complete-evidence rule as Entity discovery.

## Verification

The complete suite passed with 91 tests. The personal `google-drive:me` context reported 80
accessible Chunks but 0 accessible Entities, with both semantic and graph availability false. An
unrelated principal saw zero Chunks and Entities.

An isolated governed Assertion in `it-graph-capability-v1` reported two accessible Entities and
`graph_available=true` to `user:reader`; `user:denied` saw zero and false. Exact cleanup removed all
10 fixture nodes and left zero workspace nodes. The operations database was temporary.
