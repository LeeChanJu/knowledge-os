# Personal canonical graph consumption through MCP — 2026-09-06

## Claim

The approved personal semantic graph is consumable by an AI adapter through the real MCP protocol,
without Cypher access and without exposing approval or canonical mutation tools.

## Execution boundary

- Workspace: `personal`
- Fixed adapter principal: `google-drive:me`
- Transport: in-process MCP client through the Knowledge Service ASGI lifespan
- MCP tools discovered: 27
- Operations: `search_entities`, `get_neighbors`, and `get_decision` only
- Mutation: none

## Result

`search_entities("Knowledge OS")` returned one authorized Project Entity in graph mode. Its bounded
neighbor read returned exactly four approved relationships to Google Drive, MCP, Neo4j, and Notion.
The stable Decision read for artifact-specific source authority returned status `VERIFIED`, retained
its Evidence, and exposed exactly one Approval.

All three Knowledge Service requests returned HTTP 200. This proves the personal canonical records
created through the human governance gate can be consumed through the same replaceable MCP adapter
intended for Codex and Claude Code. It does not grant either agent direct source-system or canonical
write authority.

## Negative authorization proof

The same MCP calls were repeated with a fixed `unauthorized-test-principal` context. Entity search
returned zero results. A direct request using the known stable Decision ID returned HTTP 404 and no
Decision, Evidence, or Approval payload. This preserves non-disclosure even when an identifier is
guessed or learned elsewhere.

The first run also showed that an anticipated Knowledge Service 404 was classified by the MCP SDK
as an unexpected exception and logged a stack trace. The adapter now raises the SDK's deliberate
`ToolError` for service HTTP failures. The repeated denial remained an MCP error, exposed only the
bounded HTTP status, and logged no exception trace or private response body.
