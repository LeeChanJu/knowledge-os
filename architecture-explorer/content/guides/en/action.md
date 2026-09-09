A governed request to change something through a System-of-Record adapter.

## The problem at this stage

Permission to suggest a change is different from permission to approve or perform it. Knowledge access must not silently grant permission to mutate external records.

## Follow one study note

When Claude/GPT asks about the note, MCP carries a bounded read. Connection does not grant arbitrary Cypher, knowledge approval or external execution authority.

## Distinguish the concept from its implementation

An approved Action remains unexecuted until an authorized adapter performs it. External APIs that ignore idempotency do not gain an exactly-once guarantee.

Actions retain policy and principal snapshots, approval, a pre-execution claim and execution evidence.

## Boundaries the implementation must preserve

- No direct Cypher, ingestion, approval, Action execution or external mutation tools. MCP is not entirely read-only: it can submit governed requests.

## Inputs, outputs and data responsibility

- Bounded MCP tool arguments plus host-owned workspace/principals.
- Knowledge Service results or governed request receipts.
- Host adapter configuration only; no independent knowledge store.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Decision | What was decided? | Evidence and decision history |
| Action request | What external change is requested? | Separate policy, approval and execution authority |

<!-- CHECKS -->

### Does approving knowledge automatically execute a Notion change?

No. External change needs a specific approved request, policy and authenticated executor. An attempt also differs from confirmed provider success.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
