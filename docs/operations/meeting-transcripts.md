# Meeting transcript ingestion

Standard WebVTT (`.vtt`) and SubRip (`.srt`) transcripts use the existing local file connector and
atomic manifest-v2 path. The transcript file remains the System of Record. Timestamp, cue, speaker,
and text lines are retained verbatim instead of being normalized into lossy meeting objects.

```bash
knowledge-os-ingest-files /absolute/path/to/meeting-transcripts \
  --state data/meeting-transcripts-state.json \
  --source-id personal-meeting-transcripts \
  --source-type meeting_transcripts \
  --connector-id meeting-transcript-files-v1 \
  --owner local-user \
  --acl local-user
```

The state file is bound to the resolved directory, workspace, source external ID, source type, and
connector ID. Reusing it across any of those identities fails before graph mutation. Raw file
SHA-256 is the source revision. A successful run writes state only after the Neo4j transaction;
missing transcripts become evidence-preserving tombstones on the next complete snapshot.

Run identity binds the previous committed cursor and the newly observed cursor. The initial import
and a later unchanged inventory therefore cannot reuse one run ID with two different manifest
hashes. Repeating either exact attempt remains deterministic, while a normal no-content-change sync
completes without creating a second DocumentVersion.

This adapter does not transcribe audio, infer speakers, summarize meetings, or promote decisions.
Those are separate extraction capabilities: any derived Decision or Event must first be an
Evidence-linked Proposal and pass the normal human review boundary.
