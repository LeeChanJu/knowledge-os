# Governed Notion Actions

The Notion Action executor is a separate, human-invoked adapter. It does not add write tools to MCP
and does not change the read-only Notion ingestion connector.

## Supported capabilities

- `NOTION_CREATE_PAGE` under `notion-create-page-policy-v1`
- `NOTION_ARCHIVE_PAGE` under `notion-archive-page-policy-v1`; the API operation is
  `pages.update` with `in_trash=true`

Codex and Claude MCP hosts map those exact Action types to policy versions through
`MCP_ACTION_POLICY_VERSIONS`. When the mapping is present, an undeclared Action type fails closed.
Both capabilities use reviewer `human:owner` and executor `connector:notion` in workspace
`personal`.

## Lifecycle

1. An agent calls MCP `request_action`. This creates a review-only Action and cannot approve or run
   it.
2. The owner inspects the exact target, parameters, policy, and principals:

   ```bash
   REVIEW_PRINCIPALS=human:owner REVIEW_ACTOR=human:owner \
     .venv/bin/knowledge-os-review action-show ACTION_ID
   ```

3. The owner approves that concrete Action:

   ```bash
   REVIEW_PRINCIPALS=human:owner REVIEW_ACTOR=human:owner \
     .venv/bin/knowledge-os-review action-approve ACTION_ID \
       --reason 'Exact target and parameters reviewed' --yes
   ```

4. The separately authenticated executor claims and executes it:

   ```bash
   .venv/bin/knowledge-os-execute-notion-action ACTION_ID --yes
   ```

The executor gets an Action-stable claim before the external request and writes immutable success
or failure evidence afterward. It makes one Notion request per new claim. If the claim already
exists, or the external outcome is ambiguous, it does not retry the write.

## Creation boundary

Creation is restricted to parent `3d2c3262-9b85-801f-a806-f5fec123ec68`, a trimmed 1–200 character
plain-text title, and an optional plain-text body of at most 10,000 characters and 100 paragraph
blocks. Extra parameters, rich objects, databases, arbitrary parents, and nested structures fail
before claim.

The local connection must have Notion Insert Content capability at execution time. The owner
explicitly approved enabling Content Insert and Content Update on the current personal internal
connection for the first governed live acceptance. Comment, user-information, and agent
capabilities remain disabled. The connector credential is therefore no longer credential-level
read-only, although the ingestion program remains code-path read-only. A live write still requires
a separately reviewed concrete Action and executor claim; possession of the token is not approval.
If measured operational needs justify separate read and write credentials later, split them behind
the existing Source and Action contracts rather than redesigning those contracts.

## Compensation boundary

Compensation is never an implicit delete. A new `NOTION_ARCHIVE_PAGE` Action must reference the
successful creation Action. The executor verifies that its target page ID exactly matches immutable
creation result evidence, requires a fresh approval, and then sends `in_trash=true`. Notion API
`2026-03-11` no longer accepts the older `archived` alias. See the official
[Create a page](https://developers.notion.com/reference/post-page) and
[Trash a page](https://developers.notion.com/reference/trash-page) contracts.

The current compensation Action
`action:55e5a2e960c8692e177cb1182a0cb282bb0e8aa638c3dcff5265b3b324c5e9c3`
targeted only the disposable live-acceptance page. A negative-control invocation was first rejected
before policy validation with zero decisions, Claims, and Executions. The owner later explicitly
approved cleanup, after which the Action completed with exactly one Claim and one successful
Execution. Read-only re-ingestion tombstoned the page while retaining its historical evidence.
