# As-of knowledge reads — 2026-09-05

## Retrieval gap

Assertion, Decision, and semantic Event records preserved temporal properties, but Knowledge
Service reads had no way to apply them. An agent could retrieve future or expired knowledge and
would need to implement its own inconsistent filtering.

The live graph contained no canonical Assertions, Decisions, or semantic Events, so no production
quality or latency claim is made from current personal data.

## Knowledge-v2 extension

Entity, graph-neighbor, Decision, and semantic Event reads accept an optional timezone-aware
`as_of`. Assertion and Decision validity is half-open: the start is inclusive and end is exclusive.
A semantic Event is visible after it occurred; `ended_at` describes its occurrence duration but
does not erase the historical fact after completion. Superseded Assertions remain available at a
past as-of only while their recorded interval contains that instant.

Omitting `as_of` retains the existing historical identifier behavior. Neo4j evaluates the filters
against existing timestamp properties; no temporal database, materialized view, or new index is
introduced.

## Live boundary verification

An isolated private `it-as-of-knowledge-v2` workspace was populated through normal ingestion,
proposal, and approval paths and then removed exactly. At `2026-03-01T00:00:00Z`, Entity and
neighbor reads returned only the Assertion valid from February through April. At the exclusive
`2026-04-01T00:00:00Z` boundary, they returned only the Assertion starting in April. An omitted
`as_of` returned all three historical Assertions, preserving the prior behavior.

The governed Decision was visible during its interval, absent exactly at `valid_to`, and visible
when `as_of` was omitted. The semantic Event was absent before `occurred_at` and remained visible
after `ended_at`. A principal outside the evidence ACL received neither the Entity nor neighbors.
All assertions passed against the live Neo4j instance, and cleanup left zero matching integration
nodes. The check also exposed legacy Assertion timestamps serialized with a space separator; reads
now accept both that historical representation and canonical ISO `T` timestamps, while new writes
use canonical ISO output. No stored evidence was rewritten.
