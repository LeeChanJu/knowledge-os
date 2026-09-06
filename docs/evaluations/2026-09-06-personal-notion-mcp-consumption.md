# Personal Notion evidence consumption through Knowledge OS MCP — 2026-09-06

## Gap

The Notion page-tree connector correctly assigned imported evidence to the source-derived principal
`notion:connection:3d2c3262-9b85-8170-831e-00270582688c`, but the installed Codex and Claude Code
`knowledge-os` MCP registrations still launched with only `google-drive:me`. The graph authorization
was correct; the agent adapter lacked the exact principal required to consume the new source.

## Minimal correction

Both local host registrations now use the fixed principal set:

```text
google-drive:me,notion:connection:3d2c3262-9b85-8170-831e-00270582688c
```

No graph ACL was widened, no wildcard principal was introduced, and no credential was added to Git.
Workspace remains fixed to `personal`; Action reviewer and executor settings were unchanged. The
JSON and TOML host configurations both parsed successfully after the change.

## Authorized MCP proof

A fresh ephemeral Codex client, launched from the repository so the host-owned Knowledge Service
could load its existing local configuration, discovered `knowledge-os/search_knowledge`. Keyword
search for `Knowledge OS MCP ingestion test 2026-09-06` returned two authorized Notion results:

1. The created child Document `document:8ab452fdd321582491f74372ad43ed53c5066049c6cb5de3c3f37de9f1d8aaf1`
   and Chunk `chunk:fa04a19133c62ad3686305f0be91b44f23f9eadf753e04153f8042578b3716c3`,
   including the title and source body.
2. The parent Document `document:a98dc91d16a6612e841fc642d158c586f11c4985a7cad932311052d99a717e67`
   and Chunk `chunk:a636b7d500914ccc89d945291df85b91dfd88e2f334cbb025b27fba6b16b6c84`,
   containing the deterministic child-page reference.

The client used only the Knowledge OS MCP; it did not call the Notion or direct Neo4j MCP servers.
This proves the intended path `Notion -> manifest-v2 -> Neo4j -> Knowledge Service -> MCP -> Codex`.

## Complete provenance chain

The keyword search contract is deliberately a bounded discovery result; complete provenance is a
second stable `get_evidence` call keyed by the returned Chunk IDs. A fresh Codex MCP client executed
that exact search-to-Evidence sequence. The default search limit returned ten authorized candidates,
and the Evidence bundle returned ten matching records. For the created Notion child it retained:

- DocumentVersion `document-version:17464a4ac605e521fad9601ff3d06ef1389dab5f8f9aa0981efe9bdb7b39eef9`;
- Source `source:b328c8d2f48b788610732ebd53e760c44244688c891885887a37a5fef4a19048`;
- source type `notion_page_tree` and the stable Notion page URI;
- identical historical and current private ACL snapshots bound to the exact Notion connection.

The parent Notion result likewise returned its own current DocumentVersion and source provenance.
An earlier model response that emitted a null version after search alone was therefore an omitted
Evidence step, not a missing service field or graph lineage defect. No contract change was needed.

## Negative authorization proof

The same MCP search was launched with a one-run configuration override containing only
`unauthorized-test-principal`. It returned zero results. The override did not alter either durable
host registration.

The first diagnostic attempt from `/tmp` could not initialize the in-process service because the
registered command intentionally relies on repository-local runtime configuration. A second
read-only attempt from the repository discovered the tools but was stopped by Codex's
`approval=never` policy before data access. Neither attempt returned private data. The successful
proof used Codex's reviewed MCP-call path; both Knowledge OS operations remained read-only.

## Post-Action authorization regression

After the internal connection gained Content Insert and Content Update and the governed executor
created a second child, the same Knowledge Service search was repeated with isolated access
contexts. The exact source principal returned the governed page as rank 1 with Chunk
`chunk:8925e3df96c80641aaab8bff36477b4b7d1bfc9bdd03bb903fb645236ade0bb9`.
The result set contained the three current Notion Chunks only. A second request using
`notion:connection:unauthorized` returned zero results and its own access-bound trace ID.

This proves that expanding the external credential's mutation capabilities did not widen graph
read authorization. Source-derived ACL enforcement remains in the Knowledge Service and is
independent of the provider credential's capability switches.
