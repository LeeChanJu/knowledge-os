Follow one change from its origin to its evidence and outcome.

## The problem at this stage

Read the steps in order. Each stage has a different responsibility; arrows do not mean every stage runs automatically. Preserving identity, history and authorization makes later explanations traceable.

## Follow one study note

A failed folder listing must not tombstone an unseen note. Establish inventory completeness before building changes and persist the checkpoint after commit.

## Distinguish the concept from its implementation

This is a guided explanation of the checked snapshot, not an executed integration test. Open findings and deferred providers still apply.

Follow the diagram below and open a stage to inspect its architecture.

## Boundaries the implementation must preserve

- Compare-and-set protects current versions and cursors. Failed manifests roll back earlier records and the checkpoint. F1/F2 corrections do not establish full release acceptance.

## Inputs, outputs and data responsibility

- Typed text requests or ordered manifest records with authorization and processing metadata.
- Document/version/Chunk identities, tombstone Events, and committed checkpoints.
- Evidence lifecycle and source-run completion records in Neo4j.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Structural change | Evolve schema or indexes | Applied history and checksums |
| Correction / recovery | Address wrong records or failure state | Audit, replay and isolated restoration |

<!-- CHECKS -->

### Does having a backup or retrying prove successful recovery?

No. Require executed evidence that the correct state is restored and readable, preserving history and audits without duplication.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
