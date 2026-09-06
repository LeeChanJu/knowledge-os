# MCP Source and Document catalog — 2026-09-05

## Measured adapter gap

The REST Knowledge Service already exposed authorized Source and Document catalogs, but MCP agents
could not inspect source connector/checkpoint status or immutable document-version provenance. They
could search known content yet could not discover why a source was stale or distinguish ingestion
readiness from retrieval availability through the stable service boundary.

## Minimum extension

Source-v9 adds four read-only MCP projections: `list_sources`, `get_source`, `list_documents`, and
`get_document`. Limits are capped at 100 and access always comes from host configuration. Document
detail forces `include_chunks=false`, leaving exact bodies behind bounded search and Evidence bundle
contracts. No ingestion, tombstone, direct Cypher, canonical mutation, or external write is exposed.

## Verification

Contract tests verify tool discovery, bounds, request paths, fixed workspace/principal injection,
source filtering, and the body-exclusion flag; the complete suite passed with 87 tests.

A live personal MCP read returned one authorized `google_drive_folder` Source and 12 Documents. The
Source truthfully reported no committed sync cursor, Source detail returned all 12 current document
catalog entries, and Document detail returned one immutable version plus current authorization.
`include_chunks=false` produced zero Chunk bodies. All four Knowledge Service requests returned 200,
and the read-only integration did not mutate the graph or operations store.
