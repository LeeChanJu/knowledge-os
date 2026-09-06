# Notion provider-authenticated replay — 2026-09-06

> Historical snapshot: the least-privilege state below was accurate for this replay. The owner later
> approved Content Insert and Content Update for the separate governed Action executor. The
> ingestion code path remains read-only; current operating controls are documented in
> `../operations/notion-connector.md` and `../operations/notion-actions.md`.

## Decision

The existing internal `Knowledge OS` connection and explicitly shared personal root were reused.
No new connection, token refresh, permission change, source contract, or ingestion path was
introduced. Notion remains the System of Record and the connector used only its read API.

## Live evidence

The connector traversed root page `3d2c3262-9b85-801f-a806-f5fec123ec68` twice against the live
Notion API with the existing ignored state file and connection-bound ACL identity.

- First refresh: one page seen, zero content changes, zero tombstones. It committed sync run
  `notion-page-tree-sync:4c151f6df5f17710f5102deb96050e8277a98164d6a45c0bd60db9dbb1ca3093`
  after reconciling the provider cursor.
- Immediate replay: the same sync-run identity, one page seen, `unchanged=true`, zero records, zero
  content changes, and zero tombstones.
- The resulting state contains one page and inventory cursor
  `notion-page-tree-inventory:68cc1e8be7505a95e2b1cc0600a54dd45f90c2ba27605a72afc80371c8250846`.
- Neo4j contains one personal Notion Source, one Document, one current DocumentVersion, and one
  active Chunk. Doctor passed all 40 integrity checks with zero violations.

The token was copied from the existing Notion developer connection into process memory, was not
printed or persisted, and the clipboard was cleared after both runs.

## Least-privilege follow-up

The existing connection initially granted content read, update, and insert capabilities even though
the Knowledge OS source adapter is read-only. Content update and insert were disabled in the Notion
connection settings while content read remained enabled. A subsequent live connector run still
returned the same sync-run identity with `unchanged=true`, one page seen, zero records, zero content
changes, and zero tombstones. The browser confirmed both write capabilities disabled and Notion
reported the connection updated.

## Durable local credential

The connector now resolves `NOTION_TOKEN` first and otherwise reads `NOTION_TOKEN_FILE`, defaulting
to `~/.config/knowledge-os/notion_token`. The file path fails closed unless it is a regular,
non-symlink file owned by the current user with no group or other permissions. Missing, empty, and
unsafe files are covered by tests.

The existing token was written directly from the clipboard to the default path outside Git with
mode `0600`; it was never printed or placed in a command argument. After the installed wheel was
rebuilt, a run with both credential environment variables unset used the default file and returned
the same sync-run identity with `unchanged=true` and zero records. The clipboard was cleared.

Ruff and all 100 tests passed after this extension. No Source, Evidence, Knowledge, Governance,
Retrieval, or Action contract changed.

## Boundary

This proves provider-authenticated deterministic replay only for the explicitly shared one-page
root. It does not prove access to unshared pages, reproduce Notion human/group ACLs, or authorize
write-back. Corpus expansion remains a source-sharing decision rather than an architecture change.
