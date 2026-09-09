Rules defining what kinds of things and relationships the model allows.

## The problem at this stage

Data is what you write down. A graph connects it. An ontology defines what those connections mean and which combinations are allowed. A graph can store a connection even when it makes no sense. Rules help reject invalid combinations before promotion.

## Follow one study note

A reviewer must be authorized to read the note and compare it with the candidate. The AI submitting through MCP cannot perform this approval.

## Distinguish the concept from its implementation

The current validator returns early for scalar values. F5 records the unresolved predicate-validation gap. RUNS_ON and Platform are not registered in ontology 1.0.0.

Ontology.load reads config/ontology.yaml. Ontology.validate checks subject type, and for entity objects checks object type, predicate and allowed endpoints.

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
| Identity | How is the same subject referenced? | Not universal automatic alias merging |
| Relation rules | Which types and predicates are allowed? | Valid structure does not prove truth |

<!-- CHECKS -->

### Can a structurally allowed relation immediately be accepted as a fact?

No. Structural validity still requires supporting evidence and separate review. Consult unresolved verification scope as well.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
