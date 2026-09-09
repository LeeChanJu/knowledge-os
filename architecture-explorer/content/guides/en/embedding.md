A numeric representation used to compare text by similarity.

## The problem at this stage

Imagine placing sentences on a map where related meanings tend to be nearby. The map is imperfect. Similarity can complement exact word matching, especially when wording differs.

## Follow one study note

Semantic retrieval can help when exact words are forgotten. An existing vector index is different from a populated production corpus.

## Distinguish the concept from its implementation

Production population remains inactive in this snapshot. Exact embedding retries are idempotent; changing a stored payload requires an explicit versioned contract.

An authorized adapter can annotate eligible current chunks with a vector and explicit model/version metadata.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Embedding** implementation, not a claim that the concept or learning stage is a separate service.

- Only current active authorized evidence can be annotated. A different payload cannot silently overwrite an embedding.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Embedding** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Chunk ID, vector, model/version, authenticated access context.

Outputs: Idempotent embedding annotation or rejection of a conflicting payload.

Owned data: Embedding vector and fingerprint on the existing Chunk.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Keyword | Search remembered wording | Terms and access filtering |
| Semantic | Search similar meaning | Compatible embeddings and populated material |
| Graph | Follow recorded relationships | Recorded relations and evidence scope |

<!-- CHECKS -->

### Does a vector index mean every note is ready for semantic search?

No. Compatible models, embedded material and accepted provider selection are separate requirements. Inspect current population and provider deferrals.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
