The system responsible for the original business record.

## The problem at this stage

A school keeps official grades in its gradebook; a student’s summary does not replace it. Keeping authority clear prevents a derived graph from silently becoming a competing business database.

## Follow one study note

Editing the fictional “SAP AI study note” in Drive does not make Knowledge OS its editor. The next observation records a new state while the original remains in Drive.

## Distinguish the concept from its implementation

Systems of Record and the Source contract are distinct: one owns originals; the other describes the integration boundary.

Read-only ingestion observes provider content and permissions, then preserves evidence snapshots.

## Boundaries the implementation must preserve

- Source content is not silently rewritten by ingestion. Derived knowledge never replaces the source of record.

## Inputs, outputs and data responsibility

- User-authored source content and source-side sharing decisions.
- Provider snapshots, file bytes, revision metadata, and ACL observations.
- Original source records outside Knowledge OS.

## Why does Drive remain authoritative?

Knowledge OS derives context. Keeping the original system authoritative preserves ownership and avoids a competing transactional record store. Start with responsibility and evidence before choosing technology.

Follow the linked document journey to see this boundary in practice.

The accepted ADR is the authority. Where it gives no further rationale, this page makes no additional claim.

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
