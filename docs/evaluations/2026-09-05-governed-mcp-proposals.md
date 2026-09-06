# Governed MCP Proposals — 2026-09-05

## Measured gap

Agent hosts could retrieve exact Evidence and verified extraction prompts, but could not submit the
result to the existing Governance-v6 review boundary. Direct database writes would bypass evidence
authorization, authenticated creation, content-addressed idempotency, and approval history.

## Minimum extension

The MCP adapter now maps assertion, Decision, and Event Proposal tools to the existing Knowledge
Service endpoints. It also exposes the authorization-filtered Proposal inbox and detail reads.
Workspace, principals, and actor are injected from server configuration. A single principal is the
unambiguous actor; a multi-principal session requires an explicit `MCP_ACTOR` contained in that set.

No approval, rejection, canonical promotion, Action execution, ingestion, Cypher, or external
System-of-Record mutation is exposed. The core Governance contract is unchanged.

## Verification

- SDK schema negotiation listed exactly eleven tools and bounded assertion batches at 50 and exact
  Evidence lists at 100.
- Unit tests proved actor injection for assertion, Decision, and Event payloads and fail-closed
  behavior for ambiguous or foreign actors.
- A real stdio child in isolated workspace `it-mcp-governance-v2` created an Evidence-linked
  assertion Proposal through in-process ASGI. An identical retry returned the same ID as unchanged.
- Authorized list/detail reads returned the pending Proposal and one Evidence record.
- Direct graph counts showed one Proposal, zero canonical Assertions, and zero Entities before
  cleanup. Six exact fixture nodes were deleted and the integration workspace count returned to
  zero. Its operations database lived in a temporary directory and was removed with it.

This proves governed proposal entry from an agent host; it does not prove human review UX or
automatic extraction quality.
