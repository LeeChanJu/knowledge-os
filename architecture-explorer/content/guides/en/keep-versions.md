Evidence used yesterday must remain identifiable after a file changes. Immutable versions preserve that earlier state.

## The problem at this stage

Start with responsibility and evidence before choosing technology. Stable boundaries protect provenance and reduce unnecessary infrastructure.

## Follow one study note

Yesterday the note said “under review”; today it says “review stopped”. Overwriting yesterday’s state would make yesterday’s answer impossible to explain.

## Distinguish the concept from its implementation

The accepted ADR is the authority. Where it gives no further rationale, this page makes no additional claim.

Evidence used yesterday must remain identifiable after a file changes. Immutable versions preserve that earlier state.

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
