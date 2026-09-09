Preserve the governed review boundary when implementation technology changes. MCP and REST are adapters to these contracts. Consult the registry for exact inputs, outputs and restrictions.

<!-- DEPTH -->

### Why this responsibility exists

Define the stable architectural boundary independently of REST, MCP, storage adapters or UI.

### Inputs and outputs

Input: Evidence-backed candidates and explicit reviewer context.

Output: Immutable decisions and approved canonical records.

### What must be preserved

- Governance contract version.
- Proposal → validation → Approval/rejection → canonical graph.

### Follow the example

Changing the note’s provider does not redefine source identity, evidence or approval. Revisit contracts and design when a measured gap justifies it.

### Avoid this misconception

Proposal → validation → Approval/rejection → canonical graph.
