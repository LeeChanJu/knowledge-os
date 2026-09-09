Knowledge OS returns support through the adapter. Returning material differs from composing an answer.

<!-- DEPTH -->

### Why this responsibility exists

Define the stable architectural boundary independently of REST, MCP, storage adapters or UI.

### Inputs and outputs

Input: Stable Chunk IDs and current access context.

Output: Bounded all-or-nothing evidence bundles.

### What must be preserved

- Evidence contract version.
- Historical ACL snapshots never replace current authorization.

### Follow the example

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

### Avoid this misconception

Historical ACL snapshots never replace current authorization.
