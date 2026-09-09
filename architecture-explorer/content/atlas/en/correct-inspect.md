## Did the document change, or was our interpretation wrong?

```diagram
The original has new content → a new observation
An earlier interpretation was wrong → a correction candidate
Distinguish the cases and inspect prior support
```

A source edit and a knowledge correction are different operations. Depending on what changed, preserve a new document state or review an accepted statement again. Inspect the earlier record so the correction identifies what it changes.

<!-- DEPTH -->

### Why this responsibility exists

Separate changed source observations from stable Document identity and maintain supersession lineage.

### Inputs and outputs

Input: Content, source revision, metadata, ACL snapshot, parser/chunker contract.

Output: Content-addressed version identity and version-linked evidence Chunks.

### What must be preserved

- Historical metadata, authorization snapshot, hashes, processing provenance.
- Metadata hashes must match persisted title/URI. Reusing one source revision with conflicting metadata fails closed. Historical ACLs are provenance, not permanent read grants.

### Follow the example

Yesterday the note said “under review”; today it says “review stopped”. Overwriting yesterday’s state would make yesterday’s answer impossible to explain.

### Avoid this misconception

Metadata hashes must match persisted title/URI. Reusing one source revision with conflicting metadata fails closed. Historical ACLs are provenance, not permanent read grants.
