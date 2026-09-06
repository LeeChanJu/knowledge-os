# Semantic retrieval readiness — 2026-09-05

## Measured state

The personal workspace has twelve current Documents and eighty active Chunks. Zero Chunks have an
embedding. The Neo4j `chunk_embedding_vector` index is online with cosine similarity and 1,536
dimensions, but no local Ollama or llama.cpp executable and no configured OpenAI, Voyage, or Cohere
credential was detected.

This proves the semantic storage/query contract is structurally present, not that semantic
retrieval is operational or high quality. Installing a model, changing the vector store, or writing
synthetic hash vectors would be unsupported novelty rather than evidence-led engineering.

## Minimum integrity extension

The Doctor previously checked only whether indexes were online and whether stored vectors carried
complete provenance. `EMBEDDING_DIMENSIONS` could differ from the actual Neo4j index and still pass
readiness, causing every embedding write/query to fail later.

The existing Doctor now verifies exactly one `chunk_embedding_vector` index, its VECTOR type,
ONLINE state, configured dimension, and COSINE similarity against the runtime embedding contract.
No provider, model dependency, vector store, or second index was added.

## Decision gate

Semantic population remains deferred until one explicit provider/runtime is selected and can
produce reproducible document and query embeddings with stable model/version identity. The same
held-out golden-question suite must then compare semantic and hybrid recall against the existing
keyword baseline before any retrieval foundation changes.
