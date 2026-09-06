# Meeting transcript ingestion — 2026-09-05

## Measured gaps

The local file connector did not recognize the two common text transcript formats, and its sync-run
identity used only the new inventory cursor. After an initial successful run, a later unchanged run
had the same run ID but a different `expected_previous_cursor`, producing a different manifest hash
for an already bound identity. The Notion connector shared the same collision pattern.

## Minimum extension

The existing connector now accepts UTF-8 WebVTT and SRT without stripping timestamps or speaker
labels and permits an explicit `source_type`. Its state is additionally bound to workspace, source
type, and connector ID. Both file and Notion run identities now include previous and new cursors;
no service contract or graph schema changed.

## Verification

- Fixtures prove byte-to-text preservation for VTT/SRT, deterministic manifests, source-type
  propagation, state identity binding, and stable retry/run identities.
- A real installed CLI imported a VTT fixture through the live Neo4j transaction path in isolated
  workspace `it-meeting-ingestion-v2`.
- A second unchanged snapshot completed without manifest identity conflict, retained the same
  content cursor, used a distinct follow-up run ID, and left exactly one DocumentVersion and Chunk.
- The stored Chunk retained both its timestamp and speaker text.
- Seven exact fixture nodes were deleted and the integration workspace count returned to zero. Its
  operations database and source/state files were temporary and removed automatically.
- Ruff and all 70 unit tests passed before documentation completion.

This proves transcript-file ingestion and replay safety. It does not prove direct Zoom, Teams,
Meet, audio transcription, summarization, or extracted meeting knowledge quality.
