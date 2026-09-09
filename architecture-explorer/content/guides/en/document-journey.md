The trace of where information came from and how it reached this record.

## The problem at this stage

A quotation needs a book, edition and page—not just the author’s name. Without lineage, a changed or deleted original makes old answers difficult to explain.

## Follow one study note

Yesterday the note said “under review”; today it says “review stopped”. Overwriting yesterday’s state would make yesterday’s answer impossible to explain.

## Distinguish the concept from its implementation

Historical authorization snapshots are evidence of past context, not permanent access grants. Reads check current authorization.

The Source → Document → DocumentVersion → Chunk → Assertion lineage is preserved.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **DocumentVersion** implementation, not a claim that the concept or learning stage is a separate service.

- Metadata hashes must match persisted title/URI. Reusing one source revision with conflicting metadata fails closed. Historical ACLs are provenance, not permanent read grants.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **DocumentVersion** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Content, source revision, metadata, ACL snapshot, parser/chunker contract.

Outputs: Content-addressed version identity and version-linked evidence Chunks.

Owned data: Historical metadata, authorization snapshot, hashes, processing provenance.

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
