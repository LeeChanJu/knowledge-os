# Governed Notion Action executor — 2026-09-06

## Decision and scope

The owner approved `notion-create-page-policy-v1`. The existing Action-v6 contract was extended by
a replaceable executor adapter; no Action lifecycle, graph schema, database, queue, or MCP mutation
tool was introduced. MCP remains request-only.

The companion `NOTION_ARCHIVE_PAGE` capability uses a separate policy version and Notion's current
`in_trash=true` operation. The MCP adapter now supports a host-controlled Action-type-to-policy map;
when configured, unlisted capabilities fail closed.

## Verification

- Policy validation restricts creation to the one approved root and exact bounded plain-text keys.
- The fake Notion transport proves one `POST /pages` with current API headers and bounded paragraph
  blocks.
- The fake compensation path proves one `PATCH /pages/{id}` with only `in_trash=true`.
- Archive refuses a target not proven by exactly one successful creation execution.
- An existing claim causes zero external calls.
- Timeout, transport failure, 5xx, malformed success, and ordinary API rejection become immutable
  non-retryable failure evidence rather than a second write.
- Type-specific MCP policy mapping rejects undeclared capabilities.
- Full suite: 111 tests passed.
- Clean non-editable wheel import and executor CLI entrypoint passed from outside the repository.
- Doctor: 40 checks passed with zero violations.

## Live acceptance

The owner approved one concrete disposable creation Action and explicitly approved enabling Content
Insert and Content Update on the existing internal connection. Content Read remained enabled; comment,
user, and agent capabilities remained disabled.

- Creation Action: `action:034a490890756f796766fbc28c0090f9d9ff5ab9e7f3ec7971a9a6f24c03ace2`
- Immutable Approval: `approval:35500045adf3c8a47acbc8674d87371087d5119b0bc6f829f275bb69fe717ecf`
- Execution Claim: `action-execution-claim:9ccab35a7a23a6e35a654f5202202a5fec91bebbe9adc87eb3a8f3656e305f74`
- Successful execution: `action-execution:8562c9c067a32b8acc5b48ea34c093f2cee0f20cf6fc2a7c27aa2dde3ad50e49`
- Created Notion page: `3d2c3262-9b85-8148-aabf-d54035050a38`

The Action has exactly one completed claim and one successful execution. The Notion response did not
expose a request ID, so the evidence records `external_request_id=unavailable` rather than inventing
one. The first read-only tree sync imported the page and its changed parent. The immediate replay
reused all three DocumentVersion IDs, created zero Chunks, and reported three unchanged records.
Keyword retrieval returned the exact title and body with owner and ACL both set to the originating
Notion connection.

A later live attempt to execute the already successful Action exited before any provider request
with `Action already succeeded`. A fresh Action detail read still showed exactly the original one
Claim and one Execution, with execution revision 2. This proves the real adapter's terminal replay
boundary without relying only on fake transport tests. The following third Notion refresh reused the
same sync-run ID, checkpoint Event, and inventory cursor as the prior refresh; it returned no records
and manifest-level `unchanged=true`.

A separate compensation Action,
`action:55e5a2e960c8692e177cb1182a0cb282bb0e8aa638c3dcff5265b3b324c5e9c3`,
was created in `PROPOSED` state. It references the successful creation Action and targets only the
created page. It was not approved or executed; trashing the page requires a new explicit owner
approval.

The real executor was invoked against that unapproved compensation Action as a negative control. It
stopped with `Action must be approved before policy validation`. A subsequent Action detail read
confirmed `PROPOSED/NOT_EXECUTED`, zero decisions, zero Claims, and zero Executions. The failure
therefore occurred before policy evaluation, credential use, or any Notion provider request.

The owner later clarified that the disposable page had served its end-to-end test purpose and
explicitly approved the compensation. Approval
`approval:4eba506e0f04fe679a14b7598d019e6645ba60dd0328776c3bd051910cca57be`
authorized only the exact created page. The executor produced one completed Claim and one successful
`notion.pages.update` Execution with `in_trash=true`; the response again exposed no request ID, which
is recorded as `unavailable`.

The next read-only source refresh created a new parent version and tombstoned the governed test
Document. Its historical DocumentVersion and Chunk remain stored, while current keyword retrieval
no longer returns the deleted page and the Evidence bundle denies it under current source access.
The immediate replay reused both active DocumentVersions and created zero Chunks. The stable third
replay returned no records and reused the exact sync-run, checkpoint Event, and cursor.

After the live run, the 111-test suite and Ruff passed again and Doctor passed 40/40 with zero
violations. Recovery set `20260905T190101Z-19bc5fa3` captured the initial live result. After the
terminal replay and stable third source refresh were committed, clean recovery set
`20260905T190521Z-f4f7d62a` pinned commit `620bd99` and passed file hashes, SQLite integrity, and
Neo4j archive consistency verification.

After approved compensation and stable tombstone replay, clean recovery set
`20260905T191640Z-6a16d7ff` pinned commit `f0ec6d5` and passed the same file-hash, SQLite-integrity,
and Neo4j archive-consistency checks. Its manifest retains both Actions, both Claims, both
Executions, five Approvals, the deleted Document history, and the current active corpus state.
