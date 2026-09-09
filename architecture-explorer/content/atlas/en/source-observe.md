A connector observes authorized content, permissions and revisions. For example, it reads this note from a Drive folder into a change manifest. Read permission differs from permission to modify the source.

<!-- DEPTH -->

### Why this responsibility exists

Complete the inventory before declaring deletions. Write local connector checkpoints only after the graph commit succeeds.

### Inputs and outputs

Input: Provider inventory, source authorization, previous connector checkpoint.

Output: Deterministic UPSERT/TOMBSTONE manifest and proposed next checkpoint.

### What must be preserved

- Adapter-local checkpoint files; no canonical semantic truth.
- Retries must reproduce the same semantic state. Provider failures must not be interpreted as an empty successful inventory.

### Follow the example

A failed folder listing must not tombstone an unseen note. Establish inventory completeness before building changes and persist the checkpoint after commit.

### Avoid this misconception

Retries must reproduce the same semantic state. Provider failures must not be interpreted as an empty successful inventory.
