# Knowledge OS — Agent Instructions

## Mission

This repository implements a local-first governed Knowledge OS: a customer-specific System of Context built on Neo4j.

Systems of Record remain authoritative. This repository must not silently evolve into a replacement document store, transactional system of record, or collection of unnecessary infrastructure.

## Read First

Before making architectural or cross-cutting changes, read:

1. `README.md`
2. `docs/architecture/0001-stable-context-contracts.md`
3. `docs/architecture/north-star-conformance.md`
4. `config/contracts.yaml`
5. relevant migrations and tests

Treat the accepted ADR and versioned contracts as architectural authority.

## Stable Architecture Boundaries

The stable contracts are:

* Source
* Evidence
* Knowledge
* Governance
* Retrieval
* Action

Implementations behind these contracts may change.

REST, MCP, A2A, UI frameworks, LLM providers, embedding providers, retrieval libraries, connector implementations, and visualization technologies are replaceable adapters and must not redefine the core architecture.

## Core Data Lineage

Preserve:

Source
→ Document
→ DocumentVersion
→ Chunk
→ Assertion

Also preserve canonical:

* Entity
* Event
* Decision
* Action
* Proposal
* Approval

Source versions, evidence, authorization snapshots, temporal validity, supersession, correction lineage, and decision traces must not be silently discarded.

## Engineering Rules

Prefer the minimum sufficient engineering.

Do not introduce a new:

* database
* vector store
* queue
* orchestration system
* authorization engine
* observability platform
* distributed transaction mechanism
* custom abstraction

unless a measured requirement demonstrates that the current architecture is insufficient.

Do not redesign stable boundaries merely because another technology appears cleaner or newer.

Extend contracts rather than replacing foundations.

## Knowledge Integrity

Never silently rewrite historical knowledge.

Corrections to persisted canonical or provenance data must be:

* explicit
* versioned or content-addressed where appropriate
* auditable
* idempotent
* lineage-preserving

Ingestion must remain deterministic and idempotent.

Retries must not duplicate semantic state.

## Governance

Extracted knowledge must not silently become canonical truth.

Respect:

Proposal
→ validation
→ Approval / rejection
→ canonical graph

Actions must execute only through authenticated and authorized System-of-Record adapters and their declared policy boundaries.

Do not bypass human or policy gates.

## Testing

Implementation existing is not proof that a requirement is complete.

For correctness fixes:

1. reproduce the defect with a failing regression test
2. identify the violated invariant
3. make the smallest production correction
4. run focused regression tests
5. run affected existing tests
6. run the full suite when required by the remediation phase

Do not delete, weaken, skip, or xfail a regression merely to make the suite pass.

Use isolated real Neo4j tests where persistence, transactions, concurrency, rollback, or recovery behavior is being claimed.

## Current Remediation Workflow

v0.1 is still under correctness verification.

F1:

* metadata hash integrity
* corrected and verified

F2:

* deterministic deletion replay
* corrected and verified

Remaining audit findings must be resolved through the existing regression-driven remediation process.

Do not declare v0.1 complete until the release acceptance gate is explicitly executed.

## Deferred Capabilities

Unless separately requested and justified, do not implement:

* external vector databases
* enterprise ReBAC
* A2A production integration
* production embedding providers
* automated extraction providers
* product-facing custom graph UI
* enterprise observability infrastructure

Architecture/documentation tooling is allowed if it remains isolated and read-only with respect to the production Knowledge OS.

## Architecture Explorer

`architecture-explorer/`, if present, is developer documentation tooling.

It may read repository-owned architecture metadata and reference code, tests, ADRs, and contracts.

It must not:

* mutate Neo4j
* become a runtime dependency of `knowledge_os`
* change migrations
* change production contracts
* implement product behavior
* become another knowledge database

It must be removable without affecting the Knowledge OS.

## Validation Commands

Use the repository's existing environment and documented commands.

At minimum for Python changes run the relevant pytest scope and Ruff.

Do not claim broad verification based only on unit tests when the behavior depends on real Neo4j persistence.

## Change Discipline

Before making a broad change, state:

* invariant being changed or preserved
* authoritative contract
* files affected
* tests proving correctness
* whether persisted data requires migration or correction

When repository evidence is insufficient, report the uncertainty instead of inventing behavior.
