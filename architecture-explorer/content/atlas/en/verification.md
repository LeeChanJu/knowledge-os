Check exactly what ran, on which revision and environment. Scoped passing results do not verify the entire system.

<!-- DEPTH -->

### Why this responsibility exists

Preserve the accepted verification scope and its dependency coverage without turning it into a subsystem-wide claim.

### Inputs and outputs

Input: No input scope is specified here; inspect the linked contract.

Output: No output scope is specified here.

### What must be preserved

- Documentation of the claim; no runtime data.
- Verification applies only to the declared scope and pinned dependencies.

### Follow the example

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

### Avoid this misconception

Verification applies only to the declared scope and pinned dependencies.
