A representation of things and the connections between them.

## The problem at this stage

Think of people and places on a map, with labeled lines explaining how they relate. Connections support questions that a list of isolated paragraphs cannot directly express.

## Follow one study note

Evidence that two technologies were reviewed together does not establish that one uses the other. Review whether the proposed claim is stronger than its evidence.

## Distinguish the concept from its implementation

The Explorer graph is a documentation map; its nodes and edges are not the runtime ontology.

Neo4j stores entities alongside document lineage, assertions and governed records.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Neo4j** implementation, not a claim that the concept or learning stage is a separate service.

- Original Systems of Record remain authoritative. No external vector store or second knowledge database is introduced.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Neo4j** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Governed GraphStore writes and versioned migrations.

Outputs: Authorized evidence, canonical reads, search results and operational provenance.

Owned data: Context graph, full-text/vector indexes, migration ledger.

## Read a knowledge graph

A representation of things and the connections between them. Think of people and places on a map, with labeled lines explaining how they relate.

Joule Studio and SAP can be represented as distinct entities connected through an evidence-backed assertion.

The Explorer graph is a documentation map; its nodes and edges are not the runtime ontology.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Entity | What is being discussed? | One entity may have many statements |
| Assertion | What is accepted about it? | Evidence, time and correction lineage are required |

<!-- CHECKS -->

### Does mentioning two names justify a “uses” relation?

No. Identifying subjects does not establish a relationship. Do not infer a stronger claim than the co-mention supports.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
