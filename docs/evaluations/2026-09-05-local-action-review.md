# Local governed Action review — 2026-09-05

## Gap and decision

MCP could create review-required Actions, but the existing local review CLI handled only semantic
Proposals. Requiring ad hoc REST calls for Action decisions would make the safe path harder to use.
The existing CLI was extended with `action-list`, `action-show`, `action-approve`, and
`action-reject`; no UI, database, or alternate governance path was added.

The reviewer workspace, principals, and actor continue to come only from `REVIEW_*` host settings.
Both decisions require `--yes` after the human inspects capability, target, parameters, policy,
reviewer set, executor set, and history. The CLI exposes no execution claim or result endpoint.

## Verification

- Unit tests prove Action list/show routing, fixed reviewer injection, full access-context
  propagation, and refusal to call the service without `--yes`.
- The full suite passes 78 tests and Doctor passes 35/35 checks.
- In isolated live workspace `it-action-review-v1`, an Action requested by `agent:codex` designated
  `human:owner` as reviewer and `connector:notion` as executor.
- The CLI path listed exactly one pending Action and showed its pending detail.
- Explicit approval returned `APPROVED`; Neo4j contained one immutable Approval and zero
  ActionExecutions.
- Exact cleanup removed the Action, Approval, Workspace, and temporary SQLite store, leaving zero
  matching workspaces.

This closes the local human decision path. It deliberately does not prove or authorize external
execution; that remains a separate connector capability with an execution claim and idempotency
boundary.

## Recovery point

After commit `00617f5`, recovery set `20260905T140942Z-e924b658` captured Neo4j and SQLite over a
4.97-second bounded window. Both SHA-256 checks, SQLite integrity, and Neo4j offline archive
consistency passed. The private recovery artifacts remain in ignored local storage.
