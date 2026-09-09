Follow one change from its origin to its evidence and outcome.

## The problem at this stage

Read the steps in order. Each stage has a different responsibility; arrows do not mean every stage runs automatically. Preserving identity, history and authorization makes later explanations traceable.

## Follow one study note

Two connectors may expose notes with the same title. Identity includes workspace, source and connector context instead of merging by title.

## Distinguish the concept from its implementation

This is a guided explanation of the checked snapshot, not an executed integration test. Open findings and deferred providers still apply.

Follow the diagram below and open a stage to inspect its architecture.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Action** implementation, not a claim that the concept or learning stage is a separate service.

- MCP cannot approve or execute. A lease expiry is not takeover permission. External exactly-once delivery is not guaranteed if the provider ignores idempotency. F4/F8 remain open.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Action** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Action request, designated reviewers/executors, policy version, explicit approval.

Outputs: Execution claim, provider operation, and immutable execution evidence.

Owned data: Action snapshots, review decisions, claim lease and execution records in Neo4j.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Decision | What was decided? | Evidence and decision history |
| Action request | What external change is requested? | Separate policy, approval and execution authority |

<!-- CHECKS -->

### Does approving knowledge automatically execute a Notion change?

No. External change needs a specific approved request, policy and authenticated executor. An attempt also differs from confirmed provider success.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
