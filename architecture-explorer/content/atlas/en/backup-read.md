Check lineage, permissions and execution records after restore. Recorded same-DBMS recovery does not prove host-loss recovery or off-device retention.

<!-- DEPTH -->

### Why this responsibility exists

Make recovery inspectable and verify artifacts without treating the cross-store capture window as a distributed transaction.

### Inputs and outputs

Input: Existing graph and operations stores plus explicit administrative backup tooling.

Output: Recovery manifest, database artifacts, hashes, verification results.

### What must be preserved

- Protected local backup files outside committed documentation.
- Verify hashes and archive consistency before restore. Local same-DBMS restore evidence does not establish host-loss recovery or off-device retention.

### Follow the example

After retaining a backup, read the note, permissions and history in an isolated restore. Possessing a file and proving recovery are different claims.

### Avoid this misconception

Verify hashes and archive consistency before restore. Local same-DBMS restore evidence does not establish host-loss recovery or off-device retention.
