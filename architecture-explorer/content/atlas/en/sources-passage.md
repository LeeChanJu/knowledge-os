## Which passage provides support?

```diagram
📄 SAP AI study note
✂️ The passage saying “We reviewed both”
Check what the passage actually supports
```

Pointing to the precise part used makes review easier than citing an entire document. Two names in that passage do not necessarily establish usage. Distinguish the existence of material from support for a claim.

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
