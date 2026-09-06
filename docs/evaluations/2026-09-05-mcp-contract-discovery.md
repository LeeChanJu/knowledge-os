# MCP stable-contract discovery — 2026-09-05

## Measured adapter gap

The REST Knowledge Service exposed its versioned contract registry, while MCP agents could discover
tools but not the Source, Evidence, Knowledge, Governance, Retrieval, and Action versions governing
their behavior. Inferring versions from documentation or response shape couples an agent to an
implementation snapshot.

## Minimum extension

`get_contracts` is a read-only projection of `GET /v1/contracts`. It returns the Git-controlled
registry, required evidence classes, decision priority, and the highest-order rule. It exposes no
credentials, graph data, readiness samples, or mutation capability. Global Doctor readiness is
deliberately not projected because its bounded violation IDs are not workspace-scoped.

## Verification

Contract tests verify MCP discovery and exact endpoint mapping; the complete suite passed with 90
tests. A live in-process read returned registry `1.32.0`, all six domain contracts, five required
evidence classes, and the unchanged highest-order rule. The request returned 200 and read only
Git-controlled configuration.
