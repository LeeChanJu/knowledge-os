# MCP canonical Decision and Event reads — 2026-09-05

## Measured adapter gap

Governed Proposal approval creates canonical Decision and semantic Event records behind authorized
REST reads. MCP agents could propose and inspect candidates but could not resolve either canonical
primitive by its stable ID after a human decision. Entity reads alone do not replace Decision or
Event semantics.

## Minimum extension

Knowledge-v4 adds `get_decision` and `get_event` as read-only projections of the existing Knowledge
Service endpoints. Workspace and principals remain host-fixed, and optional `as_of` values pass
through the established temporal contract. Results retain evidence and current authorization.

No approval, rejection, canonical write, direct Cypher, or source mutation capability is added.

## Verification

Contract tests verify tool discovery, exact endpoint mapping, fixed access injection, and optional
as-of propagation; the complete suite passed with 88 tests. Existing REST integration evidence in
`2026-09-05-as-of-knowledge-reads.md` already verifies the underlying canonical temporal boundary,
so this adapter extension does not duplicate graph fixtures.

The installed MCP surface is verified with the implementation.
The personal graph has no approved canonical Decision or semantic Event, so no personal record is
created merely to demonstrate the read adapter.
