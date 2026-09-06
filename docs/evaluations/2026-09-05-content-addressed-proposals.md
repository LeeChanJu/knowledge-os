# Content-addressed Proposal evidence — 2026-09-05

## Correctness gap

Assertion, Decision, and Event Proposal IDs previously included the API call time. A transport
retry of an identical extracted payload therefore created a second review item. Both items could
later be approved, multiplying semantically identical canonical records even though no new source
evidence or human intent existed.

The live graph contained zero Proposals, so establishing deterministic identity required no data
migration.

## Governance-v5 extension

Each Proposal now has a canonical JSON SHA-256 over its complete typed payload. Its stable ID binds
proposal kind, workspace, and that hash. Creation claims the ID inside the Neo4j transaction,
persists `payload_hash` and `contract_version`, and removes its transient creation marker before
commit. An exact retry returns the existing Proposal ID and current status with `unchanged=true`.

Evidence, ontology, supersession, authorization, and approval boundaries remain unchanged. A
rejected or approved payload is not reopened implicitly; a genuinely new proposal must change its
reason, evidence, temporal fields, or asserted content.

## Live verification

Sixteen concurrent submissions of one Assertion payload produced one Proposal ID and exactly one
creation. After approval created one canonical Assertion, submitting the identical payload returned
that Proposal's `APPROVED` status with `unchanged=true`. Repeated Decision and Event payloads also
returned their first IDs as unchanged. All three Proposal nodes carried governance-v5, a 64-character
payload hash, and no transient creation marker. The isolated graph and exact operational records
were removed after verification.
