The identity and connector binding of an observed source.

## The problem at this stage

The identity and connector binding of an observed source. It is one part of the larger document journey. Stable boundaries prevent one adapter from silently taking over another source.

## Follow one study note

A failed folder listing must not tombstone an unseen note. Establish inventory completeness before building changes and persist the checkpoint after commit.

## Distinguish the concept from its implementation

Follow the exact repository references below. Their presence does not constitute a fresh execution result.

First ingestion binds a stable connector instance. Checkpoints advance only when the run commits.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Source Registry** implementation, not a claim that the concept or learning stage is a separate service.

- A different connector cannot silently take ownership. Item ingestion does not independently advance a completed-run checkpoint.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Source Registry** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Workspace, source type, opaque external ID, connector ID.

Outputs: Stable Source identity and authorized catalog/checkpoint summaries.

Owned data: Source node, connector binding, committed sync cursor.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Observation and parsing | Preserve readable source evidence | Do not silently change the source |
| Interpretation and review | Decide what content to accept | Requires proposal and approval boundaries |

<!-- CHECKS -->

### Does finishing extraction of readable text and passages approve semantic relations?

No. Evidence preservation differs from semantic judgment. Compare a candidate against evidence and rules, then review it separately.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
