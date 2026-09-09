A focused regression pass differs from release verification. Include required real-database, concurrency and recovery checks.

<!-- DEPTH -->

### Why this responsibility exists

Keep graph/evidence relationships and transactional transitions in one existing persistence boundary.

### Inputs and outputs

Input: Governed GraphStore writes and versioned migrations.

Output: Authorized evidence, canonical reads, search results and operational provenance.

### What must be preserved

- Context graph, full-text/vector indexes, migration ledger.
- Original Systems of Record remain authoritative. No external vector store or second knowledge database is introduced.

### Follow the example

Evidence that two technologies were reviewed together does not establish that one uses the other. Review whether the proposed claim is stronger than its evidence.

### Avoid this misconception

Original Systems of Record remain authoritative. No external vector store or second knowledge database is introduced.
