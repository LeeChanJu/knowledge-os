Even an excluded document is a failure if returned without authorization. Evaluate retrieval quality together with access control.

<!-- DEPTH -->

### Why this responsibility exists

Record operational evidence without becoming canonical knowledge or leaking raw principals and source payloads into error records.

### Inputs and outputs

Input: Adapter timings, access-bound trace IDs, evaluation cases and feedback.

Output: Operational rows, measured retrieval metrics and diagnostic records.

### What must be preserved

- Evidence of operations in the existing local SQLite store.
- Authorization-denial cases must fail on leaked results before exclusions; F7 remains open. Cross-store graph/audit recovery is not a distributed transaction; F8 remains open.

### Follow the example

Consider a graph commit that succeeds while its audit fails. Report the outcome truthfully and reconcile only the missing audit on retry.

### Avoid this misconception

Authorization-denial cases must fail on leaked results before exclusions; F7 remains open. Cross-store graph/audit recovery is not a distributed transaction; F8 remains open.
