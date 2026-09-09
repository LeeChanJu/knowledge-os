The document identity groups revisions of the same note. Equal titles do not automatically merge documents across source systems.

<!-- DEPTH -->

### Why this responsibility exists

Provide the lifecycle and CURRENT_VERSION anchor without overwriting historical evidence.

### Inputs and outputs

Input: Source identity plus external document ID.

Output: Stable document ID, current-version pointer, version history.

### What must be preserved

- Document identity, active/deleted lifecycle, current-version relationship.
- Identity is workspace/source scoped. A tombstone retains version history; direct updates require the current version precondition.

### Follow the example

A renamed note still belongs to the same source document. That is why document identity differs from the identity of its observed state.

### Avoid this misconception

Identity is workspace/source scoped. A tombstone retains version history; direct updates require the current version precondition.
