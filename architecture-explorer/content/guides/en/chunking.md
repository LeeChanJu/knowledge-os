Splitting parsed text into addressable evidence pieces.

## The problem at this stage

Splitting parsed text into addressable evidence pieces. It is one part of the larger document journey. Repeatable processing avoids duplicate semantic state on retries.

## Follow one study note

Cite the passage saying “review stopped” rather than the whole note. Even identical text needs the identity of its document version and passage.

## Distinguish the concept from its implementation

Follow the exact repository references below. Their presence does not constitute a fresh execution result.

Chunking is versioned and deterministic; F6 leaves hard-bound enforcement unresolved.

## Boundaries the implementation must preserve

- Current ACL and active Document lifecycle govern reads. Historical Chunk provenance is retained even when its source is deleted.

## Inputs, outputs and data responsibility

- Version identity, chunk order, text, processing metadata.
- Authorized exact evidence and retrieval candidates.
- Evidence text, version link, lifecycle flags, optional embedding provenance.

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
