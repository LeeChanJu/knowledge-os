A bounded piece of document text used as addressable evidence.

## The problem at this stage

Instead of pointing to an entire textbook, point to the relevant passage. Small evidence units make retrieval and citations more precise.

## Follow one study note

Cite the passage saying “review stopped” rather than the whole note. Even identical text needs the identity of its document version and passage.

## Distinguish the concept from its implementation

F6 tracks hard chunk-bound correctness. A configured limit is not proof that every input obeys it.

Chunks belong to an immutable DocumentVersion and are generated under a versioned chunking contract.

## Boundaries the implementation must preserve

- Current ACL and active Document lifecycle govern reads. Historical Chunk provenance is retained even when its source is deleted.

## Inputs, outputs and data responsibility

- Version identity, chunk order, text, processing metadata.
- Authorized exact evidence and retrieval candidates.
- Evidence text, version link, lifecycle flags, optional embedding provenance.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Evidence passage | Which text supports the claim? | An exact part of an observed version |
| Provenance | Where did that passage come from? | Links to version, document and source |

<!-- CHECKS -->

### Is copying the same sentence sufficient provenance?

No. Preserve passage identity, document version, source and authorization context to inspect a past answer.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
