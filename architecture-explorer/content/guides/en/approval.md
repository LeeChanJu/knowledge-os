An authorized recorded decision about a proposed change.

## The problem at this stage

A reviewer signs off after checking the proposal and its evidence. The record explains who decided and prevents extraction from bypassing governance.

## Follow one study note

A reviewer must be authorized to read the note and compare it with the candidate. The AI submitting through MCP cannot perform this approval.

## Distinguish the concept from its implementation

F4 concerns reviewer-policy enforcement. An implemented access check is not proof that every intended policy restriction is enforced.

Approval rechecks evidence lifecycle and access inside the graph transaction before promotion.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Approval** implementation, not a claim that the concept or learning stage is a separate service.

- Approval does not itself execute an external Action.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Approval** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Review identity, decision, reason and authorized evidence.

Outputs: One approval/rejection outcome.

Owned data: Decision record with exactly one governance parent.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Proposal | Request acceptance of candidate content | Includes evidence and structure |
| Approval | An authorized reviewer accepts it | Separate from MCP submission authority |

## Review and approve in Telegram

A personal Telegram bot can now serve as the human review surface. The first notification includes the proposed change and complete source evidence attachment. After reading it, choose **Approve** or **Reject**. The existing Knowledge Service rechecks access and lifecycle state and records the decision. The AI submitting a proposal does not approve it on your behalf.

For example, review the document version supporting “the project uses Neo4j” before accepting that claim. Proposal approval can promote canonical knowledge. Action approval records permission only; a separately authorized executor performs an external operation such as creating a Notion page.

Creating a bot or sending plain `/start` does not complete pairing. Enter the token in the local setup prompt, then use the one-time link, including its `?start=` value, to pair your own account. Decisions are bound to the numeric owner ID and private chat. Wrong users, wrong messages, expired buttons, and changed review content cannot authorize a decision.

The current run command is a foreground terminal process. If closing the window terminates it, or the Mac sleeps, processing stops. A visible terminal is a property of this deployment, not a Telegram requirement; background-service deployment is separate work. The review process and Neo4j must be running to process decisions. A user-requested sync starts ingestion and automatic extraction; this bot delivers the resulting proposals for review.

The adapter and isolated-database approval tests are implemented. Live delivery still requires each owner's bot token, account pairing, and running process to be checked separately. Adding this interface does not resolve every existing reviewer-policy audit finding.

[Setup and operating boundaries](https://github.com/LeeChanJu/knowledge-os/blob/main/docs/operations/telegram-review.md) · [Review adapter implementation](https://github.com/LeeChanJu/knowledge-os/blob/main/src/knowledge_os/telegram_review.py)

## What happens after I request a Notion sync?

Start with one request to Codex: **“Sync Notion.”** Codex continues through source ingestion, evidence-grounded proposal extraction, and Telegram delivery without another extraction request. There is no recurring Notion polling or scheduled model run.

The first Telegram notification includes the proposal summary and complete evidence attachment. Read it and choose **Approve** or **Reject** directly. The separate Review-opening step has been removed; decision buttons appear only after evidence delivery succeeds. Owner checks, changed-content detection, and duplicate-decision prevention remain in force.

Previously imported, unprocessed versions are included. Receipts prevent repeated submissions for the same version. Insufficient evidence and navigation-only pages yield no candidate, with an explanation. Goals are not achieved facts, and a document creation date is not assumed to be a decision date. Changed sources do not automatically supersede or invalidate previously approved knowledge.

Keep the Mac, Codex, and Neo4j available while the requested run is processed. Later Telegram decisions require the Mac, Neo4j, and review program. Telegram message long polling does not synchronize Notion or invoke extraction. Interrupted work resumes from its receipts when the user next requests a sync.

[Automatic continuation and recovery](https://github.com/LeeChanJu/knowledge-os/blob/main/docs/operations/notion-pipeline.md)

<!-- CHECKS -->

### Does AI submission complete approval?

No. Candidate submission and separate review are different stages. Current evidence access and an approval record are required.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
