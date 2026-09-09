OpsStore writes operations records to SQLite. It is not one transaction with the Neo4j commit, so code must distinguish and reconcile outcomes.

<!-- DEPTH -->

### Why this responsibility exists

Keep local operational evidence outside the canonical context graph with minimal infrastructure.

### Inputs and outputs

Input: Bounded application observations and trace-linked evaluation/feedback.

Output: Operational diagnostics and online backup artifact.

### What must be preserved

- Operations tables only; no source document or canonical knowledge store.
- Operations data cannot promote canonical truth. Graph commits and SQLite writes do not form one atomic distributed transaction.

### Follow the example

Consider a graph commit that succeeds while its audit fails. Report the outcome truthfully and reconcile only the missing audit on retry.

### Avoid this misconception

Operations data cannot promote canonical truth. Graph commits and SQLite writes do not form one atomic distributed transaction.
