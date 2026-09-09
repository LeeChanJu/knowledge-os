Reads relationships within a bounded scope. Do not assume unrestricted natural-language-to-graph queries.

<!-- DEPTH -->

### Why this responsibility exists

Connect retrieved evidence to approved semantic relationships while preserving access and temporal constraints.

### Inputs and outputs

Input: Entity/record IDs or discovery query, access context, optional as-of time.

Output: Bounded authorized canonical records and traced discovery results.

### What must be preserved

- No separate database; retrieval traces belong to the operations store.
- Known IDs do not bypass ACLs. Canonical reads require all supporting evidence to remain accessible.

### Follow the example

Follow accepted relations to read neighbors. The graph does not automatically invent and persist relationships that were never recorded.

### Avoid this misconception

Known IDs do not bypass ACLs. Canonical reads require all supporting evidence to remain accessible.
