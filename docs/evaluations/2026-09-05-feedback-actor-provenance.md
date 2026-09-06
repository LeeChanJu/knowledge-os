# Feedback actor provenance — 2026-09-05

## Correctness gap

The MCP adapter supplied its configured actor, but the underlying REST feedback request accepted an
arbitrary actor string. Trace ownership was enforced while attribution was not, allowing operational
quality evidence to claim an unrelated identity.

## Minimum compatible extension

Retrieval-v7 binds `FeedbackCreate.actor` to its existing `AccessContext`. A sole principal is
derived when actor is omitted. Multi-principal access must identify one of its members, and a foreign
actor fails validation. Comments use the same 4,000-character bound already exposed through MCP.
This changes no storage engine, authentication mechanism, trace identity, or canonical graph data.

## Verification

Contract tests cover derived and explicit valid actors, foreign attribution, ambiguous
multi-principal attribution, and the comment bound; the complete suite passed with 83 tests.

An in-process REST integration used live local Neo4j retrieval and a temporary operations database.
Feedback without an explicit actor derived `google-drive:me` and returned `201`. Reusing the same
authorized trace while claiming `principal:mallory` returned `422`; the feedback table contained
only the one legitimate row. The temporary database was removed on context exit, so durable personal
operations data and the personal graph were not changed.
