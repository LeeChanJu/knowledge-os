# Personal recovery point after live source completion — 2026-09-06

## Decision

Create a new local recovery set after Google Drive and Notion provider replay, governance approval,
Notion permission narrowing, and durable local credential setup. This extends the existing
recovery-manifest-v1 process; it adds no store, export format, or recovery abstraction.

## Executed evidence

Doctor passed all 40 checks with zero violations before capture. Recovery set
`20260905T172252Z-48c27282` was then created from clean commit
`d682e2a2f6ceceb99ce52993e6da9c23108d1d7f` using the `neo4j-admin` and Java 21 runtime belonging
to the active Neo4j Desktop Enterprise 2026.07.1 DBMS.

The bounded capture window ran from `2026-09-05T17:22:52.809239+00:00` through
`2026-09-05T17:22:57.846057+00:00`. Independent verification passed:

- Neo4j backup artifact SHA-256;
- SQLite backup artifact SHA-256;
- SQLite `PRAGMA integrity_check`;
- Neo4j archive consistency check.

The manifest records contract registry `1.37.0`, Git `dirty=false`, 13 Documents, 25 retained
DocumentVersions, 161 retained Chunks, three Proposals and Approvals, four Assertions, two
Decisions, two Sources, and one Workspace. Its SQLite snapshot records 390 telemetry rows, 203
retrieval traces, 154 evaluations, 23 audit rows, three errors, and zero feedback rows.

Only the Neo4j backup and `ops.db` are listed as artifacts. The Google ADC and owner-only Notion
token file remain outside the recovery set and outside Git.

## End-to-end restore drill

The verified artifact was restored to the previously nonexistent database
`kos-recovery-drill-20260906c` in the active local DBMS. The live `neo4j` database remained online
and was never a restore target. The restored database reached `online`, and its label counts,
relationship counts, and all migration names/checksums exactly matched the recovery manifest.

A copied `ops.db` in a temporary directory and the restored graph passed all 40 Doctor checks. The
checked-in personal authorization suite passed with policy pass rate `1.0`, proving both authorized
retrieval and workspace/principal denial through the restored application path. The exact drill
database was then dropped with `DESTROY DATA`; `SHOW DATABASES` and filesystem checks confirmed it
absent, and the active database again passed all 40 Doctor checks with zero violations. Total
measured restore, registration, validation, evaluation, and cleanup time was 6.771 seconds.

The first command attempt also exposed a runbook mismatch: Neo4j 2026.07.1 permits
`--source-database` only when `--from-path` names a directory, not an individual backup artifact.
That attempt failed before writing a target database. The successful command used the exact
artifact without `--source-database`; the runbook now records this condition.

## Boundary

This supersedes `20260905T171346Z-c29b1337` as the current verified local recovery point and proves
the current backup through a second database in the same local DBMS. It does not prove recovery
after loss of the Neo4j installation or host, encrypted off-device retention, or credential
recovery. An in-place restore still requires explicit human authorization.
