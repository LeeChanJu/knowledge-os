Reproduce the failure, make the smallest correction and retest affected scope. This documentation task neither fixes production code nor closes findings.

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
