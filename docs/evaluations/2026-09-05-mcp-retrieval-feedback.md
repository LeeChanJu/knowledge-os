# MCP retrieval feedback — 2026-09-05

## Measured gap

MCP retrieval returned durable trace identifiers, while agents had no MCP operation to inspect a
trace or attach quality feedback. The REST Knowledge Service and local operations store already
enforced trace ownership and stored feedback, so adding another store or feedback subsystem was not
justified.

## Minimum extension

Retrieval-v6 adds two adapter projections over the existing service:

- `get_retrieval_trace` supplies the MCP server's fixed workspace and principals.
- `record_retrieval_feedback` supplies that same access context plus the configured authenticated
  actor, accepts only ratings from `-1` through `1`, and bounds comments at 4,000 characters.

Neither tool mutates Neo4j, canonical knowledge, or an external System of Record. Trace lookup and
feedback remain inaccessible across workspace/principal fingerprints.

## Verification

The contract test exercises both MCP request shapes, proves access and actor values come from host
configuration rather than tool arguments, rejects empty feedback, and checks the exposed comment
bound. The complete suite passed with 82 tests.

An in-process MCP integration used the live local Neo4j graph and a temporary operations database.
It retrieved two authorized personal results, read the resulting `retrieval-v6` trace, and recorded
rating `1` under `google-drive:me`. Re-reading that trace under `principal:denied` returned `404`,
confirming no cross-principal existence disclosure. The temporary operations database was removed
on context exit; the personal graph and durable operations database were not mutated.
