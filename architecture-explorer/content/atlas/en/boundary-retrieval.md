Preserve the bounded retrieval boundary when implementation technology changes. MCP and REST are adapters to these contracts. Consult the registry for exact inputs, outputs and restrictions.

<!-- DEPTH -->

### Why this responsibility exists

Define the stable architectural boundary independently of REST, MCP, storage adapters or UI.

### Inputs and outputs

Input: Queries, exact model/version when semantic, authenticated access.

Output: Bounded ranked context, capabilities, traces and evaluation evidence.

### What must be preserved

- Retrieval contract version.
- Ranking and vector search do not bypass evidence authorization.

### Follow the example

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

### Avoid this misconception

Ranking and vector search do not bypass evidence authorization.
