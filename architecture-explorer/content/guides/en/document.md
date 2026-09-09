The stable identity of one source document across its versions.

## The problem at this stage

Your notebook remains the same notebook even after you edit a page. Stable identity connects updates and deletion observations to one history.

## Follow one study note

A renamed note still belongs to the same source document. That is why document identity differs from the identity of its observed state.

## Distinguish the concept from its implementation

Document identity is not the same as content hash. Metadata and permissions participate in versioning.

Source-scoped external identity identifies the Document; CURRENT_VERSION points to its current snapshot.

## Boundaries the implementation must preserve

- Identity is workspace/source scoped. A tombstone retains version history; direct updates require the current version precondition.

## Inputs, outputs and data responsibility

- Source identity plus external document ID.
- Stable document ID, current-version pointer, version history.
- Document identity, active/deleted lifecycle, current-version relationship.

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
