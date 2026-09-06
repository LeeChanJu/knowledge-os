# Governed MCP Action requests — 2026-09-05

## Measured gap

Codex and Claude could propose semantic knowledge but had no stable way to request an operational
capability or recover its state. Direct source-system tools would bypass the existing Action-v6
idempotency, reviewer policy, execution claims, and audit history.

## Minimum extension

The replaceable MCP adapter now exposes `request_action`, `list_actions`, and `get_action` over the
existing Knowledge Service. The model may declare a capability, target, parameters, reason, and
idempotency key. Workspace, authenticated requester, review principals, execution principals, and
policy version are host configuration. Missing reviewer or executor configuration fails closed,
and `approval_required` is always true.

No Action approval, rejection, execution claim, execution result, ingestion, Cypher, or external
System-of-Record mutation was exposed. The existing Action-v6 persistence and policy contract did
not change. A bounded authorization-filtered Action list was added so an agent can recover request
state without retaining an ID in conversation memory.

## Verification

- MCP schema negotiation exposes fourteen tools and still contains no tool name for approval,
  rejection, execution, ingestion, or tombstones.
- Unit tests prove host-policy injection, identity sorting, access propagation, and fail-closed
  behavior when capability principals are missing.
- All 77 tests pass.
- A real MCP protocol client in isolated workspace `it-mcp-action-v4` created one
  `NOTION_CREATE_PAGE` Action through the in-process Knowledge Service.
- An exact retry returned the same ID with `unchanged=true`.
- Authorized list and detail reads returned exactly that pending Action, reviewer `human:owner`,
  and executor `connector:notion`.
- Direct graph counts were one Action, zero Approvals, and zero ActionExecutions.
- Exact cleanup left zero matching workspaces and removed the temporary SQLite store.
- Codex global and Claude project-local registrations were updated with the personal reviewer,
  logical executor, and action-policy environment. Both registration reads confirmed the values.
- The active non-editable wheel initially still exposed the previous eleven-tool build after an
  ordinary `uv sync`. An explicit `--reinstall-package knowledge-os` rebuilt it; installed-package
  negotiation then exposed exactly fourteen tools, including the three Action tools and no
  forbidden mutation tool. Operations documentation now makes this deployment step explicit.

The live test also exposed an existing Cartesian-product notification in Action creation. The
Workspace relationship is now created in the original atomic query, removing that unnecessary
second match without changing Action identity or lifecycle behavior.

## Remaining boundary

This proves safe request and observation, not external execution. A separately authenticated human
must approve an Action, and a separately authorized connector must obtain an execution claim before
calling a System-of-Record API. MCP cannot perform either operation.
