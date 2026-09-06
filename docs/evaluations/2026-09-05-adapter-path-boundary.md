# Adapter URL path boundary — 2026-09-05

## Measured security gap

Dynamic stable IDs were interpolated directly into MCP and human-review URL paths. An HTTPX request
constructed with Source ID `../health` normalized `/v1/sources/../health` to `/v1/health`. MCP's
dynamic operations were read-only, but this still allowed tool input to select a route outside the
declared resource boundary. Review CLI identifiers also participate in governance POST paths and
required the same hardening.

## Minimum extension

Every dynamic identifier is encoded as one path segment with `/` and `%` escaped before transport.
Colons remain readable for normal stable IDs. Static route suffixes such as `approve`, `reject`, and
`neighbors` are appended only by trusted adapter code. No router, authentication system, API shape,
or storage contract changes.

## Verification

Tests cover normal IDs, slash traversal, pre-encoded traversal, and both MCP and review helpers.
They construct actual HTTPX requests and require the resulting raw path to remain below its intended
resource prefix; the complete suite passed with 89 tests.

A live in-process MCP check read the real authorized personal Source successfully, then supplied
`../../health` to the same tool. The transport requested
`/v1/sources/..%2F..%2Fhealth` and received 404 instead of normalizing to another endpoint. Both
operations were read-only and left graph and operations data unchanged.
