Follow one change from its origin to its evidence and outcome.

## The problem at this stage

Read the steps in order. Each stage has a different responsibility; arrows do not mean every stage runs automatically. Preserving identity, history and authorization makes later explanations traceable.

## Follow one study note

Yesterday the note said “under review”; today it says “review stopped”. Overwriting yesterday’s state would make yesterday’s answer impossible to explain.

## Distinguish the concept from its implementation

This is a guided explanation of the checked snapshot, not an executed integration test. Open findings and deferred providers still apply.

Follow the diagram below and open a stage to inspect its architecture.

## Boundaries the implementation must preserve

- Metadata hashes must match persisted title/URI. Reusing one source revision with conflicting metadata fails closed. Historical ACLs are provenance, not permanent read grants.

## Inputs, outputs and data responsibility

- Content, source revision, metadata, ACL snapshot, parser/chunker contract.
- Content-addressed version identity and version-linked evidence Chunks.
- Historical metadata, authorization snapshot, hashes, processing provenance.

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
