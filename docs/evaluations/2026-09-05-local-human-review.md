# Local human review — 2026-09-05

## Measured gap

Governance-v6 stored content-addressed Proposals and immutable Approval history, but the only review
surface was raw REST. MCP intentionally could not approve or reject. A human therefore lacked a
minimal way to inspect the exact Evidence text before making a decision.

## Minimum extension

`knowledge-os-review` uses the existing in-process FastAPI routes to list and show Proposals and to
submit approval or rejection. `show` resolves the Proposal's complete Evidence lineage through the
all-or-nothing evidence-v2 bundle. Decision commands require `--yes`; reviewer identity is injected
from fixed process settings and fails closed when a multi-principal actor is ambiguous or foreign.

No new UI framework, database, authorization engine, or promotion path was added. This CLI is a
personal local trust boundary and is explicitly not suitable as an unauthenticated network service.

## Live verification

An isolated `it-human-review-v1` workspace in the live Neo4j database contained one private fixture
Chunk and two governed assertion Proposals. The installed CLI:

- displayed one exact Evidence record for the first Proposal;
- approved the first Proposal and rejected the second with explicit confirmation;
- produced two Approval records, one canonical Assertion, and two Entities;
- left the rejected Proposal without canonical promotion; and
- used a temporary operations database rather than personal audit storage.

All twelve reachable fixture nodes were then deleted and the workspace count returned to zero.
Unit tests separately verify that no request occurs without `--yes`, exact Chunk IDs are forwarded
in sorted order, identity is injected, and ambiguous or foreign reviewers fail closed. Ruff and all
69 tests passed before documentation completion.

This proves a working local human decision path. It does not prove multi-user authentication,
browser UX, or review quality.
