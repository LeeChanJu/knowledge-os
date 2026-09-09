The accepted architecture keeps graph, vector and full-text in Neo4j until measured evidence justifies replacement. It does not claim a universal performance advantage.

## The problem at this stage

Start with responsibility and evidence before choosing technology. Stable boundaries protect provenance and reduce unnecessary infrastructure.

## Follow one study note

Semantic retrieval can help when exact words are forgotten. An existing vector index is different from a populated production corpus.

## Distinguish the concept from its implementation

The accepted ADR is the authority. Where it gives no further rationale, this page makes no additional claim.

The accepted architecture keeps graph, vector and full-text in Neo4j until measured evidence justifies replacement. It does not claim a universal performance advantage.

## Boundaries the implementation must preserve

- Do not change dimensionality merely to activate a provider. Model/version provenance must match the query. Index availability does not imply populated vectors.

## Inputs, outputs and data responsibility

- Authorized current Chunk vectors with model/version metadata.
- Filtered semantic search candidates.
- A Neo4j index over Chunk embeddings.

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
