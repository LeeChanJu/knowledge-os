# Authorized evidence bundle — 2026-09-05

## Adapter gap

Search and Document reads exposed evidence, but an extraction or MCP adapter could not request a
bounded set of exact Chunk IDs through one stable contract. It had to retain search payloads or
fetch whole Documents, coupling the adapter to retrieval behavior and widening the content passed
to a model.

## Evidence-v2 extension

`POST /v1/evidence/bundle` accepts one to 100 Chunk IDs and an explicit workspace/principal access
context. IDs are deduplicated and sorted. A successful response contains the exact Chunk text and
hash, immutable DocumentVersion provenance, Source identity, historical authorization snapshot,
and the Document's current authorization snapshot.

The query reuses the governance boundary: every Chunk must belong to the requested workspace, its
Document must remain active, and the latest DocumentVersion must be public, owned by, or shared
with an authenticated principal. The entire request returns 404 if any ID is missing or
inaccessible. It never returns a partial bundle that could reveal which denied ID exists.

This is a read-only Evidence contract. It introduces no model, MCP dependency, database, queue, or
canonical mutation. MCP, Codex, Claude Code, and future extraction adapters can consume it without
receiving direct Neo4j credentials or Cypher access.

## Live verification

- Ruff passed and all 52 unit tests passed.
- Two exact Chunks from the live private `google_drive_folder` Source were requested in reversed,
  duplicated order using the preserved `google-drive:me` principal. The service returned exactly
  two records ordered by Chunk ID with content hashes and DocumentVersion provenance.
- The same IDs requested by an unrelated principal returned 404.
- A mixed request containing one valid ID and one nonexistent ID also returned 404, proving that
  the API did not return a partial bundle or distinguish denial from absence.
- No Chunk text was printed during verification and no graph mutation was performed.
