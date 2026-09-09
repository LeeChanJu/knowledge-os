A deferred agent-to-agent integration direction.

## The problem at this stage

A deferred agent-to-agent integration direction. It is one part of the larger document journey. A new protocol needs a measured requirement, not only availability.

## Follow one study note

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

## Distinguish the concept from its implementation

Follow the exact repository references below. Their presence does not constitute a fresh execution result.

A2A production integration is intentionally deferred; current access uses existing API/MCP boundaries.

## Boundaries the implementation must preserve

- Provider retries must not duplicate semantic state.

## Inputs, outputs and data responsibility

- Provider observations with stable identity and authorization.
- Versioned evidence and committed source-run history.
- Source contract version; runtime data lives in Neo4j.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Adapter | Carry external requests into defined contracts | MCP and REST are replaceable |
| Stable contract | Define bounded reads, proposals and actions | Preserve lineage, authorization and governance |

<!-- CHECKS -->

### Does connecting an AI through MCP grant arbitrary Cypher or approval?

No. The adapter carries defined requests. Connection alone does not permit arbitrary database access, approval or external execution.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
