A recorded comparison between expected and observed behavior.

## The problem at this stage

A test paper needs both questions and a scoring rule; a high score on one paper is not universal mastery. Evidence should guide architectural changes and expose limits, not merely decorate a success claim.

## Follow one study note

Consider a graph commit that succeeds while its audit fails. Report the outcome truthfully and reconcile only the missing audit on retry.

## Distinguish the concept from its implementation

F7 concerns authorization evaluation exclusions. Historical PROVEN entries are not automatic current VERIFIED status.

Evaluation records use the existing retrieval contract and SQLite, scoped by workspace and access fingerprint.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Telemetry / Evaluation** implementation, not a claim that the concept or learning stage is a separate service.

- Authorization-denial cases must fail on leaked results before exclusions; F7 remains open. Cross-store graph/audit recovery is not a distributed transaction; F8 remains open.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Telemetry / Evaluation** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Adapter timings, access-bound trace IDs, evaluation cases and feedback.

Outputs: Operational rows, measured retrieval metrics and diagnostic records.

Owned data: Evidence of operations in the existing local SQLite store.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Tests | Does code behave as expected? | Defined inputs and failure cases |
| Doctor | Is persisted structure intact? | Lineage and schema checks |
| Evaluation | Are retrieval quality and access sufficient? | Question suites and raw-result checks |

<!-- CHECKS -->

### What can still be wrong when a search succeeds or scores well?

Lineage corruption and unauthorized results need separate checks. An overall quality score must not conceal open scopes such as F3 or F7.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
