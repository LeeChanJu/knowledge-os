## Where is the original, and who may read it?

```diagram
Supporting passage → document at that time
↓ Record linking to the source document
☁️ Drive / Notion / Files · originals stay here
```

Originals remain in systems outside Knowledge OS. Even traceable historical material is not returned without current permission to read. Preservation does not grant permanent access.

<!-- DEPTH -->

### Why this responsibility exists

Bind source identity and checkpoint state so retries and source catalogs refer to the same collection.

### Inputs and outputs

Input: Workspace, source type, opaque external ID, connector ID.

Output: Stable Source identity and authorized catalog/checkpoint summaries.

### What must be preserved

- Source node, connector binding, committed sync cursor.
- A different connector cannot silently take ownership. Item ingestion does not independently advance a completed-run checkpoint.

### Follow the example

Two connectors may expose notes with the same title. Identity includes workspace, source and connector context instead of merging by title.

### Avoid this misconception

A different connector cannot silently take ownership. Item ingestion does not independently advance a completed-run checkpoint.
