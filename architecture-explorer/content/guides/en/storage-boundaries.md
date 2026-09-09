The ADR assigns semantic context to Neo4j and local operational records to SQLite. This is a responsibility boundary, not a claim that Neo4j cannot store logs.

## The problem at this stage

Start with responsibility and evidence before choosing technology. Stable boundaries protect provenance and reduce unnecessary infrastructure.

## Follow one study note

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

## Distinguish the concept from its implementation

The accepted ADR is the authority. Where it gives no further rationale, this page makes no additional claim.

The ADR assigns semantic context to Neo4j and local operational records to SQLite. This is a responsibility boundary, not a claim that Neo4j cannot store logs.

## Boundaries the implementation must preserve

- Provider retries must not duplicate semantic state.

## Inputs, outputs and data responsibility

- Provider observations with stable identity and authorization.
- Versioned evidence and committed source-run history.
- Source contract version; runtime data lives in Neo4j.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| System of Record | Edit originals and decide sharing | Source content and permissions |
| Knowledge OS | Preserve and retrieve context grounded in sources | Lineage and reviewed knowledge |

<!-- CHECKS -->

### Why are editing a note and inspecting a past answer different operations?

The source system owns original editing. Knowledge OS preserves observed evidence and decision history rather than replacing the original.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
