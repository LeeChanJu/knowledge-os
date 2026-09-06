# Backup and restore runbook

Status: recovery-manifest-v1, 2026-09-05

This runbook preserves the existing storage foundation. Neo4j remains the System of Context,
SQLite remains the local operations/evaluation store, and Git remains the versioned source for
contracts, ontology, migrations, prompts, configuration, and code. No shadow database or custom
logical export is introduced.

## Recovery set contract

Each recovery set is an immutable directory containing:

- one official, compressed Neo4j Enterprise full-backup artifact;
- one SQLite online-backup artifact containing telemetry, audit, retrieval traces, feedback,
  evaluations, and errors;
- `manifest.json` with artifact hashes and sizes, database name, UTC capture interval, stable
  contract versions and registry checksum, and Git commit/dirty state.

Neo4j and SQLite cannot share a transaction. The manifest therefore declares
`BOUNDED_CAPTURE_WINDOW` and records both ends of that window. Canonical graph integrity and
governance history reside in Neo4j; SQLite records operational evidence. Consumers must not infer
cross-store atomicity.

Backups contain private content, ACL snapshots, decisions, action evidence, and possibly sensitive
operational metadata. Store them only on access-controlled, encrypted local media. The tool never
uploads a recovery set.

## Create and verify

Run the Doctor first and require zero violations. Find the `neo4j-admin` executable and the Java
runtime belonging to the active Neo4j Desktop DBMS; do not use a binary from a different Neo4j
version.

```bash
PYTHONPATH=src uv run --no-sync python -m knowledge_os.doctor
PYTHONPATH=src uv run --no-sync python -m knowledge_os.recovery create \
  --neo4j-admin /path/to/active-dbms/bin/neo4j-admin \
  --java-home /path/to/neo4j-desktop/runtime/Contents/Home
PYTHONPATH=src uv run --no-sync python -m knowledge_os.recovery verify \
  data/backups/BACKUP_ID \
  --neo4j-admin /path/to/active-dbms/bin/neo4j-admin \
  --java-home /path/to/neo4j-desktop/runtime/Contents/Home
```

Creation writes to a hidden staging directory and publishes the set by rename only after both
backups, SQLite integrity checking, and manifest creation succeed. A failed staging directory is
removed; an already published recovery set is never overwritten. Verification is read-only with
respect to both live stores and fails if a file is missing, altered, corrupt, or escapes the set's
directory through a forged manifest path.

## Restore drill

Never test a restore over the active database. Use either a separate disposable Neo4j DBMS of the
same version or an explicitly named, previously nonexistent drill database in the active DBMS.
For the latter, use `neo4j-admin database restore DRILL_NAME --from-path=ARTIFACT` for a single
backup artifact. Use `--source-database=SOURCE_NAME` only when `--from-path` points to a directory;
Neo4j 2026.07.1 rejects that option for an individual artifact. `load` does not rename a backup.
Confirm through `SHOW DATABASES` and the database/transaction directories that the drill name is
absent before restoring. Restore `ops.db` to a temporary path, never over the live operations
database.

After registering and starting the drill database:

1. run all current Git migrations; checksum mismatches must fail rather than rewrite history;
2. run `knowledge_os.doctor` against the restored database and SQLite file;
3. compare restored label/relationship counts, migration ledger, source IDs, document/version
   counts, proposal/approval counts, action/execution counts, and SQLite table counts with the
   recorded pre-restore evidence;
4. exercise one authorized retrieval and one denied retrieval without writing feedback;
5. record the drill date, backup ID, Git commit, Neo4j version, results, deviations, RPO, and RTO;
6. drop only the explicitly named drill database with `DESTROY DATA` after retaining the report;
7. confirm through `SHOW DATABASES` and filesystem inspection that the drill database is gone,
   then rerun the Doctor against the active database.

A passing `verify` proves archive checksums and internal consistency. It does not by itself prove
that credentials, destination capacity, operator access, RTO, or an end-to-end restored service
work. Those claims require the isolated restore drill above. A second database inside the active
DBMS proves the database and application path but not recovery from loss of the DBMS installation
or host; that requires a separate-host drill.

## Restore decision boundary

An in-place production restore is destructive and requires explicit human authorization, a named
target DBMS/database, a verified recovery set, a confirmed pre-restore backup, and an outage plan.
Agents may prepare and verify artifacts but must never overwrite the active database implicitly.

Source-system re-ingestion is complementary, not a substitute for backup: it can reconstruct
source evidence but cannot reconstruct locally governed proposals, approvals, semantic knowledge,
action evidence, feedback, or decision traces that do not exist in the Systems of Record.
