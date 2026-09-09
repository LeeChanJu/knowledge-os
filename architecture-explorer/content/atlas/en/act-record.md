## What should be checked after execution?

```diagram
Record the outcome
↓ Read the source back and connect evidence
Distinguish success, failure and ambiguity
```

Connect execution records with observed source state for later inspection. Undoing a change may itself require a separately approved action; do not assume automatic recovery of every failure. This documentation site is read-only and executes nothing.

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
