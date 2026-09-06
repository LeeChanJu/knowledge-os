# Embedding provenance and semantic-readiness evidence — 2026-09-05

## Observation

The live `personal` workspace contained 80 chunks and zero stored embeddings. No existing local
embedding runtime was detected. This is not evidence of semantic retrieval quality, so no model,
vector store, or framework was added and no quality claim is made.

Code inspection found a data-integrity failure in the existing write path: an authorized adapter
could overwrite a chunk's vector, model, and version without preserving the prior embedding or
requiring a versioned transition.

## Minimal change

Retrieval-v4 retains Neo4j's existing Chunk property and vector-index design. It adds a canonical
SHA-256 fingerprint over vector, model, and model version, persists the creating principal and
creation time, accepts an identical retry as `UNCHANGED`, and rejects a different payload. This
prevents silent provenance loss without introducing another store or embedding runtime.

Semantic quality remains unproven until trusted corpus embeddings and a held-out semantic suite
exist. A future model replacement must use an explicit, governed re-embedding contract rather than
relaxing the conflict check.

## Live contract verification

An isolated temporary workspace in the live Neo4j DBMS used two 1536-dimensional synthetic
vectors. The test verified:

- first write returned `CREATED` and the identical retry returned `UNCHANGED` with the same hash;
- a different vector/model-version payload was rejected;
- a principal without source authorization could neither write nor retrieve the private chunks;
- the authorized query returned the matching chunk at rank 1; and
- a different model version returned no results.

A separate two-writer race used different payloads for one previously empty chunk; Neo4j accepted
exactly one as `CREATED` and returned `CONFLICT` for the other. Doctor now also fails if a Chunk has
an embedding without its hash/model/version/creator/time tuple, or provenance metadata without an
embedding.

The temporary graph and its exact audit/telemetry rows were removed after the assertions. These
synthetic results demonstrate storage, idempotency, model-isolation, and authorization behavior
only; they do not measure semantic relevance.
