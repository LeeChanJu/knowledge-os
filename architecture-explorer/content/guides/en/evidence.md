Source material that supports a statement or answer.

## The problem at this stage

An answer is easier to trust when you can inspect the paragraph it relied on. Evidence lets a reader check an answer instead of trusting fluent text alone.

## Follow one study note

Yesterday the note said “under review”; today it says “review stopped”. Overwriting yesterday’s state would make yesterday’s answer impossible to explain.

## Distinguish the concept from its implementation

A mixed-access evidence bundle fails closed when any requested chunk cannot be returned.

Evidence bundles resolve exact chunk IDs with immutable version and source provenance, subject to current access checks.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Evidence Contract** implementation, not a claim that the concept or learning stage is a separate service.

- Historical ACL snapshots never replace current authorization.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Evidence Contract** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Stable Chunk IDs and current access context.

Outputs: Bounded all-or-nothing evidence bundles.

Owned data: Evidence contract version.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Evidence passage | Which text supports the claim? | An exact part of an observed version |
| Provenance | Where did that passage come from? | Links to version, document and source |

<!-- CHECKS -->

### Is copying the same sentence sufficient provenance?

No. Preserve passage identity, document version, source and authorization context to inspect a past answer.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
