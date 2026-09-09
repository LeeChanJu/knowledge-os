Preserve the knowledge reads boundary when implementation technology changes. MCP and REST are adapters to these contracts. Consult the registry for exact inputs, outputs and restrictions.

<!-- DEPTH -->

### Why this responsibility exists

Define the stable architectural boundary independently of REST, MCP, storage adapters or UI.

### Inputs and outputs

Input: Record IDs, query context, ontology/prompt names.

Output: Authorized semantic records and versioned extraction context.

### What must be preserved

- Knowledge contract version.
- Knowledge requires approved provenance; adapters cannot redefine canonical truth.

### Follow the example

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

### Avoid this misconception

Knowledge requires approved provenance; adapters cannot redefine canonical truth.
