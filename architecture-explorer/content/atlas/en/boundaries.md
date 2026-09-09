Changing a store, LLM or MCP adapter does not redefine the six contracts. Evidence lineage and approval rules constrain implementation choices.

<!-- DEPTH -->

### Why this responsibility exists

Define the stable architectural boundary independently of REST, MCP, storage adapters or UI.

### Inputs and outputs

Input: Provider observations with stable identity and authorization.

Output: Versioned evidence and committed source-run history.

### What must be preserved

- Source contract version; runtime data lives in Neo4j.
- Provider retries must not duplicate semantic state.

### Follow the example

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

### Avoid this misconception

Provider retries must not duplicate semantic state.
