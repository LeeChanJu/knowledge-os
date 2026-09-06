# NOTION_ARCHIVE_PAGE policy v1

Status: `ACTIVE_CODE_VERIFIED_LIVE_WRITE_NOT_RUN`

This is the compensation policy paired with `notion-create-page-policy-v1`.

## Capability

- Action type: `NOTION_ARCHIVE_PAGE`
- Policy version: `notion-archive-page-policy-v1`
- Reviewer: `human:owner`
- Executor: `connector:notion`
- External API: `notion.pages.update`
- Credential reference: `credential:local-notion`
- Workspace: `personal`

## Required target and parameter

The target must be `notion:page:<uuid>`. The only parameter is a non-empty
`creation_action_id`. Before claim, the executor retrieves that Action through the Knowledge
Service and requires:

- type `NOTION_CREATE_PAGE`;
- approved status and exactly one successful execution;
- immutable result evidence containing the same normalized page ID as the archive target.

An arbitrary visible page, the shared root, or a page produced outside the governed creation path
cannot pass this policy.

## Execution and ambiguity

After a new claim, the executor makes at most one `PATCH /pages/{id}` request containing only
`{"in_trash": true}`. It does not permanently delete content. Existing claims are reconciled rather
than retried. Timeout, transport failure, 5xx, or malformed success is recorded as a non-retryable
ambiguous failure, matching the creation policy.

The owner approved this compensation boundary together with the creation policy on 2026-09-06.
Automated fake-transport tests prove target lineage, exact payload, and success recording. No live
compensation has run.
