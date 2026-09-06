# Notion MCP creation and ingestion round trip — 2026-09-06

> Historical snapshot: this direct hosted-MCP proof preceded the governed executor. A later
> owner-approved Action completed the Action execution gate without retroactively changing the
> classification of this direct write. Current state is recorded in
> `2026-09-06-governed-notion-action-executor.md`.

## Purpose

Verify that the official hosted Notion MCP can remain a replaceable write adapter while the
existing read-only Notion connector continues to preserve the Source and Evidence contracts. This
is an operational proof, not authorization for unattended Notion mutation and not evidence that a
governed Action executor exists.

## Configuration and authorization

- Codex global MCP name: `notion`
- Transport: streamable HTTP at `https://mcp.notion.com/mcp`
- Authentication: Notion-hosted OAuth; no token was added to this repository
- Approval boundary: the owner explicitly requested the test page creation in the active session
- Existing ingestion connection: separate internal connection with content-read capability only
- Shared ingestion root: `3d2c3262-9b85-801f-a806-f5fec123ec68`

The hosted MCP is not the ingestion credential and does not replace the deterministic page-tree
connector. Its OAuth grant can write to Notion, so it must be treated as an external action adapter,
not as part of the read-only Source adapter.

## Executed proof

An ephemeral Codex client discovered and invoked the hosted MCP tools in this order:

1. `notion-fetch` read the requested parent.
2. `notion-create-pages` created exactly one child page.
3. `notion-fetch` reread the created page.

The created page was:

- page ID: `3d2c3262-9b85-81c1-9728-c3c6ba4b6416`
- title: `Knowledge OS MCP ingestion test 2026-09-06`
- body: `Created through the official Notion MCP to verify governed ingestion into the local
  Knowledge OS. This is source content, not canonical truth.`

The existing connector then traversed the shared root and committed manifest-v2. It produced one
new Document/DocumentVersion/Chunk for the child and one new version for the parent because the
parent's child-page reference changed. A second provider-authenticated run observed two items,
reported zero changed items and two unchanged items, and created zero Chunks while advancing from
the changed run to the stable current/current checkpoint identity. A third run then reused exact
sync-run `notion-page-tree-sync:2822399f8a00d4dd6c1cc8ff0980f51ad68aba5b81bbcec380b78465d56e4ca6`
and checkpoint event `event:8d7c2340593e2cb9cb9336165ca25be7ec6e9ddd1a0c0a994e4456d19c103867`,
emitted zero records, and returned manifest-level `unchanged=true`.

Current graph measurement after the round trip:

| Source type | Active Documents | Current versions | Current Chunks |
|---|---:|---:|---:|
| `google_drive_folder` | 12 | 12 | 80 |
| `notion_page_tree` | 2 | 2 | 2 |

Doctor passed all 40 checks with zero violations. The repository worktree remained unchanged by the
external MCP operation and ingestion state stayed outside Git.

After committing this evidence, recovery set `20260905T181140Z-6faa9611` captured the graph and
operations store from clean Git commit `06e0920e32390f9faf29beeae3aba7de2ef9b488`. Read-only
verification passed both artifact SHA-256 checks, SQLite integrity, and Neo4j archive consistency.
The immediately preceding recovery set already passed an isolated end-to-end restore drill on the
same contract and DBMS foundation; this content-only change did not justify repeating that drill.

## Governance finding

This proof does not close the Action execution gate. The user approved the concrete mutation, but
the hosted MCP call did not first create an Action, obtain an immutable Approval, claim execution,
or append ActionExecution evidence. Therefore:

- do not use the hosted MCP for unattended or inferred writes;
- require an explicit user request for each direct write while it remains enabled;
- do not describe direct hosted-MCP writes as governed Knowledge OS Actions;
- before automating `notion.pages.create`, specify reviewer and executor principals, parameter
  constraints, reconciliation, duplicate handling, and rollback/compensation behavior, then extend
  the existing Action contracts rather than replacing them.
