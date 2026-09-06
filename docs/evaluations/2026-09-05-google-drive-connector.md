# Google Drive connector verification — 2026-09-05

## Decision

Extend the existing source-v6 and manifest-v2 foundations with a read-only Google Drive adapter
and the backward-compatible source-v7 `document_source_uri` field. No database, queue, scheduler,
SDK, or authorization service was added.

The field was necessary because the existing manifest could preserve only the folder-level Source
URI. A Drive file's stable view link was therefore available to the connector but could not be
retained on its DocumentVersion. Source-v7 keeps the collection and evidence-item identities
separate without changing older clients.

## Provider contract evidence

The implementation was checked against the current official Google Drive v3 documentation:

- `files.list` and `permissions.list` expose continuation tokens; the adapter exhausts both before
  constructing a manifest.
- `permissions.list` permits at most 100 results and can return fewer, so permission pagination is
  mandatory.
- Google Workspace files use `files.export`; the selected Docs, Sheets, and Slides text export MIME
  types are listed in Google's export-format table.
- exported Workspace content has a 10 MB service limit. An API error therefore fails the complete
  snapshot rather than silently omitting the file.

References:

- <https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list>
- <https://developers.google.com/workspace/drive/api/reference/rest/v3/permissions/list>
- <https://developers.google.com/workspace/drive/api/reference/rest/v3/files/export>
- <https://developers.google.com/workspace/drive/api/guides/ref-export-formats>

## Automated verification

- Ruff: pass.
- Pytest: 74 passed.
- Doctor: 35/35 checks passed with zero violations.
- Mock API tests prove bearer-token transport, file-list pagination, private/shared/public principal
  mapping, content download, post-read revision checking, deterministic listing order, replay-safe
  run identity, state rebinding rejection, and tombstone construction.

## Isolated live Neo4j verification

Workspace `it-drive-5123960cc17a` used two synthetic Drive snapshots against the real local Neo4j
instance and a temporary SQLite operations database.

- Initial manifest: 2 changed, 0 unchanged, 0 tombstoned.
- Identical follow-up: 0 changed, 2 unchanged, 0 tombstoned; version count remained 2.
- One-file removal: 0 changed, 1 unchanged, 1 tombstoned.
- Source URI remained `https://drive.google.com/drive/folders/folder-it`.
- File A's current DocumentVersion URI was `https://drive.test/file-a`.
- File A remained active and File B became deleted.
- Exact cleanup left zero matching workspaces; the temporary operations database was removed.

## Personal corpus evidence and remaining gate

The 12 Markdown filenames in the ignored local inbox exactly match the 12 current personal Drive
Document titles, and every local content SHA-256 equals its current Neo4j DocumentVersion content
hash. Earlier connected-Drive discovery also returned the same 12 file IDs and titles. This proves
the local cache and current graph agree; it does not prove a fresh API download.

`GOOGLE_DRIVE_TOKEN` was not configured during this verification. The new connector therefore has
not yet performed an authenticated end-to-end pull of the personal folder and did not mutate its
existing Source checkpoint. The next production gate is a read-only OAuth token with Drive content,
metadata, and permission access, followed by two identical personal-folder runs. Until then the
existing personal Source remains usable but its original one-off ingestion is not claimed as a
repeatable connector run.

## Recovery point

After commit `2937775`, recovery set `20260905T134453Z-ae5d555d` captured the local Neo4j database
and SQLite operations store over a 5.16-second bounded window. Verification passed both artifact
SHA-256 checks, SQLite integrity, and Neo4j offline archive consistency. The ignored recovery set
contains private evidence and remains outside Git.
