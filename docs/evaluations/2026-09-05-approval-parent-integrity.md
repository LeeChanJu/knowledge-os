# Approval parent integrity — 2026-09-05

## Measured correctness gap

A requirement-level graph audit found 12 `Approval` nodes with no incoming or outgoing
relationships. All used integration-fixture metadata (`user:reviewer`, reason `verified`), while the
three personal Proposals remained `PROPOSED` with no Approval. Earlier exact cleanup deleted fixture
parents and relationships but left the Approval nodes themselves.

Orphan Approval history cannot be assigned to a workspace, Proposal, or Action and therefore
violates decision provenance even though canonical personal knowledge was unaffected.

## Minimum extension

Governance-v8 adds the read-only Doctor invariant `approval_has_one_governed_parent`. Every Approval
must have exactly one incoming `HAS_APPROVAL` relationship, and that parent must be a Proposal or
Action. The check detects and reports bounded IDs; it never repairs or deletes graph data.

No schema replacement or new store is introduced. The 12 confirmed fixture IDs are removed only
after a verified cross-store recovery point and an exact-count precondition.

## Verification

Recovery set `20260905T143528Z-e54e0c86` was verified before cleanup, including both archive hashes,
SQLite integrity, and offline Neo4j consistency. The extended Doctor then reported exactly 12
`approval_has_one_governed_parent` violations.

One write transaction required all 12 previously enumerated IDs, fixture reviewer and reason, and
zero relationships before deletion; a count or identity mismatch would have rolled it back. It
deleted exactly 12 fixture Approvals. Zero Approval nodes remain, while all three personal pending
Proposals remain `PROPOSED` with zero Approval relationships. Full test, migration, graph, and SQLite
checks follow the cleanup.

Post-cleanup recovery set `20260905T144010Z-9f457161` captures commit `f9a1592` and the cleaned
stores. Independent verification passed both SHA-256 checks, SQLite integrity, and offline Neo4j
archive consistency.
