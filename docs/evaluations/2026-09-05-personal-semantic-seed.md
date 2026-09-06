# Personal semantic seed Proposal — 2026-09-05

## Measured gap

The live personal workspace contained twelve current Google Drive Documents but zero Proposals,
Entities, Assertions, Decisions, or semantic Events. The evidence and governance platform was
working, but the personal Context Graph had no semantic content.

## Conservative extraction decision

Only relationships stated directly in current/accepted architecture evidence were selected. One
assertion Proposal contains:

- `Knowledge OS (Project)-[:USES]->Neo4j (Technology)`
- `Knowledge OS (Project)-[:USES]->Google Drive (Technology)`
- `Knowledge OS (Project)-[:USES]->Notion (Technology)`
- `Knowledge OS (Project)-[:USES]->MCP (Tool)`

The Proposal is supported by exact Chunks from `01_Knowledge_OS_Architecture.md` and
`06_GoogleDrive_vs_Notion_Source.md`. It was submitted through the real MCP protocol as
`google-drive:me`, using ontology `1.0.0` and extractor marker
`codex:manual-evidence-review-v1`.

The source review record also contains valuable accepted Decisions, but records only the calendar
date `2026-09-02`. The current Decision contract requires an exact timezone-aware timestamp.
Inventing midnight would create false temporal precision, so no Decision Proposal was created.
This is now evidence for a future backward-compatible temporal-precision extension.

That measured gap was subsequently closed by Governance-v7 and decision extraction prompt v2;
see `2026-09-05-decision-day-precision.md`. The seed audit above remains the reason the extension
was made rather than being rewritten after the fact.

## Live verification

- Proposal ID: `proposal:61418232f130d764b4484e64c3dc3409006676299bc9e7e9433d6fa6d81646b1`
- Type/status: `ASSERTION / PROPOSED`
- Changes: 4
- Distinct authorized Evidence Chunks: 2
- Approval records: 0
- Personal canonical Assertions: 0
- Personal canonical Entities: 0

The Proposal remains intentionally pending. A human can inspect it with:

```bash
knowledge-os-review show \
  proposal:61418232f130d764b4484e64c3dc3409006676299bc9e7e9433d6fa6d81646b1
```

Approval or rejection must be a separate explicit `--yes` decision. This record does not treat the
extraction as truth and does not authorize automatic promotion.

## Date-precision Decision follow-up

After Governance-v7 closed the measured date-precision gap, two accepted/current statements were
submitted through the installed MCP adapter as pending Decision Proposals:

- `proposal:d2f8078d70ef6dfd9984474c3dcad87497c993312e1880f6cf91a9cff7531989` —
  personal knowledge storage is first; one exact review-record Chunk.
- `proposal:5179b295fd0740f20f60c2632678d789491200f2541dc5b4daf700378d3b90d1` —
  use Notion and Google Drive with artifact-specific authority; two exact policy/review Chunks.

Both preserve `decided_on=2026-09-02` rather than claiming an unsupported time. An exact retry of
the second payload returned the same ID with `unchanged=true`. The authorized Decision inbox
contains exactly two items. The personal workspace now has three pending Proposals total—one
Governance-v6 assertion seed and two Governance-v7 Decisions—but still has zero canonical
Decisions, Assertions, and Entities.

Recovery set `20260905T141910Z-a910dcf3` binds this three-Proposal state to Git commit `5d93067`
over a 4.90-second capture window. Neo4j and SQLite SHA-256 checks, SQLite integrity, and Neo4j
offline archive consistency all passed. The private artifacts remain outside Git.

## Recovery point

After commit `4d99d91`, the first recovery invocation failed while calling Neo4j's official backup
command and automatically removed its staging directory. Doctor still passed 35/35. Re-running the
same Neo4j backup command into an isolated temporary directory succeeded, showing a transient
capture failure rather than graph corruption; the diagnostic artifact was then removed exactly.

The subsequent recovery set `20260905T141347Z-ec53d7e0` captured the pending personal Proposal with
Neo4j and SQLite over a 4.91-second bounded window. Both SHA-256 checks, SQLite integrity, and Neo4j
offline archive consistency passed. The private artifacts remain in ignored local storage.
