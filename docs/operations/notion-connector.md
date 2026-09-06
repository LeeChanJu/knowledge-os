# Notion page-tree connector

This read-only connector translates one Notion page tree into the existing atomic manifest-v2.
Notion remains the System of Record; Neo4j stores immutable evidence versions and the connector
never writes back to Notion.

## Authorization and setup

Create a Notion internal connection with read-content capability and explicitly share the desired
root page with it. Disable content update, content insert, comments, user information, and agent
capabilities unless a separately governed use case needs them. Keep the token outside Git and the
command line. For a one-session run:

```bash
export NOTION_TOKEN='set-locally'
knowledge-os-ingest-notion \
  --root-page 00000000-0000-0000-0000-000000000000 \
  --state data/notion-page-tree-state.json
```

For durable local operation, store the token at
`~/.config/knowledge-os/notion_token` with mode `0600`. Alternatively, point
`NOTION_TOKEN_FILE` to another owner-only file. `NOTION_TOKEN` takes precedence when both are set.
The connector rejects symlinks, non-regular files, files owned by another user, and any file with
group or other permissions. The token file, like the connector state, is local operational state
and must never be committed or copied into a recovery set.

The connector calls `/users/me` and records
`notion:connection:<connection-id>` as both owner and ACL principal for every imported version. Add
that exact principal to a Knowledge Service or MCP access context to retrieve the evidence. An
operator cannot substitute a display name or arbitrary user principal.

In the current personal deployment, the owner explicitly enabled Content Insert and Content Update
on this internal connection for the governed Notion Action executor. Comment, user-information, and
agent capabilities remain disabled. This credential-level expansion does not make the ingestion
connector writable: its code path still performs only reads. All Knowledge OS writes require an
exact Action type, policy version, reviewer, executor, target, parameters, claim, and immutable
execution evidence through the separate executor. Direct use of the shared token outside those
paths is unauthorized. If a second credential becomes operationally justified, split read and write
credentials without changing Source or Action contracts.

The token is sent only as a bearer header to `https://api.notion.com/v1`; errors report status and
Notion request ID without response bodies or secrets. The pinned `Notion-Version` is `2026-03-11`.
Changing it requires a parser review and measured regression evidence, not an implicit latest-version
upgrade.

## Determinism and recovery

Block children and data-source queries are read in complete 100-item cursor pages. Nested blocks
are recursively traversed; child pages and data-source rows become separate Documents. Row
properties are rendered in deterministic property-name order. Title, rich-text, and relation
properties are reread through the page-property endpoint so values beyond the page object's
25-reference limit are retained. Canonical page identity,
last-edited time, extracted content, title, API version, and parser version determine each source
revision. Sorted page revisions determine the source cursor, which is combined with the previous
committed cursor to determine sync-run identity. State is replaced
atomically only after manifest commit, so a crash safely replays the same run and an unchanged
follow-up snapshot cannot collide with the initial manifest identity. A page
missing from a successful traversal becomes a tombstone; a failed or unauthorized traversal
commits nothing and retains the prior state.

Temporary signed Notion file URLs are excluded from version identity. Stable external URLs and
captions are retained. Unknown block types are rendered as an explicit unsupported-block marker so
extraction loss cannot be silent.

## Deliberate initial boundary

This version covers ordinary pages, nested blocks, child pages, and rows from child data sources
below one shared root. Database containers are resolved to their versioned data-source IDs and each
data source is fully cursor-paginated. A query reaching Notion's 10,000-result completeness limit
fails instead of publishing a potentially partial snapshot. It does not yet download file bodies,
ingest comments, subscribe to webhooks, or reproduce Notion's human/group ACL graph. Complex rollup
aggregations can still inherit limitations imposed by Notion itself. The Notion API connection
scope is retained truthfully as connection-level authorization; it is not mislabeled as complete
human ACL parity.
Add each missing capability only with a fixture or live corpus that proves the need and verifies the
same Source, Evidence, authorization, and recovery contracts.

## Official Notion MCP is a separate adapter

Codex may also be configured with Notion's hosted OAuth MCP endpoint:

```bash
codex mcp add notion --url https://mcp.notion.com/mcp
```

This is not the ingestion connector and must not share or replace its internal-connection token.
The hosted MCP can mutate Notion under its OAuth grant; the page-tree connector remains read-only
and is the only path from Notion into manifest-v2 and Neo4j. Direct MCP writes require an explicit
user request and are not governed Knowledge OS Actions unless an Action was created, approved,
claimed, executed through an authorized connector, and given immutable execution evidence.

The round-trip evidence and the remaining governance boundary are recorded in
[`../evaluations/2026-09-06-notion-mcp-round-trip.md`](../evaluations/2026-09-06-notion-mcp-round-trip.md).
