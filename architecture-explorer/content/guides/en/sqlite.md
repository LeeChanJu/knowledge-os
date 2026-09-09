Local storage for operational records rather than canonical knowledge.

## The problem at this stage

Local storage for operational records rather than canonical knowledge. It is one part of the larger document journey. This keeps operational bookkeeping separate without adding another knowledge database.

## Follow one study note

Consider a graph commit that succeeds while its audit fails. Report the outcome truthfully and reconcile only the missing audit on retry.

## Distinguish the concept from its implementation

Follow the exact repository references below. Their presence does not constitute a fresh execution result.

SQLite owns local audit, telemetry, errors, feedback and evaluations under the ADR.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **SQLite Operations** implementation, not a claim that the concept or learning stage is a separate service.

- Operations data cannot promote canonical truth. Graph commits and SQLite writes do not form one atomic distributed transaction.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **SQLite Operations** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Bounded application observations and trace-linked evaluation/feedback.

Outputs: Operational diagnostics and online backup artifact.

Owned data: Operations tables only; no source document or canonical knowledge store.

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
