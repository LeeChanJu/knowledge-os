Preserve the authorized action boundary when implementation technology changes. MCP and REST are adapters to these contracts. Consult the registry for exact inputs, outputs and restrictions.

<!-- DEPTH -->

### Why this responsibility exists

Define the stable architectural boundary independently of REST, MCP, storage adapters or UI.

### Inputs and outputs

Input: Explicit capability/policy, principals and source-system authorization.

Output: Approved request, bounded claim and immutable execution records.

### What must be preserved

- Action contract version.
- External writes occur only through separately authenticated, authorized adapters.

### Follow the example

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

### Avoid this misconception

External writes occur only through separately authenticated, authorized adapters.
