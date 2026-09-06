# Canonical time contract evidence — 2026-09-05

## Integrity gap

All externally supplied source, semantic knowledge, event, decision, and action execution times
previously used an unconstrained `datetime` type. A timestamp without a timezone could therefore
be interpreted differently by adapters or hosts, participate inconsistently in deterministic IDs,
or fail when compared with an offset-aware timestamp.

The live corpus check found eight distinct `DocumentVersion.source_updated_at` samples, all with
explicit `+00:00` offsets. No existing canonical semantic or Action records required migration.

## Contract extension

Source-v4, Governance-v4, and Action-v4 use one shared `CanonicalDatetime` input type. It rejects
timezone-naive values and converts every accepted offset to UTC before hashing, comparison, or
persistence. Default system timestamps were already UTC-aware. Storage remains ISO 8601 strings in
Neo4j, so this changes no database or adapter architecture.

Tests cover fail-closed naive timestamps in source ingestion, governed Decision proposals, and
Action execution evidence, plus canonical payload equivalence of a `+09:00` timestamp with the
same instant expressed as `Z`.
