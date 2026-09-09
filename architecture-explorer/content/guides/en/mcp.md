An adapter protocol through which an AI host can call exposed tools.

## The problem at this stage

It is a plug connecting an assistant to tools, not the database’s rules. Keeping MCP replaceable prevents one AI protocol from defining core knowledge semantics.

## Follow one study note

When Claude/GPT asks about the note, MCP carries a bounded read. Connection does not grant arbitrary Cypher, knowledge approval or external execution authority.

## Distinguish the concept from its implementation

The adapter can submit governed requests but cannot approve or execute Actions. It does not expose arbitrary Cypher.

The stdio adapter projects service contracts with host-fixed workspace and principals.

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
