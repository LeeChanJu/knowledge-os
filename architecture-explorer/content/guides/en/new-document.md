Follow one change from its origin to its evidence and outcome.

## The problem at this stage

Read the steps in order. Each stage has a different responsibility; arrows do not mean every stage runs automatically. Preserving identity, history and authorization makes later explanations traceable.

## Follow one study note

A failed folder listing must not tombstone an unseen note. Establish inventory completeness before building changes and persist the checkpoint after commit.

## Distinguish the concept from its implementation

This is a guided explanation of the checked snapshot, not an executed integration test. Open findings and deferred providers still apply.

Follow the diagram below and open a stage to inspect its architecture.

## Boundaries the implementation must preserve

- Retries must reproduce the same semantic state. Provider failures must not be interpreted as an empty successful inventory.

## Inputs, outputs and data responsibility

- Provider inventory, source authorization, previous connector checkpoint.
- Deterministic UPSERT/TOMBSTONE manifest and proposed next checkpoint.
- Adapter-local checkpoint files; no canonical semantic truth.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Document | Which source document? | Groups multiple observed states |
| DocumentVersion | What state was observed? | Preserves historical content, ACL and metadata |

<!-- CHECKS -->

### If only permissions change, can historical evidence keep granting access?

Historical authorization is provenance, not a permanent grant. Reevaluate current permissions while preserving the earlier evidence identity.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
