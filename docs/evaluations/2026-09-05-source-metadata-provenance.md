# Source metadata provenance — 2026-09-05

## Integrity gap

The live graph had 12 DocumentVersions with source URI snapshots but zero versioned title snapshots
and zero metadata hashes. Title existed only on mutable Document nodes. Ingestion's unchanged check
also ignored title and URI, so a connector could reuse a source revision with different metadata
and receive a successful no-op while the supplied metadata was not represented as new evidence.

## Source-v6 extension

New DocumentVersions store title, source URI, a canonical SHA-256 of both fields, and the active
Source contract version. If content, processing, source revision, and ACL identify the current
version but supplied metadata differs, ingestion fails closed. A genuine rename or move uses a new
provider version or timestamp and creates another immutable DocumentVersion.

The existing processing fingerprint, Chunk identity, manifest shape, Neo4j store, and mutable
Document projection remain unchanged. Historical titles that were never captured are left unknown
rather than fabricated by backfill.

## Live verification

An isolated direct-ingestion sequence stored the original and renamed title/URI pairs on two
DocumentVersions with distinct metadata hashes and source-v6 provenance. An exact retry returned
unchanged; title-only and URI-only drift under the original revision were rejected; a new revision
created the renamed current version.

A separate atomic-manifest sequence reported one unchanged item for identical metadata, rejected
same-revision title drift without advancing the cursor, and accepted the rename with a new revision
at `cursor-c4`. Temporary graph and exact operational rows were removed after both integrations.
