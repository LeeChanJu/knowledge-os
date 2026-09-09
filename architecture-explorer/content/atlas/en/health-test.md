Check missing schema, incorrect metadata hashes, current-contract compatibility and multi-node supersession cycles. Passing F1 does not close these complete F3 scopes.

<!-- DEPTH -->

### Why this responsibility exists

Detect violations without normalizing away history.

### Inputs and outputs

Input: Existing graph, migration files, operations store.

Output: Bounded integrity report.

### What must be preserved

- No repair state.
- Detection is separate from correction. F3 has unresolved coverage and compatibility cases.

### Follow the example

A successful note search can coexist with missing lineage or an incorrect hash. Structural Doctor checks differ from answer quality.

### Avoid this misconception

Detection is separate from correction. F3 has unresolved coverage and compatibility cases.
