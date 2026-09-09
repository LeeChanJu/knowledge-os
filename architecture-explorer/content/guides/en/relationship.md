A labeled connection expressing how two things relate.

## The problem at this stage

“Uses” says more than drawing an unlabeled line between two tools. Labels make graph traversal interpretable.

## Follow one study note

Evidence that two technologies were reviewed together does not establish that one uses the other. Review whether the proposed claim is stronger than its evidence.

## Distinguish the concept from its implementation

An assertion retains the predicate, evidence and time; a bare entity-to-entity link cannot replace that record.

Semantic predicates belong to the ontology; lineage edges such as supported-by serve a different structural role.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Ontology** implementation, not a claim that the concept or learning stage is a separate service.

- Unknown types and object relations must be rejected. F5 tracks the scalar-value path bypassing predicate validation.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Ontology** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: EntityRef and AssertionChange candidates.

Outputs: Validated typed relations or a validation error.

Owned data: config/ontology.yaml version and vocabulary.

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
