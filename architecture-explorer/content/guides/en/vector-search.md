Retrieval by distance between numeric representations.

## The problem at this stage

It looks for nearby meanings rather than requiring the exact same words. It provides an additional retrieval signal when lexical overlap is weak.

## Follow one study note

Semantic retrieval can help when exact words are forgotten. An existing vector index is different from a populated production corpus.

## Distinguish the concept from its implementation

Index support does not imply active provider population or proven retrieval quality. Model compatibility and current authorization still matter.

The vector index is inside Neo4j; it is not a second external vector database.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Vector Index** implementation, not a claim that the concept or learning stage is a separate service.

- Do not change dimensionality merely to activate a provider. Model/version provenance must match the query. Index availability does not imply populated vectors.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Vector Index** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Authorized current Chunk vectors with model/version metadata.

Outputs: Filtered semantic search candidates.

Owned data: A Neo4j index over Chunk embeddings.

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
