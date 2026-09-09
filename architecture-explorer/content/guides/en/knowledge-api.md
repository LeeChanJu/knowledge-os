The service interface for bounded knowledge and evidence operations.

## The problem at this stage

Like a counter with defined request forms, it offers specific operations instead of unrestricted storage access. Consumers can use knowledge without depending on graph storage internals.

## Follow one study note

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

## Distinguish the concept from its implementation

Workspace and source-derived authorization apply to reads. This documentation site calls none of these endpoints.

REST exposes stable contract operations; adapters derive authenticated access context.

## Boundaries the implementation must preserve

- Ranking and vector search do not bypass evidence authorization.

## Inputs, outputs and data responsibility

- Queries, exact model/version when semantic, authenticated access.
- Bounded ranked context, capabilities, traces and evaluation evidence.
- Retrieval contract version.

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
