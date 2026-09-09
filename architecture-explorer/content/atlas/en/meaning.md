A numerical-comparison search path exists. Production provider activation is deferred; similarity is not proof.

<!-- DEPTH -->

### Why this responsibility exists

Provide semantic candidates inside the existing graph store.

### Inputs and outputs

Input: Authorized current Chunk vectors with model/version metadata.

Output: Filtered semantic search candidates.

### What must be preserved

- A Neo4j index over Chunk embeddings.
- Do not change dimensionality merely to activate a provider. Model/version provenance must match the query. Index availability does not imply populated vectors.

### Follow the example

Semantic retrieval can help when exact words are forgotten. An existing vector index is different from a populated production corpus.

### Avoid this misconception

Do not change dimensionality merely to activate a provider. Model/version provenance must match the query. Index availability does not imply populated vectors.
