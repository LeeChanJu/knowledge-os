Source, Evidence, Knowledge, Governance, Retrieval and Action remain stable boundaries. Change foundations only with measured correctness, quality, performance, security or source-contract evidence.

## The problem at this stage

Start with responsibility and evidence before choosing technology. Stable boundaries protect provenance and reduce unnecessary infrastructure.

## Follow one study note

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

## Distinguish the concept from its implementation

The accepted ADR is the authority. Where it gives no further rationale, this page makes no additional claim.

Source, Evidence, Knowledge, Governance, Retrieval and Action remain stable boundaries. Change foundations only with measured correctness, quality, performance, security or source-contract evidence.

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
