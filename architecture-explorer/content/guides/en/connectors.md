Adapters that translate source observations into the ingestion contract.

## The problem at this stage

Adapters that translate source observations into the ingestion contract. It is one part of the larger document journey. Provider SDKs should not redefine the knowledge model.

## Follow one study note

A failed folder listing must not tombstone an unseen note. Establish inventory completeness before building changes and persist the checkpoint after commit.

## Distinguish the concept from its implementation

Follow the exact repository references below. Their presence does not constitute a fresh execution result.

Provider snapshots become manifest-v2 upserts and tombstones. Provider ACL limitations remain explicit.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Connectors** implementation, not a claim that the concept or learning stage is a separate service.

- Retries must reproduce the same semantic state. Provider failures must not be interpreted as an empty successful inventory.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Connectors** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Provider inventory, source authorization, previous connector checkpoint.

Outputs: Deterministic UPSERT/TOMBSTONE manifest and proposed next checkpoint.

Owned data: Adapter-local checkpoint files; no canonical semantic truth.

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
