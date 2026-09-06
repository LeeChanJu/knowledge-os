# Feedback access provenance — 2026-09-05

## Correctness gap

Feedback stored its retrieval trace and authenticated actor but not the trace workspace or access
fingerprint on the feedback row. This was safe for trace-authorized writes, yet left a multi-customer
operations store dependent on an indirect join for every feedback scoping decision.

## Minimum compatible extension

Retrieval-v9 adds `workspace_id` and `access_fingerprint` to the existing SQLite feedback table.
New feedback derives both from the referenced immutable trace inside the same local transaction.
Legacy linked rows are backfilled from trace context when the schema opens; raw principal sets are
not duplicated. A new read-only Doctor check detects missing provenance and never repairs data.

No graph schema, canonical knowledge, authentication engine, or additional store is introduced.

## Verification

Tests cover new-row derivation, legacy fixture backfill, missing-provenance detection, and the
existing missing-trace rejection; the complete suite passed with 84 tests.

Recovery set `20260905T143528Z-e54e0c86` protected the pre-transition state and passed archive
hashes, SQLite integrity, and offline Neo4j consistency verification. The personal feedback table
contained zero rows, so the new columns required no personal data rewrite; zero rows remain
unscoped. SQLite integrity returned `ok`, and the extended Doctor passed 38 checks.

An in-process MCP integration used live local Neo4j retrieval with a temporary operations database.
The persisted feedback row contained actor `google-drive:me`, workspace `personal`, and the exact
expected access fingerprint under `retrieval-v9`. The temporary database was removed on exit; the
durable personal feedback table remained unchanged.
