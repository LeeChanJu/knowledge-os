Numbered changes that establish and evolve persisted structure.

## The problem at this stage

Numbered changes that establish and evolve persisted structure. It is one part of the larger document journey. Versioned changes make persisted structure auditable.

## Follow one study note

Adding an index differs from correcting wrong metadata in an old note. Do not silently edit an applied migration as a repair.

## Distinguish the concept from its implementation

Follow the exact repository references below. Their presence does not constitute a fresh execution result.

Applied migrations are checksum-protected. The Explorer reads identities and never executes them.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Migration** implementation, not a claim that the concept or learning stage is a separate service.

- Applied migrations are never edited silently. Explorer checks read migration files but never execute them.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Migration** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Git-owned Cypher files and current SchemaMigration ledger.

Outputs: Applied schema/backfill operations and recorded checksums.

Owned data: SchemaMigration records in Neo4j; migration files remain authoritative in Git.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Structural change | Evolve schema or indexes | Applied history and checksums |
| Correction / recovery | Address wrong records or failure state | Audit, replay and isolated restoration |

<!-- CHECKS -->

### Does having a backup or retrying prove successful recovery?

No. Require executed evidence that the correct state is restored and readable, preserving history and audits without duplication.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
