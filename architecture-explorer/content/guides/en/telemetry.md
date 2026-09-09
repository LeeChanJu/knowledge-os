Bounded records describing how operations behaved.

## The problem at this stage

A stopwatch and error counter help diagnose a process without copying the whole document. Measured behavior helps diagnose failures and justify changes.

## Follow one study note

Consider a graph commit that succeeds while its audit fails. Report the outcome truthfully and reconcile only the missing audit on retry.

## Distinguish the concept from its implementation

F8 concerns graph/audit failure recovery. Separate stores do not imply a distributed transaction.

SQLite stores operational traces and bounded metadata. Adapter traces exclude document content and credentials.

## Boundaries the implementation must preserve

- Authorization-denial cases must fail on leaked results before exclusions; F7 remains open. Cross-store graph/audit recovery is not a distributed transaction; F8 remains open.

## Inputs, outputs and data responsibility

- Adapter timings, access-bound trace IDs, evaluation cases and feedback.
- Operational rows, measured retrieval metrics and diagnostic records.
- Evidence of operations in the existing local SQLite store.

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
