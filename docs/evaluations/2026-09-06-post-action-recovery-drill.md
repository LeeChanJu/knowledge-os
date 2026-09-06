# Post-Action recovery drill — 2026-09-06

## Scope

Recovery set `20260905T190521Z-f4f7d62a`, captured from clean commit `620bd99`, was restored into
the previously nonexistent database `kos-recovery-drill-20260906d` in the active local Neo4j
Desktop Enterprise 2026.07.1 DBMS. The live `neo4j` database remained online and was never a
restore target. A copy of the recovery set's `ops.db` was used from a dedicated temporary path.

## Results

- The database restore completed and the drill database reached `online`.
- All 14 label counts and all 22 relationship counts exactly matched the recovery manifest.
- Both Source IDs were present.
- The governed creation Action restored as `APPROVED/SUCCEEDED` with one Claim and one Execution.
- The compensation Action restored as `PROPOSED/NOT_EXECUTED` with zero Claims and Executions.
- All nine Git-controlled migrations were already current; no migration history was rewritten.
- Doctor passed all 40 checks against the restored graph and copied SQLite database.
- `personal-authorization-retrieval-v1` passed with recall 1.0, MRR 1.0, and policy pass rate 1.0,
  exercising authorized retrieval plus principal/workspace denial through the restored service.

The backup capture window was 5.952 seconds. The measured restore, registration, migration,
application validation, authorization evaluation, and topology comparison commands totaled about
19.0 seconds, excluding operator pauses; this is the local same-DBMS drill RTO observation, not an
off-host disaster-recovery claim.

Neo4j emitted a database-permission metadata script for optional role restoration. It was not
applied because this drill used the existing local administrator and validates Knowledge OS source
ACL enforcement stored in the graph, not recreation of a lost DBMS security realm. A separate-host
drill must explicitly plan and verify DBMS identities, roles, credentials, and that metadata step.

## Cleanup and boundary

The exact drill database was dropped with `DESTROY DATA`. `SHOW DATABASES` returned no matching
database, both its database and transaction directories were absent, and the active database again
passed Doctor 40/40 with zero violations. The temporary copied SQLite directory was moved to the
user Trash, so it remains recoverable until the Trash is emptied.

This drill proves recovery of the post-Action graph, operations database, governed execution
history, and application authorization behavior inside the existing DBMS. It does not prove host
loss recovery, off-device retention, credential recovery, or external System-of-Record recovery.
