# Decision day precision — 2026-09-05

## Measured gap

The accepted personal decision record states a calendar date, `2026-09-02`, but no time or timezone.
`DecisionProposalCreate` required a timezone-aware `decided_at`. Converting the date to midnight and
presenting it as an observed instant would violate temporal provenance.

## Minimum compatible extension

Governance-v7 retains the existing `decided_at` input and adds `decided_on`. An instant produces
`decided_at_precision=INSTANT`. A source date produces `decided_at_precision=DAY`, preserves the
original ISO date, and derives midnight UTC only as a deterministic lower comparison boundary.
Canonical payload replay accepts that internally consistent pair; conflicting date/boundary values
fail validation.

Decision extraction prompt v2 tells adapters to use exactly one form and never invent midnight.
Prompt v1 remains immutable in Git. The Doctor's existing Decision temporal check now also rejects
unknown precision, a missing date for `DAY`, or a date attached to `INSTANT`. No new store or
temporal framework was added.

## Verification

- Unit tests cover legacy instant input, day derivation, missing time, conflicting values, and
  canonical JSON replay.
- The complete suite passes 78 tests.
- In isolated live workspace `it-day-decision-v3`, one exact Evidence Chunk supported a
  `decided_on=2026-09-02` Proposal.
- Human approval created a verified Decision with `decided_on=2026-09-02`,
  `decided_at=2026-09-02T00:00:00+00:00`, and `decided_at_precision=DAY`.
- Exact cleanup removed the Source, Document, DocumentVersion, Chunk, Proposal, Approval, Decision,
  Workspace, and temporary SQLite store, leaving zero matching workspaces.

Two earlier isolated attempts did not reach canonical promotion: the first validation harness used
the wrong method name; the second exposed canonical replay treating its derived timestamp as a
second external input. Both fixtures were inspected and exactly removed before the successful run.
No personal data was affected.
