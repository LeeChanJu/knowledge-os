Reproduce the source deletion time and event identity. Inspect the failure boundary between connector-built manifests and the GraphStore commit.

<!-- DEPTH -->

### Why this responsibility exists

Create immutable evidence versions and preserve replay identity. Atomically commit complete manifests under Source serialization.

### Inputs and outputs

Input: Typed text requests or ordered manifest records with authorization and processing metadata.

Output: Document/version/Chunk identities, tombstone Events, and committed checkpoints.

### What must be preserved

- Evidence lifecycle and source-run completion records in Neo4j.
- Compare-and-set protects current versions and cursors. Failed manifests roll back earlier records and the checkpoint. F1/F2 corrections do not establish full release acceptance.

### Follow the example

A failed folder listing must not tombstone an unseen note. Establish inventory completeness before building changes and persist the checkpoint after commit.

### Avoid this misconception

Compare-and-set protects current versions and cursors. Failed manifests roll back earlier records and the checkpoint. F1/F2 corrections do not establish full release acceptance.
