A software consumer that can use tools while pursuing a task.

## The problem at this stage

An assistant can look up information before deciding what to say or request next. Separating consumers from contracts allows different agent frameworks to use the same context.

## Follow one study note

When Claude/GPT asks about the note, MCP carries a bounded read. Connection does not grant arbitrary Cypher, knowledge approval or external execution authority.

## Distinguish the concept from its implementation

Agent requests cannot bypass policy, source authorization or human approval. A2A production integration remains deferred.

The repository exposes knowledge to agents through adapters; it does not make every consumer a built-in autonomous agent.

## Boundaries the implementation must preserve

- No direct Cypher, ingestion, approval, Action execution or external mutation tools. MCP is not entirely read-only: it can submit governed requests.

## Inputs, outputs and data responsibility

- Bounded MCP tool arguments plus host-owned workspace/principals.
- Knowledge Service results or governed request receipts.
- Host adapter configuration only; no independent knowledge store.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Adapter | Carry external requests into defined contracts | MCP and REST are replaceable |
| Stable contract | Define bounded reads, proposals and actions | Preserve lineage, authorization and governance |

<!-- CHECKS -->

### Does connecting an AI through MCP grant arbitrary Cypher or approval?

No. The adapter carries defined requests. Connection alone does not permit arbitrary database access, approval or external execution.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
