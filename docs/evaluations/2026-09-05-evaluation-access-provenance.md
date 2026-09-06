# Evaluation access provenance — 2026-09-05

## Correctness gap

Evaluation rows retained the evaluator version and optional retrieval trace but not their workspace
or authorized access fingerprint. A reusable multi-customer operations database therefore could not
scope evaluation evidence without resolving every row indirectly, and unlinked evaluations had no
tenant provenance at all.

## Minimum compatible extension

Retrieval-v8 adds nullable `workspace_id` and `access_fingerprint` columns to the existing SQLite
evaluations table. Every new linked evaluation derives those values from its immutable retrieval
trace and rejects caller mismatches. New unlinked evaluations must supply both. On schema open,
legacy trace-linked rows are backfilled only when both values exist in the trace context; no raw
principal set is copied.

This reuses the existing operations store and trace identity. It adds no database, evaluation
service, authorization engine, or canonical graph mutation.

## Verification

Tests cover new-row derivation, mismatch and unlinked rejection, evaluation-runner propagation, and
migration of a pre-extension SQLite fixture. The complete suite passed with 84 tests.

Before the personal operations schema transition, recovery set
`20260905T143155Z-d7847826` captured and verified both stores. Opening the extended store backfilled
all 154 existing trace-linked evaluations: 151 belong to `personal`, three to the isolated
`customer-other` authorization fixture, and zero remain unscoped. SQLite integrity returned `ok` and
the extended Knowledge OS Doctor passed 37 checks with zero violations. The new read-only
`evaluation_has_access_provenance` check reports both the violation count and bounded row-ID samples;
it detects an intentionally unattributed fixture without attempting repair.
