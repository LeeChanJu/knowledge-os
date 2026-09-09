A connected view that helps interpret records without replacing their owners.

## The problem at this stage

A single note says little; linking it to a project, a decision and the evidence explains its context. Agents need explainable context rather than disconnected copies of files.

## Follow one study note

Evidence that two technologies were reviewed together does not establish that one uses the other. Review whether the proposed claim is stronger than its evidence.

## Distinguish the concept from its implementation

The accepted ADR assigns semantic context to Neo4j and operations to SQLite.

The graph retains semantic records, evidence and decision history under stable contracts.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Neo4j** implementation, not a claim that the concept or learning stage is a separate service.

- Original Systems of Record remain authoritative. No external vector store or second knowledge database is introduced.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Neo4j** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Governed GraphStore writes and versioned migrations.

Outputs: Authorized evidence, canonical reads, search results and operational provenance.

Owned data: Context graph, full-text/vector indexes, migration ledger.

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
