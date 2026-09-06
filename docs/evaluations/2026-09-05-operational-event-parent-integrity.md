# Operational Event parent integrity — 2026-09-05

## Measured correctness gap

The primitive topology audit found one relationship-free Event. Its metadata identifies the prior
Google Drive integration fixture `google-drive-it-v1` and event type `SOURCE_DOCUMENT_DELETED`.
The tombstone contract originally linked it from a Document through `HAS_EVENT`; fixture cleanup
removed the Document but did not delete the Event.

An operational Event without its Source or Document parent loses workspace and source provenance.
This is distinct from governed semantic Events, which are owned by a Workspace and already covered
by governance checks.

## Minimum extension

Source-v8 adds the read-only Doctor invariant `operational_event_has_one_source_parent`. Every Event
without `event_class='SEMANTIC'` must have exactly one incoming `HAS_EVENT` relationship from a
Source or Document. Detection remains separate from cleanup.

The single confirmed fixture ID is eligible for deletion only when its ID, event type, recorder,
and zero-relationship preconditions all match inside one transaction. No personal document,
semantic Event, or source record is eligible.

## Verification

Verified recovery set `20260905T144010Z-9f457161` protected the pre-cleanup stores. The extended
Doctor then detected exactly one violation with the expected Event ID.

One transaction required that ID, event type `SOURCE_DOCUMENT_DELETED`, recorder
`google-drive-it-v1`, and zero relationships; it deleted exactly one Event. A repeat of the broad
topology query found zero isolated stable primitives, while all three personal pending Proposals
remained intact. Complete tests, Doctor checks, and a post-cleanup recovery point follow.

Post-cleanup recovery set `20260905T144225Z-50f1520b` captures commit `4aef8d3` and passed both
SHA-256 checks, SQLite integrity, and offline Neo4j archive consistency. The final suite passed 86
tests and the Doctor passed all 40 checks with zero violations.
