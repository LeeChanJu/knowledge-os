# REST operational error coverage — 2026-09-05

## Measured gap

The existing SQLite operations store captured ingestion/retrieval success and retrieval failures,
but REST-level governance and Action denials/conflicts, validation failures, unmatched routes, and
unexpected endpoint exceptions had no common operational record. Adding another observability
stack was not justified.

## Decision

Extend the existing FastAPI adapter with one middleware and reuse `OpsStore`. Record only request
method, resolved route template, response status/class, duration, generated request ID, and
`http-v1`. Do not record URLs containing resource identifiers, request bodies, principals,
credentials, or source content.

Unexpected exceptions create one correlated error row and return generic 500 JSON containing only
`error_id` and `request_id`. The stored error preserves its Python type for diagnosis but replaces
exception text with `unhandled HTTP adapter failure`. Retrieval errors now store a SHA-256 query
hash rather than the raw failed query.

## Executed evidence

The adapter test exercised four paths against a temporary real SQLite OpsStore:

- `GET /v1/contracts` produced `SUCCESS`, status 200, and `X-Request-ID`;
- an unmatched route produced `NOT_FOUND`, status 404, and route `UNMATCHED`;
- an invalid ingestion body produced `CLIENT_ERROR`, status 422, with the stable ingestion route
  template but without the body;
- a synthetic unexpected endpoint exception produced status 500, correlated telemetry/error IDs,
  a generic persisted message, and no original exception text in the response.

The test asserts that neither `principal` nor `body` appears in recorded contexts. These records
are adapter-layer evidence; existing domain telemetry remains authoritative for ingestion and
retrieval outcomes, so intentional duplication across layers is distinguishable by operation name.

## Source-adapter extension

The filesystem, Notion, and Google Drive CLI adapters now share
`source-adapter-observation-v1`. A run records its adapter name, workspace, source type, connector
identity, outcome, and duration in the existing SQLite store. Failures also receive a correlated
error ID, while the stored message is always `source adapter run failed`; exception text, access
tokens, source identifiers, file paths, and source content are excluded.

The focused test executed one success and one failure against a temporary real OpsStore. It proved
both telemetry outcomes, error correlation through the exception note, the stable adapter contract,
and absence of a synthetic token/content secret from every persisted message and context. The full
suite passed 75 tests and Doctor passed 35/35 checks. This closes failures that occur before a
connector reaches Neo4j or the REST middleware without introducing another observability system.
