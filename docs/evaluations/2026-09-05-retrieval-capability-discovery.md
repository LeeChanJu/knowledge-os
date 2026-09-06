# Retrieval capability discovery — 2026-09-05

## Measured gap

MCP could call semantic and hybrid retrieval but could not discover whether its authorized corpus
contained any compatible embeddings. An online empty index and a usable semantic corpus looked the
same to an agent, encouraging blind calls and misleading readiness claims.

## Minimum extension

Retrieval-v5 adds `GET /v1/retrieval/capabilities` and MCP
`get_retrieval_capabilities`. The contract reports supported modes, configured dimensions,
authorized active/embedded Chunk counts, semantic availability, and the exact model/version groups
available to the current access context.

The query reuses current DocumentVersion ACL enforcement. It returns no text, vector, raw ACL, or
unauthorized model metadata. No provider registry, model router, vector store, or cache was added.

## Verification

- Schema and adapter tests bring the full suite to 81 passing tests; Doctor passes 36/36.
- The real personal access context reports 80 accessible Chunks, zero embedded Chunks, no models,
  and `semantic_available=false`.
- The same personal workspace with an unrelated principal reports zero accessible and embedded
  Chunks.
- Isolated workspace `it-capability-v1` reported one authorized embedded Chunk and exactly
  `it-capability-model` version `1`; a different principal saw zero counts and no model metadata.
- Exact cleanup removed the embedded fixture, its evidence ancestry, temporary SQLite store, and
  Workspace, leaving zero matching workspaces.

This makes semantic readiness machine-readable without pretending that the personal corpus is
already embedded or selecting a technology before quality evidence exists.
