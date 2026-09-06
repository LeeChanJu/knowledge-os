# Atomic manifest ingestion verification — 2026-09-05

## Correctness gap

Source-v2 processed each manifest record in an independent Neo4j transaction and committed the
cursor last. A failed run was replayable, but a stale or concurrent run could write one or more
DocumentVersions before its final cursor compare-and-set failed. The failed checkpoint therefore
did not prove that the graph was untouched.

## Decision

Source-v3 retains the existing Source, DocumentVersion, Event, Neo4j, and manifest boundaries. It
makes the complete manifest one transaction and uses the Source node as the lock target. No queue,
workflow engine, staging database, or connector-specific graph path is added.

New manifest-v2 output provides these semantics while explicit manifest-v1 payloads remain accepted
and are processed atomically. After initial sync, omission or mismatch of
`expected_previous_cursor` fails before record processing. Completion binds `sync_run_id`, cursor,
and a canonical manifest hash. The manifest validator rejects two operations for the same external
document and sorts records by external document ID before hashing and execution.

## Executed integration evidence

Tests against the live Neo4j transaction implementation used isolated `it-*` workspaces and then
deleted exactly those workspaces and their SQLite operational rows:

- an initial two-document manifest atomically committed cursor `cursor-1`;
- a stale manifest without the prior cursor failed, leaving the current version and version count
  unchanged;
- the next manifest atomically updated one document, tombstoned another, and committed `cursor-2`;
- a later manifest whose second record referenced an unknown tombstone target rolled back its
  earlier valid document update as well as its checkpoint;
- replaying the completed manifest returned unchanged;
- two manifests released concurrently with the same expected cursor resolved to one commit and one
  `source cursor changed; manifest is stale` rejection; the winning document had exactly two
  versions, not an interleaved third version;
- reuse of a completed `sync_run_id` with changed content failed because its manifest hash differed;
- the completion Event retained the opaque `sync-manifest:*` hash while the source content remained
  only in its governed DocumentVersion/Chunk lineage.

## Consequence

A committed manifest now proves all of its graph writes and checkpoint share one transaction. A
failed, stale, concurrent, or payload-substituted manifest proves no partial document mutation.
Standalone item/checkpoint APIs remain available for streaming connectors, but connectors seeking
this whole-snapshot guarantee must use manifest-v2.
