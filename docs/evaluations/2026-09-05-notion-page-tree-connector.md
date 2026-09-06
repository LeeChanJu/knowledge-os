# Notion page-tree connector — 2026-09-05

## Measured gap

The provider-neutral manifest-v2 already supported Notion-shaped evidence, but there was no
executable adapter for a real Notion read API. Adding Notion-specific nodes or a second ingestion
path would have duplicated the stable Source and Evidence contracts.

## Minimum extension

The new `knowledge-os-ingest-notion` command reads a single explicitly shared page tree using the
versioned Notion API and produces the existing `SyncManifest`. It derives its access principal from
the authenticated connection ID, uses content-addressed page revisions and inventory cursors, and
writes connector state only after the atomic graph transaction succeeds. It performs no extraction
into canonical Assertions, Events, or Decisions and exposes no Notion mutation.

The adapter renders known textual blocks, recursively follows nested blocks, treats child pages and
data-source rows as separate Documents, excludes temporary signed file URLs, and emits an explicit
marker for unknown blocks. Database containers resolve to every declared data source and POST
pagination stops with an error at Notion's 10,000-row completeness boundary. This favors visible
incompleteness over silent evidence loss.

## Verification

- A transport-level test proves bearer and pinned `Notion-Version` headers plus two-page cursor
  traversal.
- A page-tree fixture proves nested-block traversal, separate child Documents, stable run identity,
  connection-derived private ACL, explicit unsupported-block evidence, and tombstones for pages
  absent from a later successful snapshot.
- Invalid page identities and connector-state rebinding to another Notion connection fail closed.
- A separate fixture proves database-to-data-source resolution, row discovery, and retention of row
  properties as evidence text.
- Transport and page-tree fixtures prove that encoded property IDs and multi-page title, rich-text,
  and relation values use the complete page-property endpoint instead of the page object's
  25-reference projection.
- Ruff and all 63 tests passed before documentation completion.

No live Notion token or customer page was available in the execution environment, so a real-source
sync remains unproven. Comments, file bodies, webhooks, Notion-limited complex rollups, and complete
human ACL parity remain explicit gaps rather than implied capabilities.
