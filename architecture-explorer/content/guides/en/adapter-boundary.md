Protocols can change while evidence and governance contracts remain stable. The protocol must not redefine the knowledge model.

## The problem at this stage

Start with responsibility and evidence before choosing technology. Stable boundaries protect provenance and reduce unnecessary infrastructure.

## Follow one study note

When Claude/GPT asks about the note, MCP carries a bounded read. Connection does not grant arbitrary Cypher, knowledge approval or external execution authority.

## Distinguish the concept from its implementation

The accepted ADR is the authority. Where it gives no further rationale, this page makes no additional claim.

Protocols can change while evidence and governance contracts remain stable. The protocol must not redefine the knowledge model.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **MCP** implementation, not a claim that the concept or learning stage is a separate service.

- No direct Cypher, ingestion, approval, Action execution or external mutation tools. MCP is not entirely read-only: it can submit governed requests.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **MCP** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Bounded MCP tool arguments plus host-owned workspace/principals.

Outputs: Knowledge Service results or governed request receipts.

Owned data: Host adapter configuration only; no independent knowledge store.

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
