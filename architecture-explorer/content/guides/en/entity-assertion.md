An evidence-backed statement about a subject.

## The problem at this stage

Separate “this is what the document says” from “this must be universally true.” Keeping statements separate allows evidence, validity and corrections to remain explainable.

## Follow one study note

Evidence that two technologies were reviewed together does not establish that one uses the other. Review whether the proposed claim is stronger than its evidence.

## Distinguish the concept from its implementation

Assertions have source evidence and temporal bounds. Runtime knowledge status is different from the Explorer’s implementation verification status.

Candidate assertion changes enter a Proposal and become canonical only through the approval path.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Assertion** implementation, not a claim that the concept or learning stage is a separate service.

- Canonical promotion requires approval. A superseding assertion preserves subject and predicate and must not silently erase its predecessor.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Assertion** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: An approved AssertionChange with evidence, predicate and temporal fields.

Outputs: Canonical Assertion reads and graph relationships.

Owned data: Claim predicate/value, evidence link, confidence, temporal and extraction provenance.

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
