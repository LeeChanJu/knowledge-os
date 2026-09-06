# Direct document mutation CAS — 2026-09-05

## Correctness gap

Manifest-v2 serializes a whole source run on the Source node and checks its committed cursor. The
direct text and tombstone endpoints instead read a Document's current version before opening their
write transaction and then changed it without a version precondition. Two adapters could therefore
both validate stale state, with the later commit silently becoming current.

## Source-v5 extension

Direct changes and deletions now carry `expected_current_version_id`. The write transaction checks
the same `DocumentVersion.id` before replacing `CURRENT_VERSION` or changing lifecycle state.
Initial creation requires no expected ID, and an identical current payload remains an idempotent
no-op. Atomic manifests calculate the document precondition within their existing Source lock;
their provider-neutral payload and transaction boundary remain unchanged.
Direct updates also require the Document to remain `ACTIVE`, preventing a late write from silently
resurrecting a concurrently tombstoned document. A later authoritative manifest may reactivate a
record that has genuinely reappeared because its Source lock orders that lifecycle transition.

This is optimistic concurrency on the existing graph primitive, not a queue, orchestration layer,
or new source-version ordering abstraction. Opaque provider revisions remain preserved rather than
being incorrectly treated as sortable values.

## Live verification

An isolated source in the live Neo4j DBMS demonstrated:

- two different direct updates using the same expected version produced exactly one success and
  one conflict;
- retrying the winning payload returned the same version as an unchanged operation;
- a direct update and tombstone racing on one version produced exactly one success and one
  conflict; and
- the resulting Document retained exactly one `CURRENT_VERSION`, with lifecycle state and active
  chunks consistent with the winning mutation.

A separate compatibility sequence submitted three atomic manifests: initial upsert, changed
upsert, and tombstone. It committed through `cursor-3` and ended with one current version, a
`DELETED` Document, and zero active chunks. Temporary graph and exact operational rows were removed
after both integrations.

The same review also closed a lifecycle response mismatch: an upsert equal to a deleted current
version can no longer return `UNCHANGED` while leaving the Document deleted. It reaches the existing
ambiguous-reversion guard and requires a distinct source version or source timestamp before a
manifest may create a new active version.

A live deletion/reappearance sequence confirmed that the same historical revision was rejected
without advancing the source cursor. Repeating the content with a distinct revision then created a
second DocumentVersion, advanced the cursor, and restored the Document to `ACTIVE`.
