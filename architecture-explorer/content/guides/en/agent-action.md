Follow one change from its origin to its evidence and outcome.

## The problem at this stage

Read the steps in order. Each stage has a different responsibility; arrows do not mean every stage runs automatically. Preserving identity, history and authorization makes later explanations traceable.

## Follow one study note

Two connectors may expose notes with the same title. Identity includes workspace, source and connector context instead of merging by title.

## Distinguish the concept from its implementation

This is a guided explanation of the checked snapshot, not an executed integration test. Open findings and deferred providers still apply.

Follow the diagram below and open a stage to inspect its architecture.

## Boundaries the implementation must preserve

- A different connector cannot silently take ownership. Item ingestion does not independently advance a completed-run checkpoint.

## Inputs, outputs and data responsibility

- Workspace, source type, opaque external ID, connector ID.
- Stable Source identity and authorized catalog/checkpoint summaries.
- Source node, connector binding, committed sync cursor.

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
