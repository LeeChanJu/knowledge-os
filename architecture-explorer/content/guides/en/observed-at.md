When information was observed.

## The problem at this stage

Ask a different clock question for validity, observation and recording. Distinguishing clocks prevents misleading historical answers.

## Follow one study note

Yesterday the note said “under review”; today it says “review stopped”. Overwriting yesterday’s state would make yesterday’s answer impossible to explain.

## Distinguish the concept from its implementation

Observation is distinct from real-world validity and database recording time.

Temporal metadata is preserved with governed records rather than inferred from document ordering.

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
| Document | Which source document? | Groups multiple observed states |
| DocumentVersion | What state was observed? | Preserves historical content, ACL and metadata |

<!-- CHECKS -->

### If only permissions change, can historical evidence keep granting access?

Historical authorization is provenance, not a permanent grant. Reevaluate current permissions while preserving the earlier evidence identity.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
