# Extraction context service — 2026-09-05

## Observed gap

The live personal workspace contains one Google Drive source and twelve evidence Documents, but no
canonical Assertions, Decisions, or semantic Events. Versioned extraction prompts existed and
required a supplied ontology, while the REST boundary exposed only prompt checksum metadata. An
external LLM or agent adapter therefore had to know repository file paths before it could produce
a valid governed Proposal.

## Knowledge-v3 extension

`GET /v1/ontology` returns the active ontology version, deterministically ordered entity types, and
relation subject/object constraints. `GET /v1/prompts/{name}` returns one checksum-verified prompt,
its version, checksum, and declared Proposal output contract. The existing prompt-list endpoint is
unchanged. Unknown prompt names fail with 404.

These are read-only configuration views. They do not call a model, accept extracted claims, create
canonical knowledge, or approve anything. Replaceable adapters still submit typed candidates to
the existing Assertion, Decision, or Event Proposal endpoints, where source ACL, evidence lineage,
workspace, ontology, actor, and approval controls remain authoritative.

No model SDK, agent framework, queue, or additional store was introduced. This extends the stable
Knowledge Service boundary rather than relocating prompt or ontology truth out of Git.

## Verification

- Ruff passed and all 51 unit tests passed.
- HTTP tests against the application lifecycle returned ontology v1.0.0 with deterministic
  ordering and returned the registered assertion prompt with its `ProposalCreate` output contract
  and verified content.
- An unknown prompt name returned 404, and both new routes appeared in generated OpenAPI.
- The live Doctor passed all 35 checks with zero violations.
- The live personal graph remained at one Google Drive Source, twelve Documents, and zero canonical
  semantic records; the test did not manufacture or approve user knowledge.
