# NOTION_CREATE_PAGE policy v1 — draft

Status: `ACTIVE_CODE_VERIFIED_LIVE_WRITE_NOT_RUN`

This policy specifies the minimum safe boundary for a future governed Notion page-creation
executor. It does not authorize execution, change the existing read-only ingestion connector, or
turn the separately installed hosted Notion MCP into a Knowledge OS Action executor.

## Capability and identities

- Action type: `NOTION_CREATE_PAGE`
- Policy version: `notion-create-page-policy-v1`
- Reviewer: `human:owner`
- Executor: `connector:notion`
- External API: `notion.pages.create`
- Credential reference: `credential:local-notion`
- Workspace: `personal`

Approval remains mandatory. The requester cannot review or execute its own request unless it also
arrives with the separately configured reviewer or executor principal. Existing Action claim and
execution-evidence contracts remain authoritative.

## Target and parameters

The only permitted parent is the explicitly shared page
`3d2c3262-9b85-801f-a806-f5fec123ec68`. Descendant pages, databases, data sources, and arbitrary
workspace locations are denied in v1 rather than inferred from visibility.

The canonical parameters are:

```json
{
  "title": "required plain text, 1–200 Unicode code points",
  "body": "optional plain text, at most 10000 Unicode code points"
}
```

No additional keys are accepted. The executor may encode `body` only as ordinary paragraph blocks;
it may not create databases, relations, mentions, embeds, files, formulas, templates, or nested
children. Empty titles, control characters other than newline/tab in the body, and post-normalized
limit violations fail before an execution claim is obtained.

## Idempotency and reconciliation

Knowledge OS Action identity and the execution claim remain the local source of authorization. A
successful external response must record the returned Notion page ID, URL, request ID when
available, and the stable external idempotency key in immutable ActionExecution evidence.

Notion page creation does not provide a relied-upon native idempotency guarantee. Therefore:

1. the executor performs at most one create request per claim;
2. a timeout, disconnect, or malformed success response is `AMBIGUOUS`, never an automatic retry;
3. the Action is recorded as failed with structured ambiguity evidence and requires human
   reconciliation before any replacement Action is approved;
4. an exact retry of the Action request returns the existing Action lifecycle instead of creating a
   second request;
5. a new idempotency key never serves as permission to bypass unresolved ambiguity.

The initial implementation must prove these rules with a fake API transport before any live write.
A live acceptance test, if explicitly approved later, creates one disposable child page, records its
external identifiers, imports it through the read-only connector, proves exact connector replay,
and then uses the compensation path below.

## Compensation boundary

Creation is not silently rolled back. Compensation is a separate `NOTION_ARCHIVE_PAGE` Action that
references the successful creation Action and returned page ID, requires a fresh human approval,
and sends `in_trash=true` rather than permanently deleting the page. (`archived` is not accepted by
Notion API version `2026-03-11`.) V1 must not activate creation until this compensating capability
and its audit evidence can be proven together.

## Activation gate

The owner accepted the named reviewer/executor, exact parent, parameter limits, ambiguity rule, and
trash-only compensation boundary on 2026-09-06. Automated tests now prove creation and compensation,
including duplicate claims and ambiguous outcomes. The policy is active for approved Actions, but no
live Action has been executed. Any semantic change requires a new Git commit and policy version.
