## Who changes the original?

```diagram
Approved request
↓ Separately authorized executor
Allowed Notion location → inspect outcome
```

An executor with separate authority and policy performs the outside write. Attempting execution differs from confirming success at the source. Duplicate prevention and ambiguous outcomes have explicit verification limits and open findings.

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
