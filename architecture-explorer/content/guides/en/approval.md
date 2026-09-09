An authorized recorded decision about a proposed change.

## The problem at this stage

A reviewer signs off after checking the proposal and its evidence. The record explains who decided and prevents extraction from bypassing governance.

## Follow one study note

A reviewer must be authorized to read the note and compare it with the candidate. The AI submitting through MCP cannot perform this approval.

## Distinguish the concept from its implementation

F4 concerns reviewer-policy enforcement. An implemented access check is not proof that every intended policy restriction is enforced.

Approval rechecks evidence lifecycle and access inside the graph transaction before promotion.

## Boundaries the implementation must preserve

- MCP cannot approve or reject. A pending proposal cannot acquire conflicting review outcomes. Authorization uses current evidence ACLs.

## Inputs, outputs and data responsibility

- Typed candidates, creator access context, reviewer identity and decision.
- One immutable approval/rejection outcome and, on approval, canonical records.
- Proposal identity/payload, SUPPORTED_BY lineage, Approval history.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Proposal | Request acceptance of candidate content | Includes evidence and structure |
| Approval | An authorized reviewer accepts it | Separate from MCP submission authority |

<!-- CHECKS -->

### Does AI submission complete approval?

No. Candidate submission and separate review are different stages. Current evidence access and an approval record are required.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
