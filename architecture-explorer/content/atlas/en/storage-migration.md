Migrations change constraints, indexes or storage structure. Applied files are not silently edited; compare Git with the applied checksum ledger.

<!-- DEPTH -->

### Why this responsibility exists

Evolve schema explicitly and detect missing, changed, or unexpected migrations.

### Inputs and outputs

Input: Git-owned Cypher files and current SchemaMigration ledger.

Output: Applied schema/backfill operations and recorded checksums.

### What must be preserved

- SchemaMigration records in Neo4j; migration files remain authoritative in Git.
- Applied migrations are never edited silently. Explorer checks read migration files but never execute them.

### Follow the example

Adding an index differs from correcting wrong metadata in an old note. Do not silently edit an applied migration as a repair.

### Avoid this misconception

Applied migrations are never edited silently. Explorer checks read migration files but never execute them.
